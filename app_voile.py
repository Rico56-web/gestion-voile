import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS (FIXE & MOBILE) ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 20px; font-size: 1.2rem; font-weight: bold; }
    div.stButton > button {
        border-radius: 12px; height: 55px;
        border: 1px solid #dcdde1; background-color: white;
        color: #2f3640; font-weight: bold; font-size: 0.85rem;
    }
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #e1e8ed; border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .contact-bar a { 
        text-decoration: none; color: #2980b9; background: #f1f7fa; 
        padding: 8px 12px; border-radius: 8px; display: inline-block; 
        margin-right: 10px; font-size: 0.9rem; font-weight: bold;
    }
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
    except: return 0
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
ANNEES = [2026, 2027, 2028]
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# Nettoyage colonnes
cols_attendues = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur"]
for c in cols_attendues:
    if c not in df.columns: df[c] = "0" if c in ["Milles", "HeuresMoteur"] else ""

# --- MENU NAVIGATION ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
if m1.button("📋\nListe", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"):
    st.session_state.page = "LISTE"; st.session_state.edit_idx = None; st.rerun()
if m2.button("🗓️\nPlan", use_container_width=True, type="primary" if st.session_state.page == "PLAN" else "secondary"):
    st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰\nStats", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"):
    st.session_state.page = "BUDGET"; st.rerun()
if m4.button("🔧\nFrais", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"):
    st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- LOGIQUE AFFICHAGE ---

# 1. PAGE FORMULAIRE (MODIFICATION)
if st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_attendues}
    
    st.subheader("📝 " + ("Modifier Navigation" if idx is not None else "Nouvelle Navigation"))
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=["🟡 Attente", "🟢 OK", "🔴 Annulé"].index(init.get("Statut", "🟡 Attente")))
        f_nom = st.text_input("NOM", value=init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", value=init.get("Société", "")).upper()
        
        c_a, c_b = st.columns(2)
        f_milles = c_a.number_input("Milles (NM)", value=to_float(init.get("Milles", 0)))
        f_heures = c_b.number_input("Moteur (h)", value=to_float(init.get("HeuresMoteur", 0)))
        
        f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
        f_mail = st.text_input("Email", value=init.get("Email", ""))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
        f_nbj = st.number_input("Nombre de Jours", value=to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix Total (€)", value=init.get("PrixJour", ""))
        
        if st.form_submit_button("💾 ENREGISTRER"):
            row = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Milles": str(f_milles), "HeuresMoteur": str(f_heures)}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df)
            st.session_state.page = "LISTE"; st.session_state.edit_idx = None; st.rerun()
            
    if st.button("🔙 Annuler et Retour"):
        st.session_state.page = "LISTE"; st.session_state.edit_idx = None; st.rerun()

# 2. PAGE LISTE
elif st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    if c_add.button("➕ NEW", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    df_base = df[df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)] if search else df
    
    for idx, r in df_base.sort_values('dt', ascending=False).iterrows():
        cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente"
        st.markdown(f"""
            <div class="client-card {cl}">
                <div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div>
                <div style="font-size:1.1rem;"><b>{r["Prénom"]} {r["Nom"]}</b></div>
                <div style="color:#d35400; font-weight:bold; font-size:0.85rem;">🏢 {r['Société'] if r['Société'] else "Particulier"}</div>
                <div class="contact-bar">
                    <a href="tel:{str(r['Téléphone']).replace(' ','')}">📞 Appeler</a>
                    <a href="mailto:{r['Email']}">✉️ Mail</a>
                </div>
                <div style="font-size:0.8rem; color:#7f8c8d;">
                    📅 {r["DateNav"]} | 🚢 {r.get('Milles', 0)} NM | ⚙️ {r.get('HeuresMoteur', 0)}h
                </div>
            </div>
        """, unsafe_allow_html=True)
        if st.button(f"✏️ Modifier {r['Prénom']}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.session_state.page = "FORM"
            st.rerun()

# 3. AUTRES PAGES (PLAN, BUDGET, FRAIS...)
elif st.session_state.page == "PLAN":
    st.write("### Calendrier de Navigation")
    # (Logique Planning identique précédente...)
    pass
elif st.session_state.page == "BUDGET":
    st.write("### Statistiques & Chiffres")
    # (Logique Budget identique précédente...)
    pass
elif st.session_state.page == "FRAIS":
    st.write("### Gestion des Frais")
    # (Logique Frais identique précédente...)
    pass














































































































