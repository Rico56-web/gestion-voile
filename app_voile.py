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
    .note-box { background-color: #e7f3fe; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3; margin-bottom: 20px; }
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
if "edit_note_idx" not in st.session_state:
    st.session_state.edit_note_idx = -1

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

    # ... (Gardez ici le code des sections Dashboard, Contacts, Demandes, Checklists) ...

    if menu == "💬 Historique":
        st.title("💬 Journal des Échanges")
        
        # --- FORMULAIRE DE SAISIE / MODIFICATION ---
        with st.expander("✍️ Noter un échange", expanded=(st.session_state.edit_note_idx != -1)):
            note_a_modifier = echanges[st.session_state.edit_note_idx] if st.session_state.edit_note_idx != -1 else {"Nom": contacts[0]['Nom'] if contacts else "", "Note": "", "Type": "📞 Téléphone"}
            
            with st.form("form_echange"):
                qui_e = st.selectbox("Contact", [c['Nom'] for c in contacts], index=[c['Nom'] for c in contacts].index(note_a_modifier['Nom']) if note_a_modifier['Nom'] in [c['Nom'] for c in contacts] else 0)
                type_e = st.selectbox("Type", ["📞 Téléphone", "🤝 Rencontre", "📧 Relance Email", "⚓ Autre"], index=["📞 Téléphone", "🤝 Rencontre", "📧 Relance Email", "⚓ Autre"].index(note_a_modifier.get('Type', "📞 Téléphone")))
                comm = st.text_area("Commentaires", value=note_a_modifier['Note'])
                
                txt_bouton = "💾 Mettre à jour" if st.session_state.edit_note_idx != -1 else "💾 Enregistrer"
                if st.form_submit_button(txt_bouton):
                    if comm:
                        nouvelle_note = {"Nom": qui_e, "Date": datetime.now().strftime("%d/%m/%Y %H:%M"), "Type": type_e, "Note": comm}
                        if st.session_state.edit_note_idx == -1:
                            echanges.append(nouvelle_note)
                        else:
                            echanges[st.session_state.edit_note_idx] = nouvelle_note
                        sauvegarder_donnees('echanges.json', echanges)
                        st.session_state.edit_note_idx = -1
                        st.rerun()

        st.divider()

        # --- AFFICHAGE DES NOTES ---
        for i, e in enumerate(reversed(echanges)):
            # Calcul de l'index réel (car on utilise reversed)
            real_idx = len(echanges) - 1 - i
            
            col_text, col_btns = st.columns([4, 1])
            
            with col_text:
                st.markdown(f"""<div class="note-box">
                    <strong>📅 {e['Date']} - {e['Nom']}</strong> ({e.get('Type', 'Note')})<br>
                    {e['Note']}
                </div>""", unsafe_allow_html=True)
            
            with col_btns:
                if st.button("✏️", key=f"edit_n_{real_idx}"):
                    st.session_state.edit_note_idx = real_idx
                    st.rerun()
                if st.button("🗑️", key=f"del_n_{real_idx}"):
                    echanges.pop(real_idx)
                    sauvegarder_donnees('echanges.json', echanges)
                    st.rerun()

