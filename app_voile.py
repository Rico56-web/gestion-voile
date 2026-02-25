import streamlit as st
import pandas as pd
import json
import base64
import requests

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
    cols = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique"]
    df = charger_data("contacts", cols)
    for c in cols:
        if c not in df.columns: df[c] = ""

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if c1.button("📅 LISTE", use_container_width=True):
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
        st.subheader("Tableau de Bord")
        
        # --- NOUVELLES OPTIONS DE TRI ---
        col_sort, col_filt = st.columns(2)
        with col_sort:
            tri = st.selectbox("Trier par :", ["📅 Date de navigation", "🔤 Nom de famille"])
        with col_filt:
            f_statut = st.multiselect("Filtrer par statut :", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])
        
        search = st.text_input("🔍 Rechercher un nom...")
        
        # Application des filtres
        filt_df = df[df['Statut'].isin(f_statut)].copy()
        if search:
            filt_df = filt_df[(filt_df['Nom'].str.contains(search, case=False)) | (filt_df['Prénom'].str.contains(search, case=False))]

        # --- LOGIQUE DE TRI ---
        if tri == "📅 Date de navigation":
            filt_df = filt_df.sort_values(by="DateNav")
        else:
            filt_df = filt_df.sort_values(by="Nom")

        # Affichage
        if filt_df.empty:
            st.info("Aucune navigation enregistrée.")
        else:
            for idx, row in filt_df.iterrows():
                bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
                st.markdown(f"""
                <div style="background-color:{bg}; padding:10px; border-radius:10px; border:1px solid #777; margin-bottom:5px; color:black;">
                    <div style="display: flex; justify-content: space-between; font-weight:bold;">
                        <span>📅 {row['DateNav']}</span>
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
                        # Attention : on cherche l'index original dans df car filt_df est trié
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
                        st.write(f"📧 {row['Email']}")
                        st.write(f"📝 {row['Demande']}")
                        st.write(f"📜 {row['Historique']}")

    # --- PAGE FORMULAIRE (Inchangée mais nécessaire pour le fonctionnement) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Détails Navigation")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        if not init.get("Statut"): init["Statut"] = "🟡 Attente"

        with st.form("form_nav"):
            c_l, c_r = st.columns(2)
            with c_l:
                f_date = st.text_input("Date (ex: 2026-07-14)", value=init["DateNav"])
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]))
                f_cau = st.text_input("Motif", value=init["Cause"])
            with c_r:
                f_nom = st.text_input("Nom", value=init["Nom"])
                f_pre = st.text_input("Prénom", value=init["Prénom"])
                f_tel = st.text_input("Téléphone", value=init["Téléphone"])
            f_ema = st.text_input("Email", value=init["Email"])
            f_dem = st.text_area("Demande", value=init["Demande"])
            f_his = st.text_area("Historique", value=init["Historique"])
            
            st.markdown("""<style> div.stButton > button { background-color: #002b5c !important; color: white !important; width: 100% !important; border-radius: 10px !important; } </style>""", unsafe_allow_html=True)
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = {"DateNav":f_date, "Statut":f_stat, "Nom":f_nom, "Prénom":f_pre, "Téléphone":f_tel, "Email":f_ema, "Cause":f_cau, "Demande":f_dem, "Historique":f_his}
                if idx is not None:
                    df.loc[idx] = new_row
                else:
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df, "contacts")
                st.session_state.page = "LISTE"
                st.rerun()

    # --- PAGE CHECKLIST ---
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
        


