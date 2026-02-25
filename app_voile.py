import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

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
            # Réparation des colonnes critiques
            for col in colonnes:
                if col not in df_load.columns:
                    df_load[col] = ""
            df_load['Statut'] = df_load['Statut'].replace('', '🟡 Attente').fillna('🟡 Attente')
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
    data = {"message": "Fix Statut Display", "content": content_b64}
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
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique", "Paye", "PrixJour"]
    df = charger_data("contacts", cols)

    # Navigation
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("💰 FINANCES", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher par nom...")
        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        
        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        
        filt_df = filt_df.sort_values(by="temp_date", ascending=True)

        for idx, row in filt_df.iterrows():
            # Sécurité Statut : on s'assure qu'il y a du texte
            current_statut = str(row['Statut']) if row['Statut'] else "🟡 Attente"
            
            # Couleur du bandeau
            bg = "#c8e6c9" if "🟢" in current_statut else "#fff9c4" if "🟡" in current_statut else "#ffcdd2"
            
            # Calcul financier sécurisé
            try:
                total = int(float(str(row['PrixJour']).replace(',','.')) * float(str(row['Jours']).replace(',','.')))
            except: total = 0
            
            # AFFICHAGE FORCE
            st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom:10px; color:black;">
                <div style="display: flex; justify-content: space-between; font-weight:bold;">
                    <span>📅 {row['DateNav']}</span>
                    <span style="background: white; padding: 2px 8px; border-radius: 5px; border: 1px solid black;">{current_statut}</span>
                </div>
                <div style="font-size:1.4em; margin-top:5px;"><b>{row['Nom']}</b> {row['Prénom']}</div>
                <div style="font-size:1.0em; margin-top:5px;">📧 {row['Email']}</div>
                <div style="font-size:1.0em; margin-top:2px;">📞 {row['Téléphone']}</div>
                <div style="margin-top:10px; font-weight:bold;">💰 TOTAL : {total}€ ({'✅ PAYÉ' if row['Paye'] == 'Oui' else '⏳ À PAYER'})</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_ed, c_pa, c_ex = st.columns(3)
            with c_ed:
                if st.button("✏️ Modifier", key=f"e_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            with c_pa:
                if st.button("💰 Encaissé/Non", key=f"p_{idx}", use_container_width=True):
                    df.at[idx, 'Paye'] = "Oui" if row['Paye'] != "Oui" else "Non"
                    sauvegarder_data(df, "contacts"); st.rerun()
            with c_ex:
                with st.expander("Notes"):
                    st.write(f"**Motif Statut :** {row['Cause']}")
                    st.write(f"**Demande :** {row['Demande']}")
                    st.write(f"**Historique :** {row['Historique']}")

    # --- PAGE FORMULAIRE (Le reste du code reste identique pour les finances et le formulaire) ---
    elif st.session_state.page == "CALENDRIER":
        st.subheader("💰 Finances")
        df['J_num'] = pd.to_numeric(df['Jours'], errors='coerce').fillna(0)
        df['P_num'] = pd.to_numeric(df['PrixJour'], errors='coerce').fillna(0)
        df['Total'] = df['J_num'] * df['P_num']
        enc = df[(df['Statut'] == "🟢 OK") & (df['Paye'] == "Oui")]['Total'].sum()
        att = df[df['Statut'] == "🟢 OK"]['Total'].sum()
        st.metric("ENCAISSÉ GLOBAL", f"{int(enc)} €", f"sur {int(att)} €")

    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("f"):
            c1, c2 = st.columns(2)
            f_date = c1.text_input("Date", value=init.get("DateNav", ""))
            f_jours = c1.text_input("Jours", value=str(init.get("Jours", "0")))
            f_prix = c1.text_input("Prix/j", value=str(init.get("PrixJour", "20")))
            f_stat = c1.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_nom = c2.text_input("Nom", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c2.text_input("Tél", value=init.get("Téléphone", ""))
            f_ema = c2.text_input("Email", value=init.get("Email", ""))
            f_paye = st.checkbox("Payé", value=(init.get("Paye") == "Oui"))
            f_cau = st.text_input("Motif Statut", value=init.get("Cause", ""))
            f_dem = st.text_area("Demande", value=init.get("Demande", ""))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            if st.form_submit_button("SAUVEGARDER"):
                new = {"DateNav": f_date, "Jours": f_jours, "PrixJour": f_prix, "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Paye": "Oui" if f_paye else "Non", "Téléphone": f_tel, "Email": f_ema, "Demande": f_dem, "Cause": f_cau, "Historique": f_his}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()

    elif st.session_state.page == "CHECK":
        st.subheader("Check-list")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Ajouter tâche")
        if st.button("OK"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            if st.button(f"✅ {r['Tâche']}", key=f"c_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()

            
















