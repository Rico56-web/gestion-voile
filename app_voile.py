import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB (Secrets) ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

# --- FONCTIONS DE DONNÉES ---
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
    data = {"message": f"Update {fichier}", "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

def safe_get(row, col, default=""):
    return str(row[col]) if col in row and pd.notnull(row[col]) else default

# --- INTERFACE ET DESIGN ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .fiche-globale { background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e4e8; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .border-cmn { border-left: 10px solid #3498db !important; }
    .statut-badge { float: right; padding: 6px 14px; border-radius: 20px; color: white; font-size: 12px; font-weight: 800; margin-left: 10px; text-transform: uppercase; }
    .societe-style { color: #7f8c8d; font-size: 13px; font-weight: bold; letter-spacing: 1.2px; }
    .prenom-style { font-size: 22px; font-weight: 800; color: #1a1a1a; margin: 10px 0; }
    .notes-box { background: #f1f3f5; padding: 15px; border-radius: 8px; font-size: 14px; margin-top: 15px; border-left: 4px solid #ced4da; color: #444; }
    .btn-contact { display: inline-block; padding: 12px 24px; border-radius: 8px; color: white !important; text-decoration: none !important; font-size: 14px; margin-right: 10px; font-weight: bold; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "view_archive" not in st.session_state: st.session_state.view_archive = False

with st.sidebar:
    st.title("⚓ Vesta Skipper")
    st.info("Saison 2026")
    if st.button("📅 PLANNING", use_container_width=True): st.session_state.page = "PLANNING"
    if st.button("👤 MISSIONS", use_container_width=True): st.session_state.page = "CONTACTS"
    if st.button("🔧 ENTRETIEN", use_container_width=True): st.session_state.page = "MAINTENANCE"
    if st.button("📝 JOURNAL", use_container_width=True): st.session_state.page = "NOTES"
    if st.button("📊 STATISTIQUES", use_container_width=True): st.session_state.page = "STATS"

df_c = charger_data("contacts.json")

# --- PAGE STATISTIQUES (STT) ---
if st.session_state.page == "STATS":
    st.title("📊 Analyse de la Saison")
    if not df_c.empty:
        # Nettoyage des données pour calcul
        df_c['Prix_Float'] = df_c['Prix'].apply(lambda x: float(str(x).replace('€','').strip() or 0))
        df_c['Jours_Int'] = df_c['NbreJours'].apply(lambda x: int(str(x) or 0))
        
        # Colonnes de Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("CA Total", f"{df_c['Prix_Float'].sum():.2f} €")
        m2.metric("Missions", len(df_c))
        m3.metric("Jours Mer", df_c['Jours_Int'].sum())
        m4.metric("Prix/Jour Moy.", f"{(df_c['Prix_Float'].sum() / df_c['Jours_Int'].sum() if df_c['Jours_Int'].sum() > 0 else 0):.2f} €")
        
        st.divider()
        
        # Graphiques
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Volume par Société")
            st.bar_chart(df_c.groupby('Société')['Prix_Float'].sum())
        with col_g2:
            st.subheader("Répartition des Statuts")
            st.pie_chart(df_c['Statut'].value_counts())
            
        st.subheader("Détail Financier par Mission")
        st.dataframe(df_c[['DateNav', 'Société', 'Prénom', 'Nom', 'NbreJours', 'Prix', 'Statut', 'Paiement']], use_container_width=True)
    else:
        st.warning("Aucune donnée pour les statistiques.")

# --- PAGE CONTACTS ---
elif st.session_state.page == "CONTACTS":
    st.title("👤 Gestion des Missions")
    
    # Boutons de contrôle
    c_btn1, c_btn2 = st.columns(2)
    if c_btn1.button("➕ NOUVELLE MISSION", use_container_width=True, type="primary"):
        new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()
    
    label_arch = "📁 ARCHIVES (Terminé/Refusé)" if not st.session_state.view_archive else "🚀 RETOUR MISSIONS EN COURS"
    if c_btn2.button(label_arch, use_container_width=True):
        st.session_state.view_archive = not st.session_state.view_archive; st.rerun()

    # Affichage
    df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
    
    for i, r in df_disp.iterrows():
        soc, s_val, pay_val = safe_get(r, 'Société'), safe_get(r, 'Statut'), safe_get(r, 'Paiement')
        c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
        c_p = "#FF0000" if "PAS" in pay_val.upper() else "#2ecc71"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""
        
        st.markdown(f'''<div class="fiche-globale {cl_b}">
            <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
            <span class="statut-badge" style="background:{c_s};">{s_val}</span>
            <div class="societe-style">{soc or "PARTICULIER"}</div>
            <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
            📅 <b>{safe_get(r, "DateNav")}</b> ({safe_get(r, "NbreJours")} jrs) | 💰 <b>{safe_get(r, "Prix")} €</b><br>
            📞 {safe_get(r, "Téléphone")} | ✉️ {safe_get(r, "Email")}
            <div class="notes-box">📝 {safe_get(r, "Notes") or "..."}</div>
            <div style="margin-top:15px;">
                <a href="tel:{safe_get(r, 'Téléphone')}" class="btn-contact" style="background:#3498db;">Appeler</a>
                <a href="https://wa.me/{safe_get(r, 'Téléphone').replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
            </div>
        </div>''', unsafe_allow_html=True)
        if st.button(f"✏️ MODIFIER {i}", key=f"ed_{i}"):
            st.session_state.edit_idx = i; st.rerun()

# --- AUTRES PAGES (NOTES, MAINTENANCE, PLANNING) ---
# ... (Elles reprennent les structures complètes précédentes)




























































































































































































































































































































































































































































































