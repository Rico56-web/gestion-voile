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
    contact_existant_similaire,
)

SOCIETES = ["PERSO", "CLICK", "CMN", "VOG"]

COULEURS_PARTICIPANT = ["#2980B9", "#27AE60", "#8E44AD", "#D35400", "#C0392B", "#16A085"]


def _injecter_style_cartes():
    """Renforce visuellement les cartes participants : le contour par
    défaut de st.container(border=True) est trop fin (1px gris clair,
    à peine visible). On l'épaissit et on l'arrondit."""
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 3px solid #2980B9 !important;
            border-radius: 12px !important;
            padding: 6px !important;
            margin-bottom: 14px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
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


def _participant_vide():
    return {
        "contact_id": None, "societe": "PERSO", "prix": 0.0, "acompte": 0.0,
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


def _creer_et_choisir_contact(index, p, prenom, nom, sauvegarder_contacts, charger_contacts):
    """Crée un nouveau contact et le choisit pour ce participant. Centralisé
    ici car appelé depuis 2 endroits : création directe (pas de doublon
    détecté) et création forcée après confirmation d'un doublon."""
    nouveau = {
        "id": generer_id_contact(), "prenom": prenom.strip(), "nom": nom.strip(),
        "telephone": "", "email": "", "adresse": "", "notes": "",
        "habitue": "Non", "photos": [],
    }
    tous_contacts = charger_contacts()
    tous_contacts.append(nouveau)
    sauvegarder_contacts(tous_contacts)
    p["contact_id"] = nouveau["id"]
    st.toast(f"Contact {prenom} {nom} créé et choisi.", icon="👤")
    st.rerun()


def _zone_choix_contact(index, p, contacts, sauvegarder_contacts, charger_contacts):
    """Zone de recherche/création de contact pour LE participant numéro
    `index`. Modifie p['contact_id'] directement (p est déjà l'élément de
    la liste en session_state, donc la modification est conservée).

    Ouverte AUTOMATIQUEMENT tant qu'aucun contact n'est choisi (sinon ce
    participant ressemble à une ligne vide sans rien à cliquer, facile à
    manquer — c'est ce qui rendait la page confuse)."""
    deja_un_contact = bool(p.get("contact_id"))
    titre = "🔍 Changer le contact" if deja_un_contact else "🔍 Choisis ou crée un contact pour ce participant"
    with st.expander(titre, expanded=not deja_un_contact):
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
                doublon = contact_existant_similaire(contacts, np_prenom, np_nom)
                if doublon:
                    st.session_state[f"doublon_en_attente_{index}"] = {
                        "prenom": np_prenom.strip(), "nom": np_nom.strip(), "existant": doublon,
                    }
                    st.rerun()
                else:
                    _creer_et_choisir_contact(index, p, np_prenom, np_nom, sauvegarder_contacts, charger_contacts)

        # --- Avertissement de doublon, en attente de confirmation ---
        attente = st.session_state.get(f"doublon_en_attente_{index}")
        if attente:
            existant = attente["existant"]
            st.warning(
                f"⚠️ Un contact nommé **{existant['prenom']} {existant['nom']}** existe déjà "
                f"(tél: {existant.get('telephone') or '—'}). Est-ce la même personne ?"
            )
            cb1, cb2 = st.columns(2)
            if cb1.button("✅ C'est lui, je le choisis", key=f"choisir_existant_{index}"):
                p["contact_id"] = existant["id"]
                st.session_state.pop(f"doublon_en_attente_{index}")
                st.rerun()
            if cb2.button("➕ Non, créer quand même", key=f"forcer_creation_{index}"):
                _creer_et_choisir_contact(index, p, attente["prenom"], attente["nom"], sauvegarder_contacts, charger_contacts)
                st.session_state.pop(f"doublon_en_attente_{index}")


def _carte_participant(index, p, contacts_par_id, contacts, sauvegarder_contacts, charger_contacts, autoriser_retrait):
    """Affiche et édite un participant : contact, société, prix, statut,
    bouton de retrait."""
    contact = contacts_par_id.get(p.get("contact_id"))
    couleur = COULEURS_PARTICIPANT[index % len(COULEURS_PARTICIPANT)]
    with st.container(border=True):
        st.markdown(
            f"""<div style="background:{couleur}; color:white; padding:6px 14px;
            border-radius:8px; font-weight:bold; margin-bottom:10px; display:inline-block;">
            👤 Participant {index + 1}</div>""",
            unsafe_allow_html=True,
        )
        if contact:
            st.success(f"**{contact['prenom']} {contact['nom']}**")
        else:
            st.warning("Pas encore de contact choisi — utilise la recherche ci-dessous ⬇️")

        _zone_choix_contact(index, p, contacts, sauvegarder_contacts, charger_contacts)

        c1, c2, c3 = st.columns(3)
        p["societe"] = c1.selectbox(
            "Société", SOCIETES,
            index=SOCIETES.index(p["societe"]) if p.get("societe") in SOCIETES else 0,
            key=f"societe_{index}",
        )
        p["prix"] = c2.number_input("Prix (€)", min_value=0.0, value=float(p.get("prix", 0.0)),
                                     step=10.0, key=f"prix_{index}")
        p["acompte"] = c3.number_input(
            "Acompte versé (€)", min_value=0.0, value=float(p.get("acompte", 0.0)),
            step=10.0, key=f"acompte_{index}",
            help="Montant déjà reçu si la case 'Payée' n'est pas cochée. Une fois 'Payée' cochée, c'est le prix entier qui compte, pas l'acompte.",
        )

        c4, c5, c6 = st.columns(3)
        p["terminee"] = c4.checkbox("✅ Terminée", value=bool(p.get("terminee")), key=f"terminee_{index}")
        p["payee"] = c5.checkbox("💰 Payée", value=bool(p.get("payee")), key=f"payee_{index}")
        p["annulee"] = c6.checkbox("❌ Annulée", value=bool(p.get("annulee")), key=f"annulee_{index}")

        if not p["payee"] and p["prix"] > 0 and p["acompte"] >= p["prix"]:
            st.warning(
                "⚠️ L'acompte versé couvre déjà tout le prix, mais 'Payée' n'est pas cochée. "
                "Si c'est réglé, coche 'Payée'. Sinon, vérifie le montant de l'acompte."
            )

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
    _injecter_style_cartes()

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
            st.toast("Croisière enregistrée.", icon="💾")
            st.session_state.page = "PLANNING"
            st.rerun()

    if st.button("↩️ Retour au planning sans enregistrer"):
        st.session_state.pop("participants_source_id", None)
        st.session_state.pop("participants_liste", None)
        st.session_state.page = "PLANNING"
        st.rerun()
