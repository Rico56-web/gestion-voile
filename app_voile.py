import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# --- STYLE CSS (Optimisé iPhone/iPad/PC) ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 20px; font-family: sans-serif; }
    
    /* Fiches Coéquipiers */
    .client-card {
        background-color: #ffffff !important; 
        padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    .cmn-tag { 
        background-color: #ebf5fb; color: #2980b9; 
        padding: 4px 10px; border-radius: 6px; 
        font-weight: bold; border: 1px solid #2980b9; display: inline-block;
        margin-top: 5px; font-size: 0.8rem;
    }

    /* Bandeau financier */
    .finance-banner {
        background-color: #e8f4fd;
        padding: 12px; border-radius: 10px;
        border: 1px solid #3498db; margin-bottom: 20px;
    }

    /* TABLEAU CALENDRIER (Format Grille Fixe) */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { padding: 8px 2px; border: 1px solid #eee; background: #f8f9fa; font-size: 0.7rem; color: #7f8c8d; text-transform: uppercase; }
    .cal-table td { border: 1px solid #eee; text-align: center; vertical-align: middle; height: 50px; }
    .day-num { font-weight: bold; font-size: 1rem; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- ENTETE ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper</h1>', unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=10)
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
        data = {"message": "Mise à jour Vesta", "content": content_b64, "sha": sha}
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

def to_int(v):
    try: return int(float(str(v)))
    except: return 1

# --- SESSION & AUTH ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- CHARGEMENT DONNEES ---
df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- MENU ---
m1, m2 = st.columns(2)
if m1.button("📋 COÉQUIPIERS", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLANNING", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
st.markdown("---")

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom ou Société").upper()
    if c_add.button("➕ NOUVEAU", use_container_width=True, type="primary"):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_base = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)] if search else df
    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def afficher_cartes(data_f, inverse=False):
        data_f = data_f.sort_values('dt', ascending=not inverse)
        for idx, r in data_f.iterrows():
            cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente"
            v_soc = clean_val(r['Société'])
            soc_html = f'<div class="cmn-tag">🏢 CMN</div>' if v_soc == "CMN" else f'<div style="color:#d35400; font-weight:bold; font-size:0.8rem;">🏢 {v_soc}</div>' if v_soc else ''
            st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div><div><b>{r["Prénom"]} {r["Nom"]}</b></div>{soc_html}<div style="font-size:0.85rem; color:#444; margin-top:5px;">📅 {r["DateNav"]} ({r["NbJours"]}j)<br>📞 {r["Téléphone"]}</div></div>', unsafe_allow_html=True)
            if st.button(f"✏️ Modifier {r['Prénom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE PLANNING (FORMAT 01, 02... SANS PUCES) ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    jours_lettres = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

    # Finances
    ca_ok, ca_att = 0.0, 0.0
    for _, r in df.iterrows():
        dt = parse_date(r['DateNav'])
        if dt.month == st.session_state.m_idx and dt.year == 2026:
            p = to_float(r['PrixJour']); ca_ok += p if "🟢" in str(r['Statut']) else 0; ca_att += p if "🟡" in str(r['Statut']) else 0
    st.markdown(f'<div class="finance-banner"><div style="display:flex; justify-content:space-around; text-align:center; font-size:0.9rem;"><div><b>Encaissé</b><br>{ca_ok:,.0f}€</div><div><b>Attente</b><br>{ca_att:,.0f}€</div><div><b>Total</b><br>{(ca_ok+ca_att):,.0f}€</div></div></div>'.replace(",", " "), unsafe_allow_html=True)

    # Calcul des occupations
    occu = {}
    for _, r in df.iterrows():
        d_obj = parse_date(r['DateNav'])
        if d_obj.year == 2026:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)

    # Grille HTML
    cal = calendar.monthcalendar(2026, st.session_state.m_idx)
    html_cal = '<table class="cal-table"><tr>'
    for j in jours_lettres: html_cal += f'<th>{j}</th>'
    html_cal += '</tr>'

    for week in cal:
        html_cal += '<tr>'
        for day in week:
            if day == 0: html_cal += '<td style="background:#fafafa;"></td>'
            else:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                day_str = f"{day:02d}" # Force le format 01, 02...
                data_j = occu.get(d_s, [])
                bg, col = "white", "black"
                if data_j:
                    if any(clean_val(x.get('Société')) == "CMN" for x in data_j): bg, col = "#2980b9", "white"
                    elif any("🟢" in str(x['Statut']) for x in data_j): bg, col = "#2ecc71", "white"
                    else: bg, col = "#f1c40f", "black"
                html_cal += f'<td style="background:{bg}; color:{col}; border: 1px solid #eee;"><span class="day-num">{day_str}</span></td>'
        html_cal += '</tr>'
    st.markdown(html_cal + '</table>', unsafe_allow_html=True)

    # Détails
    st.markdown("---")
    jours_m = sorted([d for d in occu.keys() if int(d.split('/')[1]) == st.session_state.m_idx], key=lambda x: int(x.split('/')[0]))
    if jours_m:
        sel = st.selectbox("Voir les détails d'une journée :", ["Choisir une date..."] + jours_m)
        if sel != "Choisir une date...":
            for x in occu[sel]: st.info(f"⚓ **{x['Prénom']} {x['Nom']}** ({x['Société']})")

# --- PAGE FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_v}
    if idx is None: init["Statut"], init["NbJours"] = "🟡 Attente", "1"
    
    with st.form("f_coep"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=0)
        f_nom = st.text_input("NOM", value=init["Nom"]).upper()
        f_pre = st.text_input("Prénom", value=init["Prénom"])
        f_soc = st.text_input("SOCIÉTÉ (CMN pour le bleu)", value=init["Société"]).upper()
        f_tel = st.text_input("Téléphone", value=init["Téléphone"])
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init["DateNav"])
        f_nbj = st.number_input("Nombre de jours", value=to_int(init["NbJours"]), min_value=1)
        f_prix = st.text_input("Prix Total (€)", value=init["PrixJour"])
        f_his = st.text_area("Notes", value=init["Historique"])
        if st.form_submit_button("💾 ENREGISTRER"):
            new = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Statut": f_stat, "Email": init.get("Email",""), "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": "1", "Historique": f_his}
            if idx is not None: df.loc[idx] = new
            else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 Annuler"): st.session_state.page = "LISTE"; st.rerun()























































































