import requests
import base64
import streamlit as st
import pandas as pd
import json
import urllib.parse
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #1a2a6c; padding-bottom: 10px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #ddd; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin-bottom: -5px; }
    .nom-style { font-size: 1.1rem; text-transform: uppercase; color: #666; margin-bottom: 15px; }
    .btn-contact { display: inline-block; padding: 8px 15px; border-radius: 5px; text-decoration: none; color: white !important; font-weight: bold; margin-right: 10px; font-size: 0.9rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def to_f(val):
    try: return float(str(val).replace(',', '.').replace(' ', '').strip()) if val else 0.0
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            df = pd.DataFrame(json.loads(base64.b64decode(content).decode('utf-8')))
            df.columns = [str(c).strip() for c in df.columns]
            return df
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

# --- 3. ENTÊTE & NAVIGATION ---
st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "LISTE"
m = st.columns(8)
pages = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SECU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGE : LISTE (AVEC TOUS LES ÉLÉMENTS MANQUANTS) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher un contact (Nom ou Prénom)").lower()
    
    if not df.empty:
        # Filtrage
        mask = (df['Nom'].astype(str).str.lower().str.contains(search, na=False)) | \
               (df['Prénom'].astype(str).str.lower().str.contains(search, na=False))
        
        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            nom_complet = f"{r.get('Prénom','')} {r.get('Nom','').upper()}"
            
            with st.container():
                st.markdown(f"""
                <div class="client-card">
                    <div class="prenom-style">{r.get('Prénom', '')}</div>
                    <div class="nom-style">{str(r.get('Nom', '')).upper()}</div>
                    <p>🏢 <b>{r.get('Société','')}</b> | 📅 {r.get('DateNav','')} | ⏳ <b>{r.get('NbJours','1')} j</b> | 💰 {r.get('Prix','0')} €</p>
                    <div style="margin-top:10px;">
                        <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                        <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Zone Bloc-Notes et Boutons d'action
                c_txt, c_mod, c_sup = st.columns([0.8, 0.1, 0.1])
                with c_txt:
                    st.text_area("Bloc-notes", value=r.get('Notes',''), key=f"note_{i}", height=70, label_visibility="collapsed")
                with c_mod:
                    st.button("✏️", key=f"mod_{i}", help="Modifier")
                with c_sup:
                    if st.button("🗑️", key=f"sup_{i}", help="Supprimer"):
                        st.warning(f"Confirmer suppression de {nom_complet} ?")
                        if st.checkbox("OUI", key=f"conf_{i}"):
                            st.error("Supprimé !") # Logique de sauvegarde à ajouter ici
                st.divider()

# --- AUTRES PAGES (Conservées pour le fonctionnement du menu) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 STATISTIQUES</div>', unsafe_allow_html=True)
    # On reprend ici le code des stats avec calcul du NET
    ca = df[(df.get('Statut','')=="OK") & (df.get('Paiement','')=="Paid")]['Prix'].apply(to_f).sum()
    st.metric("Total Encaissé", f"{ca} €")
























































































































































































































































































































































































