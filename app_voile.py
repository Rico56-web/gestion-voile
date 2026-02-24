
import streamlit as st
import pandas as pd
import json
import base64
import requests

# Configuration
st.set_page_config(page_title="Vesta Nav Manager", layout="wide")

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
    data = {"message": "Update data", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- INITIALISATION SESSION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "onglet_actuel" not in st.session_state:
    st.session_state.onglet_actuel = "LISTE"

# --- AUTHENTIFICATION ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code d'accès", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    # --- STRUCTURE DES DONNÉES ---
    cols = ["Nom", "Prénom", "Téléphone", "Email", "Rôle", "Statut", "DateNav", "Motif", "Demande", "Historique"]
    df_contacts = charger_data("contacts", cols)
    # Réparation automatique si colonnes manquantes
    for c in cols:
        if c not in df_contacts.columns: df_contacts[c] = ""

    # --- BARRE DE NAVIGATION (BOUTONS) ---
    c_nav1, c_nav2, c_nav3 = st.columns(3)
    if c_nav1.button("👥 LISTE DES DEMANDES", use_container_width=True):
        st.session_state.onglet_actuel = "LISTE"
        st.rerun()
    if c_nav2.button("✅ CHECK-LIST", use_container_width=True):
        st.session_state.onglet_actuel = "CHECK"
        st.rerun()
    if c_nav3.button("➕ NOUVELLE DEMANDE", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        if "edit_data" in st.session_state: del st.session_state.edit_data
        st.session_state.onglet_actuel = "FORM"
        st.rerun()

    # --- ONGLET 1 : LISTE ---
    if st.session_state.onglet_actuel == "LISTE":
        st.subheader("Tableau de Bord des Navigations")
        search = st.text_input("🔍 Rechercher...")
        
        filt = df_contacts.copy()
        if search:
            filt = filt[(filt['Nom'].str.contains(search, case=False)) | (filt['Prénom'].str.contains(search, case=False))]

        for idx, row in filt.iterrows():
            # Couleur selon statut
            bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
            
            st.markdown(f"""
            <div style="background-color:{bg}; padding:12px; border-radius:10px; border:1px solid #999; margin-top:10px;">
                <h3 style="margin:0; color:black;">{row['Statut']} {row['Prénom']} {row['Nom']}</h3>
                <p style="margin:0; color:black;">📅 <b>Date : {row['DateNav']}</b> | 👤 {row['Rôle']}</p>
                <p style="margin:0; color:#444; font-style:italic;">{row['Motif']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                t_url = f"tel:{row['Téléphone']}".replace(" ", "")
                st.markdown(f'<a href="{t_url}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:8px; border-radius:5px;">📞 Appel</button></a>', unsafe_allow_html=True)
            with c2:
                m_url = f"mailto:{row['Email']}"
                st.markdown(f'<a href="{m_url}"><button style="width:100%; background:#1565c0; color:white; border:none; padding:8px; border-radius:5px;">📧 Email</button></a>', unsafe_allow_html=True)
            with c3:
                if st.button("✏️ Modifier", key=f"btn_ed_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx
                    st.session_state.edit_data = row.to_dict()
                    st.session_state.onglet_actuel = "FORM"
                    st.rerun()
            with c4:
                if st.button("🗑️ Supprimer", key=f"btn_del_{idx}", use_container_width=True):
                    df_contacts = df_contacts.drop(idx)
                    sauvegarder_data(df_contacts, "contacts")
                    st.rerun()
            
            with st.expander("Détails de la demande & Historique"):
                st.write("**📝 Demande complète :**", row['Demande'])
                st.write("**📜 Historique Skipper :**", row['Historique'])

    # --- ONGLET 2 : CHECK-LIST ---
    elif st.session_state.onglet_actuel == "CHECK":
        st.subheader("Check-list Technique")
        df_check = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Ajouter une tâche")
        if st.button("Ajouter"):
            if nt:
                df_check = pd.concat([df_check, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
                sauvegarder_data(df_check, "checklist")
                st.rerun()
        for i, r in df_check.iterrows():
            col1, col2 = st.columns([4,1])
            col1.write(f"• {r['Tâche']}")
            if col2.button("Fait", key=f"done_{i}"):
                df_check = df_check.drop(i)
                sauvegarder_data(df_check, "checklist")
                st.rerun()

    # --- ONGLET 3 : FORMULAIRE ---
    elif st.session_state.onglet_actuel == "FORM":
        is_edit = "edit_idx" in st.session_state
        st.subheader("📝 " + ("Modifier la fiche" if is_edit else "Nouvelle Demande"))
        
        # Pré-remplissage
        init = st.session_state.get("edit_data", {c: "" for c in cols})
        if not init.get("Statut"): init["Statut"] = "🟡 Attente"

        with st.form("form_val"):
            c_a, c_b = st.columns(2)
            with c_a:
                f_nom = st.text_input("Nom", value=init["Nom"])
                f_pre = st.text_input("Prénom", value=init["Prénom"])
                f_dat = st.text_input("Date de navigation (ex: 15/08/2026)", value=init["DateNav"])
            with c_b:
                f_tel = st.text_input("Téléphone", value=init["Téléphone"])
                f_ema = st.text_input("Email", value=init["Email"])
                f_sta = st.selectbox("Statut de la demande", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]))
            
            f_mot = st.text_input("Cause/Motif du statut (ex: Bateau complet, Dossier validé...)", value=init["Motif"])
            f_rol = st.selectbox("Rôle", ["Équipier", "Skipper", "Maintenance", "Invité"], index=0)
            f_dem = st.text_area("Détails de la demande", value=init["Demande"])
            f_his = st.text_area("Historique / Notes privées", value=init["Historique"])
            
            # Style du bouton SAUVEGARDER
            st.markdown("""<style> div.stButton > button { background-color: #002b5c !important; color: white !important; font-weight: bold !important; height: 3em !important; width: 100% !important; border-radius: 10px !important; } </style>""", unsafe_allow_html=True)
            
            if st.form_submit_button("💾 SAUVEGARDER ET RETOURNER À LA LISTE"):
                new_d = {"Nom":f_nom,"Prénom":f_pre,"Téléphone":f_tel,"Email":f_ema,"Rôle":f_rol,"Statut":f_sta,"DateNav":f_dat,"Motif":f_mot,"Demande":f_dem,"Historique":f_his}
                
                if is_edit:
                    df_contacts.iloc[st.session_state.edit_idx] = new_d
                    del st.session_state.edit_idx
                    del st.session_state.edit_data
                else:
                    df_contacts = pd.concat([df_contacts, pd.DataFrame([new_d])], ignore_index=True)
                
                sauvegarder_data(df_contacts, "contacts")
                st.session_state.onglet_actuel = "LISTE"
                st.rerun()

