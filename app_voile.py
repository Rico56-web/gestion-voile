import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- 1. CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# On injecte le design UNE SEULE FOIS pour toute la page
st.markdown("""
    <style>
    /* On stylise les blocs natifs de Streamlit pour qu'ils soient beaux */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white !important;
        border-radius: 15px !important;
        border-left: 10px solid #3498db !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        padding: 10px !important;
    }
    .stAlert { padding: 5px !important; } /* Pour réduire la taille des badges */
    </style>
""", unsafe_allow_html=True)

# --- 2. DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

df = charger_data()

# --- 3. INTERFACE ---
st.title("⚓ Vesta Skipper 2026")

# Barre de recherche
search = st.text_input("🔍 Rechercher...", "").lower()

for idx, r in df.iterrows():
    if search and not any(search in str(r[c]).lower() for c in ['Nom', 'Prénom', 'Société']):
        continue

    # --- LE CONTENEUR (C'est lui qui fait la fiche) ---
    with st.container(border=True):
        # Ligne 1 : Identité
        st.subheader(f"{r['Prénom']} {str(r['Nom']).upper()}")
        
        # Ligne 2 : Société et Tel
        c_soc, c_tel = st.columns(2)
        c_soc.write(f"🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}")
        c_tel.write(f"📞 **{r['Téléphone']}**")
        
        # Ligne 3 : La durée (dans un bloc coloré natif)
        st.info(f"⏳ Durée de la mission : **{r['NbreJours']} jour(s)**")
        
        st.divider() # La barre horizontale propre
        
        # Ligne 4 : Date et Badges
        c_date, c_sta, c_pay = st.columns([2, 1, 1])
        c_date.markdown(f"### 📅 {r['DateNav']}")
        
        # Badges de Statut (Natifs)
        if r['Statut'] == "OK": c_sta.success(r['Statut'])
        elif r['Statut'] == "Terminé": c_sta.info(r['Statut'])
        else: c_sta.warning(r['Statut'])
            
        if r['Paiement'] == "Payé": c_pay.success("✔ Payé")
        else: c_pay.error("✖ Impayé")

        # Boutons d'actions
        b1, b2, b3 = st.columns(3)
        b1.button("🔄 RE-BOOK", key=f"rb_{idx}", use_container_width=True)
        b2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True)
        b3.button("🗑️ Supprimer", key=f"del_{idx}", use_container_width=True)
















































































































































































































































































































































































































































































