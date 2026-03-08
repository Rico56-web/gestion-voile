import streamlit as st
import pandas as pd
import json, base64, requests, calendar
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "SKIPPER2026": 
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect ❌")
    st.stop()

# Initialisation
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_s_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin: 5px 0; }
    .secu-item { display: flex; align-items: center; justify-content: space-between; background: #f9f9f9; padding: 5px 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #eee; }
</style>""", unsafe_allow_html=True)

# --- 2. DATA ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    # Default Sécu si vide
    if file == "secu.json": return pd.DataFrame([{"Item": "Vannes de coque"}, {"Item": "Niveau Huile/Eau"}, {"Item": "Météo consultée"}])
    return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    st.cache_data.clear()

df = charger_data("contacts.json")
df_s = charger_data("secu.json")

def nav_to(p): st.session_state.page = p

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
m_cols = st.columns(6)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    m_cols[i].button(l, on_click=nav_to, args=(p,), use_container_width=True, type="primary" if st.session_state.page==p else "secondary")

# --- 4. PAGES ---

if st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 GESTION SÉCURITÉ</div>', unsafe_allow_html=True)
    
    # Mode édition d'un item
    if st.session_state.edit_s_idx is not None:
        idx = st.session_state.edit_s_idx
        init_val = df_s.loc[idx, "Item"] if idx != "NEW" else ""
        with st.form("edit_item_secu"):
            new_val = st.text_input("Intitulé du point de contrôle", init_val)
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ VALIDER"):
                if idx == "NEW": df_s = pd.concat([df_s, pd.DataFrame([{"Item": new_val}])], ignore_index=True)
                else: df_s.at[idx, "Item"] = new_val
                sauvegarder_data(df_s, "secu.json"); st.session_state.edit_s_idx = None; st.rerun()
            if c2.form_submit_button("ANNULER"): st.session_state.edit_s_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER UN POINT DE CONTRÔLE", on_click=lambda: st.session_state.update({"edit_s_idx":"NEW"}), use_container_width=True)
        st.write("---")
        for i, r in df_s.iterrows():
            col_txt, col_ed, col_del = st.columns([6, 1, 1])
            col_txt.checkbox(r["Item"], key=f"c_{i}")
            if col_ed.button("✏️", key=f"ed_s_{i}"):
                st.session_state.edit_s_idx = i; st.rerun()
            if col_del.button("🗑️", key=f"del_s_{i}"):
                df_s.drop(i).pipe(sauvegarder_data, "secu.json"); st.rerun()

elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    if not df.empty:
        df['dt'] = pd.to_datetime(df['DateNav'], format='%d/%m/%Y', errors='coerce')
        for i, r in df.sort_values('dt', ascending=True).iterrows():
            soc = str(r.get('Société','')).strip().upper()
            col_s = "#3498db" if soc == "CMN" else "#2ecc71"
            tel = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            # AJOUT DE L'EMAIL ICI
            mail = r.get('Email','')
            st.markdown(f"""<div class="client-card" style="border-left:12px solid {col_s};">
                <b>{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 {soc} | 📅 {r.get('DateNav')}<br>
                📧 <a href="mailto:{mail}">{mail}</a><br>
                📞 <a href="tel:{tel}">{r.get('Téléphone','')}</a> | <a href="https://wa.me/{tel}" class="wa-btn">💬 WA</a>
                </div>""", unsafe_allow_html=True)

# Les autres menus (PLANNING, BUDGET, FRAIS, NOTES) restent inchangés dans ta logique globale.
















































































































































































































































