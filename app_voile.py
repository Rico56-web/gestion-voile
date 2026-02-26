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

# CSS pour iPhone
st.markdown("""
    <style>
    .stButton > button { border-radius: 10px !important; height: 45px !important; font-weight: bold !important; }
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #eee; border-left: 10px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .price-tag { float: right; font-weight: bold; color: #1e3799; font-size: 1.1em; }
    .info-sub { font-size: 0.95em; color: #444; margin-top: 5px; line-height: 1.5; }
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
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")

# --- UTILS ---
def format_tel(tel):
    if not tel: return ""
    nums = re.sub(r'\D', '', str(tel))
    return " ".join(nums[i:i+2] for i in range(0, len(nums), 2))

def parse_date(d):
    try: 
        s = str(d).strip().replace(" ", "").replace("-", "/")
        return datetime.strptime(s, '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

def to_int(v):
    try: return int(float(str(v))) if v and str(v).strip() != "" else 1
    except: return 1

# --- SESSION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "auth" not in st.session_state: st.session_state.auth = False

# --- AUTHENTIFICATION ---
if not st.session_state.auth:
    st.title("⚓ Vesta Skipper")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.auth = True
        st.rerun()
else:
    # --- BARRE DE MENU ---
    m1, m2, m3 = st.columns(3)
    if m1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if m2.button("🗓️ PLAN", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
    if m3.button("➕ NEW", use_container_width=True): st.session_state.page = "FORM"; st.session_state.edit_idx = None; st.rerun()
    st.markdown("---")

    df = charger_data()
    cols_v = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "PrixJour", "Passagers", "Historique"]
    for c in cols_v:
        if c not in df.columns: df[c] = ""

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        df['dt'] = df['DateNav'].apply(parse_date)
        auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        
        def render_fiches(data_f):
            for idx, r in data_f.iterrows():
                st_str = str(r['Statut'])
                cl = "status-ok" if "🟢" in st_str else "status-attente" if "🟡" in st_str else "status-non"
                st.markdown(f"""
                <div class="client-card {cl}">
                    <div class="price-tag">{r['PrixJour']}€</div>
                    <b>{r['Prénom']} {r['Nom']}</b><br>
                    <div class="info-sub">
                        📅 <b>{r['DateNav']}</b> ({r['NbJours']}j) — 👤 {r['Passagers']}p<br>
                        📞 <b>{format_tel(r['Téléphone'])}</b> | ✉️ {r['Email']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Modifier {r['Nom']}", key=f"ed_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1: render_fiches(df[df['dt'] >= auj].sort_values('dt'))
        with tab2: render_fiches(df[df['dt'] < auj].sort_values('dt', ascending=False).head(20))

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.edit_idx
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_v}
        with st.form("f_fiche"):
            st.subheader("📝 Détails Dossier")
            f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_mail = st.text_input("Email", value=init.get("Email", ""))
            st.markdown("---")
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            f_date = c1.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = c2.number_input("Jours", value=to_int(init.get("NbJours", 1)))
            f_pass = c3.number_input("Pers.", value=to_int(init.get("Passagers", 1)))
            f_prix = c4.text_input("Prix €", value=init.get("PrixJour", "0"))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Passagers": str(f_pass), "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
        if st.button("🔙 ANNULER"): st.session_state.page = "LISTE"; st.rerun()

    # --- PAGE PLANNING ---
    elif st.session_state.page == "PLAN":
        if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month
        m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
        c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
        if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

        # Construction de la map
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
                        # DÉTECTION ROBUSTE : On cherche le vert et le jaune séparément
                        possede_vert = False
                        possede_jaune = False
                        
                        for x in occu[d_s]:
                            statut_actuel = str(x.get('Statut', ''))
                            if "🟢" in statut_actuel or "OK" in statut_actuel.upper():
                                possede_vert = True
                            if "🟡" in statut_actuel or "ATTENTE" in statut_actuel.upper():
                                possede_jaune = True
                        
                        # DÉCISION DU LABEL
                        if possede_vert and possede_jaune: label = "🟢+🟡"
                        elif possede_vert: label = "🟢"
                        elif possede_jaune: label = "🟡"
                    
                    if cols[i].button(label, key=f"p_{d_s}", use_container_width=True):
                        if d_s in occu:
                            st.write(f"**Journée du {d_s}**")
                            for x in occu[d_s]: 
                                st.info(f"{x['Statut']} {x['Nom']} ({x['Passagers']}p) - {format_tel(x['Téléphone'])}")































































