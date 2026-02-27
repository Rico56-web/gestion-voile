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

# CSS MIS À JOUR (Gestion des couleurs de boutons par type)
st.markdown("""
    <style>
    /* Style de base des fiches */
    .client-card {
        background-color: #ffffff !important; 
        padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    /* Tag CMN dans les fiches */
    .cmn-tag { 
        background-color: #ebf5fb; color: #2980b9; 
        padding: 4px 8px; border-radius: 4px; 
        font-weight: bold; border: 1px solid #2980b9; display: inline-block;
    }

    /* COULEURS DES BOUTONS DU CALENDRIER */
    /* 1. Bouton Standard (Gris/Bleu clair) */
    div[data-testid="column"] button[key^="p_"] {
        background-color: #f1f2f6 !important;
        color: #2f3542 !important;
        border: 1px solid #dcdde1 !important;
    }

    /* 2. Bouton Spécial CMN (Bleu Roi) */
    div.stButton > button[key*="_cmn"] {
        background-color: #2980b9 !important;
        color: white !important;
        border: none !important;
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
        data = {"message": "Update Vesta UI", "content": content_b64, "sha": sha}
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

# --- SESSION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "auth" not in st.session_state: st.session_state.auth = False

# --- AUTH ---
if not st.session_state.auth:
    st.title("⚓ Vesta Skipper")
    pwd = st.text_input("Code d'accès", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- MENU PRINCIPAL ---
m1, m2 = st.columns(2)
if m1.button("📋 LISTE COÉQUIPIERS", use_container_width=True): 
    st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLANNING & FINANCES", use_container_width=True): 
    st.session_state.page = "PLAN"; st.rerun()
st.markdown("---")

df = charger_data()
cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
for c in cols_v:
    if c not in df.columns: df[c] = ""

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="NOM ou SOCIÉTÉ").upper()
    
    with c_add:
        if st.button("➕ NOUVEAU COÉQUIPIER", use_container_width=True, type="primary"):
            st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_base = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)] if search else df

    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def afficher_cartes(data_f, inverse=False):
        data_f = data_f.sort_values('dt', ascending=not inverse)
        for idx, r in data_f.iterrows():
            st_str = str(r['Statut'])
            cl = "status-ok" if "🟢" in st_str else "status-attente" if "🟡" in st_str else "status-non"
            v_soc = clean_val(r['Société'])
            soc_html = f'<div class="cmn-tag">🏢 CMN</div>' if v_soc == "CMN" else f'<div style="color:#d35400; font-weight:bold;">🏢 {v_soc}</div>' if v_soc else ''
            
            st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold; font-size:1.2rem;">{r['PrixJour']}€</div>
                    <div style="font-size:1.2rem;"><b>{r['Prénom']} {r['Nom']}</b></div>
                    {soc_html}
                    <div style="font-size:0.9rem; color:#444; margin-top:5px;">
                        📅 <b>{r['DateNav']}</b> ({r['NbJours']}j) | 📞 {r['Téléphone']}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Modifier {r['Prénom']} {r['Nom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE FORMULAIRE (Identique) ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    if idx is not None: init = df.loc[idx].to_dict()
    else: init = {c: "" for c in cols_v}; init["Statut"], init["NbJours"] = "🟡 Attente", "1"

    with st.form("f_coep"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
        f_nom = st.text_input("NOM", value=init["Nom"])
        f_pre = st.text_input("Prénom", value=init["Prénom"])
        f_soc = st.text_input("SOCIÉTÉ", value=init["Société"])
        f_tel = st.text_input("Téléphone", value=init["Téléphone"])
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init["DateNav"])
        f_nbj = st.number_input("Jours", value=to_int(init["NbJours"]), min_value=1)
        f_prix = st.text_input("Prix Total €", value=init["PrixJour"])
        f_his = st.text_area("Notes", value=init["Historique"])
        if st.form_submit_button("💾 ENREGISTRER"):
            new_row = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Société": f_soc.upper(), "Statut": f_stat, "Email": init["Email"], "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": init["Passagers"], "Historique": f_his}
            if idx is not None: df.loc[idx] = new_row
            else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            if sauvegarder_data(df): st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 Annuler"): st.session_state.page = "LISTE"; st.rerun()

# --- PAGE PLANNING ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

    # Logique d'occupation
    occu = {}
    for _, r in df.iterrows():
        d_obj = parse_date(r['DateNav'])
        if d_obj.year == 2026:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)

    cal = calendar.monthcalendar(2026, st.session_state.m_idx)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                est_cmn = any(clean_val(x.get('Société')) == "CMN" for x in occu.get(d_s, []))
                has_ok = any("🟢" in str(x['Statut']) for x in occu.get(d_s, []))
                
                label = f"{day} 🔵" if est_cmn else f"{day} 🟢" if has_ok else f"{day} 🟡" if d_s in occu else str(day)
                # On ajoute "_cmn" à la clé pour que le CSS l'attrape
                key_btn = f"p_{d_s}_cmn" if est_cmn else f"p_{d_s}"
                
                if cols[i].button(label, key=key_btn, use_container_width=True):
                    st.write(f"**Détails du {d_s} :**")
                    for x in occu.get(d_s, []): st.info(f"{x['Statut']} {x['Prénom']} {x['Nom']} ({x['Société']})")

















































































