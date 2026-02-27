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

# CSS PERSONNALISÉ (COULEURS ET TAILLES)
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    
    /* Couleurs spécifiques demandées */
    div.stButton > button:first-child[style*="background-color"] { border: none; }
    
    /* Bouton + NOUVEAU en Vert */
    .btn-vert > div[data-testid="stButton"] > button {
        background-color: #27ae60 !important;
        color: white !important;
        border: none !important;
    }
    
    /* Bouton PLANNING en Bleu */
    .btn-bleu > div[data-testid="stButton"] > button {
        background-color: #2980b9 !important;
        color: white !important;
        border: none !important;
    }

    /* Cartes clients améliorées */
    .client-card {
        background-color: #ffffff !important; 
        color: #1a1a1a !important; 
        padding: 15px; border-radius: 12px; 
        margin-bottom: 5px; border: 1px solid #eee; border-left: 10px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    
    .price-tag { float: right; font-weight: bold; color: #2c3e50 !important; font-size: 1.1rem; background: #f1f2f6; padding: 2px 8px; border-radius: 5px; }
    .societe-tag { color: #d35400 !important; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; }
    
    /* Bouton modifier miniature */
    .btn-edit > div[data-testid="stButton"] > button {
        height: 25px !important;
        font-size: 0.7rem !important;
        color: #95a5a6 !important;
        border: 1px solid #ecf0f1 !important;
        margin-top: -10px;
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
        data = {"message": "Update UI", "content": content_b64, "sha": sha}
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
for k in ["auth", "page", "m_idx", "sel_date", "edit_idx"]:
    if k not in st.session_state:
        if k == "auth": st.session_state[k] = False
        elif k == "page": st.session_state[k] = "LISTE"
        elif k == "m_idx": st.session_state[k] = datetime.now().month
        else: st.session_state[k] = None

# --- AUTH ---
if not st.session_state.auth:
    st.title("⚓ Vesta")
    pwd = st.text_input("Code", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENU PRINCIPAL ---
col_m1, col_m2 = st.columns(2)
with col_m1:
    if st.button("📋 LISTE CLIENTS", use_container_width=True): 
        st.session_state.page = "LISTE"; st.rerun()
with col_m2:
    st.markdown('<div class="btn-bleu">', unsafe_allow_html=True)
    if st.button("🗓️ PLANNING", use_container_width=True): 
        st.session_state.page = "PLAN"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    
    with c_add:
        st.markdown('<div class="btn-vert">', unsafe_allow_html=True)
        if st.button("➕ NOUVEAU", use_container_width=True):
            st.session_state.edit_idx = None
            st.session_state.page = "FORM"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if search:
        df = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)]

    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def render(data_f):
        for idx, r in data_f.iterrows():
            st_str = str(r['Statut'])
            cl = "status-ok" if "🟢" in st_str else "status-attente" if "🟡" in st_str else "status-non"
            v_soc, v_tel, v_mail = clean_val(r['Société']), format_tel(r['Téléphone']), clean_val(r['Email'])
            soc_h = f"<div class='societe-tag'>🏢 {v_soc}</div>" if v_soc else ""
            
            st.markdown(f'''
                <div class="client-card {cl}">
                    <div class="price-tag">{r["PrixJour"]}€</div>
                    <b>{clean_val(r["Prénom"])} {clean_val(r["Nom"])}</b>
                    {soc_h}
                    <div style="font-size:0.85rem; color:#555;">
                        📅 {r["DateNav"]} ({r["NbJours"]}j) • 👤 {r["Passagers"]}p<br>
                        {f"📞 {v_tel}" if v_tel else ""} {f"✉️ {v_mail}" if v_mail else ""}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            st.markdown('<div class="btn-edit">', unsafe_allow_html=True)
            if st.button(f"Modifier {r['Nom']}", key=f"ed_{idx}"):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    
    with t1: render(df[df['dt'] >= auj].sort_values('dt'))
    with t2: render(df[df['dt'] < auj].sort_values('dt', ascending=False).head(20))

# --- PAGE FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    if idx is not None and idx < len(df):
        init = df.loc[idx].to_dict()
    else:
        init = {c: "" for c in cols_v}
        init["Statut"] = "🟡 Attente"

    st.subheader("📝 Fiche Client" if idx is None else "✏️ Modifier Client")
    with st.form("f_v"):
        stat_list = ["🟡 Attente", "🟢 OK", "🔴 Pas OK"]
        curr_val = clean_val(init.get("Statut", "🟡 Attente"))
        idx_stat = stat_list.index(curr_val) if curr_val in stat_list else 0
        f_stat = st.selectbox("STATUT", stat_list, index=idx_stat)
        c_n, c_p = st.columns(2)
        f_nom = c_n.text_input("NOM", value=clean_val(init.get("Nom", "")))
        f_pre = c_p.text_input("Prénom", value=clean_val(init.get("Prénom", "")))
        f_soc = st.text_input("SOCIÉTÉ", value=clean_val(init.get("Société", "")))
        f_tel = st.text_input("Tél", value=clean_val(init.get("Téléphone", "")))
        f_mail = st.text_input("Email", value=clean_val(init.get("Email", "")))
        st.markdown("---")
        c1, c2, c3 = st.columns([2,1,1])
        f_date = c1.text_input("Date (JJ/MM/AAAA)", value=clean_val(init.get("DateNav", "")))
        f_nbj = c2.number_input("Jours", value=to_int(init.get("NbJours", 1)), min_value=1)
        f_pass = c3.number_input("Pers.", value=to_int(init.get("Passagers", 1)), min_value=1)
        f_prix = st.text_input("Prix Total €", value=clean_val(init.get("PrixJour", "0")))
        f_his = st.text_area("Notes", value=clean_val(init.get("Historique", "")))
        if st.form_submit_button("💾 ENREGISTRER"):
            new_row = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Société": f_soc.upper(), "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": str(f_pass), "Historique": f_his}
            if idx is not None: df.loc[idx] = new_row
            else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 ANNULER"): st.session_state.page = "LISTE"; st.rerun()

# --- PAGE PLANNING ---
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
        st.markdown(f"**Détails du {st.session_state.sel_date}**")
        if st.session_state.sel_date in occu:
            for x in occu[st.session_state.sel_date]: st.info(f"{x['Statut']} {x['Nom']} {f'({x.get('Société','')})' if x.get('Société','') else ''}")
        if st.button("Fermer"): st.session_state.sel_date = None; st.rerun()










































































