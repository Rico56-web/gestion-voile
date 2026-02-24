import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

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
    data = {"message": f"Update {nom_fichier}", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- AUTHENTIFICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code d'accès Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    # --- CHARGEMENT DES DONNÉES ---
    # On ajoute 'Statut' et 'Demande' aux colonnes
    cols_contacts = ["Nom", "Prénom", "Téléphone", "Email", "Rôle", "Statut", "Demande", "Historique"]
    df_contacts = charger_data("contacts", cols_contacts)
    df_check = charger_data("checklist", ["Tâche", "Statut"])

    # --- MENU PRINCIPAL ---
    tabs = st.tabs(["📅 Demandes de Navigation", "✅ Check-list", "⚙️ Ajouter/Modifier"])

    # --- ONGLET 1 : GESTION DES DEMANDES ---
    with tabs[0]:
        st.subheader("Tableau de bord des équipiers")
        
        # Filtres rapides
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search = st.text_input("🔍 Rechercher un nom...")
        with col_f2:
            filtre_statut = st.multiselect("Filtrer par statut", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])

        # Application des filtres
        filt = df_contacts.copy()
        if search:
            filt = filt[(filt['Nom'].str.contains(search, case=False)) | (filt['Prénom'].str.contains(search, case=False))]
        filt = filt[filt['Statut'].isin(filtre_statut)]

        for idx, row in filt.iterrows():
            # Couleur selon statut
            color = "#c8e6c9" if "🟢" in row['Statut'] else "#fff9c4" if "🟡" in row['Statut'] else "#ffcdd2"
            
            with st.container():
                st.markdown(f"""
                <div style="background-color:{color}; padding:15px; border-radius:10px; border:1px solid #ddd; margin-bottom:10px;">
                    <h3 style="margin:0; color:black;">{row['Statut']} {row['Prénom']} {row['Nom']}</h3>
                    <p style="margin:5px 0; color:black;"><b>Rôle :</b> {row['Rôle']} | <b>📞 :</b> {row['Téléphone']} | <b>📧 :</b> {row['Email']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("Voir détails et Historique"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write("**📝 Demande actuelle :**")
                        st.info(row.get('Demande', 'Aucune demande notée'))
                    with c2:
                        st.write("**📜 Historique / Notes :**")
                        st.write(row.get('Historique', 'Pas d\'historique'))
                    
                    # Actions rapides
                    ca, cb, cc = st.columns(3)
                    with ca:
                        t_l = f"tel:{row['Téléphone']}".replace(" ", "")
                        st.markdown(f'<a href="{t_l}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:8px; border-radius:5px;">📞 Appeler</button></a>', unsafe_allow_html=True)
                    with cb:
                        if st.button(f"✏️ Modifier/Statut", key=f"ed_{idx}"):
                            st.session_state.edit_idx = idx
                            st.session_state.edit_data = row.to_dict()
                            st.info("Allez dans l'onglet 'Ajouter/Modifier'")
                    with cc:
                        if st.button(f"🗑️ Supprimer", key=f"del_{idx}"):
                            df_contacts = df_contacts.drop(idx)
                            sauvegarder_data(df_contacts, "contacts")
                            st.rerun()

    # --- ONGLET 2 : CHECK-LIST ---
    with tabs[1]:
        st.subheader("Check-list Technique")
        new_t = st.text_input("Ajouter une tâche")
        if st.button("Ajouter"):
            df_check = pd.concat([df_check, pd.DataFrame([{"Tâche": new_t, "Statut": "À faire"}])], ignore_index=True)
            sauvegarder_data(df_check, "checklist")
            st.rerun()
        
        for i, r in df_check.iterrows():
            col_t, col_b = st.columns([4, 1])
            col_t.write(f"• {r['Tâche']}")
            if col_b.button("Fait", key=f"ch_{i}"):
                df_check = df_check.drop(i)
                sauvegarder_data(df_check, "checklist")
                st.rerun()

    # --- ONGLET 3 : AJOUT / MODIFICATION ---
    with tabs[2]:
        is_edit = "edit_idx" in st.session_state
        st.subheader("📝 " + ("Modifier la demande" if is_edit else "Nouvelle demande de navigation"))
        
        init = st.session_state.get("edit_data", {"Nom":"","Prénom":"","Téléphone":"","Email":"","Rôle":"Équipier","Statut":"🟡 Attente","Demande":"","Historique":""})

        with st.form("form_contact"):
            col1, col2 = st.columns(2)
            with col1:
                f_n = st.text_input("Nom", value=init["Nom"])
                f_p = st.text_input("Prénom", value=init["Prénom"])
                f_s = st.selectbox("Statut Nav", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]))
            with col2:
                f_t = st.text_input("Téléphone", value=init["Téléphone"])
                f_e = st.text_input("Email", value=init["Email"])
                f_r = st.selectbox("Rôle souhaité", ["Équipier", "Skipper", "Proprio", "Maintenance"], index=["Équipier", "Skipper", "Proprio", "Maintenance"].index(init["Rôle"]))
            
            f_dem = st.text_area("Détails de la demande (Dates, trajet...)", value=init["Demande"])
            f_his = st.text_area("Historique / Notes privées", value=init["Historique"])
            
            if st.form_submit_button("Enregistrer sur le Cloud"):
                new_data = {"Nom":f_n, "Prénom":f_p, "Téléphone":f_t, "Email":f_e, "Rôle":f_r, "Statut":f_s, "Demande":f_dem, "Historique":f_his}
                
                if is_edit:
                    df_contacts.iloc[st.session_state.edit_idx] = new_data
                    del st.session_state.edit_idx
                    del st.session_state.edit_data
                else:
                    df_contacts = pd.concat([df_contacts, pd.DataFrame([new_data])], ignore_index=True)
                
                sauvegarder_data(df_contacts, "contacts")
                st.success("Données synchronisées avec GitHub !")
                st.rerun()
        
        if is_edit:
            if st.button("Annuler modification"):
                del st.session_state.edit_idx
                del st.session_state.edit_data
                st.rerun()







