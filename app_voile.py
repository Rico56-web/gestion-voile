import streamlit as st
import pandas as pd
import json
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Skipper Manager", layout="wide", page_icon="⛵")

# Vérification du mot de passe
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Skipper Manager")
    mdp = st.text_input("Entrez le code d'accès au bord", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
        else:
            st.error("Code incorrect.")
else:
    st.title("⚓ Tableau de bord Skipper")
    st.write("Bienvenue à bord !")
    # (Le reste du code suivra une fois que ceci fonctionnera)     
