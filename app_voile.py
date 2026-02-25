import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Totale", layout="wide")

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
    data = {"message": "Vesta: Full Restore + Planning", "content": content_b64}
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

    # --- PAGE LISTE (RESTAURÉE) ---
    if st.session_state.page == "LISTE":
        c_search, c_view = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher un nom...")
        with c_view: vue_temps = st.selectbox("Période :", ["🚀 Prochaines Navigations", "📜 Archives", "🌍 Tout voir"])
        
        # Retour des boutons de statuts
        opts_stat = ["🟢 OK", "🟡 Attente", "🔴 Pas OK"]
        f_statut = st.multiselect("Filtrer statuts :", opts_stat, default=opts_stat)

        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        
        filt_df = filt_df[filt_df['Statut'].isin(f_statut)]
        
        if vue_temps == "🚀 Prochaines Navigations":
            filt_df = filt_df[(filt_df['temp_date'] >= today) | (filt_df['temp_date'].isna())]
        elif vue_temps == "📜 Archives":
            filt_df = filt_df[filt_df['temp_date'] < today]

        for idx, row in filt_df.sort_values('temp_date').iterrows():
            stat = row['Statut'] if row['Statut'] else "🟡 Attente"
            bg = "#c8e6c9" if "🟢" in stat else "#fff9c4" if "🟡" in stat else "#ffcdd2"
            color_p = "#d32f2f" if row['Paye'] != "Oui" else "#1b5e20"
            pay_txt = "⏳ À PAYER" if row['Paye'] != "Oui" else "✅ PAYÉ"
            
            st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom:10px; color:black;">
                <div style="display: flex; justify-content: space-between; font-weight:bold;">
                    <span>📅 {row['DateNav']} ({row['Jours']}j)</span>
                    <span style="background: white; padding: 2px 8px; border-radius: 5px; border: 1px solid black;">{stat}</span>
                </div>
                <div style="font-size:1.3em; margin-top:8px;">👤 <b>{row['Nom']}</b> {row['Prénom']}</div>
                <div style="margin-top:8px; font-weight:bold; color:{color_p};">💰 FORFAIT : {row['PrixJour']}€ — {pay_txt} ({row['Passagers']} pers.)</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_ed, c_del, c_ex = st.columns(3)
            if c_ed.button("✏️ Modifier", key=f"e_{idx}", use_container_width=True): 
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            if c_del.button("🗑️ Supprimer", key=f"d_{idx}", use_container_width=True): 
                df = df.drop(idx); sauvegarder_data(df, "contacts"); st.rerun()
            with c_ex:
                with st.expander("📝 Détails"):
                    st.write(f"📞 {row['Téléphone']} | 📧 {row['Email']}")
                    st.write(f"**Motif :** {row['Cause']}")
                    st.write(f"**Demande :** {row['Demande']}")

    # --- PAGE PLANNING (AMÉLIORÉE) ---
    elif st.session_state.page == "CALENDRIER":
        st.subheader("🗓️ Planning d'Occupation")
        c_m, c_y = st.columns(2)
        m_sel = c_m.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
        y_sel = c_y.selectbox("Année", [2025, 2026], index=0)
        
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
                    date_str = f"{day:02d}/{m_sel:02d}/{y_sel}"
                    occ = df[(df['DateNav'] == date_str) & (df['Statut'] == "🟢 OK")]
                    bg_day = "#e3f2fd" if i >= 5 else "#f5f5f5"
                    txt = ""
                    if not occ.empty:
                        bg_day = "#4caf50"
                        txt = f"<br><span style='font-size:0.7em; color:white;'><b>{occ.iloc[0]['Nom']}</b><br>👥 {occ.iloc[0]['Passagers']}p.</span>"
                    cols_week[i].markdown(f"<div style='background-color:{bg_day}; height:90px; border:1px solid #ddd; border-radius:5px; padding:5px; color:black; text-align:center;'><b>{day}</b>{txt}</div>", unsafe_allow_html=True)

    # --- PAGE FORMULAIRE (COMPLET RESTAURÉ) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("f"):
            c1, c2 = st.columns(2)
            f_date = c1.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_pass = c1.number_input("Nombre de Passagers", value=int(init.get("Passagers", 1)) if str(init.get("Passagers")).isdigit() else 1)
            f_prix = c1.text_input("Forfait Global (€)", value=str(init.get("PrixJour", "0")))
            f_stat = c1.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente") if init.get("Statut") in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else "🟡 Attente"))
            
            f_nom = c2.text_input("Nom", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c2.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_ema = c2.text_input("Email", value=init.get("Email", ""))
            
            f_paye = st.checkbox("✅ MARQUER COMME PAYÉ", value=(init.get("Paye") == "Oui"))
            f_cau = st.text_input("Motif Statut (Cause)", value=init.get("Cause", ""))
            f_dem = st.text_area("Détails demande", value=init.get("Demande", ""))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new = {"DateNav": f_date, "Jours": "1", "PrixJour": f_prix, "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Paye": "Oui" if f_paye else "Non", "Téléphone": f_tel, "Email": f_ema, "Passagers": str(f_pass), "Cause": f_cau, "Demande": f_dem, "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()

    # --- PAGE CHECKLIST ---
    elif st.session_state.page == "CHECK":
        st.subheader("Check-list")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Ajouter tâche")
        if st.button("OK"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            if st.button(f"✅ {r['Tâche']}", key=f"c_{i}", use_container_width=True):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()

            























