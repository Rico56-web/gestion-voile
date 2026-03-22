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

# --- FONCTIONS UTILES ---
def safe_get(row, key, default=""):
    return row[key] if key in row and pd.notnull(row[key]) else default

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

# --- CONFIGURATION PAGE & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .border-cmn { border-left: 8px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; }
    .btn-contact { display: inline-block; padding: 12px; border-radius: 8px; color: white !important; text-decoration: none; font-size: 14px; font-weight: bold; text-align: center; width: 30%; }
    /* Optimisation iPhone : gros boutons */
    div.stButton > button { height: 3.5em; border-radius: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "view_archive" not in st.session_state: st.session_state.view_archive = False

df_c = charger_data("contacts.json")

# --- MENU PRINCIPAL (Adapté Mobile) ---
st.title("⚓ Vesta Skipper 2026")
cols = st.columns(5)
menu = ["PLANNING", "CONTACTS", "MAINTENANCE", "NOTES", "STATS"]
labels = ["📅 Plann", "👤 Cont", "🔧 Maint", "📝 Notes", "📊 Stat"]
for i, m in enumerate(menu):
    if cols[i].button(labels[i]): st.session_state.page = m

st.divider()

# --- MODULE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Gestion des Contacts & Clients")
    
    # 🔍 RECHERCHE
    search = st.text_input("🔍 Rechercher un nom, prénom ou société...", "").lower()
    
    # Bouton Ajout
    if st.button("➕ NOUVEAU CONTACT / NAVIGATION", use_container_width=True):
        new_row = {"Prénom": "Nouveau", "Nom": "Contact", "Société": "", "DateNav": datetime.now().strftime("%d/%m/%2026"), 
                   "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Prix": "0.00", "Notes": "", "Téléphone": "", "Email": ""}
        df_c = pd.concat([pd.DataFrame([new_row]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # Onglets En cours / Archivés
    t1, t2 = st.columns(2)
    if t1.button("🚀 EN COURS", type="primary" if not st.session_state.view_archive else "secondary", use_container_width=True):
        st.session_state.view_archive = False; st.rerun()
    if t2.button("📁 ARCHIVÉS", type="primary" if st.session_state.view_archive else "secondary", use_container_width=True):
        st.session_state.view_archive = True; st.rerun()

    # Filtrage des données
    df_filtered = df_c.copy()
    if search:
        df_filtered = df_filtered[
            df_filtered['Nom'].str.lower().str.contains(search) | 
            df_filtered['Prénom'].str.lower().str.contains(search) | 
            df_filtered['Société'].str.lower().str.contains(search)
        ]
    
    # Séparation Archives/En cours
    if st.session_state.view_archive:
        df_disp = df_filtered[df_filtered['Statut'].isin(["Terminé", "Refusé"])]
    else:
        df_disp = df_filtered[~df_filtered['Statut'].isin(["Terminé", "Refusé"])]

# Affichage des Fiches
    for idx, r in df_disp.iterrows():
        soc = safe_get(r, 'Société')
        is_cmn = "CMN" in soc.upper()
        cl_b = "border-cmn" if is_cmn else ""
        
        # --- LOGIQUE DE COULEUR (Extraite pour éviter l'erreur f-string) ---
        color_paye = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        # Couleur statut : Vert si OK, Bleu si Terminé, Jaune si Attente, Rouge si Refusé
        s_val = r['Statut'].upper()
        color_statut = "#2ecc71" if "OK" in s_val else "#3498db" if "TERM" in s_val else "#f1c40f" if "ATTENT" in s_val else "#e74c3c"

        # Calcul fidélité
        nb_nav = len(df_c[(df_c['Nom'] == r['Nom']) & (df_c['Prénom'] == r['Prénom'])])
        badge_fid = f"<span style='color:#f1c40f;'>⭐ Fidèle ({nb_nav})</span>" if nb_nav > 1 else ""

        # La Fiche Visuelle corrigée
        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{color_paye};">{r['Paiement']}</span>
                <span class="statut-badge" style="background:{color_statut};">{r['Statut']}</span>
                <div style="font-size:12px; color:gray;">{soc if soc else "PARTICULIER"} {badge_fid}</div>
                <div class="prenom-style">{r['Prénom']} {r['Nom'].upper()}</div>
                📅 <b>{r['DateNav']}</b> ({r['NbreJours']}j) | 💰 <b>{r['Prix']}€</b><br>
                <div style="margin-top:10px; display: flex; justify-content: space-between;">
                    <a href="tel:{r['Téléphone']}" class="btn-contact" style="background:#3498db;">Appel</a>
                    <a href="https://wa.me/{str(r['Téléphone']).replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                    <a href="mailto:{r['Email']}" class="btn-contact" style="background:#e67e22;">Mail</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Boutons Action
        col_ed, col_del = st.columns([1, 1])
        if col_ed.button(f"✏️ Modifier / Historique", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()

# --- MODULE STATS (Calculs automatiques) ---
if st.session_state.page == "STATS":
    st.subheader("📊 Bilan Financier Mensuel")
    df_c['Prix'] = pd.to_numeric(df_c['Prix'], errors='coerce').fillna(0)
    
    # Logique de calcul
    recettes = df_c[(df_c['Statut'] == "OK") & (df_c['Paiement'] == "Payé")]['Prix'].sum()
    previsions = df_c[(df_c['Paiement'] == "Pas payé")]['Prix'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Recettes (Encaissé)", f"{recettes:.2f} €")
    c2.metric("Prévisionnel (À recevoir)", f"{previsions:.2f} €")
    c3.metric("Bilan Total", f"{(recettes + previsions):.2f} €", delta_color="normal")

    st.info("Les données de Maintenance seront déduites ici une fois le module complété.")


























































































































































































































































































































































































































































































