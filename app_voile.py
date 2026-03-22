import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

df = charger_data()

st.title("⚓ Mes Navigations")

# --- BOUCLE D'AFFICHAGE ---
for idx, r in df.iterrows():
    
    # Couleurs des badges
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    # CONSTRUCTION DU HTML ISOLÉ AVEC FIX POUR LE DÉBORDEMENT
    html_code = f"""
    <div style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
        background: white; 
        border-radius: 12px; 
        padding: 12px; 
        border-left: 8px solid #1e3a5f; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
        color: #2c3e50;
        box-sizing: border-box;
        width: 95%;
        margin: auto;
    ">
        <div style="font-size: 18px; font-weight: bold; margin-bottom: 2px;">{r['Prénom']} <span style="text-transform: uppercase;">{r['Nom']}</span></div>
        <div style="font-size: 13px; color: #7f8c8d; margin-bottom: 8px;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}</div>
        
        <div style="font-size: 13px; margin-bottom: 10px; line-height: 1.4;">
            📞 <b>{r['Téléphone']}</b><br>✉️ {r['Email']}
        </div>
        
        <div style="background: #f8f9fa; padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 5px;">
            <span style="font-size: 12px;">⏳ Durée : <b>{r['NbreJours']} J</b></span>
            <span style="font-size: 14px; font-weight: bold;">📅 {r['DateNav']}</span>
        </div>
        
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <span style="background: {bg_s}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; white-space: nowrap;">{r['Statut']}</span>
            <span style="background: {bg_p}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; white-space: nowrap;">{r['Paiement']}</span>
        </div>
    </div>
    """

    # Utilisation du composant HTML (Hauteur augmentée pour le wrap sur petit écran)
    components.html(html_code, height=210)
    
    # Boutons d'actions
    c1, c2, c3 = st.columns(3)
    c1.button("🔄 RE-BOOK", key=f"rb_{idx}", use_container_width=True)
    c2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True)
    c3.button("🗑️ Suppr.", key=f"del_{idx}", use_container_width=True)
    st.markdown("---")














































































































































































































































































































































































































































































