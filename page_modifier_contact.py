"""
page_modifier_contact.py
=========================
Page de création / édition d'une fiche contact.

À intégrer dans app_voile1.py (voir RECAP_SESSION_2026-07-31.md pour le
bloc exact d'intégration) via :
    afficher_page_modifier_contact(charger_contacts, sauvegarder_contacts)

st.session_state.edit_contact_id :
    - None       -> mode CRÉATION
    - "c-xxxxxx" -> mode ÉDITION de ce contact

NE TOUCHE PAS à CONTACTS, PLANNING, FACT, STATS, ARCHIVES.
"""
import streamlit as st

from modele_voile import generer_id_contact, generer_nom_fichier_photo
from stockage_photos import compresser_image, uploader_photo, supprimer_photo

MAX_PHOTOS = 2


def _trouver_contact(contacts, contact_id):
    for c in contacts:
        if c["id"] == contact_id:
            return c
    return None


def _sauvegarder_un_contact(contacts, contact_modifie):
    """Remplace (ou ajoute) un contact dans la liste complète, puis
    renvoie la liste mise à jour. Ne touche à AUCUN autre contact —
    important car sauvegarder_contacts() réécrit tout le fichier."""
    contacts = [c for c in contacts if c["id"] != contact_modifie["id"]]
    contacts.append(contact_modifie)
    return contacts


def _section_photos(contact, sauvegarder_contacts, charger_contacts):
    """Gère l'affichage, l'ajout et la suppression des photos.
    Uniquement disponible une fois le contact enregistré (donc avec un id
    stable), car le nom de fichier photo est construit à partir de l'id."""
    st.markdown("#### 📸 Photos")
    photos = contact.get("photos") or []

    if photos:
        cols = st.columns(len(photos))
        for i, (col, chemin) in enumerate(zip(cols, photos)):
            try:
                col.image(chemin, use_container_width=True)
            except Exception:
                col.caption("(photo pas encore visible : l'app doit redémarrer après l'envoi — normal, patiente une minute puis recharge la page)")
            if col.button("🗑️ Supprimer cette photo", key=f"del_photo_{i}_{contact['id']}", use_container_width=True):
                if supprimer_photo(chemin):
                    contacts = charger_contacts()
                    c = _trouver_contact(contacts, contact["id"])
                    c["photos"] = [p for p in c.get("photos", []) if p != chemin]
                    sauvegarder_contacts(_sauvegarder_un_contact(contacts, c))
                    st.success("Photo supprimée.")
                    st.rerun()

    if len(photos) < MAX_PHOTOS:
        fichier = st.file_uploader(
            f"Ajouter une photo ({len(photos)}/{MAX_PHOTOS})",
            type=["jpg", "jpeg", "png"],
            key=f"upload_photo_{contact['id']}",
        )
        if fichier is not None:
            if st.button("✅ Envoyer cette photo", key=f"envoyer_photo_{contact['id']}"):
                contenu_compresse = compresser_image(fichier)
                nouveau_chemin = generer_nom_fichier_photo(contact["id"], len(photos) + 1)
                if uploader_photo(nouveau_chemin, contenu_compresse):
                    contacts = charger_contacts()
                    c = _trouver_contact(contacts, contact["id"])
                    c.setdefault("photos", []).append(nouveau_chemin)
                    sauvegarder_contacts(_sauvegarder_un_contact(contacts, c))
                    st.success("Photo envoyée. Elle apparaîtra après le redéploiement automatique de l'app (~1 minute).")
                    st.rerun()
    else:
        st.caption(f"Maximum {MAX_PHOTOS} photos atteint. Supprime-en une pour en ajouter une autre.")


def afficher_page_modifier_contact(charger_contacts, sauvegarder_contacts):
    """Point d'entrée de la page. charger_contacts / sauvegarder_contacts
    sont injectées depuis app_voile1.py, comme pour page_contacts.py."""

    contacts = charger_contacts()
    contact_id = st.session_state.get("edit_contact_id")
    mode_creation = contact_id is None

    st.markdown("## ➕ Nouveau contact" if mode_creation else "## ✏️ Modifier le contact")

    if mode_creation:
        contact_existant = {
            "id": None, "prenom": "", "nom": "", "telephone": "", "email": "",
            "adresse": "", "notes": "", "habitue": "Non", "photos": [],
        }
    else:
        contact_existant = _trouver_contact(contacts, contact_id)
        if contact_existant is None:
            st.error("Ce contact n'existe plus (il a peut-être été supprimé entre-temps).")
            if st.button("↩️ Retour à la liste"):
                st.session_state.page = "CONTACTS"
                st.rerun()
            return

    with st.form(key="form_contact"):
        prenom = st.text_input("Prénom *", value=contact_existant.get("prenom", ""))
        nom = st.text_input("Nom *", value=contact_existant.get("nom", ""))
        telephone = st.text_input("Téléphone", value=contact_existant.get("telephone", ""))
        email = st.text_input("Email", value=contact_existant.get("email", ""))
        adresse = st.text_input("Adresse", value=contact_existant.get("adresse", ""))
        notes = st.text_area("Notes", value=contact_existant.get("notes", ""))
        habitue_actuel = str(contact_existant.get("habitue", "Non")).strip().lower() in ("oui", "true", "1")
        habitue = st.checkbox("⭐ Habitué (préférence manuelle)", value=habitue_actuel)

        col_ok, col_annuler = st.columns(2)
        enregistrer = col_ok.form_submit_button("💾 Enregistrer", use_container_width=True)
        annuler = col_annuler.form_submit_button("❌ Annuler", use_container_width=True)

    if annuler:
        st.session_state.page = "CONTACTS"
        st.rerun()

    if enregistrer:
        if not prenom.strip() or not nom.strip():
            st.error("Le prénom et le nom sont obligatoires.")
        else:
            contact_a_sauver = {
                "id": contact_existant["id"] or generer_id_contact(),
                "prenom": prenom.strip(),
                "nom": nom.strip(),
                "telephone": telephone.strip(),
                "email": email.strip(),
                "adresse": adresse.strip(),
                "notes": notes.strip(),
                "habitue": "Oui" if habitue else "Non",
                "photos": contact_existant.get("photos", []),
            }
            contacts_mis_a_jour = _sauvegarder_un_contact(contacts, contact_a_sauver)
            sauvegarder_contacts(contacts_mis_a_jour)
            st.session_state.edit_contact_id = contact_a_sauver["id"]
            st.success("Contact enregistré.")
            st.rerun()

    st.divider()

    if mode_creation:
        st.info("Enregistre d'abord la fiche pour pouvoir ajouter des photos (le nom du fichier photo dépend de l'identifiant du contact, qui n'existe qu'une fois la fiche créée).")
    else:
        _section_photos(contact_existant, sauvegarder_contacts, charger_contacts)

    if st.button("↩️ Retour à la liste des contacts"):
        st.session_state.page = "CONTACTS"
        st.rerun()
