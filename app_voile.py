import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# CSS optimisé pour la lisibilité iPhone
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff; padding: 12px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #eee; border-left: 10px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .price-tag { float: right; font-weight: bold; color: #2c3e50; font-size: 1.1em; }
    .info-sub { font-size: 0.9em; color: #666; line-height: 1.4; }
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
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df):
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

# --- UTILS ---
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace(" ", ""), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_int(v):
    try: return int(float(str(v)))
    except: return 1

# --- SESSION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "auth" not in st.session_state: st.session_state.auth = False

# --- AUTH ---
if not st.session_state.auth:
    st.title("⚓ Vesta Skipper")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
else:
    df = charger_data()
    # Garantir les colonnes
    cols = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
    for c in cols:
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
        
        def render_list(data):
            for idx, r in data.iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                st.markdown(f"""
                <div class="client-card {cl}">
                    <div class="price-tag">{r['PrixJour']}€</div>
                    <b>{r['Prénom']} {r['Nom']}</b><br>
                    <div class="info-sub">
                        📅 {r['DateNav']} ({r['NbJours']}j) — 👤 {r['Passagers']} pers.<br>
                        📞 {r['Téléphone']}<br>
                        ✉️ {r['Email']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Modifier {r['Nom']}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1: render_list(df[df['dt'] >= auj].sort_values('dt'))
        with tab2: render_list(df[df['dt'] < auj].sort_values('dt', ascending=False).head(15))

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.edit_idx
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        
        with st.form("f_edit"):
            f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c1.text_input("Tel", value=init.get("Téléphone", ""))
            f_mail = c2.text_input("Email", value=init.get("Email", ""))
            
            st.markdown("---")
            c3, c4, c5, c6 = st.columns([2,1,1,1])
            f_date = c3.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = c4.number_input("Jours", value=to_int(init.get("NbJours", 1)))
            f_pass = c5.number_input("Pers.", value=to_int(init.get("Passagers", 1)))
            f_prix = c6.text_input("Prix €", value=init.get("PrixJour", "0"))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("SAUVEGARDER"):
                new = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": str(f_pass), "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df)
                st.session_state.page = "LISTE"; st.rerun()
        if st.button("RETOUR"): st.session_state.page = "LISTE"; st.rerun()

    # --- PLANNING ---
    elif st.session_state.page == "PLAN":
        if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
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
                    label = str(day)
                    if d_s in occu:
                        label = "🟢" if any("🟢" in str(x['Statut']) for x in occu[d_s]) else "🟡"
                    if cols[i].button(label, key=d_s, use_container_width=True):
                        if d_s in occu:
                            for x in occu[d_s]: st.info(f"{x['Statut']} {x['Nom']} ({x['Passagers']}p)")























































