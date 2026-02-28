import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS OPTIMISÉ IPHONE ---
st.markdown("""
    <style>
    .header-container { text-align: center; margin-bottom: 10px; padding: 5px; background-color: #f8f9fa; border-radius: 10px; }
    .main-title { color: #1a2a6c; font-size: 1.2rem; font-weight: bold; }
    .section-confirm { background: #1a2a6c; color: white; padding: 8px; border-radius: 8px; text-align: center; font-size: 0.8rem; margin-bottom: 10px; }
    
    /* Boutons en ligne */
    .stButton button { width: 100%; border-radius: 6px; height: 35px; font-size: 0.75rem !important; }
    
    /* Cartes compactes */
    .client-card { background: white; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 8px solid #ccc; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    /* Calendrier mobile */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 0.7rem; }
    .cal-table td { border: 1px solid #eee; height: 35px; text-align: center; font-weight: bold; }
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
    except: return 1
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
for key, val in {"page": "LISTE", "auth": False, "cal_month": datetime.now().month, "cal_year": datetime.now().year}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

# Chargement sécurisé
df = charger_data("contacts.json")
if df.empty: df = pd.DataFrame(columns=["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur"])

# --- NAVIGATION ---
st.markdown('<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    if st.button("📋"): st.session_state.page = "LISTE"; st.rerun()
with m2: 
    if st.button("🗓️"): st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰"): st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧"): st.session_state.page = "FRAIS"; st.rerun()

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="section-confirm">LISTE DES NAVS</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): 
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    data = df.sort_values('dt_obj', ascending=True)
    
    for i, r in data.iterrows():
        soc = str(r.get('Société', '')).upper()
        cl = "cmn-style" if "CMN" in soc else ("status-ok" if "🟢" in str(r.get('Statut','')) else "status-attente")
        
        st.markdown(f"""
            <div class="client-card {cl}">
                <div style="float:right; font-weight:bold;">{to_float(r.get('PrixJour',0)):.2f}€</div>
                <b>{r.get('Prénom','')} {r.get('Nom','')}</b><br>
                <small>🏢 {soc} | 📅 {r.get('DateNav','')}</small><br>
                <small>⚓ {r.get('Milles',0)} NM | ⏱️ {r.get('HeuresMoteur',0)}h</small>
            </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ Gérer", key=f"ed_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
        with c2:
            if st.button("🗑️ Suppr.", key=f"del_{i}"):
                df = df.drop(i); sauvegarder_data(df); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="section-confirm">PLANNING</div>', unsafe_allow_html=True)
    
    # Navigation
    cp, cm, cn = st.columns([1,2,1])
    if cp.button("◀️"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
        st.rerun()
    cm.markdown(f"<center><b>{st.session_state.cal_month}/{st.session_state.cal_year}</b></center>", unsafe_allow_html=True)
    if cn.button("▶️"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
        st.rerun()

    # Occupation
    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        for j in range(to_int(r.get('NbJours', 1))):
            d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
            if d_c not in occu: occu[d_c] = []
            occu[d_c].append(r)

    # Calendrier
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><tr><th>L</th><th>M</th><th>M</th><th>J</th><th>V</th><th>S</th><th>D</th></tr>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td></td>'
            else:
                ds = f"{d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                bg = "white"
                if ds in occu:
                    bg = "#3498db" if any("CMN" in str(x.get('Société','')).upper() for x in occu[ds]) else "#2ecc71"
                h_c += f'<td style="background:{bg}; color:{"white" if bg!="white" else "black"};">{d}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)

    # Détails au clic
    st.markdown("---")
    jours_nav = sorted([int(k.split('/')[0]) for k in occu.keys() if f"/{st.session_state.cal_month:02d}/{st.session_state.cal_year}" in k])
    if jours_nav:
        sel_d = st.selectbox("Détails du jour :", jours_nav)
        ds_sel = f"{sel_d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
        for res in occu.get(ds_sel, []):
            st.info(f"👤 **{res.get('Prénom','')} {res.get('Nom','')}**\n\n🏢 {res.get('Société','')}\n⏱️ {res.get('HeuresMoteur',0)}h | ⚓ {res.get('Milles',0)} NM")

elif st.session_state.page == "FORM":
    st.markdown('<div class="section-confirm">ÉDITION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    with st.form("edit"):
        f_nom = st.text_input("NOM", init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", init.get("Société", "")).upper()
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.number_input("Nombre de jours", 1, 30, to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix (€)", str(init.get("PrixJour", "0")).replace(",", "."))
        f_milles = st.number_input("Milles", value=to_float(init.get("Milles", 0)))
        f_heures = st.number_input("Heures", value=to_float(init.get("HeuresMoteur", 0)))
        
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "DateNav": f_dat, "NbJours": str(f_nbj), "PrixJour": f_prix, "Milles": str(f_milles), "HeuresMoteur": str(f_heures), "Statut": init.get("Statut", "🟢 OK")}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Annuler"): st.session_state.page = "LISTE"; st.rerun()













































































































































