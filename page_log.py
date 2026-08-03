"""
page_log.py
============
Livre de bord (LOG) : saisie/modification/suppression d'étapes, vue
groupée par navigation, export CSV.

Différences par rapport à l'ancien code :
- Lit/écrit etapes_v2.json (au lieu de logbook.json)
- Le compteur moteur (comme avant) reste en Départ/Arrivée ; les MILLES
  sont simplifiés en un seul champ "Milles parcourus" (décision du
  03/08/2026 — etapes_v2 ne garde qu'une durée, pas de compteur cumulé
  pour les milles)
- Chaque étape est reliée automatiquement à une croisière existante si sa
  date tombe dans la plage [date_debut, date_fin] d'une croisière
  (même logique que la migration d'origine)
- Le nom de navigation suggéré par défaut reprend la dernière étape
  PASSÉE si elle date de moins de 5 jours (continuité probable)

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, FACT, RELANCES, MAINT, MEMOS, ARCHIVES.
"""
from datetime import date, datetime

import streamlit as st

from modele_voile import (
    generer_id_etape, trouver_croisiere_id_pour_date, suggestion_nom_navigation,
    ajouter_etape, modifier_etape, supprimer_etape, etapes_groupees_par_navigation,
    derniere_lecture_compteur, parse_date_eu,
)


def _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="creation", etape_id=None):
    """Formulaire unique pour créer ou modifier une étape."""
    title = "➕ NOUVELLE ÉTAPE QUOTIDIENNE" if mode == "creation" else "📝 MODIFIER L'ÉTAPE"

    if mode == "edition" and etape_id is not None:
        e = next(x for x in etapes if x["id"] == etape_id)
        val_date = e.get("date", "")
        val_nav = e.get("navigation", "")
        val_equi = e.get("coequipiers_texte", "")
        val_meteo = e.get("meteo", "")
        val_notes = e.get("notes", "")
        val_mot_dep = float(e.get("compteur_moteur", 0.0)) - float(e.get("heures_moteur", 0.0))
        val_mot_arr = float(e.get("compteur_moteur", 0.0))
        val_milles = float(e.get("milles", 0.0))
        val_voile = float(e.get("heures_voile", 0.0))
    else:
        aujourdhui = date.today()
        last_mot = derniere_lecture_compteur(etapes)
        val_date = datetime.now()
        val_nav = suggestion_nom_navigation(etapes, aujourdhui)
        val_equi = ""
        val_meteo = ""
        val_notes = ""
        val_mot_dep = last_mot
        val_mot_arr = last_mot
        val_milles = 0.0
        val_voile = 0.0

    with st.expander(title, expanded=True):
        with st.form(key=f"form_log_{mode}"):
            c1, c2 = st.columns(2)
            if mode == "creation":
                f_date = c1.date_input("Date", val_date)
            else:
                f_date = c2.text_input("Date", value=val_date)
            f_nav = c2.text_input("Nom du Voyage / Croisière", value=val_nav, placeholder="ex: Gijón 2026")

            f_equipage = st.text_area("Équipage / Rôle", value=val_equi, height=60)

            cm1, cm2 = st.columns(2)
            f_meteo = cm1.text_input("Météo (Vent/Mer)", value=val_meteo)
            f_notes = cm2.text_area("Observations / Escale", value=val_notes, height=60)

            st.divider()
            col1, col2, col3 = st.columns(3)
            m_dep = col1.number_input("Moteur Départ (h)", value=val_mot_dep, format="%.1f", step=0.5)
            m_arr = col2.number_input("Moteur Arrivée (h)", value=val_mot_arr, format="%.1f", step=0.5)
            h_voile = col3.number_input("Heures Voile (h)", value=val_voile, format="%.1f", step=0.5)

            f_milles = st.number_input("Milles parcourus cette étape", value=val_milles, format="%.1f", step=1.0)

            b1, b2 = st.columns(2)
            if b1.form_submit_button("💾 ENREGISTRER L'ÉTAPE", use_container_width=True, type="primary"):
                date_str = f_date.strftime("%d/%m/%Y") if mode == "creation" else f_date
                d_obj = parse_date_eu(date_str)
                croisiere_id = trouver_croisiere_id_pour_date(croisieres, d_obj) if d_obj else None

                champs = {
                    "date": date_str,
                    "navigation": f_nav,
                    "coequipiers_texte": f_equipage,
                    "meteo": f_meteo,
                    "notes": f_notes,
                    "compteur_moteur": m_arr,
                    "heures_moteur": round(max(0.0, m_arr - m_dep), 2),
                    "heures_voile": h_voile,
                    "milles": f_milles,
                    "croisiere_id": croisiere_id,
                }

                if mode == "creation":
                    nouvelle = {"id": generer_id_etape(), "carburant": None, **champs}
                    etapes_maj = ajouter_etape(etapes, nouvelle)
                else:
                    etapes_maj = modifier_etape(etapes, etape_id, champs)
                    st.session_state.log_edit_id = None

                sauvegarder_etapes(etapes_maj)
                st.session_state.log_saisie_ouverte = False
                st.rerun()

            if b2.form_submit_button("❌ ANNULER", use_container_width=True):
                st.session_state.log_saisie_ouverte = False
                st.session_state.log_edit_id = None
                st.rerun()


def afficher_page_log(charger_etapes, sauvegarder_etapes, charger_croisieres):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    st.markdown(
        '<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;">'
        "<h1>📖 Livre de Bord & Statistiques</h1></div>",
        unsafe_allow_html=True,
    )

    etapes = charger_etapes()
    croisieres = charger_croisieres()

    if "log_saisie_ouverte" not in st.session_state:
        st.session_state.log_saisie_ouverte = False
    if "log_edit_id" not in st.session_state:
        st.session_state.log_edit_id = None

    if st.session_state.log_edit_id is not None:
        _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="edition", etape_id=st.session_state.log_edit_id)
    elif st.session_state.log_saisie_ouverte:
        _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="creation")
    else:
        if st.button("➕ NOUVELLE ÉTAPE QUOTIDIENNE", use_container_width=True):
            st.session_state.log_saisie_ouverte = True
            st.rerun()

    # --- Vue groupée par navigation ---
    if etapes:
        st.divider()
        groupes = etapes_groupees_par_navigation(etapes)

        for nom_nav, liste in groupes:
            t_mil = sum(e.get("milles", 0) or 0 for e in liste)
            st.markdown(
                f"""
                <div style="background:#2c3e50; color:white; padding:10px; border-radius:8px; margin-top:15px; border-left: 5px solid #3498db;">
                    <b>🚢 {nom_nav}</b> | Distance Totale Voyage : {t_mil:.1f} NM
                </div>
                """,
                unsafe_allow_html=True,
            )

            for e in liste:
                with st.container():
                    c_txt, c_btn = st.columns([0.7, 0.3])
                    with c_txt:
                        st.markdown(
                            f"""
                            <div style="background:white; border-left:4px solid #bdc3c7; padding:8px 15px; border-bottom:1px solid #eee; color: black;">
                                <b>📅 {e.get('date','')}</b> | ⚙️ {e.get('heures_moteur',0):.1f}h Mot. | ⛵ {e.get('heures_voile',0):.1f}h Voile | <b>{e.get('milles',0):.1f} NM</b><br>
                                <small style="color:#34495e;">📍 Cond. Météo : {e.get('meteo') or '-'} | {e.get('notes') or ''}</small>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with c_btn:
                        ce, cd, cc = st.columns([1, 1, 2])
                        if ce.button("✏️", key=f"e_{e['id']}"):
                            st.session_state.log_edit_id = e["id"]
                            st.rerun()

                        confirm_key = f"confirm_del_log_{e['id']}"
                        if not st.session_state.get(confirm_key, False):
                            if cd.button("🗑️", key=f"d_{e['id']}"):
                                st.session_state[confirm_key] = True
                                st.rerun()
                        else:
                            if cc.button("✅ OUI", key=f"ok_{e['id']}", type="primary"):
                                st.session_state[confirm_key] = False
                                sauvegarder_etapes(supprimer_etape(etapes, e["id"]))
                                st.toast("Étape supprimée", icon="🗑️")
                                st.rerun()
                            if cc.button("❌", key=f"no_{e['id']}"):
                                st.session_state[confirm_key] = False
                                st.rerun()

    # --- Export CSV ---
    if etapes:
        st.divider()
        import pandas as pd
        df_export = pd.DataFrame(etapes)
        csv = df_export.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 Télécharger le Livre de Bord complet (.CSV)",
            data=csv, file_name="livre_de_bord_vesta.csv", mime="text/csv",
            use_container_width=True,
        )
