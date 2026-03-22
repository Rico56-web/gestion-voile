import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION & DESIGN (L'ÉLÉGANCE AVANT TOUT) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""
    <style>
    /* Fond de page gris très clair pour faire ressortir les fiches */
    .stApp { background-color: #f4f7f9; }
    
    /* La Fiche Client */
    .vesta-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border-top: 4px solid #1e3a5f; /* Ligne marine élégante */
    }
    
    /* Typographie */
    .client-name { font-size: 19px; font-weight: 700; color: #1e3a5f; margin-bottom: 2px; }
    .company-name { font-size: 13px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }
    .contact-info { font-size: 14px; color: #34495e; margin-top: 8px; }
    
    /* Boîte de mission compacte */
    .mission-box {
        background-color: #fdfdfd;
        border: 1px solid #edf2f7;
        border-radius: 8px;
        padding: 10px;
        margin: 12px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Badges minimalistes */
    .v-badge {
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

df = charger_data()

# --- 3. AFFICHAGE ---
st.title("⚓ Mes Navigations")

# Recherche discrète
search = st.text_input("🔍 Rechercher un passager...", label_visibility="collapsed")

for idx, r in df.iterrows():
    if search and not any(search.lower() in str(r[c]).lower() for c in ['Nom', 'Prénom', 'Société']):
        continue

    # Couleurs des badges
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12" if r['Statut'] == "En attente" else "#95a5a6"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    # --- LE DESIGN EN UN SEUL BLOC ---
    st.markdown(f"""
        <div class="vesta-card">
            <div class="client-name">{r['Prénom']} <span style="font-weight:900;">{str(r['Nom']).upper()}</span></div>
            <div class="company-name">🏛️ {r['Société'] if r['Société'] else 'Particulier'}</div>
            
            <div class="contact-info">
                📞 <b>{r['Téléphone']}</b> &nbsp;&nbsp; | &nbsp;&nbsp; ✉️ {r['Email']}
            </div>
            
            <div class="mission-box">
                <span style="color:#7f8c8d; font-size:13px;">⏱️ Durée : <b>{r['NbreJours']} J</b></span>
                <span style="font-size:15px; font-weight:700; color:#2c3e50;">📅 {r['DateNav']}</span>
            </div>
            
            <div style="display: flex; gap: 8px; margin-top: 10px;">
                <span class="v-badge" style="background-color: {bg_s};">{r['Statut']}</span>
                <span class="v-badge" style="background-color: {bg_p};">{r['Paiement']}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Boutons d'actions (On les garde natifs pour la réactivité iPhone)
    c1, c2, c3 = st.columns(3)
    c1.button("🔄 RE-BOOK", key=f"rb_{idx}", use_container_width=True)
    c2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True)
    c3.button("🗑️ Suppr.", key=f"dl_{idx}", use_container_width=True)
















































































































































































































































































































































































































































































