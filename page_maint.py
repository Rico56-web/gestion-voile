"""
page_maint.py
==============
Maintenance & Vidange : tableau de bord vidange, suivi carburant,
interventions, révisions moteur, filtres et export Excel.

Seule chose migrée par rapport à l'ancien code : les heures moteur
(pour l'alerte vidange) viennent maintenant de etapes_v2.json (champ
compteur_moteur) au lieu de l'ancien logbook.json. maintenance.json et
carburant.json restent inchangés — ce sont des journaux indépendants du
modèle contacts/croisières, pas besoin de les migrer.

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, FACT, RELANCES, LOG, MEMOS, ARCHIVES.
"""
import io
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from modele_voile import derniere_lecture_compteur, parser_date_flexible, generer_echeancier


def to_f(v):
    """Nettoyage/conversion numérique tolérant (même comportement que
    l'ancien to_f de app_voile1.py)."""
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).replace("€", "").replace(" ", "").replace(",", ".").strip())
    except (ValueError, TypeError):
        return 0.0


def _bouton_imprimer_fiche_maint(titre, date_str, details, statut):
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 30px; color: #2C3E50; }}
            .header {{ border-bottom: 3px solid #2980B9; padding-bottom: 10px; margin-bottom: 20px; }}
            .statut {{ display: inline-block; padding: 5px 15px; border-radius: 20px; background: #eee; font-weight: bold; }}
            .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; white-space: pre-wrap; font-size: 1.1em; }}
        </style>
    </head>
    <body>
        <div class='header'>
            <h1>🛠️ {titre}</h1>
            <p><b>Date :</b> {date_str} | <span class='statut'>État : {statut}</span></p>
        </div>
        <div class='content'>{details}</div>
        <p style='font-size: 0.8em; color: gray; margin-top: 40px;'>Vesta Skipper 2026</p>
    </body>
    </html>
    """
    js = f"""
    <script>
    function printFiche() {{
        var win = window.open('', '', 'height=600, width=800');
        win.document.write({repr(html_content)});
        win.document.close();
        setTimeout(function(){{ win.print(); }}, 500);
    }}
    </script>
    <button onclick="printFiche()" style="padding: 5px 10px; border-radius: 5px; cursor: pointer; background: #ffffff; border: 1px solid #d1d5db; width: 100%;">
        🖨️ Imprimer
    </button>
    """
    components.html(js, height=45)


FREQUENCES = {"mensuelle": "Mensuelle", "trimestrielle": "Trimestrielle", "annuelle": "Annuelle"}


def _section_echeancier(df_m, sauvegarder_maintenance):
    """Génère d'un coup toutes les fiches d'une charge fixe récurrente
    pour l'année (ex: 12 mensualités de port), avec aperçu avant
    confirmation. Les fiches générées sont 'À prévoir', à cocher 'Fait'
    au fur et à mesure comme n'importe quelle fiche MAINT existante."""
    with st.expander("📅 Générer un échéancier annuel (charges fixes)"):
        st.caption("Génère d'un coup toutes les échéances de l'année pour une charge récurrente (port, assurance...).")

        with st.form("form_echeancier"):
            c1, c2 = st.columns(2)
            libelle = c1.text_input("Libellé", placeholder="ex: Place de port Crouesty")
            type_charge = c2.selectbox("Catégorie", ["Port", "Assurances", "Maintenance", "Sécurité", "Autres"])

            c3, c4, c5 = st.columns(3)
            montant = c3.number_input("Montant par échéance (€)", min_value=0.0, step=10.0)
            frequence = c4.selectbox("Fréquence", list(FREQUENCES.keys()), format_func=lambda f: FREQUENCES[f])
            nb_echeances = c5.number_input("Nombre d'échéances", min_value=1, max_value=36, value=12, step=1)

            date_depart = st.date_input("Date de la 1ère échéance", format="DD/MM/YYYY")

            previsualiser = st.form_submit_button("👁️ Prévisualiser", use_container_width=True)

        if previsualiser:
            if not libelle.strip() or montant <= 0:
                st.error("Merci de renseigner un libellé et un montant supérieur à 0.")
            else:
                st.session_state["echeancier_preview"] = generer_echeancier(
                    libelle.strip(), montant, frequence, date_depart, int(nb_echeances), type_charge,
                )
                st.rerun()

        preview = st.session_state.get("echeancier_preview")
        if preview:
            st.markdown(f"**Aperçu : {len(preview)} fiche(s) seront créées**")
            st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)
            cb1, cb2 = st.columns(2)
            if cb1.button("✅ Confirmer et créer ces fiches", use_container_width=True, type="primary"):
                df_maj = pd.concat([df_m, pd.DataFrame(preview)], ignore_index=True)
                sauvegarder_maintenance(df_maj)
                st.session_state.pop("echeancier_preview")
                st.toast(f"{len(preview)} fiche(s) créée(s) !", icon="📅")
                st.rerun()
            if cb2.button("❌ Annuler", use_container_width=True):
                st.session_state.pop("echeancier_preview")
                st.rerun()


def afficher_page_maint(charger_maintenance, sauvegarder_maintenance,
                         charger_carburant, sauvegarder_carburant,
                         charger_etapes, charger_params, sauvegarder_params):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    df_m = charger_maintenance()
    if not df_m.empty:
        # Normalise le format de date (anciennes fiches en millisecondes,
        # nouvelles en texte jj/mm/aaaa) vers du texte jj/mm/aaaa partout.
        # Comme conséquence positive : le prochain enregistrement (même un
        # simple changement de statut) réécrit le fichier avec ce format
        # propre, donc le fichier s'auto-corrige progressivement.
        df_m["Date"] = df_m["Date"].apply(
            lambda v: d.strftime("%d/%m/%Y") if (d := parser_date_flexible(v)) else str(v)
        )
    etapes = charger_etapes()
    releve_h = derniere_lecture_compteur(etapes)

    params = charger_params()
    if "prochaine_vidange" not in params:
        params["prochaine_vidange"] = 2500.0
        sauvegarder_params(params)

    if "maint_edit_id" not in st.session_state:
        st.session_state.maint_edit_id = None
    if "show_form_classique" not in st.session_state:
        st.session_state.show_form_classique = False
    if "show_form_vidange" not in st.session_state:
        st.session_state.show_form_vidange = False

    st.markdown('<h2 style="text-align:center;">🛠️ Maintenance & Vidange</h2>', unsafe_allow_html=True)

    _section_echeancier(df_m, sauvegarder_maintenance)

    # --- Tableau de bord vidange ---
    heures_restantes = params["prochaine_vidange"] - releve_h
    color_v = "#2e7d32" if heures_restantes > 15 else "#c62828"

    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.markdown(f"""
            <div style="background-color: {color_v}15; border: 2px solid {color_v}; padding: 15px; border-radius: 10px; text-align: center;">
                <h3 style="margin:0; color: {color_v};">{heures_restantes:.1f} h restantes</h3>
                <p style="margin:0;">Cible vidange : <b>{params['prochaine_vidange']:.1f} h</b> | Actuel (compteur) : {releve_h:.1f} h</p>
            </div>
        """, unsafe_allow_html=True)
    with col_v2:
        new_target = st.number_input("Ajuster cible (h)", value=float(params["prochaine_vidange"]), step=10.0)
        if new_target != params["prochaine_vidange"]:
            params["prochaine_vidange"] = new_target
            sauvegarder_params(params)
            st.rerun()

    st.divider()

    # --- Suivi carburant ---
    st.markdown("### ⛽ Suivi Carburant")
    df_carb = charger_carburant()

    col_c1, col_c2, col_c3 = st.columns(3)
    if not df_carb.empty:
        total_l = to_f(df_carb["Litres"].sum())
        total_e = to_f(df_carb["Prix"].sum())
        dernier_pu = to_f(df_carb["PU"].iloc[-1]) if "PU" in df_carb.columns else 0.0
        col_c1.metric("Total Litres", f"{total_l:.0f} L")
        col_c2.metric("Total Dépensé", f"{total_e:.2f} €")
        col_c3.metric("Dernier Prix/L", f"{dernier_pu:.3f} €")

    with st.expander("➕ Enregistrer un plein / Voir l'historique", expanded=False):
        with st.form("form_fuel_v2026"):
            c1, c2, c3 = st.columns(3)
            d_f = c1.date_input("Date du plein", format="DD/MM/YYYY")
            l_f = c2.number_input("Litres", min_value=0.0, step=10.0)
            p_f = c3.number_input("Total TTC (€)", min_value=0.0, step=10.0)
            if st.form_submit_button("Enregistrer le plein", use_container_width=True):
                if l_f > 0:
                    new_f = {"Date": d_f.strftime("%d/%m/%Y"), "Litres": l_f, "Prix": p_f, "PU": round(p_f / l_f, 3)}
                    df_carb = pd.concat([df_carb, pd.DataFrame([new_f])], ignore_index=True)
                    sauvegarder_carburant(df_carb)
                    st.toast("Plein enregistré !", icon="⛽")
                    st.rerun()
                else:
                    st.error("Le nombre de litres doit être supérieur à 0.")
        if not df_carb.empty:
            st.dataframe(df_carb.tail(5), use_container_width=True, hide_index=True)

    # --- Boutons d'appel ---
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("🔧 NOUVELLE INTERVENTION", use_container_width=True):
        st.session_state.show_form_classique = True
        st.session_state.show_form_vidange = False
        st.rerun()
    if col_btn2.button("🛢️ RÉVISION MOTEUR", use_container_width=True):
        st.session_state.show_form_vidange = True
        st.session_state.show_form_classique = False
        st.rerun()

    # --- Formulaire classique ---
    if st.session_state.show_form_classique:
        with st.form("form_new_maint"):
            st.subheader("🔧 Nouvelle Intervention")
            f_obj = st.text_input("Désignation")
            c1, c2, c3 = st.columns(3)
            f_d = c1.date_input("Date", datetime.now(), format="DD/MM/YYYY")
            f_m = c2.number_input("Montant (€)", min_value=0.0, step=10.0)
            f_t = c3.selectbox("Catégorie", ["Maintenance", "Sécurité", "Port", "Assurances", "Autres"])
            f_notes = st.text_area("Notes détaillées")
            f_statut = st.selectbox("Statut", ["À prévoir", "Fait"])
            b_col1, b_col2 = st.columns(2)
            if b_col1.form_submit_button("✅ ENREGISTRER", use_container_width=True, type="primary"):
                new_row = {"Date": f_d.strftime("%d/%m/%Y"), "Objet": f_obj, "M_Num": f_m,
                           "Statut": f_statut, "Type": f_t, "Notes": f_notes}
                df_m = pd.concat([df_m, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_maintenance(df_m)
                st.session_state.show_form_classique = False
                st.rerun()
            if b_col2.form_submit_button("❌ FERMER", use_container_width=True):
                st.session_state.show_form_classique = False
                st.rerun()

    # --- Formulaire révision moteur ---
    if st.session_state.show_form_vidange:
        with st.form("form_vidange_moteur"):
            st.subheader("🛢️ Révision Moteur")
            c_v1, c_v2 = st.columns(2)
            v_date = c_v1.date_input("Date", datetime.now(), format="DD/MM/YYYY")
            v_heures = c_v2.number_input("Heures moteur actualisées", value=float(releve_h))
            st.markdown("**Check-list révision :**")
            col_c1, col_c2, col_c3 = st.columns(3)
            chk_huile = col_c1.checkbox("Vidange Huile")
            chk_f_huile = col_c1.checkbox("Filtre Huile")
            chk_f_gasoil = col_c2.checkbox("Filtre Gasoil")
            chk_f_pre = col_c2.checkbox("Pré-filtre")
            chk_courroie = col_c3.checkbox("Courroies")
            chk_impeller = col_c3.checkbox("Impeller")
            v_cout = st.number_input("Coût fournitures (€)", min_value=0.0, step=5.0)
            v_notes = st.text_area("Observations additionnelles")
            inc_h = st.selectbox("Échéance prochaine vidange (+h)", [50, 100, 150, 200], index=1)
            bv_col1, bv_col2 = st.columns(2)
            if bv_col1.form_submit_button("✅ VALIDER LA RÉVISION", use_container_width=True, type="primary"):
                travaux = [t for t, c in zip(
                    ["Huile", "F-Huile", "F-Gasoil", "Pré-filtre", "Courroies", "Impeller"],
                    [chk_huile, chk_f_huile, chk_f_gasoil, chk_f_pre, chk_courroie, chk_impeller]) if c]
                details = f"Révision à {v_heures}h. Travaux validés : {', '.join(travaux)}. Obs : {v_notes}"
                new_row = {"Date": v_date.strftime("%d/%m/%Y"), "Objet": f"RÉVISION MOTEUR ({v_heures}h)",
                           "M_Num": v_cout, "Statut": "Fait", "Type": "Maintenance", "Notes": details}
                params["prochaine_vidange"] = round(v_heures + inc_h, 1)
                sauvegarder_params(params)
                df_m = pd.concat([df_m, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_maintenance(df_m)
                st.session_state.show_form_vidange = False
                st.rerun()
            if bv_col2.form_submit_button("❌ FERMER", use_container_width=True):
                st.session_state.show_form_vidange = False
                st.rerun()

    # --- Filtres & affichage ---
    st.divider()
    col_menu1, col_menu2, col_menu3 = st.columns([2, 1.2, 1.2])
    filter_statut = col_menu1.radio("Filtre statut :", ["Tout", "⏳ À faire", "✅ Fait"], horizontal=True)
    mode_m = col_menu2.radio("Fenêtre :", ["À ce jour", "Année complète"], horizontal=True)
    sel_y = col_menu3.selectbox("Sélection année :", [2025, 2026, 2027], index=1)

    if not df_m.empty:
        df_m["dt_maint"] = pd.to_datetime(df_m["Date"], dayfirst=True, errors="coerce")
        df_filtre = df_m[df_m["dt_maint"].dt.year == sel_y].copy()

        if mode_m == "À ce jour":
            aujourdhui = pd.Timestamp.now().normalize()
            df_filtre = df_filtre[df_filtre["dt_maint"] <= aujourdhui]

        if filter_statut == "⏳ À faire":
            df_filtre = df_filtre[df_filtre["Statut"] == "À prévoir"]
        elif filter_statut == "✅ Fait":
            df_filtre = df_filtre[df_filtre["Statut"] == "Fait"]

        df_filtre = df_filtre.sort_values("dt_maint", ascending=False)

        if df_filtre.empty:
            st.info("Aucune fiche de maintenance ne correspond aux critères.")
        else:
            for idx, row in df_filtre.iterrows():
                est_fait = row["Statut"] == "Fait"
                border_color = "#27AE60" if est_fait else "#F39C12"
                bg_color = "#EAFAF1" if est_fait else "#FEF5E7"
                icon_stat = "✅" if est_fait else "⏳"
                couleurs_type = {
                    "Maintenance": "#3498DB", "Sécurité": "#E74C3C", "Port": "#9B59B6",
                    "Assurances": "#16A085", "Autres": "#7F8C8D",
                }
                couleur_type = couleurs_type.get(row.get("Type", "Maintenance"), "#7F8C8D")

                if st.session_state.maint_edit_id == idx:
                    with st.form(key=f"edit_maint_{idx}"):
                        e_obj = st.text_input("Désignation", value=row["Objet"])
                        c1, c2 = st.columns(2)
                        e_dat = c1.text_input("Date", value=row["Date"])
                        e_mon = c2.number_input("Montant (€)", value=float(to_f(row["M_Num"])))
                        e_not = st.text_area("Notes", value=row.get("Notes", ""))
                        e_sta = st.selectbox("Statut", ["À prévoir", "Fait"], index=1 if est_fait else 0)
                        cb1, cb2 = st.columns(2)
                        if cb1.form_submit_button("✅ SAUVER"):
                            df_m.at[idx, "Objet"] = e_obj
                            df_m.at[idx, "Date"] = e_dat
                            df_m.at[idx, "M_Num"] = e_mon
                            df_m.at[idx, "Notes"] = e_not
                            df_m.at[idx, "Statut"] = e_sta
                            sauvegarder_maintenance(df_m.drop(columns=["dt_maint"], errors="ignore"))
                            st.session_state.maint_edit_id = None
                            st.rerun()
                        if cb2.form_submit_button("❌ ANNULER"):
                            st.session_state.maint_edit_id = None
                            st.rerun()
                else:
                    st.markdown(f"""
                        <div style="background-color:{bg_color}; border-left: 10px solid {border_color}; padding: 15px; border-radius: 10px; margin-bottom: 5px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: bold; font-size: 1.1em;">{row['Objet']}</span>
                                <span style="background:{border_color}; color:white; border-radius:12px; padding:2px 10px; font-size:0.75rem; font-weight:bold;">{icon_stat} {row['Statut']}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
                                <span style="background:{couleur_type}; color:white; border-radius:10px; padding:2px 10px; font-size:0.75rem;">{row.get('Type', 'Maintenance')}</span>
                                <span style="color: #555; font-size:0.85rem;">📅 {row['Date']}</span>
                            </div>
                            <div style="margin-top:8px; font-size:1.05rem; font-weight:bold; color:#2c3e50;">💰 {row['M_Num']} €</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if row.get("Notes"):
                        st.caption(f"📝 {row['Notes']}")

                    bc1, bc2, bc3, bc4 = st.columns(4)
                    if bc1.button("✏️ Modif", key=f"ed_m_{idx}"):
                        st.session_state.maint_edit_id = idx
                        st.session_state.show_form_classique = False
                        st.session_state.show_form_vidange = False
                        st.rerun()
                    with bc2:
                        _bouton_imprimer_fiche_maint(row["Objet"], row["Date"], row.get("Notes", "N/A"), row["Statut"])
                    label_toggle = "⏳ À prévoir" if est_fait else "✅ Marquer FAIT"
                    if bc3.button(label_toggle, key=f"st_m_{idx}"):
                        df_m.at[idx, "Statut"] = "À prévoir" if est_fait else "Fait"
                        sauvegarder_maintenance(df_m.drop(columns=["dt_maint"], errors="ignore"))
                        st.rerun()
                    if bc4.button("🗑️ Suppr", key=f"pre_m_{idx}"):
                        df_m = df_m.drop(idx)
                        sauvegarder_maintenance(df_m.drop(columns=["dt_maint"], errors="ignore"))
                        st.rerun()

    # --- Export Excel ---
    if not df_m.empty:
        st.divider()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_m.drop(columns=["dt_maint"], errors="ignore").to_excel(writer, index=False)
        st.download_button("📥 Télécharger Historique Complet (Excel)", data=buffer.getvalue(),
                            file_name="Maintenance_Vesta_Skipper.xlsx", use_container_width=True)
