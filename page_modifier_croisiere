"""
page_modifier_croisiere.py
============================
Formulaire de création/édition d'une croisière.

VERSION 1 : un seul participant principal par croisière. La gestion
multi-participants (comme Benoît Couronne + Pedro Bandim Faustino) et les
accompagnants viendront dans une prochaine étape, une fois cette version
simple testée et validée.

st.session_state.edit_croisiere_id :
    - None        -> mode CRÉATION
    - "cr-xxxxxx" -> mode ÉDITION de cette croisière

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, FACT, STATS, ARCHIVES.
"""
import streamlit as st

from modele_voile import (
    generer_id_croisiere, generer_id_contact, rechercher_contacts,
    valider_croisiere,
)


def _trouver_croisiere(croisieres, croisiere_id):
    for cr in croisieres:
        if cr["id"] == croisiere_id:
            return cr
    return None


def _sauvegarder_une_croisiere(croisieres, croisiere_modifiee):
    """Remplace (ou ajoute) une croisière dans la liste complète. Ne
    touche à AUCUNE autre croisière — important car sauvegarder_croisieres
    réécrit tout le fichier d'un coup."""
    croisieres = [cr for cr in croisieres if cr["id"] != croisiere_modifiee["id"]]
    croisieres.append(croisiere_modifiee)
    return croisieres


def _choisir_participant(contacts, participant_actuel, sauvegarder_contacts, charger_contacts):
    """Zone de choix du participant principal : recherche parmi les
    contacts existants, ou création d'un nouveau contact à la volée.
    Renvoie le contact_id choisi (ou celui déjà en place si rien ne change)."""
    contact_id_actuel = participant_actuel.get("contact_id")
    contacts_par_id = {c["id"]: c for c in contacts}
    contact_actuel = contacts_par_id.get(contact_id_actuel)

    if contact_actuel:
        st.info(f"👤 Participant actuel : **{contact_actuel['prenom']} {contact_actuel['nom']}**")

    with st.expander("🔍 Changer / choisir le participant"):
        recherche = st.text_input("Rechercher un contact existant (nom ou prénom)", key="recherche_participant")
        resultats = rechercher_contacts(contacts, recherche)

        if recherche and not resultats:
            st.warning("Aucun contact trouvé.")

        for c in resultats:
            if st.button(f"✅ Choisir {c['prenom']} {c['nom']}", key=f"choisir_{c['id']}"):
                st.session_state["participant_contact_id_temp"] = c["id"]
                st.rerun()

        st.caption("— ou —")
        with st.form(key="form_nouveau_contact_rapide"):
            np_prenom = st.text_input("Prénom du nouveau contact")
            np_nom = st.text_input("Nom du nouveau contact")
            creer = st.form_submit_button("➕ Créer ce contact et le choisir")
        if creer:
            if not np_prenom.strip() or not np_nom.strip():
                st.error("Prénom et nom obligatoires pour créer un contact.")
            else:
                nouveau = {
                    "id": generer_id_contact(), "prenom": np_prenom.strip(), "nom": np_nom.strip(),
                    "telephone": "", "email": "", "adresse": "", "notes": "",
                    "habitue": "Non", "photos": [],
                }
                tous_contacts = charger_contacts()
                tous_contacts.append(nouveau)
                sauvegarder_contacts(tous_contacts)
                st.session_state["participant_contact_id_temp"] = nouveau["id"]
                st.success(f"Contact {np_prenom} {np_nom} créé.")
                st.rerun()

    # Le choix temporaire (via recherche ou création) prend le pas sur
    # l'ancien participant, une fois qu'un choix a été fait
    return st.session_state.get("participant_contact_id_temp") or contact_id_actuel


def afficher_page_modifier_croisiere(charger_croisieres, sauvegarder_croisieres,
                                      charger_contacts, sauvegarder_contacts):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py,
    même principe que pour les contacts."""

    croisieres = charger_croisieres()
    contacts = charger_contacts()
    croisiere_id = st.session_state.get("edit_croisiere_id")
    mode_creation = croisiere_id is None

    st.markdown("## ⛵ Nouvelle croisière" if mode_creation else "## ✏️ Modifier la croisière")

    if mode_creation:
        croisiere_existante = {
            "id": None, "nom_croisiere": "", "date_debut": "", "jours": 1,
            "notes": "", "participants": [{
                "contact_id": None, "societe": "PERSO", "prix": 0.0,
                "terminee": False, "payee": False, "annulee": False, "accompagnants": [],
            }],
        }
    else:
        croisiere_existante = _trouver_croisiere(croisieres, croisiere_id)
        if croisiere_existante is None:
            st.error("Cette croisière n'existe plus (elle a peut-être été supprimée entre-temps).")
            if st.button("↩️ Retour au planning"):
                st.session_state.page = "PLANNING"
                st.rerun()
            return

    participant = croisiere_existante["participants"][0] if croisiere_existante["participants"] else {
        "contact_id": None, "societe": "PERSO", "prix": 0.0,
        "terminee": False, "payee": False, "annulee": False, "accompagnants": [],
    }

    contact_id_choisi = _choisir_participant(contacts, participant, sauvegarder_contacts, charger_contacts)

    with st.form(key="form_croisiere"):
        nom_croisiere = st.text_input("Nom de la croisière", value=croisiere_existante.get("nom_croisiere", ""))
        date_debut = st.text_input("Date de début (jj/mm/aaaa)", value=croisiere_existante.get("date_debut", ""))
        jours = st.number_input("Nombre de jours", min_value=1, value=int(croisiere_existante.get("jours", 1)), step=1)
        societe = st.selectbox("Société", ["PERSO", "CLICK", "CMN", "VOG"],
                                index=["PERSO", "CLICK", "CMN", "VOG"].index(participant.get("societe", "PERSO"))
                                if participant.get("societe") in ["PERSO", "CLICK", "CMN", "VOG"] else 0)
        prix = st.number_input("Prix (€)", min_value=0.0, value=float(participant.get("prix", 0.0)), step=10.0)

        c1, c2, c3 = st.columns(3)
        terminee = c1.checkbox("✅ Terminée", value=bool(participant.get("terminee")))
        payee = c2.checkbox("💰 Payée", value=bool(participant.get("payee")))
        annulee = c3.checkbox("❌ Annulée", value=bool(participant.get("annulee")))

        notes = st.text_area("Notes", value=croisiere_existante.get("notes", ""))

        col_ok, col_annuler = st.columns(2)
        enregistrer = col_ok.form_submit_button("💾 Enregistrer", use_container_width=True)
        annuler = col_annuler.form_submit_button("❌ Annuler", use_container_width=True)

    if annuler:
        st.session_state.pop("participant_contact_id_temp", None)
        st.session_state.page = "PLANNING"
        st.rerun()

    if enregistrer:
        croisiere_a_sauver = {
            "id": croisiere_existante["id"] or generer_id_croisiere(),
            "nom_croisiere": nom_croisiere.strip(),
            "date_debut": date_debut.strip(),
            "jours": int(jours),
            "notes": notes.strip(),
            "participants": [{
                "contact_id": contact_id_choisi,
                "societe": societe,
                "prix": float(prix),
                "terminee": terminee,
                "payee": payee,
                "annulee": annulee,
                "accompagnants": participant.get("accompagnants", []),
            }],
        }
        erreurs = valider_croisiere(croisiere_a_sauver)
        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            croisieres_mises_a_jour = _sauvegarder_une_croisiere(croisieres, croisiere_a_sauver)
            sauvegarder_croisieres(croisieres_mises_a_jour)
            st.session_state.pop("participant_contact_id_temp", None)
            st.success("Croisière enregistrée.")
            st.session_state.page = "PLANNING"
            st.rerun()

    if st.button("↩️ Retour au planning sans enregistrer"):
        st.session_state.pop("participant_contact_id_temp", None)
        st.session_state.page = "PLANNING"
        st.rerun()
