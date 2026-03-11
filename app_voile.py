import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; }
    .fiche-complete { 
        border: 2px solid #1a2a6c; border-radius: 12px; 
        overflow: hidden; margin-bottom: 25px; background-color: white;
    }
    .zone-infos { padding: 18px; background: white; }
    .zone-actions { padding: 15px; background: #f1f3f6; border-top: 1px solid #1a2a6c; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; margin: 5px 0; }
    .btn-contact { 
        display: inline-block; padding: 8px 15px; border-radius: 5px; 
        text-decoration: none; color: white !important; font-size: 0.9rem; 
        font-weight: bold; margin-right: 10px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS GITHUB ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update", "content": content, "sha": sha})

# --- 3. NAVIGATION ---
st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

m = st.columns(6)
pages = [("📋 CONTACTS","CONTACTS"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.session_state.edit_idx = None; st.rerun()

# --- 4. LOGIQUE CONTACTS ---
if st.session_state.page == "CONTACTS":

    # --- MODE ÉDITION (DÉTAILS) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        st.subheader(f"📝 Modification : {r['Prénom']} {r['Nom']}")
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_tel = c1.text_input("Téléphone", value=r.get('Téléphone',''))
            u_mail = c2.text_input("Email", value=r.get('Mail',''))
            u_prix = st.text_input("Prix (€)", value=str(r.get('Prix','0')))
            u_notes = st.text_area("Notes", value=r.get('Notes',''), height=150)
            if st.form_submit_button("💾 SAUVEGARDER"):
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Notes'] = u_pre, u_nom, u_notes
                df.at[idx, 'Téléphone'], df.at[idx, 'Mail'], df.at[idx, 'Prix'] = u_tel, u_mail, u_prix
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None; st.success("Enregistré !"); st.rerun()
            if st.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None; st.rerun()

    # --- MODE AFFICHAGE ---
    else:
        search = st.text_input("🔍 Rechercher...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # --- DÉBUT ENCADRÉ GLOBAL ---
            st.markdown(f"""
            <div class="fiche-complete">
                <div class="zone-infos">
                    <div class="prenom-style">{r['Prénom']}</div>
                    <div class="nom-style">{str(r['Nom']).upper()}</div>
                    <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                    <p>🏢 <b>{r.get('Société','')}</b> | 💰 <b>{r.get('Prix','0')} €</b></p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                </div>
                <div class="zone-actions">
            """, unsafe_allow_html=True)
            
            # --- ZONE BASSE (Notes & Boutons) ---
            col_notes, col_btns = st.columns([0.7, 0.3])
            with col_notes:
                st.write("**Notes :**")
                st.write(r.get('Notes', ''))
            with col_btns:
                if st.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                    st.session_state.edit_idx = i; st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    # Confirmation simple
                    if st.checkbox("Confirmer ?", key=f"chk_{i}"):
                        df = df.drop(i)
                        sauvegarder_data(df, "contacts.json")
                        st.rerun()
            
            st.markdown('</div></div>', unsafe_allow_html=True)
            # --- FIN ENCADRÉ GLOBAL ---





























































































































































































































































































































































































