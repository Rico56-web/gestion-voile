import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
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
                if col not in df_load.columns: df_load[col] = ""
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
    if 'temp_date_obj' in df_save.columns: df_save = df_save.drop(columns=['temp_date_obj'])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta: Enhanced List & Calendar", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "cal_date_sel" not in st.session_state: st.session_state.cal_date_sel = None

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols)
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

    # --- PAGE LISTE (ENRICHIE) ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher un nom...")
        filt_df = df.copy()
        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        
        for idx, row in filt_df.sort_values('temp_date_obj', ascending=True).iterrows():
            stat = row['Statut'] if row['Statut'] else "🟡 Attente"
            bg = "#c8e6c9" if "🟢" in stat else "#fff9c4" if "🟡" in stat else "#ffcdd2"
            
            # Gestion visuelle du paiement
            est_paye = str(row['Paye']) == "Oui"
            pay_txt = "✅ PAYÉ" if est_paye else "⏳ À PAYER"
            pay_color = "#1b5e20" if est_paye else "#d32f2f" 

            st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom:10px; color:black;">
                <div style="display: flex; justify-content: space-between; font-weight:bold;">
                    <span>📅 {row['DateNav']}</span>
                    <span style="background: white; padding: 2px 8px; border-radius: 5px; border: 1px solid black;">{stat}</span>
                </div>
                <div style="font-size:1.3em; margin-top:8px;">👤 <b>{row['Nom']}</b> {row['Prénom']}</div>
                <div style="margin-top:5px; font-size:1em;">📞 {row['Téléphone']} | 👥 {row['Passagers']} pers.</div>
                <div style="margin-top:8px; font-weight:bold; color:{pay_color};">💰 FORFAIT : {row['PrixJour']}€ — {pay_txt}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_ed, c_del = st.columns(2)
            if c_ed.button("✏️ Modifier / Détails", key=f"e_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            if c_del.button("🗑️ Supprimer la fiche", key=f"d_{idx}", use_container_width=True):
                df = df.drop(idx)
                sauvegarder_data(df, "contacts")
                st.rerun()

    # --- PAGE PLANNING (RESTE IDENTIQUE) ---
    elif st.session_state.page == "CALENDRIER":
        now = datetime.now()
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        c_m, c_y = st.columns(2)
        m_nom = c_m.selectbox("Mois", mois_fr, index=now.month-1)
        m_idx = mois_fr.index(m_nom) + 1
        y_sel = c_y.selectbox("Année", list(range(2024, 2036)), index=list(range(2024, 2036)).index(now.year))
        
        cal = calendar.monthcalendar(y_sel, m_idx)
        jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        cols_h = st.columns(7)
        for i, j in enumerate(jours):
            cols_h[i].markdown(f"<div style='text-align:center; font-weight:bold;'>{j}</div>", unsafe_allow_html=True)
        
        for week in cal:
            cols_w = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{day:02d}/{m_idx:02d}/{y_sel}"
                    t_date = datetime(y_sel, m_idx, day).date()
                    occ = df[(df['temp_date_obj'].dt.date == t_date) & (df['Statut'] == "🟢 OK")]
                    btn_label = f"{day}"
                    color = "secondary"
                    if not occ.empty:
                        color = "primary"
                        btn_label = f"{day} (⚓)"
                    if cols_w[i].button(btn_label, key=f"btn_{d_str}", use_container_width=True, type=color):
                        st.session_state.cal_date_sel = d_str

        if st.session_state.cal_date_sel:
            st.markdown(f"### ⚓ Détails pour le {st.session_state.cal_date_sel}")
            sel_date_obj = pd.to_datetime(st.session_state.cal_date_sel, dayfirst=True).date()
            details = df[(df['temp_date_obj'].dt.date == sel_date_obj) & (df['Statut'] == "🟢 OK")]
            if not details.empty:
                for _, r in details.iterrows():
                    st.info(f"👤 **{r['Nom']} {r['Prénom']}** | 👥 {r['Passagers']} pers. | 📞 {r['Téléphone']} | 💰 {r['PrixJour']}€")
            else: st.write("Libre.")

    # --- PAGE FORMULAIRE (CORRIGÉE) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        
        with st.form("form_contact"):
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nom = st.text_input("Nom", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_pass = st.number_input("Passagers", min_value=1, value=int(init.get("Passagers", 1)) if str(init.get("Passagers")).isdigit() else 1)
            f_prix = st.text_input("Forfait Global (€)", value=str(init.get("PrixJour", "0")))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente") if init.get("Statut") in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else "🟡 Attente"))
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_paye = st.checkbox("Payé ✅", value=(init.get("Paye") == "Oui"))
            f_his = st.text_area("Historique / Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    pd.to_datetime(f_date, dayfirst=True)
                    new = {"DateNav": f_date, "Nom": f_nom, "Prénom": f_pre, "Passagers": str(f_pass), "PrixJour": f_prix, "Statut": f_stat, "Téléphone": f_tel, "Paye": "Oui" if f_paye else "Non", "Historique": f_his}
                    if idx is not None:
                        for key, val in new.items(): df.at[idx, key] = val
                    else:
                        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    st.session_state.page = "LISTE"
                    st.rerun()
                except: st.error("Format de date invalide.")

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

            


























