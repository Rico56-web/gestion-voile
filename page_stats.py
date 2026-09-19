"""
page_fact.py
=============
Suivi de facturation.

Contenu de la page :
- Indicateurs : Total CA, Encaissé, Reste à percevoir.
- Module d'envoi groupé du relevé CMN par email (avec signature).
  Il n'influence PAS le statut payé/non payé : c'est juste un envoi.
- Onglets À ENCAISSER / PAYÉ, avec les actions Encaisser / Annuler.

Note sur le calcul du CA : il exclut les réservations annulées (comme
STATS). L'ancien FACT sommait tous les prix sans filtre, y compris les
annulées et les prospects en liste d'attente.

FACT ne filtre PAS par année, à la différence de STATS : une facture
impayée d'une saison passée reste due et doit continuer à apparaître.

Données : croisieres_v2.json (lecture + écriture du statut payé) et
contacts_v2.json (lecture seule). Les fonctions de chargement et de
sauvegarde sont injectées depuis app_voile1.py.
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
                        st.toast(f"Le relevé a été envoyé à {email_destinataire} !", icon="📬")
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
                _carte_participation(p, contacts_par_id, aujourdhui, "payees")"""
page_stats.py
==============
Tableau de bord statistiques et financier — PARTIE A (indicateurs clés,
répartition par société, graphique chronologique + seuil de rentabilité).

La PARTIE B (tableaux détaillés ligne par ligne, éditeur des charges
fixes) sera ajoutée dans une prochaine étape.

Sources de données :
- croisieres_v2.json / etapes_v2.json (nouveau modèle, migré)
- maintenance.json (ANCIEN format, PAS migré — la page MAINT n'existe pas
  encore dans le nouveau modèle, donc on lit ce fichier tel quel, sans le
  toucher, exactement comme le faisait l'ancien code)
- params.json (charges fixes annuelles, seuil de vidange — inchangé)

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, MAINT, LOG, MEMOS, FACT, ARCHIVES.
"""
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from modele_voile import (
    bilan_financier_annee, repartition_par_societe, bilan_navigation_annee,
    recettes_par_mois, derniere_lecture_compteur, etapes_annee, fond_clair,
    montant_encaisse, parse_date_eu, parser_date_flexible,
)

ORDRE_MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


def _depenses_maintenance_par_mois(df_maintenance, annee):
    """Reprend la logique de l'ancien code (inchangée, car maintenance.json
    n'est pas encore migré) : total des dépenses par mois pour l'année,
    et le détail (pure maintenance / charges fixes réelles) séparément,
    pour pouvoir les afficher en tableau au clic sur un pavé."""
    montants = [0.0] * 12
    df_vide = pd.DataFrame()

    if df_maintenance is None or df_maintenance.empty:
        return montants, df_vide, df_vide

    df = df_maintenance.copy()
    df["_date_obj"] = df.get("Date").apply(parser_date_flexible)
    df["M_Num"] = pd.to_numeric(df.get("M_Num"), errors="coerce").fillna(0.0)
    df_y = df[df["_date_obj"].apply(lambda d: d is not None and d.year == annee)]
    df_y = df_y.sort_values("_date_obj", ascending=False, key=lambda col: col.map(lambda d: d or date.min))

    if df_y.empty:
        return montants, df_vide, df_vide

    for _, row in df_y.iterrows():
        mois = row["_date_obj"].month
        montants[mois - 1] += row["M_Num"]

    mask_fixes = df_y.get("Type", pd.Series(dtype=str)).fillna("").str.lower().str.contains("port|assur", na=False)
    df_pure = df_y[~mask_fixes].assign(Date=df_y["_date_obj"].apply(lambda d: d.strftime("%d/%m/%Y"))).drop(columns=["_date_obj"])
    df_fixes = df_y[mask_fixes].assign(Date=df_y["_date_obj"].apply(lambda d: d.strftime("%d/%m/%Y"))).drop(columns=["_date_obj"])

    return montants, df_pure, df_fixes


def _pave_metrique(col, cle, emoji, label, valeur_str, couleur):
    """Un indicateur = un pavé coloré avec un bord bien défini, plus un
    bouton discret pour afficher le tableau détaillé correspondant."""
    fond = fond_clair(couleur)
    with col:
        st.markdown(
            f"""
            <div style="border:2px solid {couleur}; border-radius:10px; padding:10px 8px;
            background:{fond}; text-align:center; margin-bottom:4px;">
                <div style="font-size:0.78rem; color:#555;">{emoji} {label}</div>
                <div style="font-size:1.25rem; font-weight:bold; color:{couleur};">{valeur_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        actif = st.session_state.get("stats_tableau_actif") == cle
        if st.button("🔍 Détail" if not actif else "✅ Affiché", key=f"detail_{cle}", use_container_width=True):
            st.session_state["stats_tableau_actif"] = None if actif else cle
            st.rerun()


def _lignes_participations(participations, contacts_par_id):
    """Transforme la liste de participations (dicts bruts) en lignes
    lisibles pour un tableau, avec le nom du contact et le reste dû.
    Triées par date décroissante (le plus récent en premier)."""
    participations_triees = sorted(
        participations,
        key=lambda p: parse_date_eu(p.get("date_debut")) or date.min,
        reverse=True,
    )
    lignes = []
    for p in participations_triees:
        contact = contacts_par_id.get(p.get("contact_id"))
        nom_aff = f"{contact['prenom']} {contact['nom']}" if contact else "?"
        prix = p.get("prix", 0) or 0
        encaisse = montant_encaisse(p)
        lignes.append({
            "Date": p.get("date_debut", ""),
            "Croisière": p.get("nom_croisiere") or "(sans nom)",
            "Contact": nom_aff,
            "Société": p.get("societe", ""),
            "Prix (€)": prix,
            "Encaissé (€)": encaisse,
            "Reste (€)": max(0.0, prix - encaisse),
            "Payée": "Oui" if p.get("payee") else "Non",
        })
    return pd.DataFrame(lignes)


def _lignes_etapes(etapes_y):
    """Transforme la liste d'étapes de l'année en lignes lisibles,
    triées par date décroissante (le plus récent en premier)."""
    etapes_triees = sorted(etapes_y, key=lambda e: parse_date_eu(e.get("date")) or date.min, reverse=True)
    lignes = [{
        "Date": e.get("date", ""),
        "Navigation": e.get("navigation", ""),
        "Milles": e.get("milles", 0),
        "H. Moteur": e.get("heures_moteur", 0),
        "H. Voile": e.get("heures_voile", 0),
        "Météo": e.get("meteo", ""),
    } for e in etapes_triees]
    return pd.DataFrame(lignes)


def _afficher_tableau_detail(cle, titre, df, colonnes_total=None):
    """Affiche le tableau détaillé correspondant au pavé cliqué, avec un
    bouton pour le refermer et une ligne de total en bas (sur les
    colonnes numériques indiquées dans colonnes_total)."""
    st.divider()
    col_titre, col_fermer = st.columns([5, 1])
    col_titre.markdown(f"### 🔍 Détail — {titre}")
    if col_fermer.button("✖️ Fermer", key=f"fermer_{cle}", use_container_width=True):
        st.session_state["stats_tableau_actif"] = None
        st.rerun()
    if df.empty:
        st.info("Aucune donnée pour cette sélection.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)

    if colonnes_total:
        morceaux = []
        for col in colonnes_total:
            if col in df.columns:
                total = pd.to_numeric(df[col], errors="coerce").sum()
                unite = "NM" if col == "Milles" else ("h" if "H." in col or col.startswith("Heures") else "€")
                morceaux.append(f"{col} : <b>{total:,.1f} {unite}</b>".replace(",", " "))
        if morceaux:
            st.markdown(
                f"""<div style="text-align:right; background:#EBF5FB; padding:10px 16px;
                border-radius:8px; margin-top:6px; color:#1a2a6c;">
                {' &nbsp;|&nbsp; '.join(morceaux)}</div>""",
                unsafe_allow_html=True,
            )


def afficher_page_stats(charger_croisieres, charger_etapes, charger_maintenance, charger_params, charger_contacts):
    """Point d'entrée de la page. Fonctions de chargement injectées
    depuis app_voile1.py."""

    st.markdown('<h2 style="text-align:center;">📊 Dashboard Intégral Vesta</h2>', unsafe_allow_html=True)

    croisieres = charger_croisieres()
    etapes = charger_etapes()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}
    df_maintenance = charger_maintenance()
    params = charger_params()

    frais_defaut = {"Port Arzon": 3800, "Assurance": 1200, "Entretien": 1500, "Divers": 500}
    if "frais_fixes" not in params or not isinstance(params["frais_fixes"], dict) or not params["frais_fixes"]:
        params["frais_fixes"] = frais_defaut
    frais_params = params["frais_fixes"]

    total_frais_fixes = 0.0
    for v in frais_params.values():
        try:
            total_frais_fixes += float(str(v).replace("€", "").replace(" ", "").replace(",", ".").strip())
        except (ValueError, TypeError):
            continue

    c_sel1, c_sel2 = st.columns([3, 1])
    mode_bilan = c_sel1.radio("Mode de calcul :", ["Réel (Encaissé)", "Prévisionnel (Saison)"], horizontal=True)
    sel_y = c_sel2.selectbox("Saison :", [2025, 2026, 2027], index=1)
    mode = "reel" if mode_bilan == "Réel (Encaissé)" else "previsionnel"

    bilan = bilan_financier_annee(croisieres, sel_y, mode)
    nav = bilan_navigation_annee(etapes, sel_y)
    h_moteur_abs = derniere_lecture_compteur(etapes)

    total_ca_display = bilan["total_encaisse"] if mode == "reel" else bilan["total_ca"]

    montants_maint_mois, df_pure_maint, df_fixes_maint = _depenses_maintenance_par_mois(df_maintenance, sel_y)
    total_pure_maint = df_pure_maint["M_Num"].sum() if not df_pure_maint.empty else 0.0
    total_reels_fixes = df_fixes_maint["M_Num"].sum() if not df_fixes_maint.empty else 0.0
    total_dep = total_pure_maint + total_reels_fixes
    solde_net = total_ca_display - total_dep

    st.divider()

    # --- Activité & Navigation (bleu) ---
    st.markdown("##### ⚓ Activité & Navigation")
    etapes_y = etapes_annee(etapes, sel_y)
    t1, t2, t3, t4 = st.columns(4)
    _pave_metrique(t1, "sorties", "⛵", "Sorties", f"{bilan['nb_sorties']}", "#2980B9")
    _pave_metrique(t2, "h_moteur", "⚙️", "Heures Mot.", f"{nav['total_h_moteur']:.1f} h", "#2980B9")
    _pave_metrique(t3, "milles", "🌊", "Milles", f"{nav['total_milles']:,.0f} NM".replace(",", " "), "#2980B9")
    _pave_metrique(t4, "voile", "⛵", "Part voile", f"{nav['ratio_voile']:.0f} %", "#2980B9")

    st.write("")

    # --- Recettes (vert) ---
    st.markdown("##### 💰 Recettes de la Saison")
    f1, f2, f3 = st.columns(3)
    _pave_metrique(f1, "ca_prevu", "🎯", "CA Prévu", f"{bilan['total_ca']:,.0f} €".replace(",", " "), "#27AE60")
    _pave_metrique(f2, "percues", "📥", "Sommes Perçues", f"{bilan['total_encaisse']:,.0f} €".replace(",", " "), "#27AE60")
    _pave_metrique(f3, "reste", "📩", "Reste à percevoir", f"{bilan['reste_a_percevoir']:,.0f} €".replace(",", " "), "#27AE60")

    st.write("")

    # --- Dépenses (orange) ---
    st.markdown("##### 💸 Sommes Dépensées")
    d1, d2, d3 = st.columns(3)
    _pave_metrique(d1, "dep_maint", "🔧", "Dépenses Maint.", f"{total_pure_maint:,.0f} €".replace(",", " "), "#E67E22")
    _pave_metrique(d2, "charges_fixes", "📋", "Charges Fixes Réelles", f"{total_reels_fixes:,.0f} €".replace(",", " "), "#E67E22")
    _pave_metrique(d3, "total_dep", "📊", "Total Dépenses", f"{total_dep:,.0f} €".replace(",", " "), "#E67E22")

    st.write("")

    # --- Bilan net & vidange (violet) ---
    st.markdown("##### 📈 Bilan Net & Maintenance")
    m_col1, m_col2 = st.columns([1, 3])
    _pave_metrique(m_col1, "solde_net", "📊", "Solde Net", f"{solde_net:,.0f} €".replace(",", " "), "#8E44AD")
    h_rest = params.get("prochaine_vidange", 2500.0) - h_moteur_abs
    with m_col2:
        st.write(f"**🔧 Vidange dans : {max(0, h_rest):.1f} h**")
        if h_rest <= 0:
            st.error(f"🚨 Échéance de vidange dépassée de {abs(h_rest):.1f} heures !")
        elif h_rest <= 20:
            st.warning(f"⚠️ Échéance de vidange proche ({h_rest:.1f} h restantes).")
        else:
            st.caption(f"Compteur absolu : {h_moteur_abs:.1f} h. Échéance : {params.get('prochaine_vidange', 2500.0):.1f} h.")

    # --- Tableau détaillé du pavé cliqué (s'il y en a un) ---
    tableau_actif = st.session_state.get("stats_tableau_actif")
    if tableau_actif:
        participations = bilan["participations"]
        if tableau_actif == "sorties":
            df_detail = _lignes_participations([p for p in participations if (p.get("prix", 0) or 0) > 0], contacts_par_id)
            _afficher_tableau_detail(tableau_actif, "Sorties de la saison", df_detail, ["Prix (€)", "Encaissé (€)"])
        elif tableau_actif in ("h_moteur", "milles", "voile"):
            titres = {"h_moteur": "Heures moteur (livre de bord)", "milles": "Milles parcourus (livre de bord)", "voile": "Répartition voile/moteur (livre de bord)"}
            _afficher_tableau_detail(tableau_actif, titres[tableau_actif], _lignes_etapes(etapes_y), ["Milles", "H. Moteur", "H. Voile"])
        elif tableau_actif == "ca_prevu":
            _afficher_tableau_detail(tableau_actif, "CA prévu — toutes les réservations", _lignes_participations(participations, contacts_par_id), ["Prix (€)"])
        elif tableau_actif == "percues":
            df_detail = _lignes_participations([p for p in participations if montant_encaisse(p) > 0], contacts_par_id)
            _afficher_tableau_detail(tableau_actif, "Sommes perçues", df_detail, ["Encaissé (€)"])
        elif tableau_actif == "reste":
            df_detail = _lignes_participations(
                [p for p in participations if (p.get("prix", 0) or 0) - montant_encaisse(p) > 0.01], contacts_par_id)
            _afficher_tableau_detail(tableau_actif, "Reste à percevoir", df_detail, ["Reste (€)"])
        elif tableau_actif == "dep_maint":
            _afficher_tableau_detail(tableau_actif, "Dépenses de maintenance pure", df_pure_maint, ["M_Num"])
        elif tableau_actif == "charges_fixes":
            _afficher_tableau_detail(tableau_actif, "Charges fixes réelles (Port, Assurance)", df_fixes_maint, ["M_Num"])
        elif tableau_actif == "total_dep":
            df_total = pd.concat([df_pure_maint, df_fixes_maint], ignore_index=True) if not df_pure_maint.empty or not df_fixes_maint.empty else pd.DataFrame()
            if not df_total.empty:
                # pd.concat empile les deux tableaux l'un après l'autre sans
                # les remélanger — chacun était trié individuellement, mais
                # pas l'ensemble. On re-trie ici par date décroissante (le
                # plus récent en premier, comme partout ailleurs dans
                # l'appli).
                df_total = df_total.sort_values(
                    "Date", ascending=False, key=lambda col: col.map(parse_date_eu)
                ).reset_index(drop=True)
            _afficher_tableau_detail(tableau_actif, "Toutes les dépenses de la saison", df_total, ["M_Num"])
        elif tableau_actif == "solde_net":
            df_solde = pd.DataFrame([
                {"Ligne": "Recettes", "Montant (€)": total_ca_display},
                {"Ligne": "Dépenses", "Montant (€)": -total_dep},
                {"Ligne": "Solde net", "Montant (€)": solde_net},
            ])
            _afficher_tableau_detail(tableau_actif, "Bilan net de la saison", df_solde)

    # --- Répartition par société ---
    st.divider()
    st.markdown("### 🏢 Répartition par Société")
    repartition = repartition_par_societe(bilan["participations_retenues"], mode)
    if repartition:
        df_rep = pd.DataFrame(repartition, columns=["Société", "Montant (€)"])
        st.dataframe(
            df_rep.style.format({"Montant (€)": "{:,.2f} €"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Aucune donnée pour cette sélection.")

    # --- Graphique chronologique + seuil de rentabilité ---
    st.divider()
    st.markdown(f"### 📈 Chronologie des Recettes ({mode_bilan}) & Seuil de Rentabilité")

    recettes_mois = recettes_par_mois(croisieres, sel_y, mode)
    df_graph = pd.DataFrame({
        "Mois": range(1, 13), "NomMois": ORDRE_MOIS,
        "Recettes": recettes_mois, "Dépenses": montants_maint_mois,
    })
    df_graph["Recettes_Cumulees"] = df_graph["Recettes"].cumsum()

    maintenant = datetime.now()
    if sel_y == maintenant.year:
        df_graph["Recettes_Cumulees_Visuel"] = df_graph.apply(
            lambda x: x["Recettes_Cumulees"] if x["Mois"] <= maintenant.month else None, axis=1
        )
    else:
        df_graph["Recettes_Cumulees_Visuel"] = df_graph["Recettes_Cumulees"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df_graph["NomMois"], y=df_graph["Recettes"], name="Recettes du Mois (€)",
                          marker_color="#a3e4d7", opacity=0.5), secondary_y=False)
    fig.add_trace(go.Bar(x=df_graph["NomMois"], y=df_graph["Dépenses"], name="Dépenses du Mois (€)",
                          marker_color="#f5b7b1", opacity=0.5), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df_graph["NomMois"], y=df_graph["Recettes_Cumulees_Visuel"], name="Cumul de la Saison (€)",
        line=dict(color="#2ecc71", width=4, shape="spline"), mode="lines+markers+text",
        text=[f"{v:,.0f}€" if (v is not None and v > 0) else "" for v in df_graph["Recettes_Cumulees_Visuel"]],
        textposition="top center",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df_graph["NomMois"], y=[total_frais_fixes] * 12, name="Seuil de Rentabilité",
        line=dict(color="#e74c3c", width=2, dash="dash"), mode="lines",
    ), secondary_y=False)

    fig.update_layout(
        height=400, barmode="group", margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=1.2, x=0),
        yaxis=dict(title="Montants (€)", gridcolor="#eee"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Seuil de rentabilité (résumé) ---
    st.divider()
    st.markdown("### ⚓ Seuil de Rentabilité (Point Mort Annuel)")
    ca_actuel = bilan["total_encaisse"]
    progression = min(1.0, ca_actuel / total_frais_fixes) if total_frais_fixes > 0 else 0
    manque_a_gagner = max(0.0, total_frais_fixes - ca_actuel)

    c_pm1, c_pm2 = st.columns([2, 1])
    with c_pm1:
        st.write(f"**Objectif : Couvrir les charges prévisionnelles de l'année ({int(total_frais_fixes):,} €)**".replace(",", " "))
        st.progress(progression)
        if progression >= 1:
            st.success(f"🎉 **Seuil de rentabilité atteint !** pour {sel_y}.")
        else:
            st.info(f"Il manque encore **{int(manque_a_gagner):,} €** pour équilibrer le budget annuel théorique.".replace(",", " "))
    with c_pm2:
        with st.expander("Détail des charges de référence"):
            for poste, montant in frais_params.items():
                st.write(f"{poste} : {int(montant):,} €".replace(",", " "))
            st.write("---")
            st.write(f"**TOTAL : {int(total_frais_fixes):,} €**".replace(",", " "))

    st.caption("📌 Tableaux détaillés (sommes perçues/à percevoir ligne par ligne, détail maintenance) et éditeur des charges fixes : à venir dans une prochaine étape.")
 
