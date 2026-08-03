"""
page_relances.py
==================
Onglet "🔔 À relancer" : liste des prospects actifs (pas "sans suite"),
triés par urgence (relance en retard en premier), avec actions pour
reporter la relance ou marquer "sans suite".

À intégrer dans app_voile1.py via afficher_page_relances().

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, FACT, MAINT, LOG, MEMOS, ARCHIVES.
"""
from datetime import date, timedelta

import streamlit as st

from modele_voile import (
    trier_relances, relance_en_retard, relance_proche,
    marquer_sans_suite, reporter_relance, parse_date_eu, fond_clair,
)


def _carte_prospect(interet, contacts_par_id, aujourdhui):
    contact = contacts_par_id.get(interet.get("contact_id"))
    nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "(contact inconnu)"

    en_retard = relance_en_retard(interet, aujourdhui)
    proche = relance_proche(interet, aujourdhui)
    if en_retard:
        couleur, badge = "#E74C3C", "⚠️ EN RETARD"
    elif proche:
        couleur, badge = "#F39C12", "🔔 BIENTÔT"
    else:
        couleur, badge = "#27AE60", "✅ À JOUR"

    fond = fond_clair(couleur)

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="border-left:8px solid {couleur}; border-radius:8px; padding:10px 14px; background:{fond};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="font-size:1.05rem; color:#2c3e50;">{nom_aff}</b>
                    <span style="background:{couleur}; color:white; border-radius:12px; padding:3px 12px; font-size:0.72rem; font-weight:bold;">{badge}</span>
                </div>
                <div style="margin-top:6px; font-size:0.85rem; color:#555;">
                    🏢 {interet.get('societe','') or '—'} &nbsp;|&nbsp;
                    📅 Demande du {interet.get('date_demande') or '—'} &nbsp;|&nbsp;
                    🔔 Relance prévue le {interet.get('prochaine_relance') or '(non définie)'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if interet.get("notes"):
            st.caption(f"📝 {interet['notes']}")

        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        nouvelle_date = c1.text_input(
            "Nouvelle date de relance (jj/mm/aaaa)",
            value=interet.get("prochaine_relance") or "",
            key=f"date_relance_{interet['id']}",
            label_visibility="collapsed",
        )
        if c2.button("🔄 Reporter", key=f"reporter_{interet['id']}", use_container_width=True):
            if not parse_date_eu(nouvelle_date):
                st.error("Date invalide (format attendu : jj/mm/aaaa).")
            else:
                st.session_state["_action_relance"] = ("reporter", interet["id"], nouvelle_date)
                st.rerun()
        if c3.button("👻 Sans suite", key=f"sans_suite_{interet['id']}", use_container_width=True):
            st.session_state["_action_relance"] = ("sans_suite", interet["id"], None)
            st.rerun()


def afficher_page_relances(charger_interets, sauvegarder_interets, charger_contacts):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    st.markdown("## 🔔 À relancer")

    interets = charger_interets()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}

    # --- Action différée (reporter / sans suite) ---
    if st.session_state.get("_action_relance"):
        action, interet_id, valeur = st.session_state.pop("_action_relance")
        if action == "reporter":
            interets = reporter_relance(interets, interet_id, valeur)
            sauvegarder_interets(interets)
            st.success("Relance reportée.")
        elif action == "sans_suite":
            interets = marquer_sans_suite(interets, interet_id)
            sauvegarder_interets(interets)
            st.success("Marqué sans suite.")
        st.rerun()

    aujourdhui = date.today()
    prospects_tries = trier_relances(interets)

    nb_retard = sum(1 for i in prospects_tries if relance_en_retard(i, aujourdhui))
    nb_proche = sum(1 for i in prospects_tries if relance_proche(i, aujourdhui))

    c1, c2, c3 = st.columns(3)
    c1.metric("👻 Prospects actifs", len(prospects_tries))
    c2.metric("⚠️ En retard", nb_retard)
    c3.metric("🔔 Bientôt (7 jours)", nb_proche)

    st.divider()

    if not prospects_tries:
        st.info("Aucun prospect actif à relancer pour l'instant.")
        return

    for interet in prospects_tries:
        _carte_prospect(interet, contacts_par_id, aujourdhui)
