import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB (Indispensable) ---
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
    except: return pd.DataFrame()

def sauvegarder_data(df, fichier):
    url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    sha = res.json()['sha'] if res.status_code == 200 else None
    content = json.dumps(df.to_dict(orient="records"), indent=4, ensure_ascii=False)
    data = {"message": f"Maj {fichier}", "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

# --- STYLE CSS (TES COULEURS) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .border-cmn { border: 3px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .societe-style { color: #7f8c8d; font-size: 12px; font-weight: bold; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px 0; }
    .notes-box { background: #f9f9f9; padding: 8px; border-radius: 5px; font-size: 13px; margin-top: 10px; border-left: 3px solid #ddd; }
    .btn-contact { display: inline-block; padding: 10px 15px; border-radius: 5px; color: white !important; text-decoration: none !important; font-size: 14px; margin-right: 5px; margin-top: 10px; font-weight: bold; }
    /* Style pour le nouveau menu horizontal */
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT ---
df_c = charger_data("contacts.json")
if "page" not in st.session_state: st.session_state.page = "PLANNING"

# --- NOUVEAU MENU HORIZONTAL (Pratique sur iPhone) ---
st.title("⚓ Vesta Skipper 2026")
m1, m2, m3, m4, m5 = st.columns(5)
if m1.button("📅 PLANN"): st.session_state.page = "PLANNING"
if m2.button("👤 CONT"): st.session_state.page = "CONTACTS"
if m3.button("🔧 MAINT"): st.session_state.page = "MAINTENANCE"
if m4.button("📝 NOTES"): st.session_state.page = "NOTES"
if m5.button("📊 STT"): st.session_state.page = "STATS"
st.divider()

# --- PAGE CONTACTS (Version avec Numérotation et Suppression) ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Mes Contacts")
    
    # Bouton Nouveau
    if st.button("➕ AJOUTER UN CONTACT", use_container_width=True):
        new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()

    # Affichage des fiches
    # On utilise enumerate pour avoir le numéro de la fiche (n+1)
    for n, (i, r) in enumerate(df_c.iterrows()):
        soc = str(r.get('Société', ""))
        pay = str(r.get('Paiement', "Pas payé"))
        stat = str(r.get('Statut', "En attente"))
        
        c_p = "#FF0000" if "PAS" in pay.upper() else "#2ecc71"
        c_s = "#3498db" if "TERM" in stat.upper() else "#f1c40f"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""
        
        # Affichage du numéro de fiche (#1, #2...) juste avant le prénom
        st.markdown(f'''<div class="fiche-globale {cl_b}">
            <span class="statut-badge" style="background:{c_p};">{pay}</span>
            <span class="statut-badge" style="background:{c_s};">{stat}</span>
            <div class="societe-style">{soc or "CLIENT PARTICULIER"}</div>
            <div class="prenom-style"><span style="color:#7f8c8d;">#{n+1}</span> | {r["Prénom"]} {str(r["Nom"]).upper()}</div>
            📅 {r["DateNav"]} ({r["NbreJours"]} jrs) | 💰 {r["Prix"]} €<br>
            <div class="notes-box">📝 {r["Notes"] or "."}</div>
            <div style="margin-top:10px;">
                <a href="tel:{r['Téléphone']}" class="btn-contact" style="background:#3498db;">Appeler</a>
                <a href="https://wa.me/{str(r['Téléphone']).replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
            </div>
        </div>''', unsafe_allow_html=True)
        
        # --- LOGIQUE DE SUPPRESSION AVEC CONFIRMATION ---
        if st.session_state.get('contact_confirm_del') == i:
            st.warning(f"⚠️ Supprimer la fiche #{n+1} ?")
            col_y, col_n = st.columns(2)
            if col_y.button("✅ OUI", key=f"y_{i}", use_container_width=True):
                df_c = df_c.drop(i)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.contact_confirm_del = None
                st.rerun()
            if col_n.button("❌ NON", key=f"n_{i}", use_container_width=True):
                st.session_state.contact_confirm_del = None
                st.rerun()
        else:
            col_edit, col_del = st.columns([1, 1])
            if col_edit.button(f"✏️ Modifier #{n+1}", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i
                # Ici tu peux ajouter ton formulaire de modification si besoin
            
            if col_del.button(f"🗑️ Supprimer #{n+1}", key=f"del_{i}", use_container_width=True):
                st.session_state.contact_confirm_del = i
                st.rerun()


























































































































































































































































































































































































































































































