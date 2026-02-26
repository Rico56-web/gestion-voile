import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta", layout="wide")

# Style CSS Épuré mais lisible
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff; padding: 12px; border-radius: 8px; 
        margin-bottom: 8px; border: 1px solid #ddd; border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 0.8em; background-color: #f4f4f4; margin-right: 4px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB (AVEC CACHE) ---
@st.cache_data(ttl=30)
def charger_data(nom_fichier, colonnes):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()
            decoded = base64.b64decode(content['content']).decode('utf-8')
            if decoded.strip():
                df_load = pd.DataFrame(json.loads(decoded))
                for col in colonnes:
                    if col not in df_load.columns: df_load[col] = ""
                return df_load
    except: pass
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    cols_save = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    json_data = df[cols_save].to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Update", "content": content_b64}
    if sha: data["sha"] = sha
    
    success = requests.put(url, headers=headers, json=data).status_code in [200, 201]
    st.cache_data.clear()
    return success

# --- NAVIGATION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"

def nav(p):
    if "edit_idx" in st.session_state: del st.session_state.edit_idx
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
    df = charger_data("contacts", cols_base)
    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')

    # MENU AVEC TEXTE (RÉTABLI)
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if m2.button("🗓️ PLAN", use_container_width=True): nav("CALENDRIER")
    if m3.button("➕ NEW", use_container_width=True): nav("FORM")
    if m4.button("✅ CHECK", use_container_width=True): nav("CHECK")
    st.markdown("---")

    # --- LISTE ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher un nom...")
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        auj = pd.Timestamp(datetime.now().date())

        def draw_cards(subset):
            for idx, row in subset.iterrows():
                cl = "status-ok" if "🟢" in str(row['Statut']) else "status-attente" if "🟡" in str(row['Statut']) else "status-non"
                st.markdown(f'<div class="client-card {cl}"><b>{row["Nom"]} {row["Prénom"]}</b><br><small>📅 {row["DateNav"]} | 👤 {row["Passagers"]}p | 💰 {row["PrixJour"]}€</small></div>', unsafe_allow_html=True)
                if st.button(f"Ouvrir {row['Nom']}", key=f"b_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx
                    st.session_state.page = "FORM"
                    st.rerun()

        with tab1:
            f_df = df[df['temp_date_obj'] >= auj].sort_values('temp_date_obj')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False)]
            draw_cards(f_df)
        with tab2:
            p_df = df[df['temp_date_obj'] < auj].sort_values('temp_date_obj', ascending=False).head(15)
            draw_cards(p_df)

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("f_v"):
            st.write("### Fiche Contact")
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = st.text_input("Tel", value=init.get("Téléphone", ""))
            f_mail = st.text_input("Email", value=init.get("Email", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_prix = st.text_input("Forfait €", value=init.get("PrixJour", "0"))
            f_pass = st.number_input("Passagers", min_value=1, value=1 if not init.get("Passagers") else int(float(str(init.get("Passagers")).replace(',','.'))))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    datetime.strptime(f_date.strip(), '%d/%m/%Y')
                    new = {"DateNav": f_date.strip(), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(), "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass), "Téléphone": f_tel, "Email": f_mail, "Paye": "Oui" if "🟢" in f_stat else "Non", "Historique": f_his}
                    if idx is not None: df.loc[idx] = new
                    else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    if sauvegarder_data(df, "contacts"): nav("LISTE")
                except: st.error("Date invalide !")
        
        c_del, c_ret = st.columns(2)
        if c_del.button("🗑️ SUPPRIMER", use_container_width=True) and idx is not None:
            df = df.drop(index=idx)
            sauvegarder_data(df, "contacts")
            nav("LISTE")
        if c_ret.button("🔙 RETOUR", use_container_width=True): nav("LISTE")

    # --- PLANNING (RÉTABLI) ---
    elif st.session_state.page == "CALENDRIER":
        st.write("### 🗓️ Planning Mensuel")
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        m_sel = st.selectbox("Sélectionner le mois", mois_fr, index=datetime.now().month-1)
        m_idx = mois_fr.index(m_sel) + 1
        y_sel = datetime.now().year
        
        cal = calendar.monthcalendar(y_sel, m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{day:02d}/{m_idx:02d}/{y_sel}"
                    occ = df[(df['DateNav'] == d_str) & (df['Statut'] == "🟢 OK")]
                    if cols[i].button(f"🟢{day}" if not occ.empty else str(day), key=f"c_{day}_{m_idx}", use_container_width=True):
                        if not occ.empty:
                            for _, r in occ.iterrows(): st.info(f"⚓ {r['Nom']} ({r['Passagers']} pers.)")
                        else: st.write("Journée libre")

    # --- CHECK ---
    elif st.session_state.page == "CHECK":
        st.write("### ✅ Checklist Skipper")
        for item in ["Vannes", "Niveaux", "Gilets", "Briefing Passagers", "Gaz"]: st.checkbox(item)
            















































