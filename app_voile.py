import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION (TOUJOURS EN PREMIER) ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- 2. INITIALISATION DU SESSION STATE ---
# On s'assure que 'page' existe AVANT de l'utiliser
if "page" not in st.session_state: 
    st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: 
    st.session_state.view_mode = "FUTURES"
if "del_idx" not in st.session_state: 
    st.session_state.del_idx = None
if "del_f_idx" not in st.session_state: 
    st.session_state.del_f_idx = None
if "edit_f_idx" not in st.session_state: 
    st.session_state.edit_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
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

# --- AUTHENTIFICATION ---
if not st.session_state.get("auth"):
    code = st.text_input("Code secret", type="password")
    if code == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

# Chargement des données
df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU PRINCIPAL ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---

# 1. PAGE LISTE
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
        
        # TRI CHRONOLOGIQUE INVERSE (Plus proche en haut)
        if st.session_state.view_mode == "FUTURES":
            data = df[df['dt'] >= now].sort_values('dt', ascending=True)
        else:
            data = df[df['dt'] < now].sort_values('dt', ascending=False)

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
            c_edit, c_del = st.columns(2)
            if c_edit.button("✏️ Modifier", key=f"ed_{i}"):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if c_del.button("🗑️ Supprimer", key=f"dl_{i}"):
                st.session_state.del_idx = i; st.rerun()
            
            if st.session_state.del_idx == i:
                st.warning("Confirmer suppression ?")
                if st.button("✅ OUI", key=f"y_{i}"):
                    df.drop(i).pipe(sauvegarder_data); st.session_state.del_idx = None; st.rerun()
                if st.button("❌ NON", key=f"n_{i}"):
                    st.session_state.del_idx = None; st.rerun()

# 2. PAGE MAINTENANCE
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    idx_f = st.session_state.edit_f_idx
    with st.expander("➕ AJOUTER / MODIFIER", expanded=(idx_f is not None)):
        init = df_f.loc[idx_f].to_dict() if (not df_f.empty and idx_f is not None) else {}
        with st.form("f_form"):
            d = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            m = st.text_input("Montant", init.get("Montant", ""))
            n = st.text_area("Note", init.get("Note", ""))
            if st.form_submit_button("VALIDER"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx_f is not None: df_f.loc[idx_f] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'<div class="frais-card"><div style="float:right;">-{fmt_p(r.get("Montant"))}</div><b>{r.get("Date")}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️", key=f"ef_{i}"): st.session_state.edit_f_idx = i; st.rerun()
            if c2.button("🗑️", key=f"df_{i}"): 
                df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# 3. PAGE BUDGET (STATS)
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    ca = sum(df[df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f)) if not df.empty else 0
    fr = sum(df_f['Montant'].apply(to_f)) if not df_f.empty else 0
    st.markdown(f'<div class="recap-line">NET : {fmt_p(ca-fr)} (Revenus: {fmt_p(ca)} / Frais: {fmt_p(fr)})</div>', unsafe_allow_html=True)
    if not df.empty: st.table(df[['DateNav', 'Nom', 'PrixJour']])

# 4. PAGE FORMULAIRE
elif st.session_state.page == "FORM":
    # (Logique du formulaire de navigation identique aux versions précédentes)
    st.button("Retour", on_click=lambda: st.session_state.update({"page": "LISTE"}))

# 5. PAGE PLANNING
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    # (Logique du calendrier identique)



















































































































































































