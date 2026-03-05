import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- 2. INITIALISATION ---
for key, val in {"page": "LISTE", "view_mode": "FUTURES", "edit_idx": None, "del_idx": None}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; }
    .cal-table td { height: 60px; text-align: center; border: 1px solid #ddd; font-weight: bold; position: relative; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
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

# --- UTILS (SÉCURISÉS) ---
def to_f(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0

def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")

def parse_d(d):
    try:
        if not d or str(d) == "None": return datetime(2000, 1, 1)
        return datetime.strptime(str(d).replace("-","/").strip(), '%d/%m/%Y')
    except:
        return datetime(2000, 1, 1)

# --- AUTH ---
if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg; st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---

# 1. LISTE (AVEC TRI CHRONO PROCHE)
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True): st.session_state.view_mode = "FUTURES"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        
        if st.session_state.view_mode == "FUTURES":
            data = df[df['dt'] >= now].sort_values('dt', ascending=True)
        else:
            data = df[df['dt'] < now].sort_values('dt', ascending=False)

        if data.empty:
            st.info(f"Aucune navigation dans {st.session_state.view_mode}")
        else:
            for i, r in data.iterrows():
                st_txt = str(r.get('Statut','🟡'))
                col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
                tel, eml = str(r.get('Téléphone','')), str(r.get('Email',''))
                st.markdown(f'''
                    <div class="client-card" style="border-left-color:{col};">
                        <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                        <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                        📅 <b>{r.get("DateNav","")}</b> — ⏱️ {r.get("NbJours","1")} j<br>
                        📞 <a href="tel:{tel}" class="contact-link">{tel}</a> | ✉️ <a href="mailto:{eml}" class="contact-link">{eml}</a><br>
                        <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                    </div>
                ''', unsafe_allow_html=True)
                c_ed, c_dl = st.columns(2)
                if c_ed.button("✏️ Modifier", key=f"ed_{i}"): 
                    st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
                if c_dl.button("🗑️ Supprimer", key=f"dl_{i}"): 
                    st.session_state.del_idx = i; st.rerun()
                
                if st.session_state.del_idx == i:
                    st.warning("Confirmer ?")
                    if st.button("OUI", key=f"y_{i}"): 
                        df.drop(i).pipe(sauvegarder_data); st.session_state.del_idx=None; st.rerun()
                    if st.button("NON", key=f"n_{i}"): st.session_state.del_idx=None; st.rerun()

# 2. PLANNING (COULEURS SYNCHRO)
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    cy, cm = st.columns(2)
    y = cy.selectbox("Année", [2026, 2027, 2028], index=0)
    m = cm.selectbox("Mois", range(1, 13), index=datetime.now().month-1)

    occu = {}
    if not df.empty:
        for i, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            st_val = str(r.get('Statut',''))
            color = "day-ok" if "OK" in st_val.upper() or "🟢" in st_val else "day-wait"
            if d_start.year == y and d_start.month == m:
                for j in range(int(float(r.get('NbJours', 1)))):
                    day = (d_start + timedelta(days=j)).day
                    if (d_start + timedelta(days=j)).month == m:
                        occu[day] = (i, r, color)

    cal = calendar.monthcalendar(y, m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            bg = f'class="{occu[day][2]}"' if day in occu else ''
            html += f'<td {bg}>{day if day != 0 else ""}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    
    for day, (idx, r, cl) in sorted(occu.items()):
        if st.button(f"Le {day:02d} : {r.get('Nom')} ({r.get('Statut')})", key=f"p_{day}_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

# [Les pages BUDGET, MAINTENANCE et FORM restent identiques et fonctionnelles]




















































































































































































