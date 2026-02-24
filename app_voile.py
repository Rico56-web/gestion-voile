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

# --- AUTHENTIFICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Code d'accès", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    # --- DATA ---
    cols = ["Nom", "Prénom", "Téléphone", "Email", "Rôle", "Statut", "Demande", "Historique"]
    df_contacts = charger_data("contacts", cols)
    for c in cols: 
        if c not in df_contacts.columns: df_contacts[c] = ""

    t1, t2, t3 = st.tabs(["👥 DEMANDES & CONTACTS", "✅ CHECK-LIST", "⚙️ AJOUTER / MODIFIER"])

    with t1:
        st.subheader("Tableau de Bord Navigation")
        search = st.text_input("🔍 Rechercher un nom...")
        
        filt = df_contacts.copy()
        if search:
            filt = filt[(filt['Nom'].str.contains(search, case=False)) | (filt['Prénom'].str.contains(search, case=False))]

        for idx, row in filt.iterrows():
            # Couleur du bandeau
            color = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
            
            with st.container():
                # Affichage du bandeau principal
                st.markdown(f"""
                <div style="background-color:{color}; padding:10px; border-radius:10px; border:1px solid #999; margin-top:10px;">
                    <h3 style="margin:0; color:black;">{row['Statut']} {row['Prénom']} {row['Nom']}</h3>
                    <p style="margin:0; color:#333;"><b>Rôle:</b> {row['Rôle']} | <b>📞:</b> {row['Téléphone']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # --- BOUTONS D'ACTION DIRECTS ---
                col_call, col_mail, col_edit, col_del = st.columns([1,1,1,1])
                
                with col_call:
                    t_url = f"tel:{row['Téléphone']}".replace(" ", "")
                    st.markdown(f'<a href="{t_url}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">📞 APPELER</button></a>', unsafe_allow_html=True)
                
                with col_mail:
                    m_url = f"mailto:{row['Email']}"
                    st.markdown(f'<a href="{m_url}"><button style="width:100%; background:#1565c0; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">📧 EMAIL</button></a>', unsafe_allow_html=True)
                
                with col_edit:
                    if st.button(f"✏️ MODIFIER", key=f"ed_{idx}"):
                        st.session_state.edit_idx = idx
                        st.session_state.edit_data = row.to_dict()
                        st.success("Prêt ! Allez dans le 3ème onglet.")
                
                with col_del:
                    if st.button(f"🗑️ SUPPRIMER", key=f"del_{idx}"):
                        df_contacts = df_contacts.drop(idx)
                        sauvegarder_data(df_contacts, "contacts")
                        st.rerun()
                
                # --- DÉTAILS CACHÉS ---
                with st.expander("📝 Voir la demande et l'historique"):
                    st.write("**Demande :**", row['Demande'])
                    st.write("**Historique :**", row['Historique'])

    with t2:
        st.subheader("Check-list Technique")
        # (Code Check-list simplifié pour rester compact)
        df_check = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Nouvelle tâche")
        if st.button("Ajouter"):
            df_check = pd.concat([df_check, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_check, "checklist"); st.rerun()
        for i, r in df_check.iterrows():
            c1, c2 = st.columns([4,1])
            c1.write(f"• {r['Tâche']}")
            if c2.button("Fait", key=f"ch_{i}"):
                df_check = df_check.drop(i); sauvegarder_data(df_check, "checklist"); st.rerun()

    with t3:
        is_edit = "edit_idx" in st.session_state
        st.subheader("⚙️ " + ("Modifier" if is_edit else "Nouveau Contact"))
        init = st.session_state.get("edit_data", {c: "" for c in cols})
        if not init.get("Statut"): init["Statut"] = "🟡 Attente"
        if not init.get("Rôle"): init["Rôle"] = "Équipier"

        with st.form("f_contact"):
            f_nom = st.text_input("Nom", value=init["Nom"])
            f_pre = st.text_input("Prénom", value=init["Prénom"])
            f_tel = st.text_input("Tel", value=init["Téléphone"])
            f_ema = st.text_input("Email", value=init["Email"])
            f_sta = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]))
            f_rol = st.selectbox("Rôle", ["Équipier", "Skipper", "Proprio", "Maintenance"], index=0)
            f_dem = st.text_area("Demande", value=init["Demande"])
            f_his = st.text_area("Historique", value=init["Historique"])
            
            if st.form_submit_button("SAUVEGARDER"):
                new_d = {"Nom":f_nom,"Prénom":f_pre,"Téléphone":f_tel,"Email":f_ema,"Rôle":f_rol,"Statut":f_sta,"Demande":f_dem,"Historique":f_his}
                if is_edit:
                    df_contacts.iloc[st.session_state.edit_idx] = new_d
                    del st.session_state.edit_idx; del st.session_state.edit_data
                else:
                    df_contacts = pd.concat([df_contacts, pd.DataFrame([new_d])], ignore_index=True)
                sauvegarder_data(df_contacts, "contacts")
                st.rerun()









