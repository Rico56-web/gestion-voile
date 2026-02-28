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
    .header-container { text-align: center; margin-bottom: 15px; padding: 8px; background-color: #f8f9fa; border-radius: 12px; border: 1px solid #e1e8ed; }
    .main-title { color: #1a2a6c; margin-bottom: 2px; font-size: 1.3rem; font-weight: bold; text-transform: uppercase; }
    .today-date { color: #e74c3c; font-size: 0.9rem; font-weight: 600; }
    
    .section-confirm { 
        background: #1a2a6c; color: white; padding: 10px; 
        border-radius: 8px; text-align: center; font-weight: bold; 
        margin-bottom: 20px; font-size: 0.9rem; letter-spacing: 1px;
        text-transform: uppercase;
    }
    
    /* Style de base des boutons */
    div.stButton > button { 
        border-radius: 8px; height: 38px; padding: 0px 5px;
        border: 1px solid #dcdde1; background-color: white; 
        color: #2f3640; font-weight: bold; font-size: 0.75rem; 
    }
    
    /* Style pour le bouton ACTIF (Bleu Marine) */
    .stButton button[kind="primary"] {
        background-color: #1a2a6c !important;
        color: white !important;
        border: none !important;
    }

    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-top: 10px; }
    .cal-table th { font-size: 0.65rem; padding: 6px 0; background: #f8f9fa; border: 1px solid #eee; color: #7f8c8d; text-align: center; }
    .cal-table td { border: 1px solid #eee; height: 40px; text-align: center; font-size: 0.8rem; font-weight: bold; vertical-align: middle; }
    
    .client-card { background-color: #ffffff; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #e1e8ed; border-left: 8px solid #ccc; }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; border: 1px solid #3498db; }
    
    .contact-bar a { text-decoration: none; color: white !important; background: #1a2a6c; padding: 8px 12px; border-radius: 8px; display: inline-block; margin-right: 5px; font-size: 0.8rem; font-weight: bold; }
    .btn-marine button { background-color: #1a2a6c !important; color: white !important; border: none !important; height: 45px !important; font-size: 0.85rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=5)
def charger_data(file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_d = df.to_json(orient="records", indent=4, force_ascii=False)
        content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
        data = {"message": f"Update {file}", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def to_int(v):
    try: 
        val = int(float(str(v)))
        return val if val >= 1 else 1
    except: return 1
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")
cols = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur"]
for c in cols:
    if c not in df.columns: df[c] = ""

# --- BANDEAU TITRE ---
st.markdown(f'<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div><div class="today-date">🗓️ {datetime.now().strftime("%d/%m/%Y")}</div></div>', unsafe_allow_html=True)

# --- MENU COMPACT ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    if st.button("📋 LISTE", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"): 
        st.session_state.page = "LISTE"; st.rerun()
with m2:
    if st.button("🗓️ PLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary"): 
        st.session_state.page = "PLANNING"; st.rerun()
with m3:
    if st.button("💰 STATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"): 
        st.session_state.page = "BUDGET"; st.rerun()
with m4:
    if st.button("🔧 FRAIS", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): 
        st.session_state.page = "FRAIS"; st.rerun()

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="section-confirm">📋 LISTE DES FICHES</div>', unsafe_allow_html=True)
    
    # Sous-menu avec coloration dynamique
    c_fut, c_arc = st.columns(2)
    with c_fut:
        if st.button("🚀 PROCHAINES", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTUR" else "secondary"): 
            st.session_state.view_mode = "FUTUR"; st.rerun()
    with c_arc:
        if st.button("📂 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_mode == "ARCHIVES" else "secondary"): 
            st.session_state.view_mode = "ARCHIVES"; st.rerun()
    
    search = st.text_input("🔍 Rechercher...", value="").upper()
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_f = df[df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)].copy()
    data = df_f[df_f['dt_obj'] >= auj].sort_values('dt_obj', ascending=True) if st.session_state.view_mode == "FUTUR" else df_f[df_f['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
    
    for i, r in data.iterrows():
        cl = "cmn-style" if "CMN" in str(r['Société']).upper() else ("status-ok" if "🟢" in str(r['Statut']) else "status-attente")
        st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div><b>{r["Prénom"]} {r["Nom"]}</b><br><span style="color:#d35400; font-weight:bold; font-size:0.8rem;">🏢 {r["Société"]}</span><div class="contact-bar"><a href="tel:{r["Téléphone"]}">📞 Appeler</a> <a href="mailto:{r["Email"]}">✉️ Mail</a></div><small>📅 {r["DateNav"]} | {r["Milles"]} NM</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-marine">', unsafe_allow_html=True)
        if st.button(f"✏️ Gérer {r['Prénom']}", key=f"btn_{i}", use_container_width=True):
            st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ... (Reste du code identique pour PLANNING, BUDGET, FORM, FRAIS) ...
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="section-confirm">🗓️ PLANNING DES SORTIES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    y_p, m_p = c1.selectbox("Année", [2026, 2027, 2028]), c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    # (Logique planning...)
    cal = calendar.monthcalendar(y_p, m_p)
    h_c = '<table class="cal-table"><thead><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr></thead><tbody>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td style="background:#f9f9f9;"></td>'
            else: h_c += f'<td>{d}</td>' # Simplifié pour l'exemple
        h_c += '</tr>'
    st.markdown(h_c + '</tbody></table>', unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="section-confirm">💰 STATISTIQUES ET CHIFFRE D\'AFFAIRES</div>', unsafe_allow_html=True)
    # (Logique budget...)

elif st.session_state.page == "FORM":
    st.markdown('<div class="section-confirm">✏️ FICHE DÉTAILLÉE</div>', unsafe_allow_html=True)
    # (Logique formulaire...)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="section-confirm">🔧 FRAIS ET MAINTENANCE</div>', unsafe_allow_html=True)
    # (Logique frais...)



































































































































