"""
page_modifier_croisiere.py
============================
Formulaire de création/édition d'une croisière — VERSION 2 : gère un
nombre libre de participants (ex: Benoît Couronne + Pedro Bandim
Faustino sur la même croisière), chacun avec son propre contact, société,
prix et statut (terminée/payée/annulée).

Choix technique : pas de st.form() global ici, contrairement aux autres
pages. Les formulaires Streamlit exigent que leur contenu soit figé (pas
de bouton qui change le nombre de lignes à l'intérieur) — or on doit
justement pouvoir ajouter/retirer des participants dynamiquement. Les
widgets sont donc "en direct" (chaque changement déclenche un rerun), et
un bouton "💾 Enregistrer" explicite valide le tout à la fin.

st.session_state.edit_croisiere_id :
    - None        -> mode CRÉATION
    - "cr-xxxxxx" -> mode ÉDITION de cette croisière

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES (liste),
FACT, STATS, ARCHIVES.
"""
import streamlit as st

from modele_voile import (
    generer_id_croisiere, generer_id_contact, rechercher_contacts,
    valider_croisiere, nb_personnes_a_bord, CAPACITE_MAX_BATEAU,
)

SOCIETES = ["PERSO", "CLICK", "CMN", "VOG"]


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


def _participant_vide():
    return {
        "contact_id": None, "societe": "PERSO", "prix": 0.0,
        "terminee": False, "payee": False, "annulee": False, "accompagnants": [],
    }


def _initialiser_liste_participants(croisiere_existante):
    """Charge les participants dans st.session_state UNE SEULE FOIS par
    croisière ouverte (sinon, à chaque rerun, on écraserait les ajouts/
    retraits en cours avec les données d'origine)."""
    cle_source = croisiere_existante["id"] or "NOUVELLE_CROISIERE"
    if st.session_state.get("participants_source_id") != cle_source:
        st.session_state["participants_source_id"] = cle_source
        participants_depart = croisiere_existante.get("participants") or []
        st.session_state["participants_liste"] = (
            [dict(p) for p in participants_depart] if participants_depart else [_participant_vide()]
        )
    return st.session_state["participants_liste"]


def _zone_choix_contact(index, p, contacts, sauvegarder_contacts, charger_contacts):
    """Zone de recherche/création de contact pour LE participant numéro
    `index`. Modifie p['contact_id'] directement (p est déjà l'élément de
    la liste en session_state, donc la modification est conservée)."""
    with st.expander("🔍 Rechercher ou créer un contact pour ce participant"):
        recherche = st.text_input("Nom ou prénom", key=f"recherche_part_{index}")
        resultats = rechercher_contacts(contacts, recherche)
        if recherche and not resultats:
            st.warning("Aucun contact trouvé.")
        for c in resultats:
            deja = c["id"] == p.get("contact_id")
            if st.button(f"{'✅ Déjà choisi : ' if deja else 'Choisir '}{c['prenom']} {c['nom']}",
                         key=f"choisir_part_{index}_{c['id']}", disabled=deja):
                p["contact_id"] = c["id"]
                st.rerun()

        st.caption("— ou créer un nouveau contact —")
        with st.form(key=f"form_nouveau_contact_{index}"):
            np_prenom = st.text_input("Prénom", key=f"np_prenom_{index}")
            np_nom = st.text_input("Nom", key=f"np_nom_{index}")
            creer = st.form_submit_button("➕ Créer et choisir")
        if creer:
            if not np_prenom.strip() or not np_nom.strip():
                st.error("Prénom et nom obligatoires.")
            else:
                nouveau = {
                    "id": generer_id_contact(), "prenom": np_prenom.strip(), "nom": np_nom.strip(),
                    "telephone": "", "email": "", "adresse": "", "notes": "",
                    "habitue": "Non", "photos": [],
                }
                tous_contacts = charger_contacts()
                tous_contacts.append(nouveau)
                sauvegarder_contacts(tous_contacts)
                p["contact_id"] = nouveau["id"]
                st.success(f"Contact {np_prenom} {np_nom} créé et choisi.")
                st.rerun()


def _carte_participant(index, p, contacts_par_id, contacts, sauvegarder_contacts, charger_contacts, autoriser_retrait):
    """Affiche et édite un participant : contact, société, prix, statut,
    bouton de retrait."""
    contact = contacts_par_id.get(p.get("contact_id"))
    with st.container(border=True):
        if contact:
            st.success(f"👤 **{contact['prenom']} {contact['nom']}**")
        else:
            st.warning("👤 Aucun contact choisi pour ce participant.")

        _zone_choix_contact(index, p, contacts, sauvegarder_contacts, charger_contacts)

        c1, c2 = st.columns(2)
        p["societe"] = c1.selectbox(
            "Société", SOCIETES,
            index=SOCIETES.index(p["societe"]) if p.get("societe") in SOCIETES else 0,
            key=f"societe_{index}",
        )
        p["prix"] = c2.number_input("Prix (€)", min_value=0.0, value=float(p.get("prix", 0.0)),
                                     step=10.0, key=f"prix_{index}")

        c3, c4, c5 = st.columns(3)
        p["terminee"] = c3.checkbox("✅ Terminée", value=bool(p.get("terminee")), key=f"terminee_{index}")
        p["payee"] = c4.checkbox("💰 Payée", value=bool(p.get("payee")), key=f"payee_{index}")
        p["annulee"] = c5.checkbox("❌ Annulée", value=bool(p.get("annulee")), key=f"annulee_{index}")

        if autoriser_retrait:
            if st.button("🗑️ Retirer ce participant", key=f"retirer_{index}"):
                st.session_state["participants_liste"].pop(index)
                st.rerun()


def afficher_page_modifier_croisiere(charger_croisieres, sauvegarder_croisieres,
                                      charger_contacts, sauvegarder_contacts):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py,
    même principe que pour les contacts."""

    croisieres = charger_croisieres()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}
    croisiere_id = st.session_state.get("edit_croisiere_id")
    mode_creation = croisiere_id is None

    st.markdown("## ⛵ Nouvelle croisière" if mode_creation else "## ✏️ Modifier la croisière")

    if mode_creation:
        croisiere_existante = {"id": None, "nom_croisiere": "", "date_debut": "", "jours": 1, "notes": "", "participants": []}
    else:
        croisiere_existante = _trouver_croisiere(croisieres, croisiere_id)
        if croisiere_existante is None:
            st.error("Cette croisière n'existe plus (elle a peut-être été supprimée entre-temps).")
            if st.button("↩️ Retour au planning"):
                st.session_state.page = "PLANNING"
                st.rerun()
            return

    participants_liste = _initialiser_liste_participants(croisiere_existante)

    nom_croisiere = st.text_input("Nom de la croisière", value=croisiere_existante.get("nom_croisiere", ""), key="nom_croisiere_edit")
    date_debut = st.text_input("Date de début (jj/mm/aaaa)", value=croisiere_existante.get("date_debut", ""), key="date_debut_edit")
    jours = st.number_input("Nombre de jours", min_value=1, value=int(croisiere_existante.get("jours", 1)), step=1, key="jours_edit")
    notes = st.text_area("Notes", value=croisiere_existante.get("notes", ""), key="notes_edit")

    st.markdown(f"### 👥 Participants ({len(participants_liste)})")

    nb_total = nb_personnes_a_bord({"participants": participants_liste})
    if nb_total > CAPACITE_MAX_BATEAU:
        st.error(f"⚠️ {nb_total} personnes à bord (vous compris) — maximum {CAPACITE_MAX_BATEAU} !")
    else:
        st.caption(f"🚢 {nb_total} / {CAPACITE_MAX_BATEAU} personnes à bord (vous compris)")

    i = 0
    while i < len(participants_liste):
        _carte_participant(i, participants_liste[i], contacts_par_id, contacts,
                            sauvegarder_contacts, charger_contacts,
                            autoriser_retrait=len(participants_liste) > 1)
        i += 1

    if st.button("➕ Ajouter un participant"):
        st.session_state["participants_liste"].append(_participant_vide())
        st.rerun()

    st.divider()
    col_ok, col_annuler = st.columns(2)
    enregistrer = col_ok.button("💾 Enregistrer", use_container_width=True)
    annuler = col_annuler.button("❌ Annuler", use_container_width=True)

    if annuler:
        st.session_state.pop("participants_source_id", None)
        st.session_state.pop("participants_liste", None)
        st.session_state.page = "PLANNING"
        st.rerun()

    if enregistrer:
        croisiere_a_sauver = {
            "id": croisiere_existante["id"] or generer_id_croisiere(),
            "nom_croisiere": nom_croisiere.strip(),
            "date_debut": date_debut.strip(),
            "jours": int(jours),
            "notes": notes.strip(),
            "participants": st.session_state["participants_liste"],
        }
        erreurs = valider_croisiere(croisiere_a_sauver)
        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            croisieres_mises_a_jour = _sauvegarder_une_croisiere(croisieres, croisiere_a_sauver)
            sauvegarder_croisieres(croisieres_mises_a_jour)
            st.session_state.pop("participants_source_id", None)
            st.session_state.pop("participants_liste", None)
            st.success("Croisière enregistrée.")
            st.session_state.page = "PLANNING"
            st.rerun()

    if st.button("↩️ Retour au planning sans enregistrer"):
        st.session_state.pop("participants_source_id", None)
        st.session_state.pop("participants_liste", None)
        st.session_state.page = "PLANNING"
        st.rerun()
