"""
page_contacts.py
=================
Page CONTACTS (liste + recherche + filtres + fiches), nouveau modèle
séparé (contacts.json / croisieres.json / interets.json).

À intégrer dans app_voile1.py : remplace le bloc actuel
    if st.session_state.page == "CONTACTS": ...
par un appel à afficher_page_contacts().

NE TOUCHE PAS à MODIFIER_CONTACT, PLANNING, FACT, STATS, ARCHIVES :
ces pages restent à migrer dans de prochains échanges (chacune sera
signalée avec ses propres risques de régression avant modification).
"""
import streamlit as st
from modele_voile import (
    croisieres_du_contact, interets_du_contact, sommes_percues,
    filtres_contact, tri_alphabetique, contact_correspond_recherche,
    est_en_cours, est_classee,
)


def _initiales_couleur(contact):
    """Couleur de cadre stable par contact (pas par société, puisqu'un
    contact peut naviguer avec plusieurs sociétés différentes)."""
    palette = ["#2980B9", "#27AE60", "#8E44AD", "#D35400", "#16A085", "#C0392B"]
    cle = (contact.get("nom", "") + contact.get("prenom", ""))
    return palette[hash(cle) % len(palette)]


def _carte_contact(numero, contact, croisieres_c, interets_c):
    """Affiche une fiche contact dans un cadre épais (5px), avec toutes
    les infos et actions demandées."""
    couleur = _initiales_couleur(contact)
    badge_pref = "⭐ " if str(contact.get("habitue", "")).strip().lower() in ("oui", "true", "1") else ""

    filtres = filtres_contact(croisieres_c, interets_c)
    badges_auto = []
    if filtres["en_cours"]:
        badges_auto.append("🟢 En cours")
    if filtres["habitue_auto"]:
        badges_auto.append("⭐ Habitué")
    if filtres["passe"]:
        badges_auto.append("⚪ Passé")
    if filtres["sans_suite"]:
        badges_auto.append("👻 Sans suite")

    total_percu = sommes_percues(croisieres_c)

    with st.container(border=False):
        st.markdown(
            f"""
            <div style="border:5px solid {couleur}; border-radius:12px; padding:14px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:baseline;">
                    <b style="font-size:1.05rem;">#{numero} — {badge_pref}{contact.get('prenom','')} {contact.get('nom','')}</b>
                </div>
                <div style="margin-top:4px; font-size:0.9rem; color:#555;">
                    📞 {contact.get('telephone') or '—'} &nbsp;|&nbsp; ✉️ {contact.get('email') or '—'}
                </div>
                <div style="margin-top:6px;">{' '.join(f'<span style="background:#eee; border-radius:6px; padding:2px 8px; font-size:0.75rem; margin-right:4px;">{b}</span>' for b in badges_auto)}</div>
                <div style="margin-top:8px; font-size:0.9rem;">
                    💰 <b>Total perçu : {total_percu:.0f} €</b> &nbsp;|&nbsp; 🧭 {len(croisieres_c)} navigation(s)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- Photos (1 à 2 max) ---
        photos = contact.get("photos") or []
        if photos:
            cols_photo = st.columns(len(photos))
            for col, chemin in zip(cols_photo, photos):
                try:
                    col.image(chemin, use_container_width=True)
                except Exception:
                    pass

        # --- 3 boutons d'appel direct ---
        tel = (contact.get("telephone") or "").replace(" ", "")
        email = contact.get("email") or ""
        c1, c2, c3 = st.columns(3)
        if tel:
            c1.link_button("📞 Appeler", f"tel:{tel}", use_container_width=True)
        else:
            c1.button("📞 Appeler", use_container_width=True, disabled=True, key=f"tel_off_{contact['id']}")
        if email:
            c2.link_button("✉️ Email", f"mailto:{email}", use_container_width=True)
        else:
            c2.button("✉️ Email", use_container_width=True, disabled=True, key=f"mail_off_{contact['id']}")
        if tel:
            c3.link_button("💬 WhatsApp", f"https://wa.me/{tel.lstrip('0').lstrip('+')}", use_container_width=True)
        else:
            c3.button("💬 WhatsApp", use_container_width=True, disabled=True, key=f"wa_off_{contact['id']}")

        # --- Notes ---
        if contact.get("notes"):
            st.caption(f"📝 {contact['notes']}")

        # --- Historique des navigations (calculé, jamais stocké) ---
        if croisieres_c:
            with st.expander(f"🧭 Historique des navigations ({len(croisieres_c)})"):
                for c in croisieres_c:
                    p = c["ma_participation"]
                    if p.get("annulee"):
                        etat = "⚪ Annulée"
                    elif est_classee(p):
                        etat = "✅ Classée"
                    elif est_en_cours(p):
                        etat = "🟢 En cours"
                    else:
                        etat = "—"
                    nom_nav = c.get("nom_croisiere") or "(sans nom)"
                    st.write(f"**{c.get('date_debut','?')}** — {nom_nav} — {p.get('societe','')} — {p.get('prix',0):.0f}€ — {etat}")

        # --- Modifier / Supprimer (numéro de fiche intégré aux boutons) ---
        cb1, cb2 = st.columns(2)
        if cb1.button(f"✏️ Modifier #{numero}", key=f"ed_{contact['id']}", use_container_width=True):
            st.session_state.edit_contact_id = contact["id"]
            st.session_state.page = "MODIFIER_CONTACT"
            st.rerun()

        cle_confirm = f"confirm_del_{contact['id']}"
        if cle_confirm not in st.session_state:
            if cb2.button(f"🗑️ Supprimer #{numero}", key=f"del_{contact['id']}", use_container_width=True):
                st.session_state[cle_confirm] = True
                st.rerun()
        else:
            st.warning(f"Confirmer la suppression de {contact.get('prenom')} {contact.get('nom')} ?")
            cx, cy = st.columns(2)
            if cx.button("✅ Oui, supprimer", key=f"y_{contact['id']}", use_container_width=True):
                st.session_state.pop(cle_confirm)
                st.session_state.contact_id_a_supprimer = contact["id"]
                st.rerun()
            if cy.button("❌ Annuler", key=f"n_{contact['id']}", use_container_width=True):
                st.session_state.pop(cle_confirm)
                st.rerun()


def afficher_page_contacts(charger_contacts, charger_croisieres, charger_interets, sauvegarder_contacts):
    """Point d'entrée de la page. Les 3 fonctions de chargement et la
    fonction de sauvegarde sont injectées depuis app_voile1.py pour
    réutiliser telles quelles tes fonctions GitHub existantes."""

    st.markdown("## 👥 Contacts")

    contacts = charger_contacts()
    croisieres = charger_croisieres()
    interets = charger_interets()

    # --- Suppression différée (demandée au tour précédent) ---
    if st.session_state.get("contact_id_a_supprimer"):
        cid = st.session_state.pop("contact_id_a_supprimer")
        contacts = [c for c in contacts if c["id"] != cid]
        sauvegarder_contacts(contacts)
        st.success("Contact supprimé.")
        st.rerun()

    # --- Barre de recherche + filtres + nouveau contact ---
    if "filtres_actifs" not in st.session_state:
        st.session_state.filtres_actifs = set()  # filtres combinables, aucun par défaut = "tous"

    c_recherche, c_nouveau = st.columns([3, 1])
    recherche = c_recherche.text_input("🔍 Rechercher (nom, prénom, société)", "", key="recherche_contacts")
    if c_nouveau.button("➕ Nouveau contact", use_container_width=True):
        st.session_state.edit_contact_id = None  # None = création
        st.session_state.page = "MODIFIER_CONTACT"
        st.rerun()

    st.caption("Filtres (cumulables — clique pour activer/désactiver) :")
    noms_filtres = [("en_cours", "🟢 En cours"), ("habitue_auto", "⭐ Habitué"),
                     ("passe", "⚪ Passé"), ("sans_suite", "👻 Sans suite")]
    cols_f = st.columns(len(noms_filtres))
    for col, (cle, label) in zip(cols_f, noms_filtres):
        actif = cle in st.session_state.filtres_actifs
        if col.button(label, key=f"filtre_{cle}", use_container_width=True,
                      type="primary" if actif else "secondary"):
            if actif:
                st.session_state.filtres_actifs.discard(cle)
            else:
                st.session_state.filtres_actifs.add(cle)
            st.rerun()

    if st.button("↩️ Retour", key="retour_contacts"):
        st.session_state.filtres_actifs = set()
        st.session_state.recherche_contacts = ""
        st.rerun()

    st.divider()

    # --- Application des filtres + recherche ---
    contacts_tries = tri_alphabetique(contacts)
    contacts_affiches = []
    for c in contacts_tries:
        cr_c = croisieres_du_contact(croisieres, c["id"])
        int_c = interets_du_contact(interets, c["id"])

        if not contact_correspond_recherche(c, cr_c, recherche):
            continue

        if st.session_state.filtres_actifs:
            f = filtres_contact(cr_c, int_c)
            if not any(f.get(cle) for cle in st.session_state.filtres_actifs):
                continue

        contacts_affiches.append((c, cr_c, int_c))

    if not contacts_affiches:
        st.info("Aucun contact ne correspond à la recherche/aux filtres actuels.")
        return

    for numero, (c, cr_c, int_c) in enumerate(contacts_affiches, start=1):
        _carte_contact(numero, c, cr_c, int_c)
