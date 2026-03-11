import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    
    /* Encadré Principal */
    .fiche-container { 
        border: 2px solid #1a2a6c; border-radius: 10px 10px 0 0; 
        padding: 15px; background: #ffffff; margin-top: 10px;
    }
    /* Sous-Encadré (Notes et Actions) */
    .action-container { 
        border: 2px solid #1a2a6c; border-top: none; border-radius: 0 0 10px 10px; 
        padding: 10px; background: #f8f9fa; margin-bottom: 25px;
    }
    
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; line-height: 1; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; margin-bottom: 10px; }
    .contact-verif { font-family: monospace; color: #d35400; font-weight: bold; font-size: 0.95rem; }
    .btn-contact { display: inline-block; padding: 5px 10px; border-radius: 4px; text-decoration: none; color: white !important; font-size: 0.8rem; margin-right: 5px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()

# Authentification (Simplifiée pour le code)
if "auth" not in st.session_state: st.session_state.auth = True # À remettre sur False en prod

df = charger_data("contacts.json")

# --- 3. ENTÊTE & NAVIGATION ---
st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
m = st.columns(8)
pages = [("📋 CONTACTS","CONTACTS"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SECU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGE : CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher un contact...").lower()
    
    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        mask = (df['Nom'].astype(str).str.lower().str.contains(search, na=False)) | \
               (df['Prénom'].astype(str).str.lower().str.contains(search, na=False))
        
        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # --- BLOC 1 : INFORMATIONS ---
            st.markdown(f"""
            <div class="fiche-container">
                <div class="prenom-style">{r.get('Prénom', '')}</div>
                <div class="nom-style">{str(r.get('Nom', '')).upper()}</div>
                <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                <p style="margin-top:10px;">🏢 <b>{r.get('Société','')}</b> | 📅 {r.get('DateNav','')} | ⏳ {r.get('NbJours','1')}j | 💰 {r.get('Prix','0')}€</p>
                <div style="margin-top:5px;">
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#2ecc71;">WhatsApp</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- BLOC 2 : NOTES & ACTIONS (Double encadré lié) ---
            with st.container():
                st.markdown('<div class="action-container">', unsafe_allow_html=True)
                c_txt, c_btns = st.columns([0.8, 0.2])
                
                with c_txt:
                    st.text_area("Bloc-notes", value=r.get('Notes',''), key=f"note_{i}", height=65, label_visibility="collapsed")
                
                with c_btns:
                    # Bouton Modifier (Ouvre un formulaire ou simule l'édition)
                    if st.button("✏️ Modifier", key=f"mod_{i}", use_container_width=True):
                        st.info(f"Édition de {r.get('Prénom')} activée")
                    
                    # Bouton Supprimer avec confirmation
                    if st.button("🗑️ Effacer", key=f"sup_{i}", use_container_width=True):
                        st.session_state[f"conf_{i}"] = True
                    
                    if st.session_state.get(f"conf_{i}"):
                        if st.button("✅ Confirmer ?", key=f"ok_{i}"):
                            st.error("Suppression effectuée") # Logique de sauvegarde à lier
                
                st.markdown('</div>', unsafe_allow_html=True)

# --- LOGIQUE DES AUTRES PAGES (Inchangée) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 STATISTIQUES</div>', unsafe_allow_html=True)
    # Votre code stats ici
























































































































































































































































































































































































