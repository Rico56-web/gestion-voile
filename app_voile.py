import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# CSS pour iPhone
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
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
    except Exception as e:
        st.error(f"Erreur chargement : {e}")
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
        data = {"message": "Update", "content": content_b64, "sha": sha} if sha else {"message": "Update", "content": content_b64}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erreur sauvegarde : {e}")

# --- OUTILS ---
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace(" ", ""), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_int(v):
    try: return int(float(str(v)))
    except: return 1

# --- LOGIQUE APP ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
else:
    df = charger_data()
    # S'assurer que les colonnes existent
    for c in ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "PrixJour", "Passagers"]:
        if c not in df.columns: df[c] = ""

    # Menu
    c1, c2, c3 = st.columns(3)
    if c1.button("📋 LISTE"): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("🗓️ PLAN"): st.session_state.page = "PLAN"; st.rerun()
    if c3.button("➕ NEW"): st.session_state.page = "FORM"; st.session_state.edit_idx = None; st.rerun()
    st.markdown("---")

    # --- LISTE ---
    if st.session_state.page == "LISTE":
        df['dt'] = df['DateNav'].apply(parse_date)
        auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        with tab1:
            for idx, r in df[df['dt'] >= auj].sort_values('dt').iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                st.markdown(f'<div class="client-card {cl}"><b>{r["Prénom"]} {r["Nom"]}</b><br>{r["DateNav"]} ({r["NbJours"]}j)<br>{r["Email"]}</div>', unsafe_allow_html=True)
                if st.button(f"Modifier {r['Nom']}", key=f"ed_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
        with tab2:
            for idx, r in df[df['dt'] < auj].sort_values('dt', ascending=False).iterrows():
                st.markdown(f'**{r["DateNav"]}** - {r["Prénom"]} {r["Nom"]}')
                if st.button(f"Voir {idx}", key=f"arch_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.edit_idx
        init = df.loc[idx].to_dict() if idx is not None else {}
        
        with st.form("f"):
            st.subheader("📝 Fiche")
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_mail = st.text_input("Email", value=init.get("Email", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = st.number_input("Jours", value=to_int(init.get("NbJours", 1)))
            f_pass = st.number_input("Passagers", value=to_int(init.get("Passagers", 1)))
            
            if st.form_submit_button("SAUVEGARDER"):
                new = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Statut": f_stat, "Email": f_mail, "Passagers": str(f_pass)}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df)
                st.session_state.page = "LISTE"; st.rerun()

    # --- PLANNING ---
    elif st.session_state.page == "PLAN":
        m_fr = ["Jan", "Fev", "Mar", "Avr", "Mai", "Juin", "Juil", "Aou", "Sep", "Oct", "Nov", "Dec"]
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
        c2.write(f"### {m_fr[st.session_state.m_idx-1]} 2026")
        if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

        occu = {}
        for _, r in df.iterrows():
            d_obj = parse_date(r['DateNav'])
            if d_obj.year == 2026:
                for j in range(to_int(r.get('NbJours', 1))):
                    d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                    if d_c not in occu: occu[d_c] = []
                    occu[d_c].append(r)

        cal = calendar.monthcalendar(2026, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                    btn = "🟢" if d_s in occu and any("🟢" in str(x['Statut']) for x in occu[d_s]) else "🟡" if d_s in occu else str(day)
                    if cols[i].button(btn, key=d_s):
                        if d_s in occu:
                            for x in occu[d_s]: st.info(f"{x['Statut']} {x['Nom']}")






















































