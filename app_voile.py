import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

def charger_donnees(fichier):
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

# --- INITIALISATION ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Vesta Manager")
    mdp = st.text_input("Entrez le code d'accès", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
else:
    contacts = charger_donnees('contacts.json')
    echanges = charger_donnees('echanges.json')
    demandes = charger_donnees('demandes.json')

    st.sidebar.title("⚓ Vesta Navigation")
    menu = st.sidebar.radio("Aller à :", ["Tableau de bord", "Carnet d'adresses", "Suivi des Demandes", "Historique des Échanges"])

    if menu == "Tableau de bord":
        st.title("📊 Vesta Dashboard")
        col1, col2, col3 = st.columns(3)
        col1.metric("Contacts", len(contacts))
        col2.metric("Échanges", len(echanges))
        col3.metric("Demandes", len([d for d in demandes if d.get('Statut') == 'En attente']))

    elif menu == "Carnet d'adresses":
        st.title("🗂️ Gestion des Contacts")
        if "edit_idx" not in st.session_state: st.session_state.edit_idx = -1

        with st.expander("📝 Ajouter/Modifier un contact", expanded=(st.session_state.edit_idx != -1)):
            c_edit = contacts[st.session_state.edit_idx] if st.session_state.edit_idx != -1 else {"Nom": "", "Tél": "", "Email": "", "Urgence": ""}
            n = st.text_input("Nom", value=c_edit.get('Nom', ''))
            t = st.text_input("Tél", value=c_edit.get('Tél', ''))
            e = st.text_input("Email", value=c_edit.get('Email', ''))
            u = st.text_input("Urgence", value=c_edit.get('Urgence', ''))
            
            if st.button("Enregistrer le contact"):
                if n:
                    new_c = {"Nom": n, "Tél": t, "Email": e, "Urgence": u}
                    if st.session_state.edit_idx == -1: contacts.append(new_c)
                    else: contacts[st.session_state.edit_idx] = new_c
                    sauvegarder_donnees('contacts.json', contacts)
                    st.session_state.edit_idx = -1
                    st.rerun()

        st.divider()
        for i, c in enumerate(contacts):
            col1, col2, col3 = st.columns([3, 1, 1])
            mail = c.get('Email', 'Pas d\'email')
            tel = c.get('Tél', '')
            col1.write(f"**{c['Nom']}** | {tel} | {mail}")
            if col2.button("✏️", key=f"ed_{i}"):
                st.session_state.edit_idx = i
                st.rerun()
            if col3.button("🗑️", key=f"del_{i}"):
                contacts.pop(i)
                sauvegarder_donnees('contacts.json', contacts)
                st.rerun()

    elif menu == "Suivi des Demandes":
        st.title("⛵ Demandes de Navigation")
        with st.expander("🆕 Enregistrer une demande"):
            if not contacts:
                st.warning("Ajoutez d'abord des contacts !")
            else:
                qui = st.selectbox("Qui demande ?", [c['Nom'] for c in contacts])
                date_d = st.date_input("Pour quand ?", datetime.now())
                statut = st.selectbox("Décision", ["En attente", "OK", "Refusé"])
                cause = st.text_input("Motif / Cause")
                if st.button("Valider la demande"):
                    demandes.append({"Nom": qui, "Date": str(date_d), "Statut": statut, "Cause": cause})
                    sauvegarder_donnees('demandes.json', demandes)
                    st.rerun()

        st.divider()
        for i, d in enumerate(reversed(demandes)):
            idx = len(demandes) - 1 - i
            color = "🟢" if d['Statut'] == "OK" else "🔴" if d['Statut'] == "Refusé" else "🟡"
            st.write(f"{color} **{d['Nom']}** - {d['Date']} : **{d['Statut']}**")
            if d.get('Cause'): st.caption(f"Motif : {d['Cause']}")
            if st.button("Effacer", key=f"deld_{idx}"):
                demandes.pop(idx)
                sauvegarder_donnees('demandes.json', demandes)
                st.rerun()

    elif menu == "Historique des Échanges":
        st.title("💬 Journal des Échanges")
        with st.expander("✍️ Noter un échange"):
            if not contacts:
                st.warning("Ajoutez d'abord des contacts !")
            else:
                qui_e = st.selectbox("Contact concerné", [c['Nom'] for c in contacts])
                type_e = st.selectbox("Type", ["Téléphone", "Rencontre", "Relance Email", "Autre"])
                comm = st.text_area("Commentaires")
                if st.button("Enregistrer l'échange"):
                    echanges.append({"Nom": qui_e, "Date": str(datetime.now().strftime("%d/%m/%Y")), "Type": type_e, "Note": comm})
                    sauvegarder_donnees('echanges.json', echanges)
                    st.rerun()

        st.divider()
        for e in reversed(echanges):
            st.info(f"📅 {e['Date']} - **{e['Nom']}** ({e['Type']})")
            st.write(e['Note'])


