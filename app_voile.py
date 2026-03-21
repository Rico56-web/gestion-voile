import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
import os
from datetime import datetime

# --- CONFIGURATION GITHUB (Secrets Streamlit) ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

# --- FONCTIONS GITHUB (Remplacent os.path pour le Cloud) ---
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

# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); position: relative; }
    .border-cmn { border: 3px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .societe-style { color: #7f8c8d; font-size: 12px; font-weight: bold; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px 0; }
    .notes-box { background: #f9f9f9; padding: 8px; border-radius: 5px; font-size: 13px; margin-top: 10px; border-left: 3px solid #ddd; }
    .btn-contact { display: inline-block; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none !important; font-size: 13px; margin-right: 5px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION SESSION ---
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "view_archive" not in st.session_state: st.session_state.view_archive = False

# --- CHARGEMENT ---
df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("⚓ Vesta 2026")
    if st.button("📅 PLANNING", use_container_width=True): st.session_state.page = "PLANNING"
    if st.button("👤 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"
    if st.button("🔧 MAINTENANCE", use_container_width=True): st.session_state.page = "MAINTENANCE"
    if st.button("📝 NOTES", use_container_width=True): st.session_state.page = "NOTES"
    if st.button("📊 STATS", use_container_width=True): st.session_state.page = "STATS"

# --- LOGIQUE DES PAGES ---

if st.session_state.page == "PLANNING":
    st.title("📅 Planning 2026")
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Nov.", "Déc."]
    sel_mois = st.selectbox("Mois", range(1, 13), index=datetime.now().month - 1, format_func=lambda x: mois_noms[x-1])
    missions_dict = {str(safe_get(r, 'DateNav')).strip(): safe_get(r, 'Société') for _, r in df_c.iterrows()}
    import calendar
    cal = calendar.Calendar(firstweekday=0)
    jours_cal = cal.monthdatescalendar(2026, sel_mois)
    cols_h = st.columns(7)
    for i, j in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]): cols_h[i].write(f"**{j}**")
    for sem in jours_cal:
        cols = st.columns(7)
        for i, d in enumerate(sem):
            if d.month == sel_mois:
                d_str = d.strftime("%d/%m/%Y")
                bg, bord, info = "#ffffff", "1px solid #eee", ""
                if d_str in missions_dict:
                    info = missions_dict[d_str][:10]
                    bg = "#e3f2fd" if "CMN" in info.upper() else "#ffffff"
                    bord = "2px solid #3498db" if "CMN" in info.upper() else "1px solid #2ecc71"
                cols[i].markdown(f'<div style="background:{bg}; border:{bord}; padding:10px 2px; border-radius:5px; text-align:center; min-height:65px;"><div style="font-weight:bold;">{d.day}</div><div style="font-size:9px; color:#555;">{info}</div></div>', unsafe_allow_html=True)

elif st.session_state.page == "CONTACTS":
    st.title("👤 Gestion des Contacts")
    if st.button("➕ NOUVEAU CONTACT", use_container_width=True):
        new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": "", "NbreJours": "1"}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()
    
    # Affichage des fiches (exactement ton style d'hier)
    for i, r in df_c.iterrows():
        soc = safe_get(r, 'Société')
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""
        st.markdown(f'''<div class="fiche-globale {cl_b}">
            <span class="statut-badge" style="background:#2ecc71;">{safe_get(r, "Statut")}</span>
            <div class="societe-style">{soc if soc else "PARTICULIER"}</div>
            <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
            📞 {safe_get(r, "Téléphone")} | ✉️ {safe_get(r, "Email")}<br>
            <div class="notes-box">📝 {safe_get(r, "Notes")}</div>
            <a href="tel:{safe_get(r, "Téléphone")}" class="btn-contact" style="background:#3498db;">Appeler</a>
        </div>''', unsafe_allow_html=True)

elif st.session_state.page == "MAINTENANCE":
    st.title("🔧 Maintenance & Travaux")
    if st.button("➕ AJOUTER UN TRAVAIL"):
        new_m = {"Date": datetime.now().strftime("%d/%m/%Y"), "Titre": "Nouvelle tâche", "Statut": "À faire"}
        df_m = pd.concat([df_m, pd.DataFrame([new_m])], ignore_index=True)
        sauvegarder_data(df_m, "maint.json"); st.rerun()
    st.table(df_m)

elif st.session_state.page == "NOTES":
    st.title("📝 Bloc-Notes")
    # On utilise GitHub pour les notes aussi pour ne rien perdre
    res_n = requests.get(f"https://api.github.com/repos/{REPO}/contents/notes.txt", headers={"Authorization": f"token {TOKEN}"})
    current_n = base64.b64decode(res_n.json()['content']).decode('utf-8') if res_n.status_code == 200 else ""
    new_n = st.text_area("Notes générales", value=current_n, height=300)
    if st.button("💾 SAUVEGARDER"):
        sha_n = res_n.json()['sha'] if res_n.status_code == 200 else None
        data_n = {"message": "Maj notes", "content": base64.b64encode(new_n.encode('utf-8')).decode('utf-8'), "sha": sha_n}
        requests.put(f"https://api.github.com/repos/{REPO}/contents/notes.txt", headers={"Authorization": f"token {TOKEN}"}, json=data_n)
        st.success("Notes sauvées !")

elif st.session_state.page == "STATS":
    st.title("📊 Statistiques")
    if not df_c.empty:
        st.metric("Total Missions", len(df_c))
        st.bar_chart(df_c['Société'].value_counts())































































































































































































































































































































































































































































































