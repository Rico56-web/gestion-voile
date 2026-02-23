import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

# Style personnalisé pour les couleurs
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #0077b6; }
    .status-ok { background-color: #d4edda; padding: 10px; border-radius: 5px; border-left: 5px solid #28a745; margin-bottom: 10px; }
    .status-refuse { background-color: #f8d7da; padding: 10px; border-radius: 5px; border-left: 5px solid #dc3545; margin-bottom: 10px; }
    .status-attente { background-color: #fff3cd; padding: 10px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

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

    st.sidebar.title("⚓ Navigation")
    menu = st.sidebar.radio("Aller à :", ["📊 Tableau de bord", "🗂️ Carnet d'adresses", "⛵ Suivi des Demandes", "💬 Historique"])

    if menu == "📊 Tableau de bord":
        st.title("📊 Vesta Dashboard")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("👥 Contacts", len(contacts))
        with col2: st.metric("💬 Échanges", len(echanges))
        with col3: st.metric("⏳ En attente", len([d for d in demandes if d.get('Statut') == 'En attente']))
        
        st.info("💡 Astuce : Utilisez le menu à gauche pour naviguer entre vos fiches.")

    elif menu == "🗂️ Carnet d'adresses":
        st.title("🗂️ Gestion des Contacts")
        search = st.text_input("🔍 Rechercher un marin...")
        
        if "edit_idx" not in st.session_state: st.session_state.edit_idx = -1

        with st.expander("📝 Ajouter/Modifier un contact", expanded=(st.session_state.edit_idx != -1)):
            c_edit = contacts[st.session_state.edit_idx] if st.session_state.edit_idx != -1 else {"Nom": "", "Tél": "", "Email": "", "Urgence": ""}
            n = st.text_input("Nom", value=c_edit.get('Nom', ''))
            t = st.text_input("Tél", value=c_edit.get('Tél', ''))
            e = st.text_input("Email", value=c_edit.get('Email', ''))
            u = st.text_input("Urgence", value=c_edit.get('Urgence', ''))
            
            if st.button("💾 Enregistrer"):
                if n:
                    new_c = {"Nom": n, "Tél": t, "Email": e, "Urgence": u}
                    if st.session_state.edit_idx == -1: contacts.append(new_c)
                    else: contacts[st.session_state.edit_idx] = new_c
                    sauvegarder_donnees('contacts.json', contacts)
                    st.session_state.edit_idx = -1
                    st.rerun()

        st.divider()
        for i, c in enumerate(contacts):
            if search.lower() in c['Nom'].lower():
                col1, col2, col3 = st.columns([3, 1, 1])
                mail = c.get('Email', '')
                tel = c.get('Tél', '')
                link_tel = f"📞 [{tel}](tel:{tel.replace(' ', '')})" if tel else "Pas de tel"
                link_mail = f"✉️ [{mail}](mailto:{mail})" if mail else "Pas d'email"
                
                col1.markdown(f"### {c['Nom']}")
                col1.markdown(f"{link_tel}  |  {link_mail}")
                if c.get('Urgence'): col1.caption(f"🚨 Urgence : {c['Urgence']}")
                
                if col2.button("✏️", key=f"ed_{i}"):
                    st.session_state.edit_idx = i
                    st.rerun()
                if col3.button("🗑️", key=f"del_{i}"):
                    contacts.pop(i)
                    sauvegarder_donnees('contacts.json', contacts)
                    st.rerun()
                st.write("---")

    elif menu == "⛵ Suivi des Demandes":
        st.title("⛵ Demandes de Navigation")
        with st.expander("🆕 Enregistrer une demande"):
            if not contacts: st.warning("Ajoutez d'abord des contacts !")
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
            css_class = "status-ok" if d['Statut'] == "OK" else "status-refuse" if d['Statut'] == "Refusé" else "status-attente"
            st.markdown(f"""<div class="{css_class}">
                <strong>{d['Nom']}</strong> - {d['Date']}<br>
                Statut : {d['Statut']}
                </div>""", unsafe_allow_html=True)
            if d.get('Cause'): st.caption(f"Motif : {d['Cause']}")
            if st.button("Effacer", key=f"deld_{idx}"):
                demandes.pop(idx)
                sauvegarder_donnees('demandes.json', demandes)
                st.rerun()

    elif menu == "💬 Historique":
        st.title("💬 Journal des Échanges")
        with st.expander("✍️ Noter un échange"):
            if not contacts: st.warning("Ajoutez d'abord des contacts !")
            else:
                qui_e = st.selectbox("Contact concerné", [c['Nom'] for c in contacts])
                type_e = st.selectbox("Type", ["📞 Téléphone", "🤝 Rencontre", "📧 Relance Email", "⚓ Autre"])
                comm = st.text_area("Commentaires")
                if st.button("Enregistrer"):
                    echanges.append({"Nom": qui_e, "Date": str(datetime.now().strftime("%d/%m/%Y")), "Type": type_e, "Note": comm})
                    sauvegarder_donnees('echanges.json', echanges)
                    st.rerun()

        st.divider()
        for e in reversed(echanges):
            st.info(f"📅 {e['Date']} - **{e['Nom']}** ({e['Type']})")
            st.write(e['Note'])

