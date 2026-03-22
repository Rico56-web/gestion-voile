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
    
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    # CONSTRUCTION DU HTML AVEC BOUTONS INTÉGRÉS
    # On utilise des colonnes Streamlit standards MAIS on réduit leur écart
    
    html_fiche = f"""
    <div style="
        font-family: -apple-system, sans-serif; 
        background: white; border-radius: 10px; padding: 10px; 
        border-left: 6px solid #1e3a5f; box-shadow: 0 1px 4px rgba(0,0,0,0.1); 
        color: #2c3e50; box-sizing: border-box; width: 98%; margin: auto;
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-size: 16px; font-weight: bold;">{r['Prénom']} <span style="text-transform: uppercase;">{r['Nom']}</span></div>
                <div style="font-size: 11px; color: #7f8c8d;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 13px; font-weight: bold;">📅 {r['DateNav']}</div>
                <div style="font-size: 10px; color: #7f8c8d;">⏳ {r['NbreJours']} J</div>
            </div>
        </div>
        
        <div style="font-size: 12px; margin: 5px 0;">
            <b>{r['Téléphone']}</b> | {r['Email']}
        </div>
        
        <div style="display: flex; gap: 5px; margin-top: 5px;">
            <span style="background: {bg_s}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Statut']}</span>
            <span style="background: {bg_p}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Paiement']}</span>
        </div>
    </div>
    """

    # Affichage de la fiche
    components.html(html_fiche, height=110)
    
    # BOUTONS STREAMLIT (On les rapproche au maximum)
    # Pour qu'ils fonctionnent, il faut qu'ils soient bien visibles par Streamlit
    col1, col2, col3 = st.columns([1,1,1])
    
    if col1.button("🔄 Book", key=f"rb_{idx}", use_container_width=True):
        st.session_state.action = ("rebook", idx)
        st.rerun()
        
    if col2.button("✏️ Edit", key=f"ed_{idx}", use_container_width=True):
        st.session_state.action = ("edit", idx)
        st.rerun()
        
    if col3.button("🗑️ Del", key=f"del_{idx}", use_container_width=True):
        st.session_state.action = ("delete", idx)
        st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)

# Traitement des actions (pour prouver que ça marche)
if "action" in st.session_state:
    act, i = st.session_state.action
    st.toast(f"Action {act} demandée pour la fiche {i} !")
    del st.session_state.action













































































































































































































































































































































































































































































