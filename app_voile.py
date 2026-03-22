import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS (BLINDÉ) ---
st.markdown("""
    <style>
    .fiche-globale {
        background-color: #ffffff; border-radius: 12px; padding: 15px;
        margin-bottom: 15px; border-left: 8px solid #3498db;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .info-box { background-color:#f8f9fa; padding:10px; border-radius:8px; margin:10px 0; border: 1px solid #eee; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; color: white; font-size: 12px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix'])

df = charger_data()

# --- MENU ---
st.sidebar.title("⚓ Vesta Skipper")
menu = st.sidebar.radio("Aller à", ["CONTACTS", "PLANNING"])

if menu == "CONTACTS":
    st.header("👤 Mes Contacts")
    
    # On affiche chaque ligne du tableau
    for idx, r in df.iterrows():
        # Détermination des couleurs
        color_s = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f"
        color_p = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        
        # --- LE BLOC D'AFFICHAGE (STRICTEMENT EN MARKDOWN HTML) ---
        html_fiche = f"""
        <div class="fiche-globale">
            <div style="font-size: 20px; font-weight: bold;">{r['Prénom']} {str(r['Nom']).upper()}</div>
            <div style="color: gray;">🏛️ {r['Société']}</div>
            <div style="margin-top: 5px;">📞 {r['Téléphone']}</div>
            
            <div class="info-box">
                ⏳ <b>Durée :</b> {r['NbreJours']} jour(s)
            </div>
            
            <hr style="border: 0; border-top: 1px solid #eee; margin: 10px 0;">
            
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 16px;">📅 <b>{r['DateNav']}</b></span>
                <div>
                    <span class="statut-badge" style="background: {color_s};">{r['Statut']}</span>
                    <span class="statut-badge" style="background: {color_p};">{r['Paiement']}</span>
                </div>
            </div>
        </div>
        """
        
        # C'est cette ligne qui transforme le texte en dessin :
        st.markdown(html_fiche, unsafe_allow_html=True)
        
        # Boutons d'actions sous la fiche
        c1, c2 = st.columns(2)
        if c1.button(f"✏️ Modifier {idx}", key=f"ed_{idx}"):
            st.info("Mode édition bientôt actif")
        if c2.button(f"🗑️ Supprimer {idx}", key=f"del_{idx}"):
            st.warning("Action de suppression")

elif menu == "PLANNING":
    st.subheader("📅 Planning 2026")
    st.write("Le calendrier s'affichera ici.")


















































































































































































































































































































































































































































































