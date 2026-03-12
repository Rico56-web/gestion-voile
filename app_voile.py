import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- 2. FONCTIONS TECHNIQUES ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

def safe_get(r, key, default=""):
    val = r.get(key)
    return default if pd.isna(val) or val is None else val

# --- 3. LOGIQUE NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

st.title("⚓ Vesta Skipper 2026")
m1, m2, m3 = st.columns(3)
if m1.button("📋 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.session_state.edit_idx = None; st.rerun()
if m2.button("💰 STATS", use_container_width=True): st.session_state.page = "STATS"; st.rerun()
if m3.button("🔧 MAINT", use_container_width=True): st.session_state.page = "MAINT"; st.rerun()

# --- 4. PAGE CONTACTS ÉPURÉE ---
if st.session_state.page == "CONTACTS":
    
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            
            # Formulaire basé sur votre structure réelle
            c1, c2, c3 = st.columns(3)
            u_date_nav = c1.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_nb_jours = c2.text_input("Nb jours", value=str(safe_get(r, 'NbJours')))
            u_statut = c3.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                    index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))

            c4, c5, c6 = st.columns(3)
            u_nom = c4.text_input("Nom", value=safe_get(r, 'Nom'))
            u_pre = c5.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_tel = c6.text_input("Téléphone", value=safe_get(r, 'Téléphone'))

            c7, c8, c9 = st.columns(3)
            u_email = c7.text_input("Email", value=safe_get(r, 'Email')) # On utilise Email (du fichier)
            u_paye = c8.selectbox("Paiement", ["Pas payé", "Payé"], 
                                  index=1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_prix = c9.text_input("Prix Total (€)", value=str(safe_get(r, 'Prix', '0')))

            u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))

            if st.form_submit_button("💾 ENREGISTRER"):
                # On ne met à jour QUE les colonnes utiles
                df.at[idx, 'DateNav'] = u_date_nav
                df.at[idx, 'NbJours'] = u_nb_jours
                df.at[idx, 'Statut'] = u_statut
                df.at[idx, 'Nom'] = u_nom
                df.at[idx, 'Prénom'] = u_pre
                df.at[idx, 'Téléphone'] = u_tel
                df.at[idx, 'Email'] = u_email
                df.at[idx, 'Paiement'] = u_paye
                df.at[idx, 'Prix'] = float(u_prix.replace(',','.'))
                df.at[idx, 'Société'] = u_soc
                df.at[idx, 'Notes'] = u_notes
                
                # Suppression des anciennes colonnes parasites si elles existent
                cols_to_drop = ['Date Nav', 'Nb jours', 'Heures moteur', 'Milles', 'dt obj', 'dt sort', 'Passager']
                for col in cols_to_drop:
                    if col in df.columns: df.drop(columns=[col], inplace=True)
                
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None
                st.rerun()
    else:
        # Affichage simplifié des fiches (uniquement le bloc Contact)
        for i, r in df.iterrows():
            st.markdown(f"""
            <div style="border:1px solid #1a2a6c; padding:15px; border-radius:10px; margin-bottom:10px;">
                <h3 style="margin:0;">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</h3>
                <p>📞 {safe_get(r, 'Téléphone')} | ✉️ {safe_get(r, 'Email')}</p>
                <p>📅 <b>{safe_get(r, 'DateNav')}</b> | 💰 <b>{safe_get(r, 'Prix')} €</b> | 🏢 {safe_get(r, 'Société')}</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_{i}"):
                st.session_state.edit_idx = i; st.rerun()

elif st.session_state.page == "MAINT":
    st.header("🔧 Bloc Maintenance")
    st.info("C'est ici que nous allons créer le nouveau formulaire pour les Milles et Heures Moteur.")



















































































































































































































































































































































































































