import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Skipper", layout="wide")

# Style CSS : Design des Cartes et Badges
st.markdown("""
    <style>
    div[data-baseweb="input"] input:placeholder-shown { background-color: #fff3e0 !important; } 
    div[data-baseweb="textarea"] textarea:placeholder-shown { background-color: #fff3e0 !important; }
    .client-card {
        background-color: #ffffff; padding: 20px; border-radius: 12px; margin-bottom: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 15px; font-size: 0.85em;
        background-color: #f0f2f6; color: #333; margin-right: 5px; border: 1px solid #ddd;
    }
    .price-tag { color: #2c3e50; font-weight: bold; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
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
                data_json = json.loads(decoded)
                df_load = pd.DataFrame(data_json)
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
    df_save = df[["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]]
    json_data = df_save.to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta Update", "content": content_b64}
    if sha: data["sha"] = sha
    return requests.put(url, headers=headers, json=data).status_code in [200, 201]

# --- INITIALISATION SESSION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "confirm_delete" not in st.session_state: st.session_state.confirm_delete = False

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols_base)
    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
    
    # --- NAVIGATION (CORRIGÉE : On nettoie l'état avant de changer de page) ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    
    def changer_page(nom_page):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.confirm_delete = False
        st.session_state.page = nom_page
        st.rerun()

    if c1.button("📋 LISTE", use_container_width=True): changer_page("LISTE")
    if c2.button("🗓️ PLANNING", use_container_width=True): changer_page("CALENDRIER")
    if c3.button("➕ NOUVEAU", use_container_width=True): changer_page("FORM")
    if c4.button("✅ CHECK", use_container_width=True): changer_page("CHECK")
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher un nom ou un téléphone...")
        tab1, tab2 = st.tabs(["🚀 PROCHAINES SORTIES", "📂 ARCHIVES"])
        auj = pd.Timestamp(datetime.now().date())

        def afficher_liste(data_df):
            if data_df.empty: st.info("Aucun contact.")
            for idx, row in data_df.iterrows():
                cl = "status-ok" if "🟢" in str(row['Statut']) else "status-attente" if "🟡" in str(row['Statut']) else "status-non"
                st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="display: flex; justify-content: space-between;">
                        <div><b>{row['Nom']} {row['Prénom']}</b><br><small>📅 {row['DateNav']}</small></div>
                        <div class="price-tag">{row['PrixJour']}€</div>
                    </div>
                    <div style="margin-top:10px;">
                        <span class="badge">👤 {row['Passagers']}</span><span class="badge">📞 {row['Téléphone']}</span><span class="badge">✉️ {row['Email']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Gérer {row['Nom']}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx
                    st.session_state.page = "FORM"
                    st.rerun()

        with tab1:
            f_df = df[df['temp_date_obj'] >= auj].sort_values('temp_date_obj')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False) | f_df['Téléphone'].str.contains(search)]
            afficher_liste(f_df)
        with tab2:
            p_df = df[df['temp_date_obj'] < auj].sort_values('temp_date_obj', ascending=False)
            if search: p_df = p_df[p_df['Nom'].str.contains(search, case=False)]
            afficher_liste(p_df)

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        
        with st.form("form_vesta"):
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c1.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_email = c2.text_input("Email", value=init.get("Email", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_prix = st.text_input("Prix (€)", value=init.get("PrixJour", "0"))
            f_pass = st.number_input("Passagers", min_value=1, value=1 if not init.get("Passagers") else int(float(str(init.get("Passagers")).replace(',','.'))))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0 if not init.get("Statut") else ["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut")))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            submit = st.form_submit_button("💾 ENREGISTRER")

        if idx is not None:
            if st.button("🗑️ SUPPRIMER CETTE FICHE", use_container_width=True, type="secondary"):
                st.session_state.confirm_delete = True
            if st.session_state.get("confirm_delete"):
                st.warning("Confirmer la suppression ?")
                if st.button("OUI, EFFACER DEFINITIVEMENT", type="primary"):
                    df = df.drop(index=idx)
                    sauvegarder_data(df, "contacts")
                    changer_page("LISTE")

        if submit:
            try:
                datetime.strptime(f_date.strip(), '%d/%m/%Y') 
                new = {"DateNav": f_date.strip(), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(), "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass), "Téléphone": f_tel, "Email": f_email, "Paye": "Oui" if "🟢" in f_stat else "Non", "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                if sauvegarder_data(df, "contacts"): changer_page("LISTE")
            except: st.error("Format date invalide")

    # --- PAGE PLANNING ---
    elif st.session_state.page == "CALENDRIER":
        st.title("🗓️ Planning")
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        m_sel = st.selectbox("Mois", mois_fr, index=datetime.now().month-1)
        m_idx = mois_fr.index(m_sel) + 1
        y_sel = datetime.now().year
        cal = calendar.monthcalendar(y_sel, m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{day:02d}/{m_idx:02d}/{y_sel}"
                    occ = df[(df['DateNav'] == d_str) & (df['Statut'] == "🟢 OK")]
                    txt = f"🟢 {day}" if not occ.empty else str(day)
                    if cols[i].button(txt, key=f"cal_{d_str}", use_container_width=True):
                        for _, r in occ.iterrows(): st.info(f"⚓ {r['Nom']} ({r['Passagers']} pers.)")

    # --- PAGE CHECK ---
    elif st.session_state.page == "CHECK":
        st.title("✅ Checklist")
        for item in ["Vannes", "Niveaux", "Gilets", "Briefing"]: st.checkbox(item)
            













































