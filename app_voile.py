import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# Style CSS minimaliste pour éviter les conflits
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; }
    .fiche-globale { border: 1px solid #ddd; border-radius: 10px; padding: 15px; background: white; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .prenom-style { font-size: 1.4rem; font-weight: bold; color: #1a2a6c; margin-bottom: 5px; }
    .contact-link { text-decoration: none; font-weight: bold; margin-right: 15px; font-size: 1.1rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
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

# --- 3. NAVIGATION (Boutons simples) ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

# Barre de menus
m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    is_active = (st.session_state.page == name)
    # On utilise "primary" (souvent coloré par défaut) uniquement pour l'actif
    if m[i].button(name, use_container_width=True, type="primary" if is_active else "secondary"):
        st.session_state.page = name
        st.session_state.edit_idx = None
        st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    # Sélection ARCHIVES / MISSIONS
    c1, c2 = st.columns(2)
    v_arc = st.session_state.view_archive
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not v_arc else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if v_arc else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    st.markdown("---")

    if st.session_state.edit_idx is not None:
        # Formulaire de modification simplifié
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom')}")
            u_date = st.text_input("Date", value=safe_get(r, 'DateNav'))
            u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                  index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            
            if st.form_submit_button("💾 SAUVEGARDER"):
                df.at[idx, 'DateNav'], df.at[idx, 'Statut'] = u_date, u_stat
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'] = u_pre, u_nom
                df.at[idx, 'Téléphone'], df.at[idx, 'Email'] = u_tel, u_mail
                df.at[idx, 'Notes'] = u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()
    
    else:
        # Tri et Affichage
        if not df.empty:
            df['dt_tri'] = pd.to_datetime(df['DateNav'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='dt_tri', ascending=True)
            
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            
            for i, r in df_disp.iterrows():
                tel = safe_get(r, 'Téléphone')
                mail = safe_get(r, 'Email')
                
                st.markdown(f"""
                <div class="fiche-globale">
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    <p>📅 <b>{safe_get(r, 'DateNav')}</b> | 💰 <b>{safe_get(r, 'Prix')}€</b> | Statut : {safe_get(r, 'Statut')}</p>
                    <div style="margin-top:10px;">
                        <a href="tel:{tel}" class="contact-link">📞 Appel</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="contact-link">💬 WhatsApp</a>
                        <a href="mailto:{mail}" class="contact-link">✉️ Email</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button("✏️ Modifier la fiche", key=f"ed_{i}"):
                    st.session_state.edit_idx = i; st.rerun()

# --- AUTRES PAGES ---
elif st.session_state.page == "PLANNING": st.header("🗓️ Planning")
elif st.session_state.page == "STATS": st.header("💰 Statistiques")
elif st.session_state.page == "MAINT": st.header("🔧 Maintenance")
elif st.session_state.page == "FACTURES": st.header("🧾 Factures")
elif st.session_state.page == "NOTES": st.header("📝 Notes")



























































































































































































































































































































































































































