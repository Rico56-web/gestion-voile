import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# --- CSS ADAPTATIF ET COMPATIBILITÉ IPAD/IPHONE ---
st.markdown("""
    <style>
    /* Forcer le contraste pour le mode sombre (iPad/iPhone) */
    .client-card {
        background-color: #ffffff !important; 
        color: #1a1a1a !important; 
        padding: 12px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #ddd; border-left: 8px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .client-card b, .client-card div, .client-card span { color: #1a1a1a !important; }
    
    /* Couleurs de bordure selon statut */
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    
    .price-tag { float: right; font-weight: bold; color: #1e3799 !important; font-size: 1.1rem; }
    .info-sub { font-size: 0.85rem; color: #444 !important; line-height: 1.4; margin-top: 4px; }
    .societe-tag { color: #e67e22 !important; font-weight: bold; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 2px; }

    /* Ajustements Mobile vs PC */
    @media only screen and (max-width: 768px) {
        html, body, [class*="css"] { font-size: 0.9rem; }
        .stButton > button { height: 42px !important; font-size: 0.85rem !important; }
        .block-container { padding-top: 1rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=30)
def charger_data():
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/contacts.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_d = df.to_json(orient="records", indent=4, force_ascii=False)
        content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
        data = {"message": "Maj Vesta", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: 
        st.error("Erreur lors de la sauvegarde sur GitHub")
        return False

# --- UTILS ---
def clean_val(val):
    """Supprime les 'None' et les espaces inutiles"""
    if val is None or str(val).lower() == "none" or str(val).strip() == "":
        return ""
    return str(val).strip()

def format_tel(tel):
    v = clean_val(tel)
    if not v: return ""
    nums = re.sub(r'\D', '', v)
    return " ".join(nums[i:i+2] for i in range(0, len(nums), 2))

def parse_date(d):
    try: 
        s = clean_val(d).replace(" ", "").replace("-", "/")
        return datetime.strptime(s, '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_int(v):
    try: return int(float(str(v))) if v and clean_val(v) != "" else 1
    except: return 1

# --- GESTION DE LA SESSION ---
if "auth" not in st.session_state: st.session_state.auth = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "sel_date" not in st.session_state: st.session_state.sel_date = None
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

# --- AUTHENTIFICATION ---
if not st.session_state.auth:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENU PRINCIPAL ---
m1, m2, m3 = st.columns(3)
if m1.button("📋 LISTE", use_container_width=True): 
    st.session_state.page = "LISTE"; st.session_state.sel_date = None; st.rerun()
if m2.button("🗓️ PLAN", use_container_width=True): 
    st.session_state.page = "PLAN"; st.rerun()
if m3.button("➕ NOUVEAU", use_container_width=True): 
    st.session_state.page = "FORM"; st.session_state.edit_idx = None; st.rerun()
st.markdown("---")

# Chargement des données
df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- LOGIQUE DES PAGES ---

# 1. PAGE LISTE
if st.session_state.page == "LISTE":
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def render_fiches(data_f):
        if data_f.empty:
            st.write("Aucun dossier trouvé.")
            return
        for idx, r in data_f.iterrows():
            st_str = str(r['Statut'])
            cl = "status-ok" if "🟢" in st_str else "status-attente" if "🟡" in st_str else "status-non"
            
            v_soc = clean_val(r['Société'])
            v_tel = format_tel(r['Téléphone'])
            v_mail = clean_val(r['Email'])
            
            soc_html = f"<div class='societe-tag'>🏢 {v_soc}</div>" if v_soc else ""
            tel_html = f"📞 {v_tel}<br>" if v_tel else ""
            mail_html = f"✉️ {v_mail}" if v_mail else ""
            
            st.markdown(f"""
            <div class="client-card {cl}">
                <div class="price-tag">{r['PrixJour']}€</div>
                <b>{clean_val(r['Prénom'])} {clean_val(r['Nom'])}</b>
                {soc_html}
                <div class="info-sub">
                    📅 {r['DateNav']} ({r['NbJours']}j) • 👤 {r['Passagers']}p<br>
                    {tel_html}{mail_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Modifier {r['Nom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    with tab1: render_fiches(df[df['dt'] >= auj].sort_values('dt'))
    with tab2: render_fiches(df[df['dt'] < auj].sort_values('dt', ascending=False).head(20))

# 2. PAGE FORMULAIRE
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_v}
    
    st.subheader("📝 Fiche Navigation")
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(clean_val(init.get("Statut", "🟡 Attente"))))
        
        col_n, col_p = st.columns(2)
        f_nom = col_n.text_input("NOM", value=clean_val(init.get("Nom", "")))
        f_pre = col_p.text_input("Prénom", value=clean_val(init.get("Prénom", "")))
        
        f_soc = st.text_input("SOCIÉTÉ", value=clean_val(init.get("Société", "")))
        f_tel = st.text_input("Téléphone", value=clean_val(init.get("Téléphone", "")))
        f_mail = st.text_input("Email", value=clean_val(init.get("Email", "")))
        
        st.markdown("---")
        c1, c2, c3 = st.columns([2,1,1])
        f_date = c1.text_input("Date (JJ/MM/AAAA)", value=clean_val(init.get("DateNav", "")))
        f_nbj = c2.number_input("Jours", value=to_int(init.get("NbJours", 1)), min_value=1)
        f_pass = c3.number_input("Pers.", value=to_int(init.get("Passagers", 1)), min_value=1)
        
        f_prix = st.text_input("Prix Total €", value=clean_val(init.get("PrixJour", "0")))
        f_his = st.text_area("Notes / Historique", value=clean_val(init.get("Historique", "")))
        
        if st.form_submit_button("💾 ENREGISTRER"):
            new_data = {
                "DateNav": f_date.strip(), "NbJours": str(f_nbj), 
                "Nom": f_nom.upper(), "




































































