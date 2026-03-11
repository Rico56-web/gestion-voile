import requests
import base64
import streamlit as st
import pandas as pd
import json

# --- 1. STYLE CSS (Double Encadré Connecté) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    
    /* ENCADRÉ DU HAUT (Identité) */
    .fiche-haut { 
        border: 2px solid #1a2a6c; border-bottom: 1px dashed #1a2a6c;
        border-radius: 10px 10px 0 0; padding: 15px; background: #ffffff; 
        margin-top: 10px;
    }
    /* ENCADRÉ DU BAS (Notes + Boutons) */
    .fiche-bas { 
        border: 2px solid #1a2a6c; border-top: none;
        border-radius: 0 0 10px 10px; padding: 15px; background: #f1f3f6; 
        margin-bottom: 30px; 
    }
    
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; line-height: 1.1; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: 'Courier New', monospace; color: #e67e22; font-weight: bold; }
    
    .btn-contact { 
        display: inline-block; padding: 6px 12px; border-radius: 4px; 
        text-decoration: none; color: white !important; font-size: 0.85rem; 
        font-weight: bold; margin-right: 8px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. CHARGEMENT DATA ---
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

df = charger_data("contacts.json")

# --- 3. ENTÊTE & NAVIGATION ---
st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

m = st.columns(8)
pages = [("📋 CONTACTS","CONTACTS"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SECU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p
        st.session_state.edit_idx = None
        st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">📇 GESTION DES CONTACTS</div>', unsafe_allow_html=True)

    # --- MODE ÉDITION (Fiche détaillée) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        row = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Détail : {row['Prénom']} {row['Nom']}")
            # Formulaire d'édition complet ici...
            if st.form_submit_button("Sauvegarder"): st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()

    # --- MODE LISTE ---
    else:
        search = st.text_input("🔍 Rechercher un nom...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # --- BLOC DU HAUT (Blanc : Infos & Liens) ---
            st.markdown(f"""
            <div class="fiche-haut">
                <div class="prenom-style">{r['Prénom']}</div>
                <div class="nom-style">{str(r['Nom']).upper()}</div>
                <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                <p style="margin-top:8px; margin-bottom:0;">🏢 <b>{r.get('Société','')}</b> | 📅 {r.get('DateNav','')} | 💰 <b>{r.get('Prix','0')} €</b></p>
                <div>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- BLOC DU BAS (Gris : Notes + Boutons) ---
            # On ouvre l'encadré gris avec Markdown
            st.markdown('<div class="fiche-bas">', unsafe_allow_html=True)
            
            # Utilisation de colonnes Streamlit à l'intérieur de l'encadré gris
            c_notes, c_actions = st.columns([0.75, 0.25])
            
            with c_notes:
                st.text_area("Notes", value=r.get('Notes',''), key=f"notes_{i}", height=75, label_visibility="collapsed")
            
            with c_actions:
                if st.button("✏️ MODIFIER", key=f"btn_edit_{i}", use_container_width=True):
                    st.session_state.edit_idx = i
                    st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"btn_del_{i}", use_container_width=True):
                    st.warning("Confirmer ?")
            
            # On ferme l'encadré gris
            st.markdown('</div>', unsafe_allow_html=True)


























































































































































































































































































































































































