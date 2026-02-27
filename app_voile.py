import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# CSS FINAL - ULTRA COMPATIBLE IPAD
st.markdown("""
    <style>
    /* Force le VERT sur le bouton 'primary' */
    .stButton button[kind="primary"] {
        background-color: #27ae60 !important;
        color: white !important;
        border: none !important;
    }
    /* Style pour les cartes clients */
    .client-card {
        background-color: #ffffff !important; 
        padding: 15px; border-radius: 12px; 
        margin-bottom: 5px; border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    /* Style du Tableau de Bord Financier */
    .finance-box {
        background-color: #2c3e50;
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=30)
def charger_data():
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_d = df.to_json(orient="records", indent=4, force_ascii=False)
        content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
        data = {"message": "Update Vesta", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def parse_date(d):
    try: 
        s = str(d).replace(" ", "").replace("-", "/")
        return datetime.strptime(s, '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").strip())
    except: return 0.0

# --- SESSION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

# --- MENU PRINCIPAL ---
# On utilise des colonnes standard sans forcer le CSS complexe
m1, m2 = st.columns(2)
if m1.button("📋 LISTE", use_container_width=True): 
    st.session_state.page = "LISTE"
    st.rerun()

# On utilise 'primary' pour le planning si on est sur la page planning pour qu'il soit bleu/couleur accent
if m2.button("🗓️ PLANNING", use_container_width=True): 
    st.session_state.page = "PLAN"
    st.rerun()

st.markdown("---")

df = charger_data()

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...").upper()
    
    # ICI LE BOUTON VERT (Type primary)
    if c_add.button("➕ NOUVEAU", use_container_width=True, type="primary"):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"
        st.rerun()
    
    # Affichage des fiches (simplifié pour la démo)
    # ... (votre code de rendu habituel ici) ...
    st.write("Faites défiler pour voir vos clients.")

# --- PAGE PLANNING + TABLEAU DE BORD ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    # Sélecteur de mois
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

    # --- LOGIQUE FINANCIÈRE ---
    ca_ok = 0.0
    ca_attente = 0.0
    
    for _, r in df.iterrows():
        dt = parse_date(r.get('DateNav', ''))
        if dt.month == st.session_state.m_idx and dt.year == 2026:
            prix = to_float(r.get('PrixJour', 0))
            if "🟢" in str(r.get('Statut', '')):
                ca_ok += prix
            elif "🟡" in str(r.get('Statut', '')):
                ca_attente += prix

    # --- AFFICHAGE DU TABLEAU DE BORD ---
    st.markdown("### 📈 Résumé de " + m_fr[st.session_state.m_idx-1])
    f1, f2, f3 = st.columns(3)
    f1.metric("Encaissé (🟢)", f"{ca_ok:,.0f} €".replace(",", " "))
    f2.metric("Attente (🟡)", f"{ca_attente:,.0f} €".replace(",", " "))
    f3.metric("Total Prévu", f"{(ca_ok + ca_attente):,.0f} €".replace(",", " "))
    
    st.markdown("---")
    # ... (votre code de calendrier habituel ici) ...
    st.write("Le calendrier s'affiche ici.")












































































