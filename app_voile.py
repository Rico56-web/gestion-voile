import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# CSS ADAPTATIF
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff !important; 
        color: #1a1a1a !important; 
        padding: 12px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #ddd; border-left: 8px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .client-card b, .client-card div, .client-card span { color: #1a1a1a !important; }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .price-tag { float: right; font-weight: bold; color: #1e3799 !important; font-size: 1.1rem; }
    .info-sub { font-size: 0.85rem; color: #444 !important; line-height: 1.4; margin-top: 4px; }
    .societe-tag { color: #e67e22 !important; font-weight: bold; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 2px; }
    @media only screen and (max-width: 768px) {
        html, body, [class*="css"] { font-size: 0.9rem; }
        .stButton > button { height: 42px !important; font-size: 0.85rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=30)
def charger_data():
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_d = df.to_json(orient="records", indent=4, force_ascii=False)
        content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
        data = {"message": "Update Vesta", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def clean_val(val):
    if val is None or str(val).lower() == "none" or str(val).strip() == "": return ""
    return str(val).strip()

def format_tel(tel):
    v = clean_val(tel)
    if not v: return ""
    nums = re.sub(r'\D', '', v)
    return " ".join(nums[i:i+2] for i in range(0, len(nums), 2))

def parse_date(d):
    try: 
        s = clean_val(d).replace(" ", "").replace("-", "/")
        return datetime.strptime(s, '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_int(v):
    try: return int(float(str(v))) if v and clean_val(v) != "" else 1
    except: return 1

# --- SESSION ---
for key in ["auth", "page", "m_idx", "sel_date", "edit_idx"]:
    if key not in st.session_state:
        if key == "auth": st.session_state[key] = False
        elif key == "page": st.session_state[key] = "LISTE"
        elif key == "m_idx": st.session_state[key] = datetime.now().month
        else: st.session_state[key] = None

# --- AUTH ---
if not st.session_state.auth:
    st.title("⚓ Vesta")
    pwd = st.text_input("Code", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENU ---
m1, m2, m3 = st.columns(3)
if m1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLAN", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
if m3.button("➕ NEW", use_container_width=True): st.session_state.page = "FORM"; st.session_state.edit_idx = None; st.rerun()
st.markdown("---")

df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- PAGES ---
if st.session_state.page == "LISTE":
    # --- BARRE DE RECHERCHE ---
    search = st.text_input("🔍 Rechercher un Nom ou une Société").upper()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Filtrage selon la recherche
    if search:
        df = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)]

    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    def render(data_f):
        for idx, r in data_f.iterrows():
            st_str = str(r['Statut'])
            cl = "status-ok" if "🟢" in st_str else "status-attente" if "🟡" in st_str else "status-non"
            v_soc, v_tel, v_mail = clean_val(r['Société']), format_tel(r['Téléphone']), clean_val(r['Email'])
            soc_h = f"<div class='societe-tag'>🏢 {v_soc}</div>" if v_soc else ""
            tel_h = f"📞 {v_tel}<br>" if v_tel else ""
            mail_h = f"✉️ {v_mail}" if v_mail else ""
            st.markdown(f'<div class="client-card {cl}"><div class="price-tag">{r["PrixJour"]}€</div><b>{clean_val(r["Prénom"])} {clean_val(r["Nom"])}</b>{soc_h}<div class="info-sub">📅 {r["DateNav"]} ({r["NbJours"]}j) • 👤 {r["Passagers"]}p<br>{tel_h}{mail_h}</div></div>', unsafe_allow_html=True)
            if st.button(f"Modifier {r['Nom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    
    with t1: render(df[df['dt'] >= auj].sort_values('dt'))
    with t2: render(df[df['dt'] < auj].sort_values('dt', ascending=False).head(20))

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_v}
    with st.form("f_v"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(clean_val(init.get("Statut", "🟡 Attente"))))
        c_n, c_p = st.columns(2)
        f_nom, f_pre = c_n.text_input("NOM", value=clean_val(init.get("Nom", ""))), c_p.text_input("Prénom", value=clean_val(init.get("Prénom", "")))
        f_soc = st.text_input("SOCIÉTÉ", value=clean_val(init.get("Société", "")))
        f_tel, f_mail = st.text_input("Tél", value=clean_val(init.get("Téléphone", ""))), st.text_input("Email", value=clean_val(init.get("Email", "")))
        st.markdown("---")
        c1, c2, c3 = st.columns([2,1,1])
        f_date, f_nbj, f_pass = c1.text_input("Date", value=clean_val(init.get("DateNav", ""))), c2.number_input("Jours", value=to_int(init.get("NbJours", 1)), min_value=1), c3.number_input("Pers.", value=to_int(init.get("Passagers", 1)), min_value=1)
        f_prix, f_his = st.text_input("Prix €", value=clean_val(init.get("PrixJour", "0"))), st.text_area("Notes", value=clean_val(init.get("Historique", "")))
        if st.form_submit_button("💾 ENREGISTRER"):
            new = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Société": f_soc.upper(), "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": str(f_pass), "Historique": f_his}
            if idx is not None: df.loc[idx] = new
            else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 RETOUR"): st.session_state.page = "LISTE"; st.rerun()

elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()
    occu = {}
    for _, r in df.iterrows():
        d_obj = parse_date(r['DateNav'])
        if d_obj.year == 2026:
            for j in range(to_int(r.get('NbJours', 1))):
                d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
    cal = calendar.monthcalendar(2026, st.session_state.m_idx)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                label = str(day)
                if d_s in occu:
                    v, j = any("🟢" in str(x['Statut']) for x in occu[d_s]), any("🟡" in str(x['Statut']) for x in occu[d_s])
                    label = "🟢+🟡" if v and j else "🟢" if v else "🟡"
                if cols[i].button(label, key=f"p_{d_s}", use_container_width=True): st.session_state.sel_date = d_s
    if st.session_state.sel_date:
        st.markdown(f"**{st.session_state.sel_date}**")
        if st.session_state.sel_date in occu:
            for x in occu[st.session_state.sel_date]: st.info(f"{x['Statut']} {x['Nom']} {f'({x.get('Société','')})' if x.get('Société','') else ''}")
        if st.button("Fermer"): st.session_state.sel_date = None; st.rerun()






































































