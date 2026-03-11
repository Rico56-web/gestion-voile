import requests
import base64
import streamlit as st
import pandas as pd
import json

# --- 1. CONFIGURATION & STYLE (CSS OPTIMISÉ) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    
    /* Bloc du haut (Infos) */
    .fiche-container { 
        border: 2px solid #1a2a6c; border-bottom: 1px dashed #ccc;
        border-radius: 10px 10px 0 0; padding: 15px; background: #ffffff; 
    }
    /* Bloc du bas (Notes + Boutons) */
    .action-container { 
        border: 2px solid #1a2a6c; border-top: none;
        border-radius: 0 0 10px 10px; padding: 15px; background: #f1f3f6; 
        margin-bottom: 30px; 
    }
    
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; line-height: 1.1; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; margin-bottom: 8px; }
    .contact-verif { font-family: 'Courier New', monospace; color: #e67e22; font-weight: bold; font-size: 1rem; }
    
    /* Boutons de contact rapides */
    .btn-contact { 
        display: inline-block; padding: 6px 12px; border-radius: 4px; 
        text-decoration: none; color: white !important; font-size: 0.85rem; 
        font-weight: bold; margin-right: 8px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def to_f(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').replace('€', '').strip())
    except: return 0.0

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
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
df = charger_data("contacts.json")

st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
m = st.columns(8)
pages = [("📋 CONTACTS","CONTACTS"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
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
        with st.form("edit_detail"):
            st.subheader(f"Modification de {row['Prénom']} {row['Nom']}")
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=row['Prénom'])
            u_nom = c2.text_input("Nom", value=row['Nom'])
            u_tel = c1.text_input("Téléphone", value=row.get('Téléphone',''))
            u_mail = c2.text_input("Email", value=row.get('Mail',''))
            u_prix = st.text_input("Prix (€)", value=str(row.get('Prix','0')))
            u_notes = st.text_area("Bloc-notes", value=row.get('Notes',''))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                # Logique de sauvegarde ici
                st.session_state.edit_idx = None
                st.rerun()
            if st.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None
                st.rerun()

    # --- MODE LISTE ---
    else:
        search = st.text_input("🔍 Rechercher...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # --- BLOC 1 : INFOS + LIENS ---
            st.markdown(f"""
            <div class="fiche-container">
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
            
            # --- BLOC 2 : NOTES + BOUTONS (DANS L'ENCADRÉ GRIS) ---
            st.markdown('<div class="action-container">', unsafe_allow_html=True)
            col_n, col_b = st.columns([0.75, 0.25])
            
            with col_n:
                # Affichage des notes (en lecture seule ici)
                st.text_area("Notes", value=r.get('Notes',''), key=f"notes_v_{i}", height=70, label_visibility="collapsed", disabled=True)
            
            with col_b:
                if st.button("✏️ MODIFIER", key=f"ed_btn_{i}", use_container_width=True):
                    st.session_state.edit_idx = i
                    st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_btn_{i}", use_container_width=True):
                    st.error("Confirmer ?") # Logique de suppression simplifiée
            
            st.markdown('</div>', unsafe_allow_html=True)

# --- PAGE STATS (Vérification des calculs) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 RÉSULTAT NET</div>', unsafe_allow_html=True)
    total_prix = df['Prix'].apply(to_f).sum()
    st.metric("Total des Prix dans Contacts", f"{total_prix} €")

























































































































































































































































































































































































