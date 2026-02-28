import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 10px; font-size: 1.3rem; }
    .client-card {
        background-color: #ffffff !important; 
        padding: 12px; border-radius: 10px; 
        margin-bottom: 8px; border: 1px solid #eee; border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .soc-text { color: #d35400; font-weight: bold; font-size: 0.8rem; }
    .contact-info { font-size: 0.85rem; margin-top: 5px; font-weight: bold; }
    .contact-info a { text-decoration: none; color: #2980b9; }
    .stat-box { background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #eee; min-height: 80px; }
    .stat-val { font-size: 1.1rem; font-weight: bold; color: #2c3e50; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-top:10px; }
    .cal-table th { padding: 6px 0; border: 1px solid #eee; background: #f8f9fa; font-size: 0.7rem; }
    .cal-table td { border: 1px solid #eee; height: 45px; padding: 0 !important; }
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

# Assurer la présence des nouvelles colonnes
cols_attendues = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur", "Historique"]
for c in cols_attendues:
    if c not in df.columns: df[c] = "0" if c in ["Milles", "HeuresMoteur"] else ""

if df_frais.empty: df_frais = pd.DataFrame(columns=["Date", "Type", "Libelle", "Montant", "Annee"])

# --- MENU PRINCIPAL ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
if m1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLAN", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰 BUDGET", use_container_width=True): st.session_state.page = "BUDGET"; st.rerun()
if m4.button("🔧 FRAIS", use_container_width=True): st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    if c_add.button("➕ NEW", use_container_width=True, type="primary"):
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
            soc_html = f'<div class="soc-text">🏢 {soc}</div>' if soc else ""
            
            st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div>
                    <div><b>{r["Prénom"]} {r["Nom"]}</b></div>
                    {soc_html}
                    <div class="contact-info">
                        <a href="tel:{tel_brut}">📞 {r['Téléphone']}</a> | <a href="mailto:{r['Email']}">✉️ Mail</a>
                    </div>
                    <div style="font-size:0.75rem; color:#444; margin-top:5px;">
                        📅 {r["DateNav"]} | 🚢 {r.get('Milles', 0)} NM | ⚙️ {r.get('HeuresMoteur', 0)}h
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Gérer {r['Prénom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    
    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE BUDGET & LOG ---
elif st.session_state.page == "BUDGET":
    y = st.selectbox("Année", ANNEES, index=ANNEES.index(st.session_state.y_idx))
    df_y = df[df['DateNav'].apply(lambda x: parse_date(x).year == y)]
    df_ok = df_y[df_y['Statut'].str.contains("🟢", na=False)]
    
    # CALCULS
    rev_ok = sum(df_ok['PrixJour'].apply(to_float))
    milles_tot = sum(df_ok['Milles'].apply(to_float))
    heures_tot = sum(df_ok['HeuresMoteur'].apply(to_float))
    frais_y = sum(df_frais[df_frais['Annee'].astype(str) == str(y)]['Montant'].apply(to_float))
    
    st.markdown("### 📊 Statistiques de navigation")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><small>DISTANCE</small><br><span class="stat-val">{milles_tot:,.0f} NM</span></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><small>MOTEUR</small><br><span class="stat-val">{heures_tot:,.1f} h</span></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-box"><small>NET</small><br><span class="stat-val" style="color:#2ecc71;">{(rev_ok - frais_y):,.0f}€</span></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.write(f"**Chiffre d'Affaires Encaissé :** {rev_ok:,.0f} €".replace(","," "))
    st.write(f"**Nombre de jours en mer :** {sum(df_ok['NbJours'].apply(to_int))} j")

# --- PAGE FORMULAIRE (AVEC MILLES ET HEURES) ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_attendues}
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=0)
        f_nom = st.text_input("NOM", value=init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", value=init.get("Société", "")).upper()
        
        col_a, col_b = st.columns(2)
        f_milles = col_a.number_input("Milles Nautiques (NM)", value=to_float(init.get("Milles", 0)))
        f_heures = col_b.number_input("Heures Moteur", value=to_float(init.get("HeuresMoteur", 0)))
        
        f_tel = st.text_input("Tél", value=init.get("Téléphone", ""))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
        f_nbj = st.number_input("Jours", value=to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix", value=init.get("PrixJour", ""))
        
        if st.form_submit_button("💾 SAUVEGARDER"):
            row = {
                "DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, 
                "Société": f_soc, "Statut": f_stat, "Email": init.get("Email",""), 
                "Téléphone": f_tel, "PrixJour": f_prix, "Milles": str(f_milles), 
                "HeuresMoteur": str(f_heures), "Historique": ""
            }
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()

    if st.button("🔙 RETOUR"): st.session_state.page = "LISTE"; st.rerun()
    if idx is not None:
        with st.expander("⚠️ ZONE DE DANGER"):
            if st.button("🗑️ SUPPRIMER"):
                df = df.drop(idx).reset_index(drop=True); sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()

# --- RESTE DU CODE (FRAIS ET PLAN IDENTIQUES) ---
elif st.session_state.page == "PLAN":
    # (Le bloc calendrier est le même que précédemment)
    pass
elif st.session_state.page == "FRAIS":
    # (Le bloc frais est le même que précédemment)
    pass









































































































