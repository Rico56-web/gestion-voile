
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

# --- PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Carnet de Contacts")
    
    # Bouton de création
    if st.button("➕ NOUVEAU CONTACT", type="primary", use_container_width=True):
        new_row = {"Prénom": "Nouveau", "Nom": "Contact", "Statut": "En attente", "DateNav": datetime.now().strftime("%d/%m/2026"), "Société": "", "Prix": "0.00", "Paiement": "Pas payé"}
        df_c = pd.concat([pd.DataFrame([new_row]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    if not df_c.empty:
        # Nettoyage et Tri
        df_c.columns = [str(c).strip() for c in df_c.columns]
        for i, r in df_c.iterrows():
            # On utilise une carte visuelle pour chaque contact
            with st.container():
                st.markdown(f"""
                <div style="border:1px solid #ddd; padding:10px; border-radius:10px; margin-bottom:10px; background:white;">
                    <b style="color:#1a2a6c;">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</b> | 📅 {safe_get(r, 'DateNav')}<br>
                    <small>{safe_get(r, 'Société')} | Statut: {safe_get(r, 'Statut')} | Paiement: {safe_get(r, 'Paiement')}</small>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 5])
                if c1.button("🗑️", key=f"del_{i}"):
                    df_c = df_c.drop(i)
                    sauvegarder_data(df_c, "contacts.json")
                    st.rerun()
    else:
        st.info("Aucun contact enregistré.")

# --- PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning 2026")
    if not df_c.empty:
        # On affiche juste une liste simplifiée pour vérifier que les données sont là
        for _, r in df_c.iterrows():
            st.write(f"📅 {safe_get(r, 'DateNav')} : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom')}")
    else:
        st.info("Le planning est vide.")

# --- PAGE MAINT ---
elif st.session_state.page == "MAINT":
    st.subheader("🔧 Maintenance")
    if not df_m.empty:
        st.table(df_m)
    else:
        st.info("Aucun frais de maintenance.")

# --- PAGE LOG (LIVRE DE BORD) ---
elif st.session_state.page == "LOG":
    st.subheader("📖 Livre de Bord")
    if not df_log.empty:
        for i, r in df_log.iterrows():
            st.info(f"⚓ {safe_get(r, 'Date')} : {safe_get(r, 'PortDep')} ➜ {safe_get(r, 'PortArr')}")
    else:
        st.info("Le livre de bord est vide.")

# --- AUTRES PAGES ---
else:
    st.info(f"Le module {st.session_state.page} est en cours de reconnexion.")

































































































































































































































































































































































































































































































