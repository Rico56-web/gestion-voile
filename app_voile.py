import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE (FORÇAGE PRIORITAIRE) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    
    /* FIX NAVIGATION : Suppression totale du rouge */
    /* On cible tous les boutons de la barre de navigation */
    div.stButton > button {
        background-color: #f0f2f6 !important; /* Gris neutre */
        color: #31333f !important;
        border: 1px solid #d3d6db !important;
        transition: none !important;
    }
    
    /* On force le bouton "Secondary" (celui qu'on a choisi comme actif) en VERT */
    div.stButton > button:first-child[data-testid="baseButton-secondary"] {
        background-color: #2ecc71 !important; /* VERT */
        color: white !important;
        border: 2px solid #27ae60 !important;
    }

    /* RETOUR AUX BELLES FICHES INITIALES */
    .fiche-globale { border-left: 5px solid #1a2a6c; border-right: 1px solid #eee; border-top: 1px solid #eee; border-bottom: 1px solid #eee; border-radius: 8px; background: white; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); overflow: hidden; padding: 15px; }
    .prenom-style { font-size: 1.4rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; float: right; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 8px; margin-top: 10px; }
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

# Menus de navigation
m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    is_active = (st.session_state.page == name)
    # On utilise secondary pour le vert (actif) et primary pour le gris (inactif)
    if m[i].button(name, use_container_width=True, type="secondary" if is_active else "primary"):
        st.session_state.page = name
        st.session_state.edit_idx = None
        st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    # Filtres Archives/Futures (Eux aussi ne seront plus rouges)
    c_f, c_p = st.columns(2)
    v_arc = st.session_state.view_archive
    if c_f.button("🚀 MISSIONS FUTURES", use_container_width=True, type="secondary" if not v_arc else "primary"):
        st.session_state.view_archive = False; st.rerun()
    if c_p.button("📁 ARCHIVES", use_container_width=True, type="secondary" if v_arc else "primary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        # Formulaire de modification (Champs complets)
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            c1, c2, c3 = st.columns(3)
            u_date = c1.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_jours = c2.text_input("Nb jours", value=str(safe_get(r, 'NbJours')))
            u_statut = c3.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))
            
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], 1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'DateNav'], df.at[idx, 'NbJours'], df.at[idx, 'Statut'] = u_date, u_jours, u_statut
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Téléphone'] = u_pre, u_nom, u_tel
                df.at[idx, 'Email'], df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = u_mail, u_paye, u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()
    else:
        # Tri chronologique automatique
        if not df.empty and 'DateNav' in df.columns:
            df['dt_tri'] = pd.to_datetime(df['DateNav'], format='%d/%m/%Y', errors='coerce')
            df = df.sort_values(by='dt_tri', ascending=True)

        df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]

        for i, r in df_disp.iterrows():
            tel, mail = safe_get(r, 'Téléphone'), safe_get(r, 'Email')
            s_val = safe_get(r, 'Statut').upper()
            c_s = "#3498db" if "TERM" in s_val else "#2ecc71" if "OK" in s_val else "#e74c3c" if "REFUS" in s_val else "#f1c40f"
            
            st.markdown(f"""
            <div class="fiche-globale">
                <span class="statut-badge" style="background:{c_s};">{safe_get(r, 'Statut')}</span>
                <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                <div style="color:#e67e22; font-weight:bold; margin: 5px 0;">📞 {tel} | ✉️ {mail}</div>
                <p>📅 <b>{safe_get(r, 'DateNav')}</b> ({safe_get(r, 'NbJours')} j.) | 💰 <b>{safe_get(r, 'Prix', '0')} €</b></p>
                <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
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





























































































































































































































































































































































































































