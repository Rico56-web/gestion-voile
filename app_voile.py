import requests
import base64
import streamlit as st
import pandas as pd
import json

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# CSS pour forcer l'encadré unique et propre
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    
    /* L'encadré global de la fiche */
    .fiche-complete { 
        border: 2px solid #1a2a6c; 
        border-radius: 12px; 
        overflow: hidden; 
        margin-bottom: 25px;
        background-color: white;
    }
    
    /* Zone du haut (Blanche) */
    .zone-infos { padding: 15px; background: white; }
    
    /* Zone du bas (Grise) */
    .zone-actions { 
        padding: 15px; 
        background: #f1f3f6; 
        border-top: 1px solid #1a2a6c; 
    }

    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; }
    
    .btn-contact { 
        display: inline-block; padding: 8px 15px; border-radius: 5px; 
        text-decoration: none; color: white !important; font-size: 0.9rem; 
        font-weight: bold; margin-right: 10px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

# --- 3. NAVIGATION ---
st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

m = st.columns(8)
pages = [("📋 CONTACTS","CONTACTS"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p
        st.session_state.edit_idx = None
        st.rerun()

# --- 4. LOGIQUE CONTACTS ---
if st.session_state.page == "CONTACTS":
    
    # --- A. FORMULAIRE DE MODIFICATION (DÉTAILS) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        st.markdown(f'<div class="page-title">📝 MODIFIER : {r["Prénom"]} {r["Nom"].upper()}</div>', unsafe_allow_html=True)
        
        with st.form("form_detail"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom', ''))
            u_nom = c2.text_input("Nom", value=r.get('Nom', ''))
            u_tel = c1.text_input("Téléphone", value=r.get('Téléphone', ''))
            u_mail = c2.text_input("Email", value=r.get('Mail', ''))
            u_soc = c1.text_input("Société", value=r.get('Société', ''))
            u_prix = c2.text_input("Prix (€)", value=str(r.get('Prix', '0')))
            u_notes = st.text_area("Notes / Livre de bord", value=r.get('Notes', ''))
            
            cb1, cb2 = st.columns(2)
            if cb1.form_submit_button("💾 ENREGISTRER"):
                # Ici la logique de sauvegarde GitHub
                st.session_state.edit_idx = None
                st.success("Enregistré !")
                st.rerun()
            if cb2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None
                st.rerun()

    # --- B. AFFICHAGE DE LA LISTE ---
    else:
        st.markdown('<div class="page-title">📇 GESTION DES CONTACTS</div>', unsafe_allow_html=True)
        search = st.text_input("🔍 Rechercher un contact...").lower()
        
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # OUVERTURE DE L'ENCADRÉ TOTAL
            st.markdown('<div class="fiche-complete">', unsafe_allow_html=True)
            
            # PARTIE HAUTE (Infos)
            st.markdown(f"""
            <div class="zone-infos">
                <div class="prenom-style">{r['Prénom']}</div>
                <div class="nom-style">{str(r['Nom']).upper()}</div>
                <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                <p style="margin-top:10px;">🏢 <b>{r.get('Société','')}</b> | 📅 {r.get('DateNav','')} | 💰 <b>{r.get('Prix','0')} €</b></p>
                <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
            </div>
            """, unsafe_allow_html=True)
            
            # PARTIE BASSE (Actions & Notes)
            st.markdown('<div class="zone-actions">', unsafe_allow_html=True)
            col_n, col_b = st.columns([0.7, 0.3])
            with col_n:
                st.text_area("Notes", value=r.get('Notes',''), key=f"nt_{i}", height=80, label_visibility="collapsed")
            with col_b:
                if st.button("✏️ MODIFIER / DÉTAILS", key=f"ed_{i}", use_container_width=True):
                    st.session_state.edit_idx = i
                    st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    st.warning("Confirmer ?")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # FERMETURE DE L'ENCADRÉ TOTAL
            st.markdown('</div>', unsafe_allow_html=True)



























































































































































































































































































































































































