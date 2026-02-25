import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
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
    data = {"message": "Vesta: Planning & Passagers", "content": content_b64}
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
    # AJOUT DE LA COLONNE "Passagers"
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique", "Paye", "PrixJour", "Passagers"]
    df = charger_data("contacts", cols)

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
        c_search, c_view = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher...")
        with c_view: vue_temps = st.selectbox("Vue :", ["Prochaines Nav", "Archives", "Tout"])
        
        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        
        if search: filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False)]
        
        for idx, row in filt_df.sort_values('temp_date').iterrows():
            stat = row['Statut'] if row['Statut'] else "🟡 Attente"
            bg = "#c8e6c9" if "🟢" in stat else "#fff9c4" if "🟡" in stat else "#ffcdd2"
            color_p = "#d32f2f" if row['Paye'] != "Oui" else "#1b5e20"
            
            st.markdown(f"""
            <div style="background-color:{bg}; padding:10px; border-radius:10px; border:1px solid #333; margin-bottom:5px; color:black;">
                <b>📅 {row['DateNav']}</b> — {row['Nom']} ({row['Passagers']} pers.) <br>
                <span style="color:{color_p}; font-weight:bold;">💰 {row['PrixJour']}€ - {'PAID' if row['Paye'] == 'Oui' else 'A PAYER'}</span> | Statut: {stat}
            </div>
            """, unsafe_allow_html=True)
            c_ed, c_del = st.columns(2)
            if c_ed.button("✏️ Modifier", key=f"e_{idx}"): st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            if c_del.button("🗑️ Supprimer", key=f"d_{idx}"): df = df.drop(idx); sauvegarder_data(df, "contacts"); st.rerun()

    # --- PAGE PLANNING (LE NOUVEAU CALENDRIER) ---
    elif st.session_state.page == "CALENDRIER":
        st.subheader("🗓️ Planning d'Occupation")
        
        # Choix du mois
        now = datetime.now()
        c_m, c_y = st.columns(2)
        m_sel = c_m.selectbox("Mois", range(1, 13), index=now.month-1)
        y_sel = c_y.selectbox("Année", [2025, 2026], index=0)
        
        cal = calendar.monthcalendar(y_sel, m_sel)
        jours_noms = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        
        # Préparation des données
        df['temp_date'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
        
        # Affichage du calendrier
        cols_cal = st.columns(7)
        for i, nom in enumerate(jours_noms):
            color = "#ff9800" if i >= 5 else "#555" # Orange pour WE
            cols_cal[i].markdown(f"<div style='text-align:center; font-weight:bold; color:{color}'>{nom}</div>", unsafe_allow_html=True)
        
        for week in cal:
            cols_week = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols_week[i].write("")
                else:
                    date_str = f"{day:02d}/{m_sel:02d}/{y_sel}"
                    # Recherche d'occupation pour ce jour
                    occ = df[(df['DateNav'] == date_str) & (df['Statut'] == "🟢 OK")]
                    
                    bg_day = "#e3f2fd" if i >= 5 else "#f5f5f5" # Bleu clair pour WE
                    txt_occ = ""
                    if not occ.empty:
                        bg_day = "#4caf50" # Vert si occupé
                        txt_occ = f"<br><span style='font-size:0.8em; color:white;'>👤 {occ.iloc[0]['Nom']}<br>👥 {occ.iloc[0]['Passagers']}p.</span>"
                    
                    cols_week[i].markdown(f"""
                    <div style="background-color:{bg_day}; height:80px; border:1px solid #ddd; border-radius:5px; padding:5px; color:black; text-align:center;">
                        <b>{day}</b>{txt_occ}
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        # Récap Finances rapide
        df['Total'] = pd.to_numeric(df['PrixJour'], errors='coerce').fillna(0)
        enc = df[(df['Statut'] == "🟢 OK") & (df['Paye'] == "Oui")]['Total'].sum()
        st.metric("Total Encaissé (OK)", f"{int(enc)} €")

    # --- PAGE FORMULAIRE (AVEC PASSAGERS) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("f"):
            c1, c2 = st.columns(2)
            f_date = c1.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_pass = c1.number_input("Nombre de Passagers (Total)", value=int(init.get("Passagers", 1)) if str(init.get("Passagers")).isdigit() else 1)
            f_prix = c1.text_input("Forfait Global (€)", value=str(init.get("PrixJour", "0")))
            f_stat = c1.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
            
            f_nom = c2.text_input("Nom", value=init.get("Nom", ""))
            f_tel = c2.text_input("Tél", value=init.get("Téléphone", ""))
            f_paye = st.checkbox("Payé ✅", value=(init.get("Paye") == "Oui"))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("SAUVEGARDER"):
                new = {"DateNav": f_date, "Jours": "1", "PrixJour": f_prix, "Statut": f_stat, "Nom": f_nom, "Paye": "Oui" if f_paye else "Non", "Téléphone": f_tel, "Passagers": str(f_pass), "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()

    # --- PAGE CHECKLIST ---
    elif st.session_state.page == "CHECK":
        st.subheader("Check-list")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Ajouter tâche")
        if st.button("Ajouter"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            if st.button(f"✅ {r['Tâche']}", key=f"c_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()

            






















