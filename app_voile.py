import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Planning & Gestion", layout="wide")

# --- FONCTIONS GITHUB ---
def charger_data(nom_fichier, colonnes):
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
                if col not in df_load.columns: df_load[col] = "0" if col == "Passagers" else ""
            return df_load
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    df_save = df.copy()
    if 'temp_date' in df_save.columns: df_save = df_save.drop(columns=['temp_date'])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta: Fixed Date Matching", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique", "Paye", "PrixJour", "Passagers"]
    df = charger_data("contacts", cols)

    # Nettoyage et formatage des dates pour le matching
    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')

    # Navigation
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("🗓️ PLANNING", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher un nom...")
        filt_df = df.copy()
        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        
        for idx, row in filt_df.sort_values('temp_date_obj', ascending=True).iterrows():
            stat = row['Statut'] if row['Statut'] else "🟡 Attente"
            bg = "#c8e6c9" if "🟢" in stat else "#fff9c4" if "🟡" in stat else "#ffcdd2"
            st.markdown(f"""<div style="background-color:{bg}; padding:10px; border-radius:10px; border:1px solid #333; margin-bottom:5px; color:black;">
            <b>📅 {row['DateNav']}</b> - {row['Nom']} {row['Prénom']} ({row['Passagers']} pers.) - <b>{stat}</b></div>""", unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"e_{idx}"):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    # --- PAGE PLANNING ---
    elif st.session_state.page == "CALENDRIER":
        now = datetime.now()
        mois_noms_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        st.subheader("🗓️ Planning d'Occupation")
        
        c_m, c_y = st.columns(2)
        m_nom_sel = c_m.selectbox("Mois", mois_noms_fr, index=now.month-1)
        m_sel = mois_noms_fr.index(m_nom_sel) + 1
        ans_dispo = list(range(2024, 2036))
        y_sel = c_y.selectbox("Année", ans_dispo, index=ans_dispo.index(now.year))
        
        st.markdown(f"### 📅 {m_nom_sel} {y_sel}")
        cal = calendar.monthcalendar(y_sel, m_sel)
        jours_noms = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        
        cols_cal = st.columns(7)
        for i, nom in enumerate(jours_noms):
            color = "#ff9800" if i >= 5 else "#555"
            cols_cal[i].markdown(f"<div style='text-align:center; font-weight:bold; color:{color}'>{nom}</div>", unsafe_allow_html=True)
        
        for week in cal:
            cols_week = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: cols_week[i].write("")
                else:
                    # On compare via l'objet date pour être sûr de ne pas rater un match à cause d'un '0' manquant
                    target_date = datetime(y_sel, m_sel, day).date()
                    occ = df[(df['temp_date_obj'].dt.date == target_date) & (df['Statut'] == "🟢 OK")]
                    
                    bg_day = "#e3f2fd" if i >= 5 else "#f5f5f5"
                    txt = ""
                    if not occ.empty:
                        bg_day = "#4caf50"
                        # On peut afficher plusieurs noms si doublon
                        noms = ", ".join(occ['Nom'].tolist())
                        total_p = sum(pd.to_numeric(occ['Passagers'], errors='coerce').fillna(0))
                        txt = f"<br><span style='font-size:0.7em; color:white;'><b>{noms}</b><br>👥 {int(total_p)}p.</span>"
                    
                    cols_week[i].markdown(f"<div style='background-color:{bg_day}; height:90px; border:1px solid #ddd; border-radius:5px; padding:5px; color:black; text-align:center;'><b>{day}</b>{txt}</div>", unsafe_allow_html=True)

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("f"):
            f_date = st.text_input("Date (EXEMPLE: 15/03/2026)", value=init.get("DateNav", ""))
            f_nom = st.text_input("Nom", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_pass = st.number_input("Passagers", min_value=1, value=int(init.get("Passagers", 1)) if str(init.get("Passagers")).isdigit() else 1)
            f_prix = st.text_input("Forfait (€)", value=str(init.get("PrixJour", "0")))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
            f_paye = st.checkbox("Payé ✅", value=(init.get("Paye") == "Oui"))
            
            if st.form_submit_button("SAUVEGARDER"):
                # Vérification rapide du format date
                try:
                    pd.to_datetime(f_date, dayfirst=True)
                    new = {"DateNav": f_date, "Jours": "1", "PrixJour": f_prix, "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Paye": "Oui" if f_paye else "Non", "Passagers": str(f_pass)}
                    if idx is not None: df.loc[idx] = new
                    else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()
                except:
                    st.error("⚠️ Format de date invalide ! Utilisez JJ/MM/AAAA (ex: 15/03/2026)")

            
























