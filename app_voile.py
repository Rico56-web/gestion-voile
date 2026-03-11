import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    /* Pas d'entête général ici */
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #eee; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin-bottom: -5px; }
    .nom-style { font-size: 1.1rem; text-transform: uppercase; color: #666; margin-bottom: 8px; }
    .info-texte { font-size: 1rem; color: #333; margin: 2px 0; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def to_f(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            df_raw = pd.DataFrame(json.loads(base64.b64decode(content).decode('utf-8')))
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            return df_raw
        return pd.DataFrame()
    except: return pd.DataFrame()

# Authentification
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Code d'accès", type="password")
    if st.button("Connexion"):
        if pwd == "SKIPPER2026": st.session_state.auth = True; st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# Chargement
df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

# --- 3. NAVIGATION (Menus en haut de page directement) ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
m = st.columns(8)
pages = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SECU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True): st.session_state.page = p; st.rerun()

# --- 4. LOGIQUE DES PAGES ---

# --- PAGE LISTE (Version Épurée) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher Nom ou Prénom").lower()
    
    if not df.empty:
        # Détection intelligente des colonnes
        c_nom = next((c for c in df.columns if 'nom' in c.lower() and 'pré' not in c.lower()), "Nom")
        c_pre = next((c for c in df.columns if 'pré' in c.lower() or 'pre' in c.lower()), "Prénom")
        c_soc = next((c for c in df.columns if 'soc' in c.lower()), "Société")
        c_dat = next((c for c in df.columns if 'date' in c.lower()), "DateNav")
        c_pri = next((c for c in df.columns if 'prix' in c.lower() or 'montant' in c.lower()), "Prix")
        
        mask = (df[c_nom].astype(str).str.lower().str.contains(search, na=False)) | \
               (df[c_pre].astype(str).str.lower().str.contains(search, na=False))
        
        for i, r in df[mask].iterrows():
            with st.container():
                # 1. Prénom (Gros)
                st.markdown(f'<div class="prenom-style">{r.get(c_pre, "")}</div>', unsafe_allow_html=True)
                # 2. NOM (Majuscule)
                st.markdown(f'<div class="nom-style">{str(r.get(c_nom, "")).upper()}</div>', unsafe_allow_html=True)
                
                # 3. Infos simples (Texte uniquement, pas de liens, pas de jours, pas de bloc-notes)
                st.markdown(f'<div class="info-texte">🏢 {r.get(c_soc, "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-texte">📅 {r.get(c_dat, "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-texte">💰 {r.get(c_pri, "0")} €</div>', unsafe_allow_html=True)
                
                st.divider()

# --- AUTRES PAGES (Conservées pour la structure) ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    st.info("Le planning reste inchangé.")

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 RÉSULTAT NET</div>', unsafe_allow_html=True)
    # Calculs statistiques ici...

elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    # Formulaire de maintenance ici...

# Les pages LOGS, FACTURES, SECU, NOTES suivent la même structure de menu























































































































































































































































































































































































