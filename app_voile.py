import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS (OPTIMISÉ IPHONE) ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 20px; font-size: 1.4rem; font-weight: bold; }
    
    /* Menu Principal Anti-Erreur */
    div.stButton > button {
        border-radius: 12px; height: 60px;
        border: 1px solid #dcdde1; background-color: white;
        color: #2f3640; font-weight: bold; font-size: 0.9rem;
        margin-bottom: 5px;
    }
    
    /* Cartes Clients */
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #e1e8ed; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    .soc-text { color: #d35400; font-weight: bold; font-size: 0.85rem; margin-bottom: 5px; }
    
    /* Liens Contacts */
    .contact-bar { font-size: 0.9rem; margin: 8px 0; font-weight: bold; }
    .contact-bar a { text-decoration: none; color: #2980b9; background: #f1f7fa; padding: 5px 10px; border-radius: 6px; display: inline-block; margin-right: 5px; }
    
    .stat-box { background: #ffffff; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #e1e8ed; }
    .stat-val { font-size: 1.2rem; font-weight: bold; color: #2980b9; display: block; }
    
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { padding: 8px 0; border: 1px solid #eee; background: #f8f9fa; font-size: 0.75rem; }
    .cal-table td { border: 1px solid #eee; height: 50px; text-align: center; }
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
def clean_val(val): return str(val).strip() if val and str(val).lower() != "none" else ""
def parse_date(d):
    try: return datetime.strptime(clean_val(d).replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)
def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def to_int(v):
    try: return int(float(str(v)))
    except: return 0

# --- INITIALISATION ---
ANNEES = [2026, 2027, 2028]
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "y_idx" not in st.session_state: st.session_state.y_idx = 2026
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# Vérification colonnes
cols_attendues = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur", "Historique"]
for c in cols_attendues:
    if c not in df.columns: df[c] = "0" if c in ["Milles", "HeuresMoteur"] else ""
if df_frais.empty: df_frais = pd.DataFrame(columns=["Date", "Type", "Libelle", "Montant", "Annee"])

# --- MENU PRINCIPAL ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
if m1.button("📋\nListe", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"):
    st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️\nPlan", use_container_width=True, type="primary" if st.session_state.page == "PLAN" else "secondary"):
    st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰\nStats", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"):
    st.session_state.page = "BUDGET"; st.rerun()
if m4.button("🔧\nFrais", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"):
    st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    if c_add.button("➕ NEW", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_base = df[df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)] if search else df
    
    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def afficher_cartes(data_f, inverse=False):
        data_f = data_f.sort_values('dt', ascending=not inverse)
        for idx, r in data_f.iterrows():
            cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente"
            tel_brut = str(r['Téléphone']).replace(" ", "").replace(".", "").replace("-", "")
            soc = clean_val(r['Société'])
            
            st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div>
                    <div style="font-size:1.1rem;"><b>{r["Prénom"]} {r["Nom"]}</b></div>
                    <div class="soc-text">🏢 {soc if soc else "Individuel"}</div>
                    <div class="contact-bar">
                        <a href="tel:{tel_brut}">📞 Appeler</a>
                        <a href="mailto:{r['Email']}">✉️ Mail</a>
                    </div>
                    <div style="font-size:0.8rem; color:#7f8c8d; margin-top:5px;">
                        📅 {r["DateNav"]} | 🚢 {r.get('Milles', 0)} NM | ⚙️ {r.get('HeuresMoteur', 0)}h
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Modifier {r['Prénom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    
    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE PLANNING ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    c_y, c_m = st.columns(2)
    st.session_state.y_idx = c_y.selectbox("Année", ANNEES, index=ANNEES.index(st.session_state.y_idx))
    st.session_state.m_idx = c_m.selectbox("Mois", range(1, 13), index=st.session_state.m_idx-1, format_func=lambda x: m_fr[x-1])

    occu = {}
    for _, r in df.iterrows():
        d_obj = parse_date(r['DateNav'])
        if d_obj.year == st.session_state.y_idx:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
    
    cal = calendar.monthcalendar(st.session_state.y_idx, st.session_state.m_idx)
    html_cal = '<table class="cal-table"><tr><th>Lun</th><th>Mar</th><th>Mer</th><th>Jeu</th><th>Ven</th><th>Sam</th><th>Dim</th></tr>'
    for week in cal:
        html_cal += '<tr>'
        for day in week:
            if day == 0: html_cal += '<td style="background:#f9f9f9;"></td>'
            else:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{st.session_state.y_idx}"
                data_j = occu.get(d_s, [])
                bg = "white"
                if data_j: bg = "#2ecc71" if any("🟢" in str(x['Statut']) for x in data_j) else "#f1c40f"
                html_cal += f'<td style="background:{bg}; font-weight:bold;">{day}</td>'
        html_cal += '</tr>'
    st.markdown(html_cal + '</table>', unsafe_allow_html=True)

# --- PAGE BUDGET ---
elif st.session_state.page == "BUDGET":
    y = st.selectbox("Année", ANNEES, index=ANNEES.index(st.session_state.y_idx))
    df_y = df[df['DateNav'].apply(lambda x: parse_date(x).year == y)]
    df_ok = df_y[df_y['Statut'].str.contains("🟢", na=False)]
    
    rev_ok = sum(df_ok['PrixJour'].apply(to_float))
    milles_tot = sum(df_ok['Milles'].apply(to_float))
    heures_tot













































































































