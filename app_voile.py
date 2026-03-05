import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .recap-box { background: #f8f9fa; padding: 20px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; margin-bottom: 20px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=2)
def charger_data(file="contacts.json"):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
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
def parse_d(d):
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "stat_y" not in st.session_state: st.session_state.stat_y = datetime.now().year
if "stat_m" not in st.session_state: st.session_state.stat_m = datetime.now().month

if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE STATS (AVEC FILTRES ANNÉE/MOIS) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN FINANCIER DÉTAILLÉ</div>', unsafe_allow_html=True)
    
    # Sélecteurs de période
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.stat_y = st.selectbox("Sélectionner l'Année", [2024, 2025, 2026, 2027, 2028], index=[2024, 2025, 2026, 2027, 2028].index(st.session_state.stat_y))
    with c2:
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre", "TOUTE L'ANNÉE"]
        choix_m = st.selectbox("Sélectionner le Mois", range(1, 14), format_func=lambda x: mois_noms[x-1], index=st.session_state.stat_m-1)
        st.session_state.stat_m = choix_m

    # Filtrage des données
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask_nav = (df['dt'].dt.year == st.session_state.stat_y)
        if st.session_state.stat_m < 13:
            mask_nav &= (df['dt'].dt.month == st.session_state.stat_m)
        df_filtre = df[mask_nav & df['Statut'].str.contains("OK|🟢", na=False)].copy()
        
        # Frais (Maintenance)
        df_f['dt'] = df_f['Date'].apply(parse_d)
        mask_frais = (df_f['dt'].dt.year == st.session_state.stat_y)
        if st.session_state.stat_m < 13:
            mask_frais &= (df_f['dt'].dt.month == st.session_state.stat_m)
        df_f_filtre = df_f[mask_frais].copy()

        # Calculs
        ca = sum(df_filtre['PrixJour'].apply(to_f))
        frais = sum(df_f_filtre['Montant'].apply(to_f))
        net = ca - frais

        # Affichage Recap
        periode_txt = f"{mois_noms[st.session_state.stat_m-1]} {st.session_state.stat_y}" if st.session_state.stat_m < 13 else f"Année {st.session_state.stat_y}"
        st.markdown(f'''
            <div class="recap-box">
                <small>Période : {periode_txt}</small>
                <h2 style="color:#1a2a6c; margin:0;">NET : {fmt_p(net)}</h2>
                <p style="margin:5px 0 0 0;">Revenus (Confirmés) : {fmt_p(ca)} | Frais : {fmt_p(frais)}</p>
            </div>
        ''', unsafe_allow_html=True)

        # Tableau de détail
        if not df_filtre.empty:
            st.write("### 📈 Détail des Navigations")
            df_tab = df_filtre[['DateNav', 'Nom', 'Société', 'PrixJour']].copy()
            df_tab['PrixJour'] = df_tab['PrixJour'].apply(fmt_p)
            st.table(df_tab)
        else:
            st.info("Aucune navigation confirmée pour cette période.")

# --- LES AUTRES PAGES (LISTE, PLAN, FRAIS) RESTENT IDENTIQUES ---














































































































































































