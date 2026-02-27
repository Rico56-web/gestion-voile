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
        data = {"message": "Update Vesta", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def clean_val(val):
    if val is None or str(val).lower() == "none" or str(val).strip() == "": return ""
    return str(val).strip()

def parse_date(d):
    try: 
        s = clean_val(d).replace(" ", "").replace("-", "/")
        return datetime.strptime(s, '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ","").strip())
    except: return 0.0

# --- SESSION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

# --- AUTH ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Code", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENU ---
m1, m2 = st.columns(2)
if m1.button("📋 LISTE CLIENTS", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLANNING", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
st.markdown("---")

df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    if c_add.button("➕ NOUVEAU", use_container_width=True, type="primary"):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"
        st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    if search:
        df_show = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)]
    else:
        df_show = df

    # Tri : Prochaines navigations en premier
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_futur = df_show[df_show['dt'] >= auj].sort_values('dt')
    
    st.subheader("🚀 Prochaines Navigations")
    for idx, r in df_futur.iterrows():
        with st.expander(f"{r['Statut']} {r['DateNav']} - {r['Nom']} {r['Prénom']}"):
            st.write(f"**Société:** {r['Société']} | **Prix:** {r['PrixJour']}€")
            st.write(f"📞 {r['Téléphone']} | ✉️ {r['Email']}")
            if st.button("Modifier", key=f"ed_{idx}"):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

# --- PAGE FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    if idx is not None: init = df.loc[idx].to_dict()
    else: init = {c: "" for c in cols_v}; init["Statut"] = "🟡 Attente"

    with st.form("f_v"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
        f_nom = st.text_input("NOM", value=init.get("Nom", ""))
        f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
        f_prix = st.text_input("Prix Total (€)", value=init.get("PrixJour", "0"))
        # ... autres champs simplifiés pour le test
        if st.form_submit_button("💾 ENREGISTRER"):
            new_row = {c: init.get(c, "") for c in cols_v}
            new_row.update({"Nom": f_nom.upper(), "Prénom": f_pre, "DateNav": f_date, "PrixJour": f_prix, "Statut": f_stat})
            if idx is not None: df.loc[idx] = new_row
            else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()

# --- PAGE PLANNING ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.subheader(f"{m_fr[st.session_state.m_idx-1]} 2026")
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

    # DASHBOARD FINANCIER
    ca_ok, ca_att = 0.0, 0.0
    for _, r in df.iterrows():
        dt = parse_date(r['DateNav'])
        if dt.month == st.session_state.m_idx and dt.year == 2026:
            p = to_float(r['PrixJour'])
            if "🟢" in str(r['Statut']): ca_ok += p
            elif "🟡" in str(r['Statut']): ca_att += p
    
    st.info(f"💰 **Encaissé : {ca_ok:.0f}€** | ⏳ Attente : {ca_att:.0f}€ | 📊 Total : {ca_ok+ca_att:.0f}€")
    st.write("Détails par jour :")
    # (Calendrier ici...)













































































