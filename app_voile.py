import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

def charger_data(fichier):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
        res = requests.get(url, headers={"Authorization": f"token {TOKEN}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def sauvegarder_data(df, fichier):
    url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    sha = res.json()['sha'] if res.status_code == 200 else None
    content = json.dumps(df.to_dict(orient="records"), indent=4, ensure_ascii=False)
    data = {
        "message": f"Mise à jour {fichier}",
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

def safe_get(row, col):
    return str(row[col]) if col in row and pd.notnull(row[col]) else ""

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- TON STYLE CSS ---
st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); position: relative; }
    .border-cmn { border: 3px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .societe-style { color: #7f8c8d; font-size: 12px; font-weight: bold; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px 0; }
    .notes-box { background: #f9f9f9; padding: 8px; border-radius: 5px; font-size: 13px; margin-top: 10px; border-left: 3px solid #ddd; }
    .btn-contact { display: inline-block; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none !important; font-size: 13px; margin-right: 5px; margin-top: 10px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- MENU EN HAUT (Visible sur iPhone/iPad/PC) ---
st.title("⚓ Vesta Skipper 2026")
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
if col_m1.button("📅 PLANN", use_container_width=True): st.session_state.page = "PLANNING"
if col_m2.button("👤 CONT", use_container_width=True): st.session_state.page = "CONTACTS"
if col_m3.button("🔧 MAINT", use_container_width=True): st.session_state.page = "MAINTENANCE"
if col_m4.button("📝 NOTES", use_container_width=True): st.session_state.page = "NOTES"
if col_m5.button("📊 STATS", use_container_width=True): st.session_state.page = "STATS"

if "page" not in st.session_state: st.session_state.page = "PLANNING"
st.divider()

# --- CHARGEMENT ---
df_c = charger_data("contacts.json")

# --- PAGE CONTACTS (TON DESIGN) ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Mes Contacts")
    if st.button("➕ NOUVEAU CONTACT", use_container_width=True):
        new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()

    for i, r in df_c.iterrows():
        soc = safe_get(r, 'Société')
        pay_val = safe_get(r, 'Paiement')
        c_p = "#FF0000" if "PAS" in pay_val.upper() else "#2ecc71"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""
        
        st.markdown(f'''<div class="fiche-globale {cl_b}">
            <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
            <div class="societe-style">{soc if soc else "PARTICULIER"}</div>
            <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
            📞 {safe_get(r, "Téléphone")} | 📅 {safe_get(r, "DateNav")}<br>
            <div class="notes-box">📝 {safe_get(r, "Notes")}</div>
            <div style="margin-top:10px;">
                <a href="tel:{safe_get(r, 'Téléphone')}" class="btn-contact" style="background:#3498db;">Appeler</a>
                <a href="https://wa.me/{safe_get(r, 'Téléphone').replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
            </div>
        </div>''', unsafe_allow_html=True)

# --- PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("📅 Calendrier")
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Nov.", "Déc."]
    sel_mois = st.selectbox("Mois", range(1, 13), index=datetime.now().month - 1, format_func=lambda x: mois_noms[x-1])
    # ... (Reste du code calendrier identique)






























































































































































































































































































































































































































































































