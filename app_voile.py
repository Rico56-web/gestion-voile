import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS FINAL OPTIMISÉ ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 15px; font-size: 1.2rem; font-weight: bold; }
    
    /* Boutons Menu Principal */
    div.stButton > button {
        border-radius: 10px; height: 50px;
        border: 1px solid #dcdde1; background-color: white;
        color: #2f3640; font-weight: bold; font-size: 0.8rem;
    }
    
    div.stButton > button:focus, div.stButton > button:active {
        color: white !important;
    }

    /* Tableaux Stats & Planning */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-top: 10px; }
    .cal-table th { font-size: 0.7rem; padding: 8px 0; background: #f8f9fa; border: 1px solid #eee; color: #7f8c8d; text-align: center; }
    .cal-table td { border: 1px solid #eee; height: 40px; text-align: center; font-size: 0.8rem; font-weight: bold; vertical-align: middle; }
    
    /* Cartes Clients */
    .client-card {
        background-color: #ffffff; padding: 12px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #e1e8ed; border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; border: 1px solid #3498db; }
    
    .btn-marine button { background-color: #1a2a6c !important; color: white !important; border: none !important; }
    .section-header { background: #34495e; padding: 6px; border-radius: 6px; margin-bottom: 8px; color: white; font-weight: bold; text-align: center; font-size: 0.85rem; }
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
    try: return int(float(str(v)))
    except: return 0
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

# --- MENU PRINCIPAL ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)

with m1:
    if st.button("📋\nLISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if st.session_state.page == "LISTE": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(1) button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)

with m2:
    if st.button("🗓️\nPLANNING", use_container_width=True): st.session_state.page = "PLANNING"; st.rerun()
    if st.session_state.page == "PLANNING": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(2) button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)

with m3:
    if st.button("💰\nSTATS", use_container_width=True): st.session_state.page = "BUDGET"; st.rerun()
    if st.session_state.page == "BUDGET": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(3) button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)

with m4:
    if st.button("🔧\nFRAIS", use_container_width=True): st.session_state.page = "FRAIS"; st.rerun()
    if st.session_state.page == "FRAIS": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(4) button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)

st.markdown("---")

# --- PAGES ---

if st.session_state.page == "BUDGET":
    y_b = st.selectbox("Sélectionner l'Année", [2026, 2027, 2028])
    df['dt'] = df['DateNav'].apply(parse_date)
    # On ne compte que les sorties validées (🟢 OK)
    df_y = df[(df['dt'].dt.year == y_b) & (df['Statut'].str.contains("🟢"))]
    
    total_ca = sum(df_y["PrixJour"].apply(to_float))
    total_nm = sum(df_y["Milles"].apply(to_float))
    
    st.metric("Total CA Annuel", f"{total_ca:,.0f} €")
    
    # Construction du tableau avec structure fixe
    ht = '<table class="cal-table"><thead><tr><th>Mois</th><th>Jours</th><th>NM</th><th>CA €</th></tr></thead><tbody>'
    
    mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    for i, m in enumerate(mois_noms, 1):
        df_m = df_y[df_y['dt'].dt.month == i]
        if not df_m.empty:
            j_m = sum(df_m["NbJours"].apply(to_int))
            nm_m = sum(df_m["Milles"].apply(to_float))
            ca_m = sum(df_m["PrixJour"].apply(to_float))
            ht += f'<tr><td>{m}</td><td>{j_m}</td><td>{nm_m:,.0f}</td><td>{ca_m:,.0f}</td></tr>'
            
    ht += '</tbody></table>'
    st.markdown(ht, unsafe_allow_html=True)

elif st.session_state.page == "LISTE":
    # ... (Logique Liste identique au code précédent) ...
    c_fut, c_arc = st.columns(2)
    with c_fut:
        if st.button("🚀 PROCHAINES", use_container_width=True): st.session_state.view_mode = "FUTUR"; st.rerun()
        if st.session_state.view_mode == "FUTUR": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(1) > div > div > button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)
    with c_arc:
        if st.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"; st.rerun()
        if st.session_state.view_mode == "ARCHIVES": st.markdown('<style>div[data-testid="stColumn"]:nth-of-type(2) > div > div > button { background-color: #e74c3c !important; color: white !important; }</style>', unsafe_allow_html=True)
    
    search = st.text_input("🔍 Rechercher...", value="").upper()
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_f = df[df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)].copy()

    data = df_f[df_f['dt_obj'] >= auj].sort_values('dt_obj', ascending=True) if st.session_state.view_mode == "FUTUR" else df_f[df_f['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
    st.markdown(f'<div class="section-header">{"🚀 PROCHAINES" if st.session_state.view_mode == "FUTUR" else "📂 ARCHIVES"}</div>', unsafe_allow_html=True)

    for i, r in data.iterrows():
        cl = "cmn-style" if "CMN" in str(r['Société']).upper() else ("status-ok" if "🟢" in str(r['Statut']) else "status-attente")
        st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div><b>{r["Prénom"]} {r["Nom"]}</b><br><span style="color:#d35400; font-weight:bold; font-size:0.8rem;">🏢 {r["Société"]}</span><div class="contact-bar"><a href="tel:{r["Téléphone"]}">📞 Appeler</a> <a href="mailto:{r["Email"]}">✉️ Mail</a></div><small>📅 {r["DateNav"]} | {r["Milles"]} NM</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="btn-marine">', unsafe_allow_html=True)
        if st.button(f"✏️ Gérer {r['Prénom']}", key=f"btn_{i}", use_container_width=True):
            st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ... (Planning, Form, Frais identiques) ...
elif st.session_state.page == "PLANNING":
    c1, c2 = st.columns(2)
    y_p, m_p = c1.selectbox("Année", [2026, 2027, 2028]), c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        if d_o.year == y_p:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
    cal = calendar.monthcalendar(y_p, m_p)
    h_c = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td style="background:#f9f9f9;"></td>'
            else:
                ds = f"{d:02d}/{m_p:02d}/{y_p}"
                dat = occu.get(ds, [])
                bg, color = "white", "black"
                if dat:
                    if any("CMN" in str(x['Société']).upper() for x in dat): bg, color = "#3498db", "white"
                    elif any("🟢" in str(x['Statut']) for x in dat): bg, color = "#2ecc71", "white"
                    else: bg, color = "#f1c40f", "black"
                h_c += f'<td style="background:{bg}; color:{color};">{d}</td>'
        h_c += '</tr>'


























































































































