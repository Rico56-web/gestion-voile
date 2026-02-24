import streamlit as st
import pandas as pd
import json
import base64
import requests

# Configuration
st.set_page_config(page_title="Vesta Gestion Pro", layout="wide")

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
        if decoded.strip():
            return pd.DataFrame(json.loads(decoded))
    return pd.DataFrame(columns=["Nom", "Prénom", "Téléphone", "Email", "Rôle", "Commentaire"])

def sauvegarder_donnees_github(df, nom_fichier):
    df = df.drop_duplicates(subset=['Nom', 'Prénom'], keep='last')
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
    st.title("⚓ Vesta - Annuaire Interactif")
    df = charger_donnees_github("contacts")

    tab1, tab2 = st.tabs(["📋 Liste & Recherche", "➕ Nouveau / Modifier"])

    with tab1:
        # --- BARRE DE RECHERCHE ---
        search = st.text_input("🔍 Rechercher un nom ou un prénom...")
        
        filtered_df = df
        if search:
            filtered_df = df[
                df['Nom'].str.contains(search, case=False, na=False) | 
                df['Prénom'].str.contains(search, case=False, na=False)
            ]

        st.subheader(f"Équipage ({len(filtered_df)})")
        
        if filtered_df.empty:
            st.info("Aucun contact trouvé.")
        else:
            for index, row in filtered_df.iterrows():
                with st.expander(f"👤 {row['Prénom']} {row['Nom']} - {row['Rôle']}"):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    
                    with c1:
                        st.write(f"**📞 Tel:** {row['Téléphone']}")
                        st.write(f"**📧 Email:** {row.get('Email', '-')}")
                        st.write(f"**📝 Note:** {row.get('Commentaire', '')}")
                    
                    with c2:
                        # Liens de contact direct
                        tel_link = f"tel:{row['Téléphone']}".replace(" ", "")
                        mail_link = f"mailto:{row.get('Email', '')}"
                        
                        st.markdown(f"""
                            <a href="{tel_link}" style="text-decoration:none;">
                                <button style="width:100%; padding:10px; background-color:#2e7d32; color:white; border:none; border-radius:5px; cursor:pointer; margin-bottom:5px;">📞 Appeler</button>
                            </a>
                            <a href="{mail_link}" style="text-decoration:none;">
                                <button style="width:100%; padding:10px; background-color:#1565c0; color:white; border:none; border-radius:5px; cursor:pointer;">📧 Envoyer Email</button>
                            </a>
                        """, unsafe_allow_html=True)
                    
                    with c3:
                        if st.button(f"✏️ Modifier", key=f"edit_{index}"):
                            st.session_state.edit_index = index
                            st.session_state.edit_data = row.to_dict()
                            st.success("Prêt pour modification ! Allez dans l'onglet d'ajout.")
                        
                        if st.button(f"🗑️ Supprimer", key=f"del_{index}"):
                            df = df.drop(index)
                            sauvegarder_donnees_github(df, "contacts")
                            st.rerun()

    with tab2:
        title = "Modifier le contact" if "edit_index" in st.session_state else "Ajouter un contact"
        st.subheader(title)
        
        init = st.session_state.get("edit_data", {"Nom":"", "Prénom":"", "Téléphone":"", "Email":"", "Rôle":"Équipier", "Commentaire":""})

        with st.form("form_contact", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                f_nom = st.text_input("Nom", value=init["Nom"])
                f_prenom = st.text_input("Prénom", value=init["Prénom"])
                f_tel = st.text_input("Téléphone", value=init["Téléphone"])
            with col_b:
                f_email = st.text_input("Email", value=init.get("Email", ""))
                f_role = st.selectbox("Rôle", ["Skipper", "Équipier", "Propriétaire", "Maintenance"], 
                                     index=["Skipper", "Équipier", "Propriétaire", "Maintenance"].index(init["Rôle"]))
            
            f_comm = st.text_area("Commentaires", value=init["Commentaire"])
            
            if st.form_submit_button("Enregistrer sur le cloud"):
                new_row = {"Nom": f_nom, "Prénom": f_prenom, "Téléphone": f_tel, "Email": f_email, "Rôle": f_role, "Commentaire": f_comm}
                
                if "edit_index" in st.session_state:
                    df.iloc[st.session_state.edit_index] = new_row
                    del st.session_state.edit_index
                    del st.session_state.edit_data
                else:
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                
                sauvegarder_donnees_github(df, "contacts")
                st.success("Mise à jour réussie !")
                st.rerun()





