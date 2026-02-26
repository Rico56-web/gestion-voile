import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta", layout="wide")

# Style CSS minimaliste pour accélérer le rendu Safari
st.markdown("""
    <style>
    .client-card {
        background-color: #fff; padding: 10px; border-radius: 8px; 
        margin-bottom: 5px; border: 1px solid #eee; border-left: 5px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTEUR DE DONNÉES ULTRA-RAPIDE ---
@st.cache_data(ttl=300) # On garde les données en mémoire 5 minutes (très important pour iOS)
def charger_data_ios(nom_fichier, colonnes):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=5)
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
    cols_s = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    json_d = df[cols_s].to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
    data = {"message": "Update", "content": content_b64, "sha": sha} if sha else {"message": "Update", "content": content_b64}
    requests.put(url, headers=headers, json=data)
    st.cache_data.clear() # On vide le cache uniquement lors d'une sauvegarde

# --- LOGIQUE DE NAVIGATION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

def nav(p):
    st.session_state.page = p
    st.rerun()

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Vesta")
    pwd = st.text_input("Code", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data_ios("contacts", cols_base)
    
    # Menu compact
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 LISTE"): nav("LISTE")
    if m2.button("🗓️ PLAN"): nav("CALENDRIER")
    if m3.button("➕ NEW"): nav("FORM")
    if m4.button("✅"): nav("CHECK")
    st.markdown("---")

    # --- LISTE OPTIMISÉE ---
    if st.session_state.page == "LISTE":
        tab1, tab2 = st.tabs(["🚀 Futur", "📂 Archives"])
        auj = datetime.now().strftime('%Y%m%d')
        df['s'] = df['DateNav'].apply(lambda x: "".join(reversed(x.split('/'))) if '/' in str(x) else "0")

        with tab1:
            f_df = df[df['s'] >= auj].sort_values('s').head(10)
            for idx, r in f_df.iterrows():
                if st.button(f"⚓ {r['DateNav']} - {r['Nom']}", key=f"b_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
        with tab2:
            p_df = df[df['s'] < auj].sort_values('s', ascending=False).head(5)
            for idx, r in p_df.iterrows():
                if st.button(f"📁 {r['DateNav']} - {r['Nom']}", key=f"p_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    # --- PLANNING SANS CLAVIER ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): 
            st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1
            st.rerun()
        c2.markdown(f"### {mois_fr[st.session_state.m_idx-1]}")
        if c3.button("▶️"): 
            st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1
            st.rerun()

        cal = calendar.monthcalendar(datetime.now().year, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{datetime.now().year}"
                    occ = df[(df['DateNav'] == d_s) & (df['Statut'] == "🟢 OK")]
                    if cols[i].button(f"🟢" if not occ.empty else f"{day}", key=f"d_{d_s}", use_container_width=True):
                        if not occ.empty: st.info(f"{occ.iloc[0]['Nom']}")

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("f"):
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
            if st.form_submit_button("💾 SAUVER"):
                new = {"DateNav": f_date, "Nom": f_nom.upper(), "Statut": f_stat, "Prénom": init.get("Prénom",""), "Téléphone": init.get("Téléphone",""), "Email": init.get("Email",""), "Paye": "Oui", "PrixJour": "0", "Passagers": "1", "Historique": ""}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df, "contacts")
                nav("LISTE")
        if st.button("🔙"): nav("LISTE")
            


















































