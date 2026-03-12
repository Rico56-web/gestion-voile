import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE (RETOUR AU DESIGN INITIAL) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 12px; background: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }
    .section-haute { padding: 15px; border-bottom: 1px solid #eee; }
    .prenom-style { font-size: 1.4rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; }
    .btn-contact { display: inline-block; padding: 6px 10px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.8rem; font-weight: bold; margin-right: 5px; margin-top: 5px; }
    
    /* MENU ACTIF EN VERT */
    div.stButton > button:first-child[data-testid="baseButton-secondary"] {
        background-color: #2ecc71 !important;
        color: white !important;
        border: none !important;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
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
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

def safe_get(r, key, default=""):
    val = r.get(key)
    return default if pd.isna(val) or val is None else val

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    is_active = (st.session_state.page == name)
    if m[i].button(name, use_container_width=True, type="secondary" if is_active else "primary"):
        st.session_state.page = name
        st.session_state.edit_idx = None
        st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    # Filtres Archives/Futures
    c_f, c_p = st.columns(2)
    if c_f.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c_p.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        # Formulaire de modification
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            c1, c2, c3 = st.columns(3)
            u_date = c1.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_statut = c3.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                    index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_prix = st.text_input("Prix", value=str(safe_get(r, 'Prix', '0')))
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], 1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'DateNav'], df.at[idx, 'Statut'] = u_date, u_statut
                df.at[idx, 'Nom'], df.at[idx, 'Prénom'] = u_nom, u_pre
                df.at[idx, 'Téléphone'], df.at[idx, 'Email'] = u_tel, u_mail
                df.at[idx, 'Prix'], df.at[idx, 'Paiement'] = float(u_prix.replace(',','.')), u_paye
                df.at[idx, 'Notes'] = u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("❌ ANNULER"): st.session_state.edit_idx = None; st.rerun()
    else:
        # Tri chronologique
        if not df.empty and 'DateNav' in df.columns:
            df['dt_tri'] = pd.to_datetime(df['DateNav'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='dt_tri', ascending=True)

        view_arc = st.session_state.view_archive
        df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if view_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]

        for i, r in df_disp.iterrows():
            tel, mail = safe_get(r, 'Téléphone'), safe_get(r, 'Email')
            s_val = safe_get(r, 'Statut').upper()
            col_s = "#3498db" if "TERM" in s_val else "#2ecc71" if "OK" in s_val else "#e74c3c" if "REFUS" in s_val else "#f1c40f"
            
            st.markdown(f"""
            <div class="fiche-globale">
                <div class="section-haute">
                    <div style="float:right;"><span class="statut-badge" style="background:{col_s};">{safe_get(r, 'Statut')}</span></div>
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    <div style="color:#e67e22; font-weight:bold;">📞 {tel} | ✉️ {mail}</div>
                    <p style="margin-top:10px;">📅 <b>{safe_get(r, 'DateNav')}</b> | 🏢 <b>{safe_get(r, 'Société')}</b> | 💰 <b>{safe_get(r, 'Prix')} €</b></p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()

# --- AUTRES PAGES ---
elif st.session_state.page == "PLANNING": st.header("🗓️ Planning")
elif st.session_state.page == "STATS": st.header("💰 Statistiques")
elif st.session_state.page == "MAINT": st.header("🔧 Maintenance")
elif st.session_state.page == "FACTURES": st.header("🧾 Factures")
elif st.session_state.page == "NOTES": st.header("📝 Notes")



























































































































































































































































































































































































































