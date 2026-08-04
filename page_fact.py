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
from datetime import date, datetime

import streamlit as st

from modele_voile import (
    bilan_facturation, marquer_participant_paye, est_en_retard,
    participations_cmn_impayees, COULEURS_SOCIETE, fond_clair,
)


def _carte_participation(p, contacts_par_id, aujourdhui, statut):
    """Affiche une carte pour une participation (facture), avec ses
    actions (Encaisser/Annuler + Voir)."""
    contact = contacts_par_id.get(p.get("contact_id"))
    nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "(contact inconnu)"
    soc = (p.get("societe") or "PERSO").upper()
    retard = statut == "a_encaisser" and est_en_retard(p, aujourdhui)

    if retard:
        couleur = "#E74C3C"
    else:
        couleur = COULEURS_SOCIETE.get(soc, "#7F8C8D")
    fond = fond_clair(couleur)

    badge_statut = (
        '<span style="background:#E74C3C; color:white; border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:bold;">⚠️ RETARD</span>'
        if retard else (
            '<span style="background:#27AE60; color:white; border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:bold;">✅ PAYÉ</span>'
            if statut == "payees" else
            '<span style="background:#F39C12; color:white; border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:bold;">⏳ À ENCAISSER</span>'
        )
    )

    st.markdown(
        f"""
        <div style="background:{fond}; border-left:10px solid {couleur};
        padding:15px; border-radius:10px; margin-bottom:10px; color:black;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <b style="font-size:1.05rem;">{nom_aff}</b>
                <span style="font-size:1.15rem; font-weight:bold; color:{couleur};">{p.get('prix', 0):.2f} €</span>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                <small style="color:#555;">📅 {p.get('date_debut', '?')} &nbsp;|&nbsp; 🏢 {soc} &nbsp;|&nbsp; {p.get('nom_croisiere') or '(sans nom)'}</small>
                {badge_statut}
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


def _module_envoi_cmn(croisieres, contacts_par_id, envoyer_email):
    """Module de préparation et d'envoi du relevé mensuel CMN — révision
    des prestations à inclure, message, signature électronique, puis
    envoi par email. N'INFLUENCE PAS le statut payé/non payé : c'est
    juste un envoi de relevé, l'encaissement se fait séparément dans les
    onglets À encaisser / Payé."""
    st.subheader("📬 Envoi groupé CMN (Vérification & Signature)")

    if "preparer_mail_cmn" not in st.session_state:
        st.session_state.preparer_mail_cmn = False

    cmn_attente = participations_cmn_impayees(croisieres)

    if not cmn_attente:
        st.write("✨ Aucune facture CMN en attente d'envoi ce mois-ci.")
        return

    mois_actuel = datetime.now().strftime("%B %Y")
    st.info(f"Il y a **{len(cmn_attente)}** prestation(s) CMN en attente de règlement.")

    if not st.session_state.preparer_mail_cmn:
        if st.button("📝 Préparer et réviser le relevé mensuel CMN", use_container_width=True):
            st.session_state.preparer_mail_cmn = True
            st.rerun()
        return

    with st.expander("🔍 CONFIGURATION DE L'EMAIL AVANT ENVOI", expanded=True):
        st.markdown("### 1. Sélectionner les prestations à inclure")
        prestations_choisies = {}
        for i, p in enumerate(cmn_attente):
            contact = contacts_par_id.get(p.get("contact_id"))
            nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "(contact inconnu)"
            label = f"📅 {p.get('date_debut','')} - {nom_aff} ({p.get('prix', 0):.2f} €)"
            prestations_choisies[i] = st.checkbox(label, value=True, key=f"chk_mail_cmn_{i}")

        retenues = [p for i, p in enumerate(cmn_attente) if prestations_choisies[i]]

        st.markdown("### 2. Destinataire et Message d'accompagnement")
        if "email" in st.secrets and "email_destinataire" in st.secrets["email"]:
            email_defaut = st.secrets["email"]["email_destinataire"]
        else:
            email_defaut = "compta.cmn@exemple.com"

        email_destinataire = st.text_input(
            "Adresse email du destinataire", value=email_defaut,
            help="Par défaut celle des secrets. Modifie-la pour faire un test.",
        )
        texte_defaut = (
            f"Bonjour,\n\nVeuillez trouver ci-dessous le récapitulatif des prestations "
            f"maritimes effectuées sur le voilier VESTA pour le compte de CMN au titre "
            f"du mois de {mois_actuel}.\n Bonne réception"
        )
        corps_texte = st.text_area("Message d'introduction", value=texte_defaut, height=120)

        st.markdown("### 3. Signature électronique & Certification")
        col_sig1, col_sig2 = st.columns([6, 4])
        with col_sig1:
            signataire = st.text_input("Nom du signataire", value="Le propriétaire de Vesta : Eric CLAVREUL")
            certifie = st.checkbox("✍️ Certifier l'exactitude des prestations et apposer ma signature numérique", value=False)
        with col_sig2:
            date_signature = datetime.now().strftime("%d/%m/%Y %H:%M")
            if certifie:
                st.markdown(
                    f"""<div style="border:2px dashed #27ae60; background-color:#f2f9f4; padding:10px;
                    border-radius:5px; text-align:center; color:#27ae60;">
                    <small style="text-transform:uppercase; font-weight:bold;">Signé Électroniquement</small><br>
                    <b>{signataire}</b><br><small>Horodatage : {date_signature}</small></div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """<div style="border:2px dashed #bdc3c7; background-color:#f9f9f9; padding:10px;
                    border-radius:5px; text-align:center; color:#7f8c8d; height:85px; display:flex;
                    align-items:center; justify-content:center;"><small>En attente de signature...</small></div>""",
                    unsafe_allow_html=True,
                )

        st.divider()
        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("❌ Annuler / Masquer la préparation", use_container_width=True):
            st.session_state.preparer_mail_cmn = False
            st.rerun()

        if c_btn2.button("🚀 CONFIRMER ET ENVOYER LE MAIL", type="primary",
                          use_container_width=True, disabled=not certifie):
            if not retenues:
                st.warning("Sélectionne au moins une prestation à inclure.")
            else:
                lignes = ""
                total_cmn = 0.0
                for p in retenues:
                    contact = contacts_par_id.get(p.get("contact_id"))
                    nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "(contact inconnu)"
                    total_cmn += p.get("prix", 0) or 0
                    lignes += f"""
                    <tr>
                        <td style='padding:8px; border:1px solid #ddd;'>{p.get('date_debut','')}</td>
                        <td style='padding:8px; border:1px solid #ddd;'>{nom_aff}</td>
                        <td style='padding:8px; border:1px solid #ddd; text-align:right;'>{p.get('prix', 0):.2f} €</td>
                    </tr>"""

                corps_html = f"""
                <html><body style="font-family:Arial, sans-serif; color:#333; line-height:1.5;">
                <p>{corps_texte.replace(chr(10), '<br>')}</p>
                <table style="border-collapse:collapse; width:100%; max-width:600px; margin:20px 0;">
                    <thead><tr style="background-color:#3498db; color:white;">
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Date</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:left;">Skipper / Contact</th>
                        <th style="padding:10px; border:1px solid #ddd; text-align:right;">Montant</th>
                    </tr></thead>
                    <tbody>{lignes}
                        <tr style="font-weight:bold; background-color:#f9f9f9;">
                            <td colspan="2" style="padding:10px; border:1px solid #ddd; text-align:right;">Total à régler :</td>
                            <td style="padding:10px; border:1px solid #ddd; text-align:right; color:#2c3e50;">{total_cmn:.2f} €</td>
                        </tr>
                    </tbody>
                </table>
                <div style="border-top:1px solid #eee; padding-top:15px; margin-top:30px;">
                    <p style="margin:0; font-size:0.9rem; color:#7f8c8d;"><i>Message certifié et signé numériquement par l'expéditeur :</i></p>
                    <p style="margin:5px 0 0 0; font-weight:bold; color:#27ae60; font-size:1.1rem;">✍️ {signataire}</p>
                    <p style="margin:0; font-size:0.8rem; color:#95a5a6;">Horodatage de certification : {date_signature}</p>
                </div>
                </body></html>"""

                with st.spinner(f"Envoi sécurisé du relevé à {email_destinataire}..."):
                    succes = envoyer_email(corps_html, mois_actuel, destinataire=email_destinataire)
                    if succes:
                        st.success(f"Le relevé a été envoyé à {email_destinataire} !")
                        st.session_state.preparer_mail_cmn = False
                        st.balloons()
                        st.rerun()


def afficher_page_fact(charger_croisieres, sauvegarder_croisieres, charger_contacts, envoyer_email):
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

    _module_envoi_cmn(croisieres, contacts_par_id, envoyer_email)

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
