"""
page_croisieres.py
===================
Liste des croisières, filtrée depuis le début de l'année en cours par
défaut (avec option pour voir tout l'historique). Donne accès à la
création d'une nouvelle croisière et à la modification d'une existante.

À intégrer dans app_voile1.py via afficher_page_croisieres().

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, FACT, STATS, ARCHIVES.
"""
from datetime import date

import streamlit as st

from modele_voile import filtrer_temporel, trier_croisieres, noms_participants, couleur_croisiere

OPTIONS_TRI = {
    "date_desc": "🗓️ Date (récent → ancien)",
    "date_asc": "🗓️ Date (ancien → récent)",
    "nom": "🔤 Nom",
    "prenom": "🔤 Prénom",
}


def afficher_page_croisieres(charger_croisieres, sauvegarder_croisieres, charger_contacts):
    """Point d'entrée de la page. charger_croisieres / sauvegarder_croisieres
    / charger_contacts injectées depuis app_voile1.py."""

    st.markdown("## ⛵ Croisières")

    croisieres = charger_croisieres()
    contacts = charger_contacts()
    contacts_par_id = {c["id"]: c for c in contacts}

    # --- Suppression différée (demandée au tour précédent) ---
    if st.session_state.get("croisiere_id_a_supprimer"):
        cid = st.session_state.pop("croisiere_id_a_supprimer")
        croisieres = [cr for cr in croisieres if cr["id"] != cid]
        sauvegarder_croisieres(croisieres)
        st.success("Croisière supprimée.")
        st.rerun()

    if st.button("➕ Nouvelle croisière", use_container_width=True):
        st.session_state.edit_croisiere_id = None
        st.session_state.page = "MODIFIER_CROISIERE"
        st.rerun()

    st.divider()

    # --- Filtre temporel : Toutes / Passées / À venir ---
    if "filtre_temporel_cr" not in st.session_state:
        st.session_state.filtre_temporel_cr = "toutes"

    st.caption("Filtrer :")
    c1, c2, c3 = st.columns(3)
    options_filtre = [("toutes", "📋 Toutes", c1), ("passees", "📅 Passées", c2), ("futures", "🔜 À venir", c3)]
    for cle, label, col in options_filtre:
        actif = st.session_state.filtre_temporel_cr == cle
        if col.button(label, key=f"filtre_temp_{cle}", use_container_width=True,
                      type="primary" if actif else "secondary"):
            st.session_state.filtre_temporel_cr = cle
            # Tri par défaut adapté au filtre : pour "à venir", la sortie la
            # plus proche est ce qu'on veut voir en premier (pas la plus
            # lointaine) ; pour "passées"/"toutes", on garde la convention
            # habituelle de l'appli (le plus récent en tête).
            st.session_state.tri_croisieres = "date_asc" if cle == "futures" else "date_desc"
            st.rerun()

    # --- Tri ---
    if "tri_croisieres" not in st.session_state:
        st.session_state.tri_croisieres = "date_desc"

    tri_choisi = st.selectbox(
        "Trier par",
        options=list(OPTIONS_TRI.keys()),
        format_func=lambda cle: OPTIONS_TRI[cle],
        index=list(OPTIONS_TRI.keys()).index(st.session_state.tri_croisieres),
        key="selectbox_tri_croisieres",
    )
    st.session_state.tri_croisieres = tri_choisi

    st.divider()

    aujourdhui = date.today()
    croisieres_filtrees = filtrer_temporel(croisieres, st.session_state.filtre_temporel_cr, aujourdhui)
    croisieres_affichees = trier_croisieres(croisieres_filtrees, contacts_par_id, st.session_state.tri_croisieres)

    if not croisieres_affichees:
        st.info("Aucune croisière à afficher pour ce filtre.")
        return

    st.caption(f"{len(croisieres_affichees)} croisière(s) affichée(s).")

    for cr in croisieres_affichees:
        couleur = couleur_croisiere(cr)
        prix_total = sum(p.get("prix", 0) or 0 for p in cr.get("participants", []))
        nom_participants = noms_participants(cr, contacts_par_id)
        nom_croisiere = cr.get("nom_croisiere") or "(sans nom)"

        with st.container(border=False):
            st.markdown(
                f"""
                <div style="border-left:8px solid {couleur}; border-radius:8px; padding:10px 14px; margin-bottom:8px; background:#fafafa;">
                    <b>{cr.get('date_debut','?')}</b> — {nom_participants} — {nom_croisiere}
                    <br><span style="font-size:0.85rem; color:#555;">{cr.get('jours',1)} jour(s) · {prix_total:.0f} €</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            c_mod, c_sup = st.columns(2)
            if c_mod.button("✏️ Modifier", key=f"ed_cr_{cr['id']}", use_container_width=True):
                st.session_state.edit_croisiere_id = cr["id"]
                st.session_state.page = "MODIFIER_CROISIERE"
                st.rerun()

            cle_confirm = f"confirm_del_cr_{cr['id']}"
            if cle_confirm not in st.session_state:
                if c_sup.button("🗑️ Supprimer", key=f"del_cr_{cr['id']}", use_container_width=True):
                    st.session_state[cle_confirm] = True
                    st.rerun()
            else:
                st.warning(f"Confirmer la suppression de la croisière du {cr.get('date_debut','?')} ({nom_participants}) ?")
                cx, cy = st.columns(2)
                if cx.button("✅ Oui, supprimer", key=f"y_cr_{cr['id']}", use_container_width=True):
                    st.session_state.pop(cle_confirm)
                    st.session_state.croisiere_id_a_supprimer = cr["id"]
                    st.rerun()
                if cy.button("❌ Annuler", key=f"n_cr_{cr['id']}", use_container_width=True):
                    st.session_state.pop(cle_confirm)
                    st.rerun()
