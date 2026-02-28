import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

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
    .cmn-tag { 
        background-color: #ebf5fb; color: #2980b9; padding: 2px 6px; border-radius: 4px; 
        font-weight: bold; border: 1px solid #2980b9; font-size: 0.65rem;
    }
    .contact-info { font-size: 0.75rem; color: #7f8c8d; margin-top: 3px; }
    .finance-banner {
        background-color: #e8f4fd; padding: 8px; border-radius: 10px;
        border: 1px solid #3498db; margin-bottom: 10px;
    }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { padding: 4px 0; border: 1px solid #eee; background: #f8f9fa; font-size: 0.6rem; }
    .cal-table td { border: 1px solid #eee; height: 38px; padding: 0 !important; }
    .day-wrapper { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; }
    .day-num { font-weight: bold; font-size: 0.85rem; }
    .detail-item { padding: 6px 10px; border-bottom: 1px solid #eee; font-size: 0.85rem; display: flex; justify-content: space-between; }
    .budget-row { padding: 8px; border-bottom: 1px solid #eee; font-size: 0.8rem; }
    .total-row { background: #2c3e50; color: white; padding: 10px; border-radius: 5px; margin-top: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=5)
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
    try: return datetime.strptime(clean_val(d).replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0

def to_int(v):
    try: return int(float(str(v)))
    except: return 1

# --- NAVIGATION ---
ANNEES_DISPO = [2026, 2027, 2028]
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "y_idx" not in st.session_state: st.session_state.y_idx = 2026
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- MENU ---
m1, m2, m3 = st.columns(3)
if m1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLAN", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰 BUDGET", use_container_width=True): st.session_state.page = "BUDGET"; st.rerun()
st.markdown("---")

# --- PAGE LISTE (CORRIGÉE) ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom/Soc").upper()
    if c_add.button("➕ NEW", use_container_width=True, type="primary"):
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
            soc_html = f'<div class="cmn-tag">🏢 CMN</div>' if v_soc == "CMN" else f'<div style="color:#d35400; font-weight:bold; font-size:0.75rem;">🏢 {v_soc}</div>' if v_soc else ''
            
            # CARTE AVEC COORDONNÉES
            st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold; font-size:0.85rem;">{r["PrixJour"]}€</div>
                    <div><b>{r["Prénom"]} {r["Nom"]}</b></div>
                    {soc_html}
                    <div class="contact-info">📞 {r['Téléphone']} | ✉️ {r['Email']}</div>
                    <div style="font-size:0.75rem; color:#444; margin-top:5px;">📅 {r["DateNav"]} ({r["NbJours"]}j)</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Gérer {r['Prénom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    
    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE PLANNING ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    c_y1, _ = st.columns([1,1])
    st.session_state.y_idx = c_y1.selectbox("Année", ANNEES_DISPO, index=ANNEES_DISPO.index(st.session_state.y_idx))
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): 
        if st.session_state.m_idx == 1:
            if st.session_state.y_idx > ANNEES_DISPO[0]: st.session_state.m_idx = 12; st.session_state.y_idx -= 1
        else: st.session_state.m_idx -= 1
        st.rerun()
    c2.markdown(f"<h4 style='text-align:center; margin:0;'>{m_fr[st.session_state.m_idx-1]} {st.session_state.y_idx}</h4>", unsafe_allow_html=True)
    if c3.button("▶️"): 
        if st.session_state.m_idx == 12:
            if st.session_state.y_idx < ANNEES_DISPO[-1]: st.session_state.m_idx = 1; st.session_state.y_idx += 1
        else: st.session_state.m_idx += 1
        st.rerun()

    # Logique calendrier identique...
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
            if day == 0: html_cal += '<td style="background:#fafafa;"></td>'
            else:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{st.session_state.y_idx}"
                data_j = occu.get(d_s, [])
                bg, col = "white", "black"
                if data_j:
                    if any(clean_val(x.get('Société')) == "CMN" for x in data_j): bg, col = "#2980b9", "white"
                    elif any("🟢" in str(x['Statut']) for x in data_j): bg, col = "#2ecc71", "white"
                    else: bg, col = "#f1c40f", "black"
                html_cal += f'<td style="background:{bg};color:{col};"><div class="day-wrapper"><span class="day-num">{day:02d}</span></div></td>'
        html_cal += '</tr>'
    st.markdown(html_cal + '</table>', unsafe_allow_html=True)

# --- PAGE BUDGET ---
elif st.session_state.page == "BUDGET":
    y_budget = st.selectbox("Année", ANNEES_DISPO, index=ANNEES_DISPO.index(st.session_state.y_idx))
    st.markdown(f"<h4 style='text-align:center;'>💰 Budget {y_budget}</h4>", unsafe_allow_html=True)
    # ... Logique budget identique ...

# --- PAGE FORMULAIRE (CORRIGÉE AVEC SUPPRIMER) ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_v}
    
    st.markdown(f"### {'📝 Modifier' if idx is not None else '➕ Nouveau'}")
    
    with st.form("f_coep"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=0)
        f_nom = st.text_input("NOM", value=init["Nom"]).upper()
        f_pre = st.text_input("Prénom", value=init["Prénom"])
        f_soc = st.text_input("SOCIÉTÉ", value=init["Société"]).upper()
        f_tel = st.text_input("Téléphone", value=init["Téléphone"])
        f_mail = st.text_input("Email", value=init["Email"])
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init["DateNav"])
        f_nbj = st.number_input("Nombre de jours", value=to_int(init["NbJours"]), min_value=1)
        f_prix = st.text_input("Prix Total (€)", value=init["PrixJour"])
        f_his = st.text_area("Notes / Historique", value=init["Historique"])
        
        col_btn1, col_btn2 = st.columns(2)
        submit = col_btn1.form_submit_button("💾 ENREGISTRER", use_container_width=True)
        cancel = col_btn2.form_submit_button("🔙 ANNULER", use_container_width=True)

        if submit:
            new = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": "1", "Historique": f_his}
            if idx is not None: df.loc[idx] = new
            else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
        if cancel: st.session_state.page = "LISTE"; st.rerun()

    # BOUTON SUPPRIMER (UNIQUEMENT EN MODE MODIFICATION)
    if idx is not None:
        st.markdown("---")
        with st.expander("⚠️ Zone de danger"):
            st.write("Voulez-vous vraiment supprimer ce contact ?")
            if st.button("🗑️ CONFIRMER LA SUPPRESSION", type="primary", use_container_width=True):
                df = df.drop(idx).reset_index(drop=True)
                if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
































































































