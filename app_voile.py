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

# --- STYLE CSS (SÉCURISÉ) ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.2rem; color: #1a2a6c; margin-bottom: 20px; }
    .contact-link { color: #1a2a6c !important; text-decoration: underline !important; font-weight: bold; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; font-size: 0.8rem; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
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

# --- DONNÉES ---
df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu_items = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu_items):
    # Le bouton sélectionné est mis en "primary" (couleur de ton thème)
    if c_m[i].button(label, key=f"menu_{pg}", use_container_width=True, type="primary" if st.session_state.page == pg else "secondary"): 
        st.session_state.page = pg; st.rerun()
st.markdown("---")

# --- 1. LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # SÉLECTEUR DE VUE (SANS CSS AGRESSIF)
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

# --- 2. STATS (FORMAT MÉMORISÉ) ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES FINANCIÈRES</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    sel_y = col1.selectbox("Année", [2025, 2026], index=1)
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

# --- 3. MAINTENANCE ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.button("➕ AJOUTER UN FRAIS", key="new_frais", use_container_width=True):
        st.session_state.edit_f_idx = "NEW"; st.rerun()

    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {}
        with st.form("f_form_safe"):
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

# --- 4. PLANNING & FORMULAIRE (IDENTIQUES) ---
# [Le reste du code PLANNING et FORM suit la même logique simplifiée]






























































































































































































