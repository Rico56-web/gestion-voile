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

--- Modif du 28/08/2026 ---
Ajout d'un DOUBLE encadrement sur chaque fiche contact : un nouveau
cadre extérieur, plus clair, qui entoure maintenant toute la fiche
(photos, boutons d'appel, historique, modifier/supprimer inclus), en
plus du cadre intérieur épais (5px) déjà existant qui reste inchangé
autour du bloc identité. Aucune autre logique n'a été touchée.
"""
import streamlit as st
from modele_voile import (
    croisieres_du_contact, interets_du_contact, sommes_percues,
    filtres_contact, tri_alphabetique, contact_correspond_recherche,
    est_en_cours, est_classee, fond_clair,
)


def _initiales_couleur(contact):
    """Couleur de cadre stable par contact (pas par société, puisqu'un
    contact peut naviguer avec plusieurs sociétés différentes)."""
    palette = ["#2980B9", "#27AE60", "#8E44AD", "#D35400", "#16A085", "#C0392B"]
    cle = (contact.get("nom", "") + contact.get("prenom", ""))
    return palette[hash(cle) % len(palette)]


# Couleur unique et fixe pour TOUS les boutons de toutes les fiches
# (indépendante de la couleur propre à chaque contact).
COULEUR_BOUTONS = "#B4ACC9"


def _couleur_eclaircie(hex_couleur, taux=0.45):
    """Mélange une couleur hexadécimale avec du blanc pour l'éclaircir,
    afin d'obtenir la couleur du cadre EXTÉRIEUR à partir de la couleur
    du cadre intérieur existant.
    taux=0   -> couleur inchangée
    taux=1   -> blanc pur
    taux=0.45 -> nettement plus clair, mais encore visible comme cadre.
    """
    hex_couleur = hex_couleur.lstrip("#")
    r, g, b = int(hex_couleur[0:2], 16), int(hex_couleur[2:4], 16), int(hex_couleur[4:6], 16)
    r = round(r + (255 - r) * taux)
    g = round(g + (255 - g) * taux)
    b = round(b + (255 - b) * taux)
    return f"#{r:02X}{g:02X}{b:02X}"


COULEURS_BADGES_CONTACT = {
    "🟢 En cours": "#2980B9",
    "⭐ Habitué": "#F1C40F",
    "⚪ Passé": "#7F8C8D",
    "👻 Sans suite": "#95A5A6",
}


def _carte_contact(numero, contact, croisieres_c, interets_c):
    """Affiche une fiche contact avec un DOUBLE cadre :
    - cadre EXTÉRIEUR (nouveau) : couleur éclaircie, entoure toute la
      fiche (photos, boutons d'appel, historique, modifier/supprimer).
    - cadre INTÉRIEUR (existant, inchangé) : épais (5px), autour du
      bloc identité (nom, téléphone, email, badges, total perçu).
    """
    couleur = _initiales_couleur(contact)
    couleur_claire = _couleur_eclaircie(couleur, taux=0.45)  # couleur du TRAIT du cadre extérieur
    fond_exterieur = _couleur_eclaircie(couleur, taux=0.85)  # fond (très pâle) du cadre extérieur
    fond = fond_clair(couleur)  # fond du bloc identité (existant, inchangé)
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
    badges_html = "".join(
        f'<span style="background:{COULEURS_BADGES_CONTACT.get(b, "#BDC3C7")}; color:white; '
        f'border-radius:12px; padding:2px 10px; font-size:0.72rem; font-weight:bold; margin-right:5px;">{b}</span>'
        for b in badges_auto
    )
    total_percu = sommes_percues(croisieres_c)

    # --- Clé unique de cette fiche, utilisée pour cibler le cadre
    # extérieur en CSS (un contact -> une couleur -> un cadre) ---
    # NB (confirmé via l'inspecteur du navigateur le 28/08, panneau Styles) :
    # la bordure par défaut de Streamlit (border=True) est posée
    # DIRECTEMENT sur le div "stVerticalBlock" qui porte notre classe
    # "st-key-...", sans !important. On la cible donc directement, avec
    # !important pour être sûr de l'emporter.
    cle_carte = f"carte_{contact['id']}"
    st.markdown(
        f"""
        <style>
        div.st-key-{cle_carte} {{
            border: 3px solid {couleur_claire} !important;
            border-radius: 16px !important;
            padding: 10px !important;
            margin-bottom: 14px !important;
            background: {fond_exterieur} !important;
        }}
        /* Boutons de cette fiche (Appeler/Email/WhatsApp, Modifier/Supprimer) :
           .stButton et .stLinkButton sont des classes Streamlit stables,
           pas besoin de passer par les classes "st-emotion-cache-..." */
        div.st-key-{cle_carte} .stButton button,
        div.st-key-{cle_carte} .stLinkButton a {{
            background-color: {COULEUR_BOUTONS} !important;
            border: 2px solid {COULEUR_BOUTONS} !important;
            color: #2c3e50 !important;
        }}
        div.st-key-{cle_carte} .stButton button:disabled {{
            background-color: #f0f0f0 !important;
            border-color: #d8d8d8 !important;
            color: #a0a0a0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key=cle_carte, border=True):
        st.markdown(
            f"""
            <div style="border:5px solid {couleur}; border-radius:12px; padding:14px; margin-bottom:12px; background:{fond};">
                <div style="display:flex; justify-content:space-between; align-items:baseline;">
                    <b style="font-size:1.05rem; color:#2c3e50;">#{numero} — {badge_pref}{contact.get('prenom','')} {contact.get('nom','')}</b>
                </div>
                <div style="margin-top:4px; font-size:0.9rem; color:#555;">
                    📞 {contact.get('telephone') or '—'} &nbsp;|&nbsp; ✉️ {contact.get('email') or '—'}
                </div>
                <div style="margin-top:8px;">{badges_html}</div>
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
        a_navigue = len(croisieres_c) > 0
        if a_navigue:
            cb2.button(
                f"🔒 A navigué ({len(croisieres_c)}) — suppr. impossible",
                key=f"del_bloque_{contact['id']}", use_container_width=True, disabled=True,
            )
            st.caption("ℹ️ Ce contact a déjà navigué avec toi — pour préserver l'historique (croisières, livre de bord, statistiques), sa fiche ne peut pas être supprimée.")
        else:
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
        # Double vérification (le bouton est déjà désactivé côté fiche, mais
        # on ne fait jamais confiance uniquement à l'interface) : on
        # n'autorise la suppression que si ce contact n'a AUCUNE croisière.
        if croisieres_du_contact(croisieres, cid):
            st.toast("Suppression refusée : ce contact a déjà navigué.", icon="🔒")
        else:
            contacts = [c for c in contacts if c["id"] != cid]
            sauvegarder_contacts(contacts)
            st.toast("Contact supprimé.", icon="🗑️")
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

    # --- Tri : par nom ou par prénom, au choix ---
    if "tri_contacts" not in st.session_state:
        st.session_state.tri_contacts = "nom"  # comportement par défaut, inchangé
    c_tri1, c_tri2, _ = st.columns([1, 1, 3])
    if c_tri1.button("🔤 Trier par NOM", use_container_width=True,
                      type="primary" if st.session_state.tri_contacts == "nom" else "secondary"):
        st.session_state.tri_contacts = "nom"
        st.rerun()
    if c_tri2.button("🔤 Trier par PRÉNOM", use_container_width=True,
                      type="primary" if st.session_state.tri_contacts == "prenom" else "secondary"):
        st.session_state.tri_contacts = "prenom"
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

    # --- Application du tri, des filtres et de la recherche ---
    contacts_tries = tri_alphabetique(contacts, critere=st.session_state.tri_contacts)
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
