
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# Sécurité Accès
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("⚓ VESTA SKIPPER 2026")
    pw = st.text_input("Code d'accès :", type="password")
    if st.button("ACCÉDER"):
        if pw == "SKIPPER2026":
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

# --- 2. FONCTIONS (LE MOTEUR) ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            data = json.loads(content)
            return pd.DataFrame(data)
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json()['sha'] if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient='records').encode('utf-8')).decode('utf-8')
        data = {"message": f"Update {file}", "content": content}
        if sha: data["sha"] = sha
        requests.put(url, headers={"Authorization": f"token {token}"}, json=data)
    except: st.error(f"Erreur de sauvegarde {file}")

def safe_get(row, col):
    return str(row[col]) if col in row and pd.notnull(row[col]) else ""

# --- 3. CHARGEMENT & NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"

df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")
df_log = charger_data("logbook.json")

st.title("⚓ VESTA SKIPPER 2026")
m = st.columns(7)
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES", "LOG"]
for i, name in enumerate(menu):
    if m[i].button(name, use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()

# --- 4. LOGIQUE DES PAGES ---

if st.session_state.page == "CONTACTS":
    st.subheader("👤 Carnet de Contacts")
    if st.button("➕ NOUVEAU CONTACT"):
        new = pd.DataFrame([{"Prénom": "Nouveau", "Nom": "Contact", "Statut": "En attente", "DateNav": "01/01/2026"}])
        df_c = pd.concat([new, df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()
    
    if not df_c.empty:
        for i, r in df_c.iterrows():
            with st.expander(f"{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()} - {safe_get(r, 'DateNav')}"):
                st.write(f"Statut: {safe_get(r, 'Statut')}")
                if st.button("Supprimer", key=f"del_{i}"):
                    df_c = df_c.drop(i)
                    sauvegarder_data(df_c, "contacts.json")
                    st.rerun()
    else:
        st.info("Aucun contact.")

elif st.session_state.page == "LOG":
    st.subheader("📖 Livre de Bord")
    # Ton code de log ici...
    st.write("Contenu du livre de bord")

else:
    st.info(f"La page {st.session_state.page} est en cours de reconstruction.")

































































































































































































































































































































































































































































































