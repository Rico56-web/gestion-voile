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
if m1.button("📋 LISTE & ARCHIVES", use_container_width=True): 
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
    search = c_search.text_input("🔍 Rechercher un nom...", placeholder="Ex: MARTIN ou VESTA").upper()
    
    with c_add:
        if st.button("➕ NOUVEAU CLIENT", use_container_width=True, type="primary"):
            st.session_state.edit_idx = None
            st.session_state.page = "FORM"
            st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if search:
        df_base = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)]
    else:
        df_base = df

    t1, t2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
    
    def afficher_fiches(data_f, inverse=False):
        data_f = data_f.sort_values('dt', ascending=not inverse)
        if inverse: data_f = data_f.head(30) # Limite pour les archives
        
        for idx, r in data_f.iterrows():
            titre = f"{r['Statut']} {r['DateNav']} - {r['Nom']} {r['Prénom']}"
            with st.expander(titre):
                c1, c2 = st.columns(2)
                c1.write(f"🏢 **Société:** {r['Société']}")
                c1.write(f"📞 **Tél:** {r['Téléphone']}")
                c1.write(f"✉️ **Email:** {r['Email']}")
                c2.write(f"💰 **Prix:** {r['PrixJour']}€")
                c2.write(f"👥 **Passagers:** {r['Passagers']}")
                c2.write(f"⏱️ **Durée:** {r['NbJours']} jour(s)")
                st.info(f"📝 **Notes:** {r['Historique']}")
                if st.button("✏️ Modifier cette fiche", key=f"ed_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    with t1: afficher_fiches(df_base[df_base['dt'] >= auj])
    with t2: afficher_fiches(df_base[df_base['dt'] < auj], inverse=True)

# --- PAGE FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    if idx is not None:
        init = df.loc[idx].to_dict()
    else:
        init = {c: "" for c in cols_v}
        init["Statut"], init["NbJours"], init["Passagers"] = "🟡 Attente", "1", "1"

    st.subheader("📝 Fiche Client")
    with st.form("f_client"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]) if init["Statut"] in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else 0)
        c_n, c_p = st.columns(2)
        f_nom = c_n.text_input("NOM", value=init["Nom"])
        f_pre = c_p.text_input("Prénom", value=init["Prénom"])
        f_soc = st.text_input("SOCIÉTÉ", value=init["Société"])
        f_tel = st.text_input("Téléphone", value=init["Téléphone"])
        f_mail = st.text_input("Email", value=init["Email"])
        st.markdown("---")
        c1, c2, c3 = st.columns([2,1,1])
        f_date = c1.text_input("Date (JJ/MM/AAAA)", value=init["DateNav"])
        f_nbj = c2.number_input("Jours", value=to_int(init["NbJours"]), min_value=1)
        f_pass = c3.number_input("Pers.", value=to_int(init["Passagers"]), min_value=1)
        f_prix = st.text_input("Prix Total €", value=init["PrixJour"])
        f_his = st.text_area("Notes / Historique", value=init["Historique"])
        
        if st.form_submit_button("💾 ENREGISTRER"):
            new_row = {
                "DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom.upper(), 
                "Prénom": f_pre, "Société": f_soc.upper(), "Statut": f_stat, 
                "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, 
                "Passagers": str(f_pass), "Historique": f_his
            }
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

    # DASHBOARD FINANCIER DU MOIS
    ca_ok, ca_att = 0.0, 0.0
    for _, r in df.iterrows():
        dt = parse_date(r['DateNav'])
        if dt.month == st.session_state.m_idx and dt.year == 2026:
            p = to_float(r['PrixJour'])
            if "🟢" in str(r['Statut']): ca_ok += p
            elif "🟡" in str(r['Statut']): ca_att += p
    
    # Affichage stylé des finances
    st.markdown("#### 💰 Bilan du mois")
    f1, f2, f3 = st.columns(3)
    f1.metric("Encaissé", f"{ca_ok:,.0f}€".replace(","," "))
    f2.metric("En attente", f"{ca_att:,.0f}€".replace(","," "))
    f3.metric("Total", f"{(ca_ok+ca_att):,.0f}€".replace(","," "))
    st.markdown("---")

    # Calendrier visuel
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
                btn_label = str(day)
                if d_s in occu:
                    has_ok = any("🟢" in str(x['Statut']) for x in occu[d_s])
                    btn_label = f"{day} 🟢" if has_ok else f"{day} 🟡"
                if cols[i].button(btn_label, key=f"p_{d_s}", use_container_width=True):
                    st.toast(f"Journée du {d_s}")
                    for x in occu.get(d_s, []): st.sidebar.info(f"{x['Statut']} {x['Nom']}")














































































