"""
page_croisieres.py
===================
Liste des croisières, filtrée depuis le début de l'année en cours par
défaut (avec option pour voir tout l'historique). Vue synthétique sous
forme de tableau (1 ligne = 1 croisière), avec "zoom" sur une ligne pour
voir le détail complet et accéder à la modification/suppression.

À intégrer dans app_voile1.py via afficher_page_croisieres().

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, FACT, STATS, ARCHIVES.
"""
from datetime import date
import io
import urllib.parse

import pandas as pd
import streamlit as st
from openpyxl.utils import get_column_letter

from modele_voile import filtrer_temporel, trier_croisieres, noms_participants, couleur_croisiere, fond_clair, parse_date_eu

OPTIONS_TRI = {
    "date_desc": "🗓️ Date (récent → ancien)",
    "date_asc": "🗓️ Date (ancien → récent)",
    "nom": "🔤 Nom",
    "prenom": "🔤 Prénom",
}


def _badges_statut(cr):
    """Construit les badges colorés (Terminée/Payée/Annulée) pour une
    croisière, en se basant sur le 1er participant (cas le plus courant)."""
    participants = cr.get("participants", [])
    if not participants:
        return ""
    p = participants[0]
    badges = []
    if p.get("annulee"):
        badges.append(("❌ Annulée", "#C0392B"))
    else:
        if p.get("terminee"):
            badges.append(("✅ Terminée", "#27AE60"))
        else:
            badges.append(("🟢 En cours", "#2980B9"))
        if p.get("payee"):
            badges.append(("💰 Payée", "#16A085"))
        else:
            badges.append(("⏳ À encaisser", "#F39C12"))
    return "".join(
        f'<span style="background:{c}; color:white; border-radius:12px; padding:2px 10px; '
        f'font-size:0.72rem; font-weight:bold; margin-right:5px;">{txt}</span>'
        for txt, c in badges
    )


def _statut_texte(cr):
    """Version texte simple (sans HTML) du statut, pour l'afficher comme
    une cellule normale dans le tableau de synthèse — les badges colorés
    HTML ne s'affichent pas correctement dans un st.dataframe."""
    participants = cr.get("participants", [])
    if not participants:
        return "-"
    p = participants[0]
    if p.get("annulee"):
        return "❌ Annulée"
    morceaux = ["✅ Terminée" if p.get("terminee") else "🟢 En cours"]
    morceaux.append("💰 Payée" if p.get("payee") else "⏳ À encaisser")
    return " · ".join(morceaux)


def _site_participant(cr):
    """Le 'site' (plateforme : CMN, CLICK, VOG, PERSO...) du 1er participant,
    même logique que pour le tableau de synthèse du LOG."""
    participants = cr.get("participants", [])
    if participants:
        return participants[0].get("societe") or "-"
    return "-"


def _etapes_liees(etapes, croisiere_id):
    """Retourne la liste des étapes du LOG (etapes_v2.json) qui sont liées
    à cette croisière — c'est-à-dire dont le champ 'croisiere_id' (posé
    automatiquement par la page LOG en comparant les dates) correspond."""
    return [e for e in etapes if e.get("croisiere_id") == croisiere_id]


# Le nom technique du champ "Identifiant" dans le Google Form, récupéré
# via "Préremplir le formulaire" (voir l'URL générée : le morceau
# 'entry.XXXXXXXXX' juste avant le signe '=').
ENTRY_ID_IDENTIFIANT_CONTACT = "entry.775952758"


def _lien_personnalise(url_base, contact_id):
    """Construit un lien vers le questionnaire, pré-rempli avec
    l'identifiant du contact caché dedans (champ 'Identifiant' du
    formulaire). Renvoie None si le paramètre technique n'a pas encore
    été renseigné (ENTRY_ID_IDENTIFIANT_CONTACT), ou si les infos de
    base manquent — dans ce cas, on n'affiche simplement pas le lien
    personnalisé plutôt que de planter."""
    if not url_base or not contact_id or not ENTRY_ID_IDENTIFIANT_CONTACT:
        return None
    separateur = "&" if "?" in url_base else "?"
    return f"{url_base}{separateur}{ENTRY_ID_IDENTIFIANT_CONTACT}={contact_id}"


def _nb_jours_etape(e):
    """Nombre de jours couverts par UNE étape du LOG (même logique que
    dans page_log.py) : 1 jour normalement, ou plus si 'date_fin' est
    renseignée (saisie 'multi-jours' — une seule ligne pour toute une
    période)."""
    date_fin_str = e.get("date_fin")
    if not date_fin_str:
        return 1
    d_debut = parse_date_eu(e.get("date", ""))
    d_fin = parse_date_eu(date_fin_str)
    if d_debut and d_fin and d_fin >= d_debut:
        return (d_fin - d_debut).days + 1
    return 1


def _jours_reels(etapes_cr):
    """Total des jours réellement couverts par les étapes du LOG liées à
    une croisière (somme de _nb_jours_etape pour chacune)."""
    return sum(_nb_jours_etape(e) for e in etapes_cr)


def _construire_tableau_synthese(croisieres_affichees, contacts_par_id, etapes):
    """Construit le DataFrame résumé : 1 ligne par croisière, dans le même
    ordre que 'croisieres_affichees' (utile pour retrouver la bonne
    croisière après une sélection dans le tableau, via son index)."""
    lignes = []
    for cr in croisieres_affichees:
        prix_total = sum(p.get("prix", 0) or 0 for p in cr.get("participants", []))
        etapes_cr = _etapes_liees(etapes, cr.get("id"))
        jours_prevus = cr.get("jours", 1)
        jours_reel = _jours_reels(etapes_cr)

        # "LOG rempli" : est-ce qu'au moins une étape du LOG est déjà liée
        # à cette croisière ? Répond à la question "ai-je déjà rempli le
        # livre de bord pour cette sortie ?".
        log_rempli = "✅ Oui" if etapes_cr else "⏳ Pas encore"

        # "Écart" : compare les jours prévus (réservation) aux jours
        # réellement saisis dans le LOG. On n'affiche une alerte que si
        # le LOG a déjà été rempli au moins une fois — sinon "Pas encore"
        # (colonne précédente) suffit à le dire, pas besoin de doublon.
        if not etapes_cr:
            ecart = "-"
        elif jours_reel == jours_prevus:
            ecart = "✅ OK"
        else:
            ecart = f"⚠️ {jours_reel}/{jours_prevus} j"

        lignes.append({
            "Date": cr.get("date_debut") or "-",
            "Nom": cr.get("nom_croisiere") or "(sans nom)",
            "Participant(s)": noms_participants(cr, contacts_par_id),
            "Site": _site_participant(cr),
            "Jours": jours_prevus,
            "Prix (€)": prix_total,
            "Statut": _statut_texte(cr),
            "LOG rempli": log_rempli,
            "Écart": ecart,
        })
    return pd.DataFrame(lignes)


def _afficher_detail_croisiere(cr, sauvegarder_croisieres, contacts_par_id, etapes, liens):
    """Affiche le détail complet d'UNE croisière (le 'zoom') : la carte
    HTML avec badges colorés, les boutons Modifier / Supprimer, les
    étapes du LOG déjà saisies, et — si le lien du questionnaire est
    enregistré et le paramètre technique renseigné — un lien
    personnalisé par participant vers le questionnaire de préparation."""
    couleur = couleur_croisiere(cr)
    fond = fond_clair(couleur)
    prix_total = sum(p.get("prix", 0) or 0 for p in cr.get("participants", []))
    nom_participants = noms_participants(cr, contacts_par_id)
    nom_croisiere = cr.get("nom_croisiere") or "(sans nom)"
    badges = _badges_statut(cr)

    with st.container(border=False):
        st.markdown(
            f"""
            <div style="border-left:10px solid {couleur}; border-radius:10px; padding:14px 16px; margin-bottom:10px; background:{fond};">
                <div style="font-size:1.05rem; font-weight:bold; color:#2c3e50;">📅 {cr.get('date_debut','?')}</div>
                <div style="font-size:0.95rem; margin-top:2px;">👤 {nom_participants}</div>
                <div style="font-size:0.9rem; color:#555; margin-top:2px;">⛵ {nom_croisiere} · {cr.get('jours',1)} jour(s) · <b>{prix_total:.0f} €</b></div>
                <div style="margin-top:8px;">{badges}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        c_mod, c_sup = st.columns(2)
        if c_mod.button("✏️ Modifier", key=f"ed_cr_{cr['id']}", use_container_width=True):
            st.session_state.edit_croisiere_id = cr["id"]
            st.session_state.page = "MODIFIER_CROISIERE"
            st.rerun()

        cle_confirm = f"confirm_del_cr_{cr['id']}"
        if cle_confirm not in st.session_state:
            if c_sup.button("🗑️ Supprimer", key=f"del_cr_{cr['id']}", use_container_width=True):
                st.session_state[cle_confirm] = True
                st.rerun()
        else:
            st.warning(f"Confirmer la suppression de la croisière du {cr.get('date_debut','?')} ({nom_participants}) ?")
            cx, cy = st.columns(2)
            if cx.button("✅ Oui, supprimer", key=f"y_cr_{cr['id']}", use_container_width=True):
                st.session_state.pop(cle_confirm)
                st.session_state.croisiere_id_a_supprimer = cr["id"]
                st.rerun()
            if cy.button("❌ Annuler", key=f"n_cr_{cr['id']}", use_container_width=True):
                st.session_state.pop(cle_confirm)
                st.rerun()

        # --- Lien personnalisé vers le questionnaire, par participant ---
        lien_questionnaire = next(
            (l.get("url") for l in liens if "questionnaire" in (l.get("nom") or "").lower()),
            None,
        )
        if lien_questionnaire:
            st.markdown("##### 🔗 Questionnaire personnalisé")
            if not ENTRY_ID_IDENTIFIANT_CONTACT:
                st.caption(
                    "⚙️ Configuration à terminer : le paramètre technique du champ "
                    "'Identifiant' n'a pas encore été renseigné dans le code "
                    "(ENTRY_ID_IDENTIFIANT_CONTACT)."
                )
            else:
                for p in cr.get("participants", []):
                    contact = contacts_par_id.get(p.get("contact_id"))
                    if not contact:
                        continue
                    nom_p = f"{contact.get('prenom','')} {contact.get('nom','')}".strip()
                    lien_perso = _lien_personnalise(lien_questionnaire, p.get("contact_id"))
                    if lien_perso:
                        numero_tel = (contact.get("telephone") or "").strip()
                        ligne = f"- **{nom_p}** : [Ouvrir son questionnaire]({lien_perso})"
                        if numero_tel:
                            message_sms = (
                                f"Bonjour, avant notre navigation pourriez-vous remplir ce "
                                f"questionnaire rapide : {lien_perso}\nMerci et à bientôt !"
                            )
                            numero_propre = numero_tel.replace(" ", "").replace(".", "")
                            lien_sms = f"sms:{numero_propre}?body={urllib.parse.quote(message_sms)}"
                            ligne += f" · [📱 Envoyer par SMS]({lien_sms})"
                        else:
                            ligne += " · *(pas de numéro de téléphone enregistré)*"
                        st.markdown(ligne)

        # --- Étapes du LOG liées à cette croisière ---
        etapes_cr = _etapes_liees(etapes, cr.get("id"))
        st.markdown("##### 📖 Livre de bord pour cette croisière")
        if not etapes_cr:
            st.info("Aucune étape saisie dans le LOG pour cette croisière pour le moment.")
        else:
            jours_prevus = cr.get("jours", 1)
            jours_reel = _jours_reels(etapes_cr)
            if jours_reel != jours_prevus:
                st.warning(
                    f"⚠️ {jours_prevus} jour(s) prévu(s) à la réservation, "
                    f"mais {jours_reel} jour(s) saisi(s) dans le LOG — vérifie "
                    f"qu'il ne manque pas une étape (ou qu'il n'y en a pas une en trop)."
                )
            else:
                st.success(f"✅ Nombre de jours cohérent avec la réservation ({jours_reel} j).")

            for e in etapes_cr:
                if e.get("date_fin"):
                    label_date = f"📅 {e.get('date','')} → {e.get('date_fin','')}"
                else:
                    label_date = f"📅 {e.get('date','')}"
                st.markdown(
                    f"""
                    <div style="background:{fond}; border-left:6px solid {couleur}; padding:8px 15px; border-radius:0 8px 8px 0; margin-bottom:4px; color: black;">
                        <b>{label_date}</b> | ⚙️ {e.get('heures_moteur',0):.1f}h Mot. | ⛵ {e.get('heures_voile',0):.1f}h Voile | <b>{e.get('milles',0):.1f} NM</b><br>
                        <small style="color:#34495e;">📍 Cond. Météo : {e.get('meteo') or '-'} | {e.get('notes') or ''}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def afficher_page_croisieres(charger_croisieres, sauvegarder_croisieres, charger_contacts, charger_etapes, charger_liens):
    """Point d'entrée de la page. charger_croisieres / sauvegarder_croisieres
    / charger_contacts / charger_etapes / charger_liens injectées depuis
    app_voile1.py. charger_liens (liens_utiles.json) est nécessaire pour
    retrouver le lien du questionnaire et générer les liens personnalisés
    par participant."""

    st.markdown("## ⛵ Croisières")

    croisieres = charger_croisieres()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}
    etapes = charger_etapes()
    liens = charger_liens()

    # --- Suppression différée (demandée au tour précédent) ---
    if st.session_state.get("croisiere_id_a_supprimer"):
        cid = st.session_state.pop("croisiere_id_a_supprimer")
        croisieres = [cr for cr in croisieres if cr["id"] != cid]
        sauvegarder_croisieres(croisieres)
        st.toast("Croisière supprimée.", icon="🗑️")
        st.rerun()

    if st.button("➕ Nouvelle croisière", use_container_width=True):
        st.session_state.edit_croisiere_id = None
        st.session_state.page = "MODIFIER_CROISIERE"
        st.rerun()

    st.divider()

    # --- Filtre temporel : Toutes / Passées / À venir ---
    if "filtre_temporel_cr" not in st.session_state:
        st.session_state.filtre_temporel_cr = "toutes"

    st.caption("Filtrer :")
    c1, c2, c3 = st.columns(3)
    options_filtre = [("toutes", "📋 Toutes", c1), ("passees", "📅 Passées", c2), ("futures", "🔜 À venir", c3)]
    for cle, label, col in options_filtre:
        actif = st.session_state.filtre_temporel_cr == cle
        if col.button(label, key=f"filtre_temp_{cle}", use_container_width=True,
                      type="primary" if actif else "secondary"):
            st.session_state.filtre_temporel_cr = cle
            # Tri par défaut adapté au filtre : pour "à venir", la sortie la
            # plus proche est ce qu'on veut voir en premier (pas la plus
            # lointaine) ; pour "passées"/"toutes", on garde la convention
            # habituelle de l'appli (le plus récent en tête).
            st.session_state.tri_croisieres = "date_asc" if cle == "futures" else "date_desc"
            st.rerun()

    # --- Tri ---
    if "tri_croisieres" not in st.session_state:
        st.session_state.tri_croisieres = "date_desc"

    tri_choisi = st.selectbox(
        "Trier par",
        options=list(OPTIONS_TRI.keys()),
        format_func=lambda cle: OPTIONS_TRI[cle],
        index=list(OPTIONS_TRI.keys()).index(st.session_state.tri_croisieres),
        key="selectbox_tri_croisieres",
    )
    st.session_state.tri_croisieres = tri_choisi

    st.divider()

    aujourdhui = date.today()
    croisieres_filtrees = filtrer_temporel(croisieres, st.session_state.filtre_temporel_cr, aujourdhui)
    croisieres_affichees = trier_croisieres(croisieres_filtrees, contacts_par_id, st.session_state.tri_croisieres)

    if not croisieres_affichees:
        st.info("Aucune croisière à afficher pour ce filtre.")
        return

    st.caption(f"{len(croisieres_affichees)} croisière(s) affichée(s).")

    # --- Vue synthétique (1 ligne = 1 croisière) + zoom ---
    df_synthese = _construire_tableau_synthese(croisieres_affichees, contacts_par_id, etapes)

    st.markdown("#### 🗂️ Vue d'ensemble")
    st.caption("Clique sur une ligne du tableau pour afficher le détail et pouvoir la modifier/supprimer.")

    selection = st.dataframe(
        df_synthese,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        use_container_width=True,
        key="tableau_synthese_croisieres",
        column_config={
            "Prix (€)": st.column_config.NumberColumn(format="%.0f €"),
        },
    )

    lignes_selectionnees = selection.selection.rows
    if lignes_selectionnees:
        idx = lignes_selectionnees[0]
        cr_choisie = croisieres_affichees[idx]
        st.divider()
        _afficher_detail_croisiere(cr_choisie, sauvegarder_croisieres, contacts_par_id, etapes, liens)
    else:
        st.info("Aucune croisière sélectionnée — clique sur une ligne ci-dessus pour voir le détail.")

    # --- Export XLSX (Excel) ---
    # On exporte le TABLEAU DE SYNTHÈSE (df_synthese), pas les données
    # brutes : une croisière contient une liste imbriquée "participants",
    # qui donnerait des cellules illisibles (du texte Python brut) dans
    # Excel. Le tableau de synthèse est déjà "aplati" et propre.
    st.divider()
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_synthese.to_excel(writer, index=False, sheet_name="Croisières")
        feuille = writer.sheets["Croisières"]

        # Auto-largeur : pour chaque colonne, on mesure la longueur du
        # texte le plus long (valeur ou en-tête), et on règle la largeur
        # en conséquence (+2 pour un peu de marge visuelle).
        for i, colonne in enumerate(df_synthese.columns, start=1):
            if df_synthese.empty:
                longueur_max = len(str(colonne))
            else:
                longueur_max = max(
                    df_synthese[colonne].astype(str).map(len).max(),
                    len(str(colonne)),
                )
            feuille.column_dimensions[get_column_letter(i)].width = longueur_max + 2

    st.download_button(
        label="📥 Télécharger les Croisières (.XLSX)",
        data=buffer.getvalue(),
        file_name="croisieres_vesta.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
