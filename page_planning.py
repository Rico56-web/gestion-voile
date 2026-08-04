"""
page_planning.py
=================
Page PLANNING (tableau de bord + calendrier des sorties), nouveau modèle
séparé (croisieres_v2.json / etapes_v2.json / contacts_v2.json).

À intégrer dans app_voile1.py : remplace le bloc actuel
    if st.session_state.page == "PLANNING": ...
par un appel à afficher_page_planning().

Les missions du calendrier sont cliquables : cliquer sur une mission ouvre
MODIFIER_CROISIERE pour l'éditer directement.

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, FACT, STATS, ARCHIVES.
"""
import calendar as calendar_module
from datetime import datetime, date, timedelta

import streamlit as st

from modele_voile import (
    derniere_lecture_compteur, croisieres_du_mois, nb_participants_impayes,
    couleur_croisiere, noms_participants, date_fin_croisiere, parse_date_eu,
)

MOIS_NOMS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
             "Août", "Septembre", "Octobre", "Novembre", "Décembre"]


def _widget_meteo():
    st.markdown(
        """
        <iframe width="100%" height="350"
        src="https://www.windy.com/embed2.html?lat=47.545&lon=-2.894&zoom=10&level=surface&overlay=wind&product=ecmwf&metricWind=kt&metricTemp=%C2%B0C"
        frameborder="0"></iframe>
        """,
        unsafe_allow_html=True,
    )


def _bloc_alertes(croisieres, etapes, params):
    col_v1, col_v2, col_v3 = st.columns(3)

    derniere_heure = derniere_lecture_compteur(etapes)
    seuil_v = params.get("prochaine_vidange", 2500.0)
    heures_restantes = seuil_v - derniere_heure
    if heures_restantes < 15:
        col_v1.error(f"🛠️ Vidange : Proche ({heures_restantes:.1f}h restantes) !")
    else:
        col_v1.success(f"⚙️ Moteur : {derniere_heure:.1f}h (Reste {heures_restantes:.1f}h)")

    nb_impayes = nb_participants_impayes(croisieres)
    col_v2.metric("Factures impayées", f"{nb_impayes}",
                   delta=f"{nb_impayes}" if nb_impayes > 0 else "OK",
                   delta_color="inverse")

    col_v3.link_button("🌊 Marées Crouesty", "https://maree.info/104", use_container_width=True)


def _construire_jours_occupes(croisieres_mois, sel_y, sel_m):
    """Renvoie {jour_du_mois: couleur} pour colorer le calendrier."""
    jours_occ = {}
    for cr in croisieres_mois:
        d_debut = parse_date_eu(cr.get("date_debut"))
        d_fin = date_fin_croisiere(cr)
        if not d_debut or not d_fin:
            continue
        couleur = couleur_croisiere(cr)
        jour = d_debut
        while jour <= d_fin:
            if jour.month == sel_m and jour.year == sel_y:
                jours_occ[jour.day] = couleur
            jour += timedelta(days=1)
    return jours_occ


def _afficher_calendrier(jours_occ, sel_y, sel_m, aujourdhui):
    h_cal = '<table style="width:100%; text-align:center; border-collapse:collapse; background:white; border:1px solid #ddd;">'
    h_cal += '<tr style="background:#f8f9fa; font-size:12px; font-weight:bold;"><td>Lu</td><td>Ma</td><td>Me</td><td>Je</td><td>Ve</td><td>Sa</td><td>Di</td></tr>'

    for semaine in calendar_module.monthcalendar(sel_y, sel_m):
        h_cal += "<tr>"
        for jour in semaine:
            if jour == 0:
                h_cal += '<td style="height:40px; border:1px solid #eee;"></td>'
            else:
                bg = jours_occ.get(jour, "transparent")
                txt_c = "white" if bg != "transparent" else "black"
                est_aujourdhui = (jour == aujourdhui.day and sel_m == aujourdhui.month and sel_y == aujourdhui.year)
                style_cellule = "background:#fff9c4;" if est_aujourdhui else ""
                h_cal += f'''<td style="{style_cellule} border:1px solid #eee; height:40px;">
                                <div style="background:{bg}; color:{txt_c}; border-radius:50%; width:26px; height:26px; line-height:26px; margin:auto; font-weight:bold; font-size:12px;">
                                    {jour}
                                </div>
                            </td>'''
        h_cal += "</tr>"
    st.markdown(h_cal + "</table>", unsafe_allow_html=True)


def _afficher_missions(croisieres_mois, contacts_par_id, sel_m_nom, aujourdhui):
    st.markdown(f"### 📋 Missions de {sel_m_nom}")
    if not croisieres_mois:
        st.info("Aucune mission ce mois-ci.")
        return

    total_prevu = sum(
        cr["participants"][0].get("prix", 0) if cr.get("participants") else 0
        for cr in croisieres_mois
        if not (cr.get("participants") and all(p.get("annulee") for p in cr["participants"]))
    )

    for cr in croisieres_mois:
        couleur = couleur_croisiere(cr)
        prix_total = sum(p.get("prix", 0) or 0 for p in cr.get("participants", []))
        col1, col2 = st.columns([1, 3.5])
        with col1:
            st.markdown(
                f"""<div style='background:{couleur}; color:white; border-radius:5px; text-align:center; padding:5px;'>
                <span style='font-size:0.75rem;'>{cr.get('date_debut','?')}</span><br><b>{prix_total:.0f} €</b>
                </div>""",
                unsafe_allow_html=True,
            )
        with col2:
            nom_aff = noms_participants(cr, contacts_par_id)
            nom_nav = cr.get("nom_croisiere") or "(sans nom)"
            if st.button(f"{nom_aff} — {nom_nav}", key=f"mission_{cr['id']}", use_container_width=True):
                st.session_state.edit_croisiere_id = cr["id"]
                st.session_state.page = "MODIFIER_CROISIERE"
                st.rerun()

    st.success(f"**💰 Total prévisionnel {sel_m_nom} : {total_prevu:,.0f} €**".replace(",", " "))


def afficher_page_planning(charger_croisieres, charger_etapes, charger_contacts, charger_params):
    """Point d'entrée de la page. Les fonctions de chargement sont
    injectées depuis app_voile1.py, comme pour les autres pages migrées."""

    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #1a2a6c, #2980B9); color:white; padding:22px 24px;
        border-radius:14px; margin-bottom:16px; text-align:center; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <div style="font-size:1.7rem; font-weight:bold;">⚓ Tableau de Bord VESTA</div>
            <div style="font-size:0.95rem; color:#dbe4ff; margin-top:4px;">Port Crouesty — Bonne navigation !</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _widget_meteo()

    croisieres = charger_croisieres()
    etapes = charger_etapes()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}
    params = charger_params()

    _bloc_alertes(croisieres, etapes, params)
    st.divider()

    st.markdown(
        '<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;">'
        "<h1>🗓️ PLANNING DES SORTIES</h1></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)

    if "curr_month_idx" not in st.session_state:
        st.session_state.curr_month_idx = aujourdhui.month - 1
    if "curr_year" not in st.session_state:
        st.session_state.curr_year = aujourdhui.year

    c_m, c_y, c_n = st.columns([1.5, 1, 0.8])
    sel_m_nom = c_m.selectbox("Mois", MOIS_NOMS, index=st.session_state.curr_month_idx)
    sel_m = MOIS_NOMS.index(sel_m_nom) + 1
    st.session_state.curr_month_idx = sel_m - 1

    annees_dispo = [2025, 2026, 2027, 2028]
    sel_y = c_y.selectbox("Année", annees_dispo, index=annees_dispo.index(st.session_state.curr_year))
    st.session_state.curr_year = sel_y

    if c_n.button("📍 ICI", use_container_width=True):
        st.session_state.curr_month_idx = aujourdhui.month - 1
        st.session_state.curr_year = aujourdhui.year
        st.rerun()

    croisieres_mois = croisieres_du_mois(croisieres, sel_y, sel_m)
    jours_occ = _construire_jours_occupes(croisieres_mois, sel_y, sel_m)

    _afficher_calendrier(jours_occ, sel_y, sel_m, aujourdhui)
    _afficher_missions(croisieres_mois, contacts_par_id, sel_m_nom, aujourdhui)
