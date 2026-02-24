import streamlit as st
import pandas as pd
import json
import base64
import requests

# Configuration de la page
st.set_page_config(page_title="Vesta Gestion", layout="wide")

# --- FONCTIONS DE SAUVEGARDE GITHUB ---
def charger_donnees_github(nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = response.json()
        decoded_content = base64.b64decode(content['content']).decode('utf-8')
        return pd.DataFrame(json.loads(decoded_content))
    else:
        return pd.DataFrame(columns=["Nom", "Prénom", "Téléphone", "Rôle"])

def sauvegarder_donnees_github(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    
    # Récupérer le SHA du fichier s'il existe (nécessaire pour modifier sur GitHub)
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    json_data = df.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": f"Mise à jour de {nom_fichier}",
        "content": content_b64
    }
    if sha:
        data["sha"] = sha
        
    requests.put(url, headers=headers, json=data)

# --- APPLICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Code d'accès", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Code incorrect")
else:
    st.title("⚓ Gestion de l'équipage - Vesta")
    
    # Chargement
    df_contacts = charger_donnees_github("contacts")

    tab1, tab2 = st.tabs(["Liste des contacts", "Ajouter un contact"])

    with tab1:
        st.subheader("Membres enregistrés")
        st.dataframe(df_contacts, use_container_width=True)

    with tab2:
        with st.form("nouveau_contact", clear_on_submit=True):
            nom = st.text_input("Nom")
            prenom = st.text_input("Prénom")
            tel = st.text_input("Téléphone")
            role = st.selectbox("Rôle", ["Skipper", "Équipier", "Propriétaire", "Maintenance"])
            
            if st.form_submit_button("Enregistrer"):
                if nom and prenom:
                    # Vérifier si le contact existe déjà
                    existe_deja = not df_contacts[(df_contacts['Nom'] == nom) & (df_contacts['Prénom'] == prenom)].empty
                    
                    if existe_deja:
                        st.warning(f"Le contact {prenom} {nom} existe déjà dans la liste.")
                    else:
                        nouveau = pd.DataFrame([{"Nom": nom, "Prénom": prenom, "Téléphone": tel, "Rôle": role}])
                        df_contacts = pd.concat([df_contacts, nouveau], ignore_index=True)
                        sauvegarder_donnees_github(df_contacts, "contacts")
                        st.success(f"Contact {prenom} {nom} enregistré !")
                        st.rerun()
                else:
                    st.error("Veuillez remplir au moins le nom et le prénom.")

