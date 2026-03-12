import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE (NETTOYAGE RADICAL) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    /* Entête */
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; }
    
    /* RESET COMPLET DES COULEURS DES BOUTONS */
    /* On force TOUS les boutons à être gris par défaut */
    div.stButton > button {
        background-color: #f0f2f6 !important;
        color: black !important;
        border: 1px solid #d3d6db !important;
    }

    /* FORCE LE BOUTON ACTIF EN VERT (uniquement celui-là) */
    div.stButton > button:first-child[data-testid="baseButton-secondary"] {
        background-color: green !important;
        color: white !important;
        border: none !important;
        font-weight: bold !important;
    }

    /* Style des fiches */
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 10px; background: white; margin-bottom: 15px; padding: 15px; }
    .prenom-style { font-size: 1.4rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; }
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

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

# Menus
m_cols = st.columns(6)
menus = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for idx, m_name in enumerate(menus):
    active = (st.session_state.page == m_name)
    # On utilise "secondary" pour le vert, "primary" pour le gris
    if m_cols[idx].button(m_name, use_container_width=True, type="secondary" if active else "primary"):
        st.session_state.page = m_name
        st.session_state.edit_idx = None
        st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    # Filtres Archives/Futures
    c1, c2 = st.columns(2)
    show_arc = st.session_state.view_archive
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="secondary" if not show_arc else "primary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="secondary" if show_arc else "primary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        # Formulaire de modification
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            # ... (champs de saisie identiques)
            u_date = st.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_statut = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_prix = st.text_input("Prix Total (€)", value=str(safe_get(r, 'Prix', '0')))
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], 1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'DateNav'], df.at[idx, 'Statut'], df.at[idx, 'Nom'] = u_date, u_statut, u_nom
                df.at[idx, 'Prénom'], df.at[idx, 'Téléphone'], df.at[idx, 'Email'] = u_pre, u_tel, u_mail
                df.at[idx, 'Prix'], df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = float(u_prix.replace(',','.')), u_paye, u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("❌ ANNULER"): st.session_state.edit_idx = None; st.rerun()
    else:
        # Tri et Affichage
        if not df.empty:
            df['dt_tri'] = pd.to_datetime(df['DateNav'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='dt_tri', ascending=True)
            
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if show_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            
            for i, r in df_disp.iterrows():
                st.markdown(f"""<div class="fiche-globale">
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    <p>📅 {safe_get(r, 'DateNav')} | 💰 {safe_get(r, 'Prix')}€ | Statut: {safe_get(r, 'Statut')}</p>
                </div>""", unsafe_allow_html=True)
                if st.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()

# --- AUTRES PAGES ---
else:
    st.header(f"Page {st.session_state.page}")

























































































































































































































































































































































































































