import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# Configuration
st.set_page_config(page_title="Vesta Master", layout="wide")

# --- FONCTIONS GITHUB (Génériques) ---
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
    df_contacts = charger_data("contacts", ["Nom", "Prénom", "Téléphone", "Email", "Rôle", "Commentaire"])
    df_check = charger_data("checklist", ["Tâche", "Statut"])
    df_histo = charger_data("historique", ["Date", "Événement", "Note"])

    # --- MENU PRINCIPAL ---
    tabs = st.tabs(["👥 Annuaire", "✅ Check-list", "📖 Historique", "⚙️ Gestion"])

    # --- ONGLET 1 : ANNUAIRE ---
    with tabs[0]:
        search = st.text_input("🔍 Rechercher...")
        filt = df_contacts[(df_contacts['Nom'].str.contains(search, case=False)) | (df_contacts['Prénom'].str.contains(search, case=False))] if search else df_contacts
        
        for idx, row in filt.iterrows():
            with st.expander(f"👤 {row['Prénom']} {row['Nom']}"):
                col1, col2 = st.columns([2,1])
                with col1:
                    st.write(f"**{row['Rôle']}** | 📞 {row['Téléphone']} | 📧 {row['Email']}")
                    st.info(f"Note : {row['Commentaire']}")
                with col2:
                    t_l = f"tel:{row['Téléphone']}".replace(" ", "")
                    m_l = f"mailto:{row['Email']}"
                    st.markdown(f'<a href="{t_l}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:5px; border-radius:5px;">📞 Appeler</button></a>', unsafe_allow_html=True)
                    st.markdown(f'<div style="margin-top:5px;"><a href="{m_l}"><button style="width:100%; background:#1565c0; color:white; border:none; padding:5px; border-radius:5px;">📧 Email</button></a></div>', unsafe_allow_html=True)

    # --- ONGLET 2 : CHECK-LIST ---
    with tabs[1]:
        st.subheader("État du Navire")
        new_task = st.text_input("Nouvelle tâche (ex: Vérifier niveau huile)")
        if st.button("Ajouter à la liste"):
            df_check = pd.concat([df_check, pd.DataFrame([{"Tâche": new_task, "Statut": "À faire"}])], ignore_index=True)
            sauvegarder_data(df_check, "checklist")
            st.rerun()
        
        for idx, row in df_check.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"• {row['Tâche']}")
            if c2.button("Terminé", key=f"check_{idx}"):
                df_check = df_check.drop(idx)
                sauvegarder_data(df_check, "checklist")
                st.rerun()

    # --- ONGLET 3 : HISTORIQUE ---
    with tabs[2]:
        st.subheader("Journal de bord")
        with st.form("journal"):
            ev = st.text_input("Événement / Sortie")
            nt = st.text_area("Détails")
            if st.form_submit_button("Inscrire au journal"):
                now = datetime.now().strftime("%d/%m/%Y")
                df_histo = pd.concat([df_histo, pd.DataFrame([{"Date": now, "Événement": ev, "Note": nt}])], ignore_index=True)
                sauvegarder_data(df_histo, "historique")
                st.rerun()
        st.table(df_histo.iloc[::-1]) # Affiche du plus récent au plus ancien

    # --- ONGLET 4 : GESTION DES CONTACTS ---
    with tabs[3]:
        st.subheader("Ajouter / Modifier un contact")
        with st.form("add_contact"):
            f_n = st.text_input("Nom")
            f_p = st.text_input("Prénom")
            f_t = st.text_input("Tel")
            f_e = st.text_input("Email")
            f_r = st.selectbox("Rôle", ["Skipper", "Équipier", "Maintenance", "Proprio"])
            f_c = st.text_area("Note")
            if st.form_submit_button("Enregistrer Contact"):
                df_contacts = pd.concat([df_contacts, pd.DataFrame([{"Nom":f_n, "Prénom":f_p, "Téléphone":f_t, "Email":f_e, "Rôle":f_r, "Commentaire":f_c}])], ignore_index=True)
                sauvegarder_data(df_contacts, "contacts")
                st.success("Contact ajouté !")
                st.rerun()






