import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- CHARGEMENT DATA ---
def charger_data():
    file = "contacts.json"
    if os.path.exists(file):
        try:
            return pd.read_json(file)
        except: pass
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix'])

df = charger_data()

# --- INTERFACE ---
st.title("⚓ Vesta Skipper 2026")

tab1, tab2 = st.tabs(["🚀 MISSIONS", "📅 PLANNING"])

with tab1:
    search = st.text_input("🔍 Rechercher...", "").lower()
    
    # On boucle sur les données
    for idx, r in df.iterrows():
        # Filtrage simple
        if search and not any(search in str(r[c]).lower() for c in ['Nom', 'Prénom', 'Société']):
            continue

        # --- CRÉATION DE LA FICHE SANS HTML ---
        with st.container(border=True):
            # Ligne 1 : Nom et Prénom
            st.subheader(f"{r['Prénom']} {str(r['Nom']).upper()}")
            
            # Ligne 2 : Société et Contacts
            col1, col2 = st.columns(2)
            col1.write(f"🏛️ **{r['Société'] if r['Société'] else 'Particulier'}**")
            col2.write(f"📞 {r['Téléphone']}")
            
            st.write(f"✉️ {r['Email']}")
            
            # Ligne 3 : Détails Mission
            st.info(f"⏳ **Durée de la mission :** {r['NbreJours']} jour(s)")
            
            st.divider() # La ligne de séparation
            
            # Ligne 4 : Date et Statuts
            c_date, c_statut, c_paie = st.columns([2, 1, 1])
            c_date.write(f"📅 **{r['DateNav']}**")
            
            # Affichage des statuts avec des couleurs natives
            if r['Statut'] == "OK":
                c_statut.success(r['Statut'])
            else:
                c_statut.warning(r['Statut'])
                
            if r['Paiement'] == "Payé":
                c_paie.success("Payé")
            else:
                c_paie.error("Impayé")

            # Boutons d'actions
            ba1, ba2, ba3 = st.columns(3)
            if ba1.button("🔄 RE-BOOK", key=f"re_{idx}"):
                st.info("Action Re-book")
            if ba2.button("✏️ Modifier", key=f"ed_{idx}"):
                st.info("Action Modifier")
            if ba3.button("🗑️ Suppr.", key=f"del_{idx}"):
                st.error("Action Supprimer")

with tab2:
    st.write("Le planning sera ici.")


















































































































































































































































































































































































































































































