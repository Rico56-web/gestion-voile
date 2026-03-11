import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE CSS ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 12px; background: white; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }
    .section-haute { padding: 20px; border-bottom: 1px solid #eee; }
    .section-basse { padding: 15px; background-color: #f8f9fc; }
    .prenom-style { font-size: 1.6rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; margin-bottom: 5px; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 5px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def to_f(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace('€', '').replace(' ', '').strip())
    except: return 0.0

def safe_get_index(liste, valeur, par_defaut=0):
    val_clean = str(valeur).strip().lower()
    for i, item in enumerate(liste):
        if item.lower() == val_clean: return i
    return par_defaut

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
if m1.button("📋 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.session_state.edit_idx = None; st.rerun()
if m2.button("💰 STATS", use_container_width=True): st.session_state.page = "STATS"; st.rerun()
if m3.button("🔧 MAINT", use_container_width=True): st.session_state.page = "MAINT"; st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    c_f, c_p = st.columns(2)
    if c_f.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c_p.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_

















































































































































































































































































































































































































