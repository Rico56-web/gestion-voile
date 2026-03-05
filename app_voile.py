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
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; }
    .cal-table td { height: 50px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
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
def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

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
        st.session_state.edit_idx = None
        st.session_state.edit_f_idx = None
        st.rerun()
st.markdown("---")

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True): st.session_state.view_mode = "FUTURES"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = "NEW"; st.rerun()

    if st.session_state.edit_idx is not None:
        # FORMULAIRE DE NAVIGATION
        idx = st.session_state.edit_idx
        init = df.loc[idx].to_dict() if idx != "NEW" else {}
        with st.form("form_nav"):
            f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
            f_nom = st.text_input("Nom", init.get("Nom",""))
            f_tel = st.text_input("Téléphone", init.get("Téléphone",""))
            f_eml = st.text_input("Email", init.get("Email",""))
            f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
            f_nbj = st.text_input("Nombre de jours", init.get("NbJours", "1"))
            f_pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
            if st.form_submit_button("SAUVEGARDER"):
                row = {"Nom":f_nom, "Téléphone":f_tel, "Email":f_eml, "DateNav":f_dat, "NbJours":f_nbj, "PrixJour":f_pri, "Statut":f_st}
                if idx != "NEW": df.loc[idx] = row
                else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
        if st.button("Annuler"): st.session_state.edit_idx = None; st.rerun()
    else:
        # AFFICHAGE DE LA LISTE
        if not df.empty:
            df['dt'] = df['DateNav'].apply(parse_d)
            now = datetime.now().replace(hour=0, minute=0, second=0)
            data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
            data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTURES"))

            for i, r in data.iterrows():
                st_txt = str(r.get('Statut','🟡'))
                col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
                st.markdown(f'''<div class="client-card" style="border-left-color:{col};">
                    <b>{r.get("Nom","").upper()}</b> ({r.get("DateNav")}) - {r.get("NbJours")}j<br>
                    📞 {r.get("Téléphone")} | ✉️ {r.get("Email")}<br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span> — {fmt_p(r.get("PrixJour"))}</div>''', unsafe_allow_html=True)
                if st.button(f"✏️ Modifier {r.get('Nom')}", key=f"ed_{i}"):
                    st.session_state.edit_idx = i; st.rerun()

# --- PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y = st.selectbox("Année", [2025, 2026], index=1)
    m = st.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    
    occu = {}
    if not df.empty:
        for i, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            if d_start.year == y and d_start.month == m:
                color = "day-ok" if "OK" in str(r.get('Statut')).upper() else "day-wait"
                occu[d_start.day] = (r.get('Nom'), color)

    cal = calendar.monthcalendar(y, m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            bg = f'class="{occu[day][1]}"' if day in occu else ''
            txt = f'{day}<br><small>{occu[day][0]}</small>' if day in occu else (day if day != 0 else "")
            html += f'<td {bg}>{txt}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)

# --- PAGE MAINTENANCE (BOUTON MODIFIER RÉTABLI) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    idx_f = st.session_state.edit_f_idx
    with st.expander("📝 SAISIR UN FRAIS", expanded=(idx_f is not None)):
        init_f = df_f.loc[idx_f].to_dict() if (not df_f.empty and idx_f is not None) else {}
        with st.form("form_f"):
            f_d = st.text_input("Date", init_f.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant", init_f.get("Montant", ""))
            f_n = st.text_area("Note", init_f.get("Note", ""))
            if st.form_submit_button("ENREGISTRER"):
                row = {"Date":f_d, "Montant":f_m, "Note":f_n}
                if idx_f is not None: df_f.loc[idx_f] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'<div class="frais-card"><div style="float:right; color:red;">-{fmt_p(r.get("Montant"))}</div><b>{r.get("Date")}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
            if st.button("✏️ Modifier ce frais", key=f"mf_{i}"):
                st.session_state.edit_f_idx = i; st.rerun()

# --- PAGE STATS ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS</div>', unsafe_allow_html=True)
    ca = sum(df[df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f)) if not df.empty else 0
    fr = sum(df_f['Montant'].apply(to_f)) if not df_f.empty else 0
    st.markdown(f'<div class="recap-line">TOTAL NET : {fmt_p(ca-fr)}</div>', unsafe_allow_html=True)
    st.write(f"Revenus : {fmt_p(ca)} | Frais : {fmt_p(fr)}")





















































































































































































