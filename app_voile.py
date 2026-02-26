import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# Style CSS pour iPhone
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .info-line { font-size: 0.85em; color: #666; margin-bottom: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=2)
def charger_data(nom_fichier, colonnes):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            df_l = pd.DataFrame(json.loads(decoded))
            for c in colonnes:
                if c not in df_l.columns: df_l[c] = ""
            return df_l
    except: pass
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    cols_s = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    json_d = df[cols_s].to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
    data = {"message": "Fix Vesta", "content": content_b64, "sha": sha}
    requests.put(url, headers=headers, json=data)
    st.cache_data.clear()

# --- LOGIQUE DE TRI ---
def parse_date(date_str):
    try:
        return datetime.strptime(str(date_str).strip().replace(" ", ""), '%d/%m/%Y')
    except:
        return datetime(2000, 1, 1)

def safe_int(val, default=1):
    try:
        if val is None or str(val).strip() == "": return default
        return int(float(str(val).strip()))
    except:
        return default

# --- NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

def nav(p):
    if "edit_idx" in st.session_state: del st.session_state.edit_idx
    st.session_state.page = p
    st.rerun()

# --- AUTH ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols_base)
    
    # Menu
    c1, c2, c3 = st.columns(3)
    if c1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if c2.button("🗓️ PLANNING", use_container_width=True): nav("CALENDRIER")
    if c3.button("➕ NOUVEAU", use_container_width=True): nav("FORM")
    st.markdown("---")

    # --- LISTE + ARCHIVES ---
    if st.session_state.page == "LISTE":
        st.write(f"**Base : {len(df)} fiches**")
        df['dt_obj'] = df['DateNav'].apply(parse_date)
        auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        
        def display_list(target_df):
            for idx, r in target_df.iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold;">{r['PrixJour']}€</div>
                    <b>{r['Prénom']} {r['Nom']}</b><br>
                    <div class="info-line">📅 {r['DateNav']} ({r.get('NbJours',1)}j) | 👤 {r['Passagers']}p</div>
                    <div class="info-line">📞 {r['Téléphone']} | ✉️ {r['Email']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Modifier {r['Prénom']} {r['Nom']}", key=f"ed_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1:
            display_list(df[df['dt_obj'] >= auj].sort_values('dt_obj'))
        with tab2:
            display_list(df[df['dt_obj'] < auj].sort_values('dt_obj', ascending=False).head(20))

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("f_final"):
            st.subheader("📝 Détails Dossier")
            f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_mail = st.text_input("Email", value=init.get("Email", ""))
            st.markdown("---")
            c1, c2, c3, c4 = st.columns([2,1,1,1])
            f_date = c1.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = c2.number_input("Jours", min_value=1, value=safe_int(init.get("NbJours", 1)))
            f_pass = c3.number_input("Pers.", min_value=1, value=safe_int(init.get("Passagers", 1)))
            f_prix = c4.text_input("Prix €", value=init.get("PrixJour", "0"))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new_rec = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(), "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass), "Téléphone": f_tel, "Email": f_mail, "Paye": "Oui", "Historique": f_his}
                if idx is not None: df.loc[idx] = new_rec
                else: df = pd.concat([df, pd.DataFrame([new_rec])], ignore_index=True)
                sauvegarder_data(df, "contacts"); nav("LISTE")
        if st.button("🔙 RETOUR"): nav("LISTE")

    # --- CALENDRIER ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
        c2.markdown(f"<h3 style='text-align:center;'>{mois_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
        if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

        occu_map = {}
        for _, r in df.iterrows():
            d_obj = parse_date(r['DateNav'])
            if d_obj.year != 2000:
                # Utilisation de safe_int pour éviter le crash ValueError
                for j in range(safe_int(r.get('NbJours', 1))):
                    d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                    if d_c not in occu_map: occu_map[d_c] = []
                    occu_map[d_c].append(r)

        cal = calendar.monthcalendar(2026, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                    label = str(day)
                    if d_s in occu_map:
                        label = "🟢" if any("🟢" in str(x['Statut']) for x in occu_map[d_s]) else "🟡"
                    
                    if cols[i].button(label, key=f"pl_{d_s}", use_container_width=True):
                        if d_s in occu_map:
                            for res in occu_map[d_s]:
                                st.info(f"{res['Statut']} {res['Prénom']} {res['Nom']}")
                                st.write("👤" * safe_int(res.get('Passagers', 1)))
                        else: st.write("Libre")





















































