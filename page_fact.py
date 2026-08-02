"""
page_fact.py
=============
Suivi de facturation — PARTIE A (indicateurs, onglets À encaisser / Payé
avec actions Encaisser/Annuler/Voir).

La PARTIE B (module d'envoi groupé d'email CMN avec signature
électronique) sera ajoutée dans une prochaine étape.

Correction importante par rapport à l'ancien FACT : l'ancien calculait
le CA en sommant TOUS les prix de contacts.json sans aucun filtre — y
compris les réservations annulées et les prospects en liste d'attente,
toutes années confondues. Le nouveau calcul (bilan_facturation) exclut
les annulées, comme le fait STATS.

À la différence de STATS, FACT ne filtre PAS par année : une facture
impayée d'une saison passée reste due et doit continuer à apparaître.

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, MAINT, LOG, MEMOS, ARCHIVES.
"""
from datetime import date

import streamlit as st

from modele_voile import bilan_facturation, marquer_participant_paye, est_en_retard


def _carte_participation(p, contacts_par_id, aujourdhui, statut):
    """Affiche une carte pour une participation (facture), avec ses
    actions (Encaisser/Annuler + Voir)."""
    contact = contacts_par_id.get(p.get("contact_id"))
    nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "(contact inconnu)"
    soc = (p.get("societe") or "PERSO").upper()
    is_cmn = "CMN" in soc
    retard = statut == "a_encaisser" and est_en_retard(p, aujourdhui)

    label_retard = (
        "<span style='color:#E74C3C; font-weight:bold; font-size:0.8rem;'>⚠️ RETARD</span>"
        if retard else ""
    )
    card_bg = "#E3F2FD" if is_cmn else "#F9F9F9"
    border_color = "#E74C3C" if retard else ("#3498db" if is_cmn else "#7F8C8D")

    st.markdown(
        f"""
        <div style="background:{card_bg}; border:1px solid #ddd; border-left:10px solid {border_color};
        padding:15px; border-radius:8px; margin-bottom:10px; color:black;">
            <div style="display:flex; justify-content:space-between;">
                <b>{nom_aff}</b>
                <span style="font-size:1.1rem; font-weight:bold;">{p.get('prix', 0):.2f} €</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <small>📅 {p.get('date_debut', '?')} | 🏢 {soc} | {p.get('nom_croisiere') or '(sans nom)'}</small>
                {label_retard}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, _ = st.columns([2.5, 2.5, 5])
    cle_action = f"{p['croisiere_id']}_{p['participant_index']}"

    if statut == "a_encaisser":
        if c1.button("💰 Encaisser", key=f"pay_{cle_action}"):
            st.session_state["_action_paiement"] = (p["croisiere_id"], p["participant_index"], True)
            st.rerun()
    else:
        if c1.button("↩️ Annuler", key=f"unpay_{cle_action}"):
            st.session_state["_action_paiement"] = (p["croisiere_id"], p["participant_index"], False)
            st.rerun()

    if c2.button("✏️ Voir", key=f"voir_{cle_action}"):
        st.session_state.edit_croisiere_id = p["croisiere_id"]
        st.session_state.page = "MODIFIER_CROISIERE"
        st.rerun()


def afficher_page_fact(charger_croisieres, sauvegarder_croisieres, charger_contacts):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    st.markdown("<h2 style='text-align: center;'>📑 Suivi de Facturation</h2>", unsafe_allow_html=True)

    croisieres = charger_croisieres()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}

    # --- Action différée : marquer payé/non payé (demandée au tour précédent) ---
    if st.session_state.get("_action_paiement"):
        croisiere_id, participant_index, payee = st.session_state.pop("_action_paiement")
        croisieres = marquer_participant_paye(croisieres, croisiere_id, participant_index, payee)
        sauvegarder_croisieres(croisieres)
        st.toast("Paiement enregistré !" if payee else "Paiement annulé, remis en attente", icon="💰")
        st.rerun()

    if not croisieres:
        st.info("Aucune donnée de facturation disponible.")
        return

    bilan = bilan_facturation(croisieres)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total CA", f"{bilan['total_ca']:,.2f} €".replace(",", " "))
    m2.metric("Encaissé", f"{bilan['total_encaisse']:,.2f} €".replace(",", " "))
    m3.metric(
        "Reste à percevoir", f"{bilan['reste_a_percevoir']:,.2f} €".replace(",", " "),
        delta=f"-{bilan['reste_a_percevoir']:,.2f} €".replace(",", " ") if bilan["reste_a_percevoir"] > 0 else None,
        delta_color="inverse",
    )

    st.divider()

    aujourdhui = date.today()
    t1, t2 = st.tabs(["⏳ À ENCAISSER", "✅ PAYÉ"])

    with t1:
        if not bilan["a_encaisser"]:
            st.info("Aucune facture en attente d'encaissement.")
        else:
            for p in bilan["a_encaisser"]:
                _carte_participation(p, contacts_par_id, aujourdhui, "a_encaisser")

    with t2:
        if not bilan["payees"]:
            st.info("Aucune facture payée pour l'instant.")
        else:
            for p in bilan["payees"]:
                _carte_participation(p, contacts_par_id, aujourdhui, "payees")
