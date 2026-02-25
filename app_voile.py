import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Planning Nav", layout="wide")

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
    json_data = df.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Mise à jour Vesta", "content": content_b64}
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

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if c1.button("📅 PLANNING", use_container_width=True):
        st.session_state.page = "LISTE"
        st.rerun()
    if c2.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"
        st.rerun()
    if c3.button("✅ CHECK-LIST", use_container_width=True):
        st.session_state.page = "CHECK"
        st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        st.subheader("Gestion des navigations")
        
        # --- FILTRES DE TEMPS ET STATUT ---
        col_time, col_filt = st.columns(2)
        with col_time:
            vue_temps = st.selectbox("Afficher :", ["🚀 Prochaines Navigations", "📜 Archives (Passées)", "🌍 Tout voir"])
        with col_filt:
            f_statut = st.multiselect("Filtrer par statut :", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])
        
        search = st.text_input("🔍 Rechercher un nom...")
        
        # Préparation du DataFrame
        filt_df = df.copy()
        
        # Conversion temporaire pour le tri et filtrage de date
        # On essaie de convertir DateNav en format date réel
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], errors='coerce')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Filtrage par Temps
        if vue_temps == "🚀 Prochaines Navigations":
            filt_df = filt_df[filt_df['temp_date'] >= today]
            filt_df = filt_df.sort_values(by="temp_date", ascending=True) # Plus proche en premier
        elif vue_temps == "📜 Archives (Passées)":
            filt_df = filt_df[filt_df['temp_date'] < today]
            filt_df = filt_df.sort_values(by="temp_date", ascending=False) # Plus récent en premier
        else:
            filt_df = filt_df.sort_values(by="temp_date", ascending=True)

        # Filtrage par Statut
        filt_df = filt_df[filt_df['Statut'].isin(f_statut)]
        
        # Recherche textuelle
        if search:
            filt_df = filt_df[(filt_df['Nom'].str.contains(search, case=False)) | (filt_df['Prénom'].str.contains(search, case=False))]

        # Affichage
        if filt_df.empty:
            st.info(f"Aucune navigation dans la catégorie : {vue_temps}")
        else:
            for idx, row in filt_df.iterrows():
                bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
                duree = f"({row['Jours']}j)" if row['Jours'] else ""
                
                st.markdown(f"""
                <div style="background-color:{bg}; padding:10px; border-radius:10px; border:1px solid #777; margin-bottom:5px; color:black;">
                    <div style="display: flex; justify-content: space-between; font-weight:bold;">
                        <span>📅 {row['DateNav']} <small style='color:#333'>{duree}</small></span>
                        <span>{row['Statut']}</span>
                    </div>
                    <div style="font-size:18px;">👤 {row['Prénom']} {row['Nom']}</div>
                    <div style="font-size:14px; font-style:italic;">{row['Cause']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    st.markdown(f'<a href="tel:{row["Téléphone"]}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:8px; border-radius:5px;">📞 Appel</button></a>', unsafe_allow_html=True)
                with b2:
                    if st.button("✏️ Modif", key=f"ed_{idx}", use_container_width=True):
                        st.session_state.edit_idx = idx
                        st.session_state.page = "FORM"
                        st.rerun()
                with b3:
                    if st.button("🗑️ Suppr", key=f"del_{idx}", use_container_width=True):
                        df = df.drop(idx)
                        sauvegarder_data(df, "contacts")
                        st.rerun()
                with b4:
                    with st.expander("Détails"):
                        st.write(f"⏳ **Durée :** {row['Jours']} jour(s)")
                        st.write(f"📧 {row['Email']}")
                        st.write(f"📝 {row['Demande']}")
                        st.write(f"📜 {row['Historique']}")

    # --- PAGE FORMULAIRE (Inchangée) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Navigation")
        if idx is not None:
            init = df.loc[idx].to_dict()
        else:
            init = {c: "" for c in cols}
            init["Statut"] = "🟡 Attente"

        with st.form("form_nav"):
            c_l, c_r = st.columns(2)
            with c_l:
                f_date = st.text_input("Date (AAAA-MM-JJ)", value=init.get("DateNav", ""))
                f_jours = st.number_input("Nombre de jours", min_value=0, value=int(init.get("Jours", 0)) if init.get("Jours") else 0)
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            with c_r:
                f_nom = st.text_input("Nom", value=init.get("Nom", ""))
                f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
                f_cau = st.text_input("Motif", value=init.get("Cause", ""))
            
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_ema = st.text_input("Email", value=init.get("Email", ""))
            f_dem = st.text_area("Demande", value=init.get("Demande", ""))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            
            st.markdown("""<style> div.stButton > button { background-color: #002b5c !important; color: white !important; font-weight: bold !important; width: 100% !important; height: 3em !important; border-radius: 10px !important; } </style>""", unsafe_allow_html=True)
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = {"DateNav": f_date, "Jours": str(f_jours), "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Téléphone": f_tel, "Email": f_ema, "Cause": f_cau, "Demande": f_dem, "Historique": f_his}
                if idx is not None:
                    df.loc[idx] = new_row
                else:
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df, "contacts")
                st.session_state.page = "LISTE"
                st.rerun()

    # --- PAGE CHECKLIST (Inchangée) ---
    elif st.session_state.page == "CHECK":
        st.subheader("Check-list Bateau")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Ajouter une tâche")
        if st.button("Ajouter"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            col1, col2 = st.columns([5,1])
            col1.write(f"• {r['Tâche']}")
            if col2.button("Fait", key=f"done_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()
            

