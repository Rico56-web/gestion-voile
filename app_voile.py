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
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; }
    .cal-table td { height: 50px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-busy { background-color: #2ecc71 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=1)
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
if "cal_y" not in st.session_state: st.session_state.cal_y = 2026
if "cal_m" not in st.session_state: st.session_state.cal_m = 3
if "edit_frais_idx" not in st.session_state: st.session_state.edit_frais_idx = None

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

# --- PAGE STATS (LIGNE UNIQUE) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN FINANCIER</div>', unsafe_allow_html=True)
    cy, cm = st.columns(2)
    sel_y = cy.selectbox("Année", [2024, 2025, 2026, 2027, 2028], index=2)
    sel_m = cm.selectbox("Mois", range(1, 13), index=2)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask = (df['dt'].dt.year == sel_y) & (df['dt'].dt.month == sel_m)
        ca = sum(df[mask & df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f))
        fr = 0
        if not df_f.empty:
            df_f['dt'] = df_f['Date'].apply(parse_d)
            fr = sum(df_f[(df_f['dt'].dt.year == sel_y) & (df_f['dt'].dt.month == sel_m)]['Montant'].apply(to_f))
        
        st.markdown(f'<div class="recap-line">CA: {fmt_p(ca)} | Frais: {fmt_p(fr)} | NET: {fmt_p(ca-fr)}</div>', unsafe_allow_html=True)
        st.table(df[mask][['DateNav', 'Nom', 'PrixJour']])

# --- PAGE PLANNING (FIX NAVIGATION) ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    st.session_state.cal_y = c1.selectbox("Année", [2026, 2027, 2028], index=[2026, 2027, 2028].index(st.session_state.cal_y))
    st.session_state.cal_m = c2.selectbox("Mois", range(1, 13), index=st.session_state.cal_m-1)

    occu = {}
    if not df.empty:
        for i, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            if d_start.year == st.session_state.cal_y and d_start.month == st.session_state.cal_m:
                occu[d_start.day] = (i, r)

    cal = calendar.monthcalendar(st.session_state.cal_y, st.session_state.cal_m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0: html += '<td></td>'
            else:
                bg = 'class="day-busy"' if day in occu else ''
                html += f'<td {bg}>{day}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    
    for day, (idx, r) in sorted(occu.items()):
        if st.button(f"Le {day:02d} : {r.get('Nom')} (Modifier)", key=f"p_{day}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.session_state.page = "FORM"
            st.rerun()

# --- PAGE MAINTENANCE (FIX MODIFIER & DETAILS) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & TRAVAUX</div>', unsafe_allow_html=True)
    
    # Formulaire de modification ou ajout
    idx_edit = st.session_state.edit_frais_idx
    with st.expander("➕ ENREGISTRER / MODIFIER UN FRAIS", expanded=(idx_edit is not None)):
        init = df_f.loc[idx_edit].to_dict() if idx_edit is not None else {}
        with st.form("form_f"):
            f_d = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_t = st.selectbox("Type", ["Moteur", "Voiles", "Elec", "Divers"], index=0)
            f_m = st.text_input("Montant (€)", init.get("Montant", ""))
            f_n = st.text_area("Détails des travaux", init.get("Note", ""))
            if st.form_submit_button("VALIDER"):
                new_row = {"Date": f_d, "Type": f_t, "Montant": f_m, "Note": f_n}
                if idx_edit is not None: df_f.loc[idx_edit] = new_row
                else: df_f = pd.concat([df_f, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_frais_idx = None
                st.rerun()
        if idx_edit is not None:
            if st.button("Annuler modification"):
                st.session_state.edit_frais_idx = None
                st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; font-weight:bold;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Type")}</b> ({r.get("Date")})<br>
                    <div style="background:#f9f9f9; padding:8px; margin-top:5px; font-size:0.9rem;">{r.get("Note","")}</div>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"ef_{i}"):
                st.session_state.edit_frais_idx = i
                st.rerun()
            if c2.button("🗑️ Supprimer", key=f"df_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json")
                st.rerun()

# --- PAGE FORMULAIRE NAVIGATION ---
elif st.session_state.page == "FORM":
    idx = st.session_state.get("edit_idx")
    init = df.loc[idx].to_dict() if idx is not None else {}
    st.markdown('<div class="page-title">FICHE NAVIGATION</div>', unsafe_allow_html=True)
    with st.form("nav_form"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom",""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_pri = st.text_input("Prix (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom":f_nom, "DateNav":f_dat, "PrixJour":f_pri, "Statut":f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df)
            st.session_state.page = "LISTE"
            st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()

# --- PAGE LISTE ---
elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 LISTE</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"; st.rerun()
    for i, r in df.iterrows():
        st.markdown(f'<div class="client-card"><b>{r.get("Nom")}</b> - {r.get("DateNav")} ({r.get("Statut")})</div>', unsafe_allow_html=True)
        if st.button("Modifier", key=f"l_{i}"):
            st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()















































































































































































