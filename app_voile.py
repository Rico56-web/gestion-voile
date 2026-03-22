import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS (CORRIGÉ POUR ÉVITER LE TEXTE BRUT) ---
st.markdown("""
    <style>
    /* La fiche principale */
    .card {
        background-color: white;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 15px;
        border-left: 10px solid #3498db;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: #2c3e50;
    }
    /* Le titre Prénom NOM */
    .title { font-size: 22px; font-weight: bold; color: #1a252f; margin-bottom: 2px; }
    .nom { text-transform: uppercase; }
    /* L'encadré gris pour la durée */
    .duration-box {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
        margin: 10px 0;
        border: 1px solid #e9ecef;
        font-size: 14px;
    }
    /* Les badges de statut */
    .badge {
        padding: 5px 12px;
        border-radius: 20px;
        color: white;
        font-size: 12px;
        font-weight: bold;
        display: inline-block;
        margin-left: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA ---
def charger_data():
    file = "contacts.json"
    if os.path.exists(file):
        return pd.read_json(file)
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix'])

df = charger_data()

# --- INTERFACE ---
st.title("⚓ Vesta Skipper 2026")

search = st.text_input("🔍 Rechercher un client...", "").lower()

for idx, r in df.iterrows():
    if search and not any(search in str(r[c]).lower() for c in ['Nom', 'Prénom', 'Société']):
        continue

    # Préparation des couleurs
    color_statut = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f" # Vert si OK, Jaune sinon
    color_paie = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c" # Vert si Payé, Rouge sinon

    # --- CONSTRUCTION DU HTML (SANS ERREUR) ---
    # On utilise f-string pour injecter les variables
    fiche_html = f"""
    <div class="card">
        <div class="title">{r['Prénom']} <span class="nom">{r['Nom']}</span></div>
        <div style="color: #7f8c8d; font-size: 14px;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}</div>
        <div style="margin-top: 8px; font-size: 15px;">
            📞 <b>{r['Téléphone']}</b> | ✉️ {r['Email']}
        </div>
        
        <div class="duration-box">
            ⏳ <span style="color: #95a5a6;">Durée de la mission :</span> <b>{r['NbreJours']} jour(s)</b>
        </div>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
        
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-size: 18px;">📅 <b>{r['DateNav']}</b></div>
            <div>
                <span class="badge" style="background-color: {color_statut};">{r['Statut']}</span>
                <span class="badge" style="background-color: {color_paie};">{r['Paiement']}</span>
            </div>
        </div>
    </div>
    """
    
    # AFFICHAGE DE LA FICHE
    st.markdown(fiche_html, unsafe_allow_html=True)
    
    # BOUTONS D'ACTIONS (NATIFS POUR LA RÉACTIVITÉ)
    c1, c2, c3 = st.columns(3)
    c1.button("🔄 RE-BOOK", key=f"rb_{idx}", use_container_width=True)
    c2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True)
    c3.button("🗑️ Suppr.", key=f"del_{idx}", use_container_width=True)
    st.write("") # Espace entre les fiches

















































































































































































































































































































































































































































































