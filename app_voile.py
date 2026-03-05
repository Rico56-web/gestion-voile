import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS (LISIBILITÉ MAXIMALE) ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #eee; border-left: 10px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .recap-box { background: #f8f9fa; padding: 20px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; margin-bottom: 25px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB (SÉCURISÉES) ---
@st.cache_data(ttl=1)
def charger_data(file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            data = json.loads(content)
            return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Erreur de chargement {file}: {e}")
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_str = df.to_json(orient="records", indent=4, force_ascii=False)
        content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_f(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0

def fmt_p(v): 
    return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")

def parse_d(d):
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "cal_y" not in st.session_state: st.session_state.cal_y = 2026
if "cal_m" not in st.session_state: st.session_state.cal_m = 1
if "del_idx" not in st.session_state: st.session_state.del_idx = None

if not st.session_state.get("auth"):
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

# Chargement forcé
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

# --- PAGE LISTE (RÉTABLIE) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view_mode = "FUTUR"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTUR" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTUR"))

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b> ({r.get("Société","")})<br>
                    📅 <b>{r.get("DateNav","")}</b> — {r.get("NbJours","1")} jour(s)<br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️", key=f"ed_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if c2.button("🗑️", key=f"dl_{i}"): 
                st.session_state.del_idx = i; st.rerun()
            
            if st.session_state.del_idx == i:
                if st.button("CONFIRMER SUPPRESSION", key=f"conf_{i}"):
                    df.drop(i).pipe(sauvegarder_data); st.session_state.del_idx = None; st.rerun()

# --- PAGE STATS (RÉTABLIE AVEC FILTRES) ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN FINANCIER</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    sel_y = c1.selectbox("Année", [2024, 2025, 2026, 2027, 2028], index=2)
    sel_m = c2.selectbox("Mois", range(1, 13), format_func=lambda x: calendar.month_name[x])

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask = (df['dt'].dt.year == sel_y) & (df['dt'].dt.month == sel_m) & (df['Statut'].str.contains("OK|🟢", na=False))
        ca = sum(df[mask]['PrixJour'].apply(to_f))
        
        frais = 0
        if not df_f.empty:
            df_f['dt'] = df_f['Date'].apply(parse_d)
            frais = sum(df_f[(df_f['dt'].dt.year == sel_y) & (df_f['dt'].dt.month == sel_m)]['Montant'].apply(to_f))

        st.markdown(f'''
            <div class="recap-box">
                <h2 style="color:#1a2a6c;">NET : {fmt_p(ca - frais)}</h2>
                <p>CA : {fmt_p(ca)} | Frais : {fmt_p(frais)}</p>
            </div>
        ''', unsafe_allow_html=True)
        st.table(df[mask][['DateNav', 'Nom', 'PrixJour']])

# --- PAGE MAINTENANCE (RÉTABLIE) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:#c62828; font-weight:bold;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Type")}</b> — {r.get("Date")}<br>
                    <div style="font-size:0.9rem; margin-top:5px; border-top:1px solid #eee; padding-top:5px;">
                        {r.get("Note","")}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️", key=f"ef_{i}"): 
                st.session_state.edit_frais_idx = i; st.rerun()
            if c2.button("🗑️", key=f"df_{i}"): 
                df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- RESTE DU CODE (PLANNING & FORM) ---
# [...]














































































































































































