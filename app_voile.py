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
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; }
    .cal-table td { height: 50px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
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
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "del_idx" not in st.session_state: st.session_state.del_idx = None
if "del_f_idx" not in st.session_state: st.session_state.del_f_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

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

# --- PAGE LISTE (EMAIL RÉTABLI) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view_mode = "FUTUR"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTUR" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTUR"))

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, eml = str(r.get('Téléphone','')), str(r.get('Email',''))
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                    📅 <b>{r.get("DateNav","")}</b> — ⏱️ {r.get("NbJours","1")} j<br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel if tel else "Non renseigné"}</a> | ✉️ <a href="mailto:{eml}" class="contact-link">{eml if eml else "Pas de mail"}</a><br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"ed_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if st.session_state.del_idx == i:
                st.warning("Supprimer ?")
                cy, cn = st.columns(2)
                if cy.button("OUI", key=f"cy_{i}"): df.drop(i).pipe(sauvegarder_data); st.session_state.del_idx=None; st.rerun()
                if cn.button("NON", key=f"cn_{i}"): st.session_state.del_idx=None; st.rerun()
            else:
                if c2.button("🗑️ Supprimer", key=f"dl_{i}"): st.session_state.del_idx = i; st.rerun()

# --- PAGE PLANNING (COULEURS PAR STATUT) ---
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
            color_class = "day-ok" if "OK" in st_val.upper() or "🟢" in st_val else "day-wait"
            for j in range(int(float(r.get('NbJours', 1)))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.year == y and d_curr.month == m:
                    occu[d_curr.day] = (i, r, color_class)

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
        btn_col = "#2ecc71" if cl == "day-ok" else "#f1c40f"
        if st.button(f"Le {day:02d} : {r.get('Nom')} ({r.get('Statut')})", key=f"p_{day}_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

# --- PAGE MAINTENANCE (BOUTON MODIFIER RÉTABLI) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    idx_f = st.session_state.edit_f_idx
    with st.expander("➕ AJOUTER / MODIFIER UN FRAIS", expanded=(idx_f is not None)):
        init_f = df_f.loc[idx_f].to_dict() if idx_f is not None else {}
        with st.form("form_f"):
            f_d = st.text_input("Date", init_f.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant (€)", init_f.get("Montant", ""))
            f_n = st.text_area("Note", init_f.get("Note", ""))
            if st.form_submit_button("Sauvegarder"):
                new_row = {"Date":f_d, "Montant":f_m, "Note":f_n, "Type":"Entretien"}
                if idx_f is not None: df_f.loc[idx_f] = new_row
                else: df_f = pd.concat([df_f, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx=None; st.rerun()
        if idx_f is not None and st.button("Annuler modif"): st.session_state.edit_f_idx=None; st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'<div class="frais-card"><div style="float:right; font-weight:bold;">-{fmt_p(r.get("Montant"))}</div><b>{r.get("Date")}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"ef_{i}"): st.session_state.edit_f_idx = i; st.rerun()
            if st.session_state.del_f_idx == i:
                st.warning("Supprimer ?")
                if st.button("OUI", key=f"yf_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.session_state.del_f_idx=None; st.rerun()
                if st.button("NON", key=f"nf_{i}"): st.session_state.del_f_idx=None; st.rerun()
            else:
                if c2.button("🗑️ Supprimer", key=f"df_{i}"): st.session_state.del_f_idx = i; st.rerun()

# --- FORMULAIRE NAVIGATION ---
elif st.session_state.page == "FORM":
    idx = st.session_state.get("edit_idx")
    init = df.loc[idx].to_dict() if idx is not None else {}
    st.markdown('<div class="page-title">FICHE NAVIGATION</div>', unsafe_allow_html=True)
    with st.form("nav_form"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom",""))
        f_pre = st.text_input("Prénom", init.get("Prénom",""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone",""))
        f_eml = st.text_input("Email", init.get("Email",""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.text_input("Nombre de jours", init.get("NbJours", "1"))
        f_pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom":f_nom, "Prénom":f_pre, "Téléphone":f_tel, "Email":f_eml, "DateNav":f_dat, "NbJours":f_nbj, "PrixJour":f_pri, "Statut":f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()

















































































































































































