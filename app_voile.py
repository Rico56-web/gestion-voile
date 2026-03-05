
import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- 2. INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_f(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")

# --- CHARGEMENT ---
df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE STATS (CORRIGÉE) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    
    ca = 0
    if not df.empty:
        # On calcule le CA sur toutes les fiches marquées "OK" ou "🟢"
        mask_ok = df['Statut'].str.contains("OK|🟢", na=False)
        ca = sum(df[mask_ok]['PrixJour'].apply(to_f))
    
    frais = 0
    if not df_f.empty:
        frais = sum(df_f['Montant'].apply(to_f))

    st.markdown(f'<div class="recap-line">CA TOTAL : {fmt_p(ca)} | FRAIS : {fmt_p(frais)} | NET : {fmt_p(ca-frais)}</div>', unsafe_allow_html=True)
    
    if not df.empty:
        st.write("### Détails des Navigations")
        st.dataframe(df[['DateNav', 'Nom', 'PrixJour', 'Statut']], use_container_width=True)

# --- PAGE MAINTENANCE (CORRIGÉE) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    # Formulaire d'ajout
    with st.expander("➕ AJOUTER UN FRAIS"):
        with st.form("new_frais"):
            d = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            m = st.text_input("Montant (€)")
            n = st.text_area("Note")
            if st.form_submit_button("Sauvegarder"):
                new_f = pd.concat([df_f, pd.DataFrame([{"Date":d, "Montant":m, "Note":n}])], ignore_index=True)
                sauvegarder_data(new_f, "frais.json")
                st.rerun()

    if not df_f.empty:
        # On parcourt le DataFrame à l'envers (plus récent en haut)
        for i in range(len(df_f)-1, -1, -1):
            r = df_f.iloc[i]
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; font-weight:bold; color:red;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Date")}</b><br>{r.get("Note")}
                </div>
            ''', unsafe_allow_html=True)
            if st.button("Supprimer", key=f"del_f_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json")
                st.rerun()
    else:
        st.info("Aucun frais enregistré dans maintenance.")




















































































































































































