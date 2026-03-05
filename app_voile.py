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
    .header-container { text-align: center; margin-bottom: 10px; padding: 5px; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e1e8ed; }
    .main-title { color: #1a2a6c; font-size: 1.2rem; font-weight: bold; text-transform: uppercase; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; font-size: 0.9rem; }
    div.stButton > button { border-radius: 8px; height: 50px; font-size: 0.7rem !important; font-weight: bold; }
    
    .client-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .frais-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 10px solid #1a2a6c; }
    
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .cal-table th { background: #f8f9fa; font-size: 0.7rem; padding: 8px; border: 1px solid #eee; }
    .cal-table td { border: 1px solid #eee; height: 50px; text-align: center; font-size: 1rem; font-weight: bold; }
    
    .day-detail { padding: 10px; border-radius: 8px; margin-bottom: 8px; background: #ffffff; border: 1px solid #eee; border-left: 10px solid #ccc; font-size: 0.9rem; }
    .contact-link { color: #1a2a6c; text-decoration: none; font-weight: bold; }
    .recap-box { background: #f1f2f6; padding: 15px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 15px; text-align: center; }
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
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "auth" not in st.session_state: st.session_state.auth = False
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "cal_month" not in st.session_state: st.session_state.cal_month = datetime.now().month
if "cal_year" not in st.session_state: st.session_state.cal_year = datetime.now().year
st.session_state.confirm_del = st.session_state.get("confirm_del", None)
st.session_state.edit_idx = st.session_state.get("edit_idx", None)

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER PRO</div></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    if st.button("📋 LISTE"): st.session_state.page = "LISTE"; st.rerun()
with m2: 
    if st.button("🗓️ PLAN"): st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰 STATS"): st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧 MAINT"): st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 LISTE DES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view_mode = "FUTUR"; st.rerun()
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"; st.rerun()
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    if not df.empty:
        df['dt_obj'] = df['DateNav'].apply(parse_date)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt_obj'] >= now].sort_values('dt_obj') if st.session_state.view_mode == "FUTUR" else df[df['dt_obj'] < now].sort_values('dt_obj', ascending=False)
        
        for i, r in data.iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Email', '')).strip()
            st_txt = str(r.get('Statut', '🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold;">{r.get("PrixJour","0")}€</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b> ({r.get("Société","")})<br>
                    📅 {r.get("DateNav","")} | ⏱️ {r.get("NbJours","1")}j<br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel if tel else "Non renseigné"}</a><br>
                    ✉️ <a href="mailto:{mail}" class="contact-link">{mail if mail else "Non renseigné"}</a><br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            
            cx, cy = st.columns(2)
            if cx.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if cy.button("🗑️ Supprimer", key=f"del_{i}"): df = df.drop(i); sauvegarder_data(df); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    # Navigation mois/année
    c_prev, c_mon, c_next = st.columns([1,2,1])
    if c_prev.button("◀️"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
        st.rerun()
    c_mon.markdown(f"<center><b>{st.session_state.cal_month:02d} / {st.session_state.cal_year}</b></center>", unsafe_allow_html=True)
    if c_next.button("▶️"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
        st.rerun()

    # Remplissage calendrier
    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d_start = parse_date(r.get('DateNav', ''))
            for j in range(to_int(r.get('NbJours', 1))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.month == st.session_state.cal_month and d_curr.year == st.session_state.cal_year:
                    ds = d_curr.strftime('%d/%m/%Y')
                    if ds not in occu: occu[ds] = []
                    occu[ds].append(r)

    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        h_c += '<tr>'
        for day in week:
            if day == 0: h_c += '<td></td>'
            else:
                ds = f"{day:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                bg = "#2ecc71" if ds in occu else "white"
                h_c += f'<td style="background:{bg};">{day}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)

    # Détails
    if occu:
        for d_key in sorted(occu.keys()):
            for res in occu[d_key]:
                tel = str(res.get('Téléphone', '')).strip()
                st.markdown(f'''
                    <div class="day-detail">
                        <b>{d_key}</b> : {res.get("Prénom","")} {res.get("Nom","")} 
                        (📞 <a href="tel:{tel}">{tel}</a>)
                    </div>''', unsafe_allow_html=True)

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    with st.form("f_nav"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Refusé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom", ""))
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("Société", init.get("Société", ""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone", ""))
        f_eml = st.text_input("Email", init.get("Email", ""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.number_input("Nombre de jours", min_value=1, value=to_int(init.get("NbJours", 1)))
        f_pri = st.text_input("Prix Total", init.get("PrixJour", "0"))
        if st.form_submit_button("💾 SAUVEGARDER"):
            row = {"Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Téléphone": f_tel, "Email": f_eml, 
                   "DateNav": f_dat, "NbJours": str(f_nbj), "PrixJour": f_pri, "Statut": f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    # Logique simplifiée pour les stats
    st.write("Calcul du CA en cours...")
    # (Code stats ici...)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    # (Code maintenance ici...)










































































































































































