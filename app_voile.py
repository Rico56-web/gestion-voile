import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

# Connexion à Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTIONS DE DONNÉES ---
def charger_onglet(nom_onglet):
    try:
        return conn.read(worksheet=nom_onglet).dropna(how="all")
    except:
        return pd.DataFrame()

def sauvegarder_onglet(df, nom_onglet):
    conn.update(worksheet=nom_onglet, data=df)
    st.cache_data.clear() # Force la mise à jour de l'affichage

# --- CSS COMPACT IPHONE ---
st.markdown("""
    <style>
    .stButton > button { padding: 2px 8px !important; font-size: 14px !important; border-radius: 5px !important; }
    .note-box { background-color: #e7f3fe; padding: 10px; border-radius: 8px; border-left: 5px solid #2196f3; margin-bottom: 5px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- AUTHENTIFICATION ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Vesta")
    mdp = st.text_input("Code d'accès", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
else:
    # Chargement des données depuis Sheets
    df_contacts = charger_onglet("contacts")
    df_notes = charger_onglet("echanges")

    st.sidebar.title("⚓ Vesta")
    menu = st.sidebar.radio("Menu", ["🗂️ Contacts", "💬 Historique", "📋 Checklists"])

    # --- 🗂️ CONTACTS ---
    if menu == "🗂️ Contacts":
        st.title("🗂️ Carnet")
        with st.expander("📝 Nouveau Contact"):
            with st.form("add_contact"):
                n = st.text_input("Nom")
                t = st.text_input("Tél")
                e = st.text_input("Email")
                if st.form_submit_button("Enregistrer"):
                    new_row = pd.DataFrame([{"Nom": n, "Tél": t, "Email": e}])
                    df_contacts = pd.concat([df_contacts, new_row], ignore_index=True)
                    sauvegarder_onglet(df_contacts, "contacts")
                    st.success("Contact enregistré dans Google Sheets !")
                    st.rerun()
