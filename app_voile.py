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
if "del_idx" not in st.session_state: st.session_state.del_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None
if "del_f_idx" not in st.session_state: st.session_state.del_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
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

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- NAVIGATION PRIORITAIRE (FORMULAIRE) ---
if st.session_state.page == "FORM":
    st.markdown('<div class="page-title">✍️ MODIFIER NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    
    with st.form("nav_form"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom",""))
        f_pre = st.text_input("Prénom", init.get("Prénom",""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone",""))
        f_eml = st.text_input("Email", init.get("Email",""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.text_input("Nombre de jours", init.get("NbJours", "1"))
        f_pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        
        c_save, c_back = st.columns(2)
        if c_save.form_submit_button("💾 SAUVEGARDER"):
            row = {"Nom":f_nom, "Prénom":f_pre, "Téléphone":f_tel, "Email":f_eml, "DateNav":f_dat, "NbJours":f_nbj, "PrixJour":f_pri, "Statut":f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df)
            st.session_state.page = "LISTE"
            st.rerun()
            
    if st.button("⬅️ Retour sans enregistrer"):
        st.session_state.page = "LISTE"
        st.rerun()
    st.stop() # Arrête le script ici pour ne pas afficher le menu

# --- MENU PRINCIPAL (S'affiche pour toutes les autres pages) ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True): st.session_state.view_mode = "FUTURES"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"
        st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        
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
            
            c_ed, c_dl = st.columns(2)
            if c_ed.button("✏️ Modifier", key=f"btn_ed_{i}"):
                st.session_state.edit_idx = i
                st.session_state.page = "FORM"
                st.rerun()
                
            if st.session_state.del_idx == i:
                st.warning("Confirmer suppression ?")
                cy, cn = st.columns(2)
                if cy.button("✅ OUI", key=f"y_{i}"):
                    df.drop(i).pipe(sauvegarder_data); st.session_state.del_idx = None; st.rerun()
                if cn.button("❌ NON", key=f"n_{i}"):
                    st.session_state.del_idx = None; st.rerun()
            else:
                if c_dl.button("🗑️ Supprimer", key=f"btn_dl_{i}"):
                    st.session_state.del_idx = i; st.rerun()

elif st.session_state.page == "FRAIS":
    # (Logique Maintenance avec bouton Modifier et Suppression avec confirmation)
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    # [...] (Le reste du code reste identique)



















































































































































































