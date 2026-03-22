import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE POUR RÉDUIRE LES BOUTONS ---
st.markdown("""
    <style>
    /* Réduit la taille globale des boutons Streamlit */
    div.stButton > button {
        padding: 2px 5px !important;
        font-size: 12px !important;
        height: 30px !important;
        border-radius: 8px !important;
        border: 1px solid #d1d5db !important;
        background-color: #f9fafb !important;
        color: #374151 !important;
    }
    /* Aligne les boutons plus près de la fiche */
    [data-testid="column"] {
        padding: 0 5px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

df = charger_data()

st.title("⚓ Mes Navigations")

for idx, r in df.iterrows():
    
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    # HTML de la fiche (légèrement plus compact)
    html_code = f"""
    <div style="
        font-family: -apple-system, sans-serif; 
        background: white; border-radius: 10px; padding: 10px; 
        border-left: 6px solid #1e3a5f; box-shadow: 0 1px 4px rgba(0,0,0,0.1); 
        color: #2c3e50; box-sizing: border-box; width: 98%; margin: auto;
    ">
        <div style="font-size: 16px; font-weight: bold;">{r['Prénom']} <span style="text-transform: uppercase;">{r['Nom']}</span></div>
        <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 5px;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}</div>
        
        <div style="font-size: 12px; margin-bottom: 8px;">
            <b>{r['Téléphone']}</b> | {r['Email']}
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 4px;">
            <span style="font-size: 11px; background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">⏳ {r['NbreJours']} J</span>
            <span style="font-size: 13px; font-weight: bold;">📅 {r['DateNav']}</span>
        </div>
        
        <div style="display: flex; gap: 5px;">
            <span style="background: {bg_s}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Statut']}</span>
            <span style="background: {bg_p}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Paiement']}</span>
        </div>
    </div>
    """

    # Affichage de la fiche (Hauteur réduite à 160px)
    components.html(html_code, height=160)
    
    # Boutons d'actions MINIATURES
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.button("🔄 Book", key=f"rb_{idx}", use_container_width=True)
    c2.button("✏️ Edit", key=f"ed_{idx}", use_container_width=True)
    c3.button("🗑️ Del", key=f"del_{idx}", use_container_width=True)
    
    st.write("") # Petit espace













































































































































































































































































































































































































































































