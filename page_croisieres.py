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

from modele_voile import croisieres_depuis, noms_participants, couleur_croisiere


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

    if "voir_tout_historique" not in st.session_state:
        st.session_state.voir_tout_historique = False

    c_nouveau, c_toggle = st.columns([1, 1])
    if c_nouveau.button("➕ Nouvelle croisière", use_container_width=True):
        st.session_state.edit_croisiere_id = None
        st.session_state.page = "MODIFIER_CROISIERE"
        st.rerun()

    label_toggle = "📅 Voir tout l'historique" if not st.session_state.voir_tout_historique else "📅 Revenir à cette année"
    if c_toggle.button(label_toggle, use_container_width=True):
        st.session_state.voir_tout_historique = not st.session_state.voir_tout_historique
        st.rerun()

    if st.session_state.voir_tout_historique:
        croisieres_affichees = croisieres_depuis(croisieres, date(2000, 1, 1))
        st.caption("Tout l'historique des croisières.")
    else:
        annee_courante = date.today().year
        croisieres_affichees = croisieres_depuis(croisieres, date(annee_courante, 1, 1))
        st.caption(f"Croisières depuis le 01/01/{annee_courante}. Les croisières sans date valide ne sont pas listées ici.")

    st.divider()

    if not croisieres_affichees:
        st.info("Aucune croisière à afficher pour cette période.")
        return

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
