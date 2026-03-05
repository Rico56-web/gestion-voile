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
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.2rem; color: #1a2a6c; margin-bottom: 20px; }
    .contact-link { color: #1a2a6c !important; text-decoration: underline !important; font-weight: bold; }
    
    /* STYLE CALENDRIER PLANNING */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; font-size: 0.8rem; text-align: center; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: middle; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
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

# --- MENU PRINCIPAL ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu_items = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu_items):
    if c_m[i].button(label, key=f"m_{pg}", use_container_width=True, type="primary" if st.session_state.page == pg else "secondary"): 
        st.session_state.page = pg; st.rerun()
st.markdown("---")

# --- 1. PAGE LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", key="v_fut", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTURES" else "secondary"):
        st.session_state.view_mode = "FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", key="v_pas", use_container_width=True, type="primary" if st.session_state.view_mode == "PASSÉES" else "secondary"):
        st.session_state.view_mode = "PASSÉES"; st.rerun()

    st.markdown("---")
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = "NEW"; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTURES"))

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col_s = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, eml = str(r.get('Téléphone','')), str(r.get('Email',''))
            st.markdown(f'''
                <div class="client-card" style="border-left: 12px solid {col_s};">
                    <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                    📅 <b>{r.get("DateNav","")}</b> — ⏱️ <b>{r.get("NbJours","1")} jours</b><br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel}</a> | ✉️ <a href="mailto:{eml}" class="contact-link">{eml}</a><br>
                    <span style="color:{col_s}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_nav_{i}"):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

# --- 2. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y = y_col.selectbox("Année", [2025, 2026, 2027], index=1)
    p_m = m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    
    occu = {}
    if not df.empty:
        for i, r in df.iterrows():
            d_s = parse_d(r.get('DateNav',''))
            if d_s.year == p_y and d_s.month == p_m:
                st_v = str(r.get('Statut',''))
                cl = "day-ok" if "OK" in st_v.upper() or "🟢" in st_v else "day-wait"
                try: nb_j = int(float(r.get('NbJours', 1)))
                except: nb_j = 1
                for j in range(nb_j):
                    target = d_s + timedelta(days=j)
                    if target.month == p_m: occu[target.day] = (i, r, cl)

    cal = calendar.monthcalendar(p_y, p_m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for d in week:
            bg = f'class="{occu[d][2]}"' if d in occu else ''
            html += f'<td {bg}>{d if d != 0 else ""}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    
    if occu:
        st.write("### 🔍 Détails du mois")
        for d, (idx, r, cl) in sorted(occu.items()):
            if st.button(f"{d:02d} : {r.get('Nom')} ({r.get('Statut')})", key=f"pl_{d}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

# --- 3. PAGE STATS (FORMAT MÉMORISÉ) ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES FINANCIÈRES</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    sel_y = col1.selectbox("Année", [2025, 2026, 2027], index=1)
    sel_m = col2.selectbox("Mois (0=Année)", range(0, 13), index=datetime.now().month)

    df_view = pd.DataFrame()
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask = (df['dt'].dt.year == sel_y)
        if sel_m > 0: mask &= (df['dt'].dt.month == sel_m)
        df_view = df[mask & df['Statut'].str.contains("OK|🟢", na=False)]

    df_f_view = pd.DataFrame()
    if not df_f.empty:
        df_f['dt'] = df_f['Date'].apply(parse_d)
        mask_f = (df_f['dt'].dt.year == sel_y)
        if sel_m > 0: mask_f &= (df_f['dt'].dt.month == sel_m)
        df_f_view = df_f[mask_f]

    ca = sum(df_view['PrixJour'].apply(to_f)) if not df_view.empty else 0
    fr = sum(df_f_view['Montant'].apply(to_f)) if not df_f_view.empty else 0
    
    st.markdown(f'<div class="recap-line">SOLDE NET : {fmt_p(ca-fr)}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.success(f"📈 REVENUS (+)\n\n**{fmt_p(ca)}**")
    c2.error(f"📉 FRAIS (-)\n\n**{fmt_p(fr)}**")
    if not df_view.empty: st.dataframe(df_view[['DateNav', 'Nom', 'PrixJour']], use_container_width=True)

# --- 4. MAINTENANCE ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.button("➕ AJOUTER UN FRAIS", use_container_width=True):
        st.session_state.edit_f_idx = "NEW"; st.rerun()

    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {}
        with st.form("f_form_fixed"):
            f_d = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant (€)", init.get("Montant", ""))
            f_n = st.text_area("Note", init.get("Note", ""))
            if st.form_submit_button("VALIDER"):
                row = {"Date":f_d, "Montant":f_m, "Note":f_n}
                if idx != "NEW": df_f.loc[idx] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
        if st.button("Annuler"): st.session_state.edit_f_idx = None; st.rerun()

    if not df_f.empty:
        for i in range(len(df_f)-1, -1, -1):
            r = df_f.iloc[i]
            st.markdown(f'''<div class="frais-card"><div style="float:right; color:red; font-weight:bold;">-{fmt_p(r.get("Montant"))}</div><b>{r.get("Date")}</b><br>{r.get("Note")}</div>''', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"mf_{i}"): st.session_state.edit_f_idx = i; st.rerun()
            if st.button("🗑️ Effacer", key=f"df_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- 5. FORMULAIRE ÉDITION ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    st.markdown('<div class="page-title">✍️ ÉDITION FICHE</div>', unsafe_allow_html=True)
    with st.form("form_edit"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom",""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone",""))
        f_eml = st.text_input("Email", init.get("Email",""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav",""))
        f_nbj = st.text_input("Nb Jours", init.get("NbJours","1"))
        f_pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom":f_nom, "Téléphone":f_tel, "Email":f_eml, "DateNav":f_dat, "NbJours":f_nbj, "PrixJour":f_pri, "Statut":f_st}
            if idx != "NEW": df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df, "contacts.json"); st.session_state.page = "LISTE"; st.session_state.edit_idx = None; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.session_state.edit_idx = None; st.rerun()































































































































































































