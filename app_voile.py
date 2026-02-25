import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Planning", layout="wide")

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
            return pd.DataFrame(json.loads(decoded))
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
    data = {"message": "Update Vesta", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "LISTE"

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique"]
    df = charger_data("contacts", cols)
    for c in cols:
        if c not in df.columns: df[c] = ""

    # --- BARRE DE NAVIGATION (MAINTENANT 4 BOUTONS) ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True):
        st.session_state.page = "LISTE"
        st.rerun()
    if c2.button("📅 CALENDRIER", use_container_width=True):
        st.session_state.page = "CALENDRIER"
        st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"
        st.rerun()
    if c4.button("✅ CHECK", use_container_width=True):
        st.session_state.page = "CHECK"
        st.rerun()
    st.markdown("---")

    # --- PAGE CALENDRIER PRÉVISIONNEL ---
    if st.session_state.page == "CALENDRIER":
        st.subheader("📅 Calendrier Prévisionnel d'Occupation")
        
        # Préparation des données
        df['temp_date'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
        df_ok = df[df['Statut'] == "🟢 OK"].copy()
        
        # On crée une liste des 6 prochains mois
        now = datetime.now()
        for i in range(6):
            target_date = now.replace(day=1)
            # Logique pour avancer les mois
            m = (now.month + i - 1) % 12 + 1
            y = now.year + (now.month + i - 1) // 12
            month_name = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"][m-1]
            
            # Filtrer les nav du mois
            month_navs = df_ok[(df_ok['temp_date'].dt.month == m) & (df_ok['temp_date'].dt.year == y)]
            total_jours = sum(pd.to_numeric(month_navs['Jours'], errors='coerce').fillna(0))
            
            st.write(f"### {month_name} {y}")
            col_info, col_bar = st.columns([1, 3])
            col_info.write(f"**{int(total_jours)} jours** occupés")
            
            # Barre de progression (sur une base de 30 jours)
            progress = min(total_jours / 30, 1.0)
            col_bar.progress(progress)
            
            if not month_navs.empty:
                with st.expander(f"Voir le détail de {month_name}"):
                    for _, r in month_navs.sort_values('temp_date').iterrows():
                        st.write(f"• **{r['DateNav']}** : {r['Prénom']} {r['Nom']} ({r['Jours']}j)")
            st.markdown("---")

    # --- PAGE LISTE ---
    elif st.session_state.page == "LISTE":
        st.subheader("Planning Vesta")
        c_p, c_t = st.columns(2)
        with c_p:
            vue_temps = st.selectbox("Période :", ["🚀 Prochaines Navigations", "📜 Archives", "🌍 Tout voir"])
        with c_t:
            tri_mode = st.selectbox("Trier par :", ["📅 Date", "🔤 Nom"])

        options_statut = ["🟢 OK", "🟡 Attente", "🔴 Pas OK"]
        f_statut = st.multiselect("Statuts à afficher :", options_statut, default=options_statut)
        
        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        filt_df = filt_df[filt_df['Statut'].isin(f_statut)]
        if vue_temps == "🚀 Prochaines Navigations":
            filt_df = filt_df[(filt_df['temp_date'] >= today) | (filt_df['temp_date'].isna())]
        elif vue_temps == "📜 Archives":
            filt_df = filt_df[filt_df['temp_date'] < today]

        if tri_mode == "📅 Date":
            ordre = True if vue_temps != "📜 Archives" else False
            filt_df = filt_df.sort_values(by="temp_date", ascending=ordre, na_position='last')
        else:
            filt_df = filt_df.sort_values(by="Nom")

        if filt_df.empty:
            st.warning("Aucun résultat.")
        else:
            for idx, row in filt_df.iterrows():
                bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
                jours_txt = f"({row['Jours']}j)" if row['Jours'] and str(row['Jours']) != "0" else ""
                st.markdown(f'<div style="background-color:{bg}; padding:12px; border-radius:10px; border:1px solid #999; margin-bottom:8px; color:black;"><b>📅 {row["DateNav"]} {jours_txt}</b> - {row["Statut"]}<br><span style="font-size:1.2em;">👤 <b>{row["Nom"]}</b> {row["Prénom"]}</span></div>', unsafe_allow_html=True)
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
                        st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
                with b2:
                    if st.button("🗑️ Suppr.", key=f"del_{idx}", use_container_width=True):
                        df = df.drop(idx); sauvegarder_data(df, "contacts"); st.rerun()
                with b3:
                    with st.expander("Infos"):
                        st.write(f"📞 {row['Téléphone']}\n📧 {row['Email']}\n💬 {row['Cause']}")

    # --- PAGE FORMULAIRE (Inchangée) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("form_nav"):
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
                f_jours = st.number_input("Nombre de jours", min_value=0, value=int(init.get("Jours", 0)) if init.get("Jours") else 0)
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            with c2:
                f_nom = st.text_input("Nom", value=init.get("Nom", ""))
                f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
                f_cau = st.text_input("Motif Statut", value=init.get("Cause", ""))
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_ema = st.text_input("Email", value=init.get("Email", ""))
            f_dem = st.text_area("Précisions", value=init.get("Demande", ""))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = {"DateNav": f_date, "Jours": str(f_jours), "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Téléphone": f_tel, "Email": f_ema, "Cause": f_cau, "Demande": f_dem, "Historique": f_his}
                if idx is not None: df.loc[idx] = new_row
                else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()

    # --- PAGE CHECKLIST (Inchangée) ---
    elif st.session_state.page == "CHECK":
        st.subheader("Check-list")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Nouvelle tâche")
        if st.button("Ajouter"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            c_a, c_b = st.columns([5,1])
            c_a.write(f"• {r['Tâche']}")
            if c_b.button("Fait", key=f"c_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()


            








