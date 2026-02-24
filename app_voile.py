import streamlit as st
import pandas as pd
import json
import base64
import requests

# Configuration
st.set_page_config(page_title="Vesta Gestion v2", layout="wide")

# --- FONCTIONS GITHUB ---
def charger_donnees_github(nom_fichier):
   repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        content = res.json()
        decoded = base64.b64decode(content['content']).decode('utf-8')
        # On vérifie si le texte n'est pas vide avant de le lire
        if decoded.strip():
            return pd.DataFrame(json.loads(decoded))
    
    # Si le fichier n'existe pas ou est vide, on renvoie un tableau vide
    return pd.DataFrame(columns=["Nom", "Prénom", "Téléphone", "Rôle", "Commentaire"])
def sauvegarder_donnees_github(df, nom_fichier):
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
    pwd = st.text_input("Code d'accès", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    st.title("⚓ Vesta - Gestion Complète")
    df = charger_donnees_github("contacts")

    tab1, tab2 = st.tabs(["📋 Liste & Actions", "➕ Nouveau Contact"])

    with tab1:
        st.subheader("Équipage et Contacts")
        if df.empty:
            st.info("Aucun contact enregistré.")
        else:
            for index, row in df.iterrows():
                with st.expander(f"👤 {row['Prénom']} {row['Nom']} - {row['Rôle']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Tel:** {row['Téléphone']}")
                        st.write(f"**Note:** {row.get('Commentaire', '')}")
                    with col2:
                        if st.button(f"🗑️ Supprimer", key=f"del_{index}"):
                            df = df.drop(index)
                            sauvegarder_donnees_github(df, "contacts")
                            st.rerun()
                        
                        if st.button(f"✏️ Modifier", key=f"edit_{index}"):
                            st.session_state.edit_index = index
                            st.session_state.edit_data = row.to_dict()
                            st.info("Passez à l'onglet 'Nouveau Contact' pour modifier.")

    with tab2:
        title = "Modifier le contact" if "edit_index" in st.session_state else "Ajouter un contact"
        st.subheader(title)
        
        # Pré-remplissage si modification
        initial_data = st.session_state.get("edit_data", {"Nom":"", "Prénom":"", "Téléphone":"", "Rôle":"Équipier", "Commentaire":""})

        with st.form("form_contact", clear_on_submit=True):
            f_nom = st.text_input("Nom", value=initial_data["Nom"])
            f_prenom = st.text_input("Prénom", value=initial_data["Prénom"])
            f_tel = st.text_input("Téléphone", value=initial_data["Téléphone"])
            f_role = st.selectbox("Rôle", ["Skipper", "Équipier", "Propriétaire", "Maintenance"], 
                                  index=["Skipper", "Équipier", "Propriétaire", "Maintenance"].index(initial_data["Rôle"]))
            f_comm = st.text_area("Commentaires / Notes", value=initial_data["Commentaire"])
            
            submit = st.form_submit_button("Valider l'enregistrement")
            
            if submit:
                new_row = {"Nom": f_nom, "Prénom": f_prenom, "Téléphone": f_tel, "Rôle": f_role, "Commentaire": f_comm}
                
                if "edit_index" in st.session_state:
                    df.iloc[st.session_state.edit_index] = new_row
                    del st.session_state.edit_index
                    del st.session_state.edit_data
                else:
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                sauvegarder_donnees_github(df, "contacts")
                st.success("Données mises à jour !")
                st.rerun()
        
        if "edit_index" in st.session_state:
            if st.button("Annuler la modification"):
                del st.session_state.edit_index
                del st.session_state.edit_data
                st.rerun()



