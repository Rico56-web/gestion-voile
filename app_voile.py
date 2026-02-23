import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

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
    check_data = charger_donnees('checklists.json')
    if not check_data:
        check_data = {"Départ": ["Météo", "Gilets"], "Arrivée": ["Vannes", "Batteries"]}

    st.sidebar.title("⚓ Navigation")
    menu = st.sidebar.radio("Aller à :", ["📊 Dashboard", "🗂️ Contacts", "⛵ Demandes", "💬 Historique", "📋 Checklists"])

    if menu == "📊 Dashboard":
        st.title("📊 Vesta Dashboard")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric("👥 Contacts", len(contacts))
        with col2: st.metric("💬 Échanges", len(echanges))
        with col3: st.metric("⏳ En attente", len([d for d in demandes if d.get('Statut') == 'En attente']))

    elif menu == "🗂️ Contacts":
        st.title("🗂️ Gestion des Contacts")
        search = st.text_input("🔍 Rechercher...")
        if "edit_idx" not in st.session_state: st.session_state.edit_idx = -1
        with st.expander("📝 Ajouter/Modifier", expanded=(st.session_state.edit_idx != -1)):
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
                mail, tel = c.get('Email', ''), c.get('Tél', '')
                link_tel = f"📞 [{tel}](tel:{tel.replace(' ', '')})" if tel else "Pas de tel"
                link_mail = f"✉️ [{mail}](mailto:{mail})" if mail else "Pas d'email"
                col1.markdown(f"### {c['Nom']}")
                col1.markdown(f"{link_tel} | {link_mail}")
                if col2.button("✏️", key=f"ed_{i}"):
                    st.session_state.edit_idx = i
                    st.rerun()
                if col3.button("🗑️", key=f"del_{i}"):
                    contacts.pop(i); sauvegarder_donnees('contacts.json', contacts); st.rerun()

    elif menu == "⛵ Demandes":
        st.title("⛵ Demandes de Navigation")
        with st.expander("🆕 Nouvelle demande"):
            if not contacts: st.warning("Ajoutez des contacts !")
            else:
                qui = st.selectbox("Qui ?", [c['Nom'] for c in contacts])
                statut = st.selectbox("Décision", ["En attente", "OK", "Refusé"])
                if st.button("Valider"):
                    demandes.append({"Nom": qui, "Date": str(datetime.now().date()), "Statut": statut})
                    sauvegarder_donnees('demandes.json', demandes); st.rerun()
        for d in reversed(demandes):
            css = "status-ok" if d['Statut'] == "OK" else "status-refuse" if d['Statut'] == "Refusé" else "status-attente"
            st.markdown(f'<div class="{css}"><strong>{d["Nom"]}</strong> - {d["Date"]} ({d["Statut"]})</div>', unsafe_allow_html=True)

    elif menu == "💬 Historique":
        st.title("💬 Journal des Échanges")
        
        # Formulaire avec bouton qui se verrouille
        with st.expander("✍️ Note", expanded=True):
            with st.form("form_echange", clear_on_submit=True):
                qui_e = st.selectbox("Contact concerné", [c['Nom'] for c in contacts])
                type_e = st.selectbox("Type", ["📞 Téléphone", "🤝 Rencontre", "📧 Relance Email", "⚓ Autre"])
                comm = st.text_area("Commentaires")
                
                # Le bouton submit d'un formulaire Streamlit évite naturellement les doubles envois
                submitted = st.form_submit_button("💾 Enregistrer l'échange")
                
                if submitted:
                    if comm:  # On vérifie qu'il y a un texte pour éviter les notes vides
                        nouvel_echange = {
                            "Nom": qui_e, 
                            "Date": datetime.now().strftime("%d/%m/%Y %H:%M"), 
                            "Type": type_e, 
                            "Note": comm
                        }
                        echanges.append(nouvel_echange)
                        sauvegarder_donnees('echanges.json', echanges)
                        st.success("Échange enregistré !")
                        st.rerun()
                    else:
                        st.error("Veuillez écrire un commentaire avant d'enregistrer.")

        st.divider()
        for e in reversed(echanges):
            st.info(f"📅 {e['Date']} - **{e['Nom']}** ({e.get('Type', 'Échange')})")
            st.write(e['Note'])

    elif menu == "📋 Checklists":
        st.title("📋 Checklists Personnalisables")
        with st.expander("🛠️ Modifier les listes"):
            col_add, col_cat = st.columns([3, 1])
            new_item = col_add.text_input("Nouveau point")
            cat = col_cat.selectbox("Liste", ["Départ", "Arrivée"])
            if st.button("➕ Ajouter"):
                if new_item:
                    check_data[cat].append(new_item)
                    sauvegarder_donnees('checklists.json', check_data); st.rerun()
            st.divider()
            for cat_name in ["Départ", "Arrivée"]:
                st.write(f"**Supprimer dans {cat_name} :**")
                for i, item in enumerate(check_data[cat_name]):
                    if st.button(f"❌ {item}", key=f"del_{cat_name}_{i}"):
                        check_data[cat_name].pop(i)
                        sauvegarder_donnees('checklists.json', check_data); st.rerun()
        st.divider()
        c_dep, c_arr = st.columns(2)
        with c_dep:
            st.subheader("⛵ Départ")
            for item in check_data["Départ"]: st.checkbox(item, key=f"run_dep_{item}")
        with c_arr:
            st.subheader("⚓ Arrivée")
            for item in check_data["Arrivée"]: st.checkbox(item, key=f"run_arr_{item}")

