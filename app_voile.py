import streamlit as st
import pandas as pd
import requests
import json
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB ---
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

def charger_data(file):
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def sauvegarder_data(file, df):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    sha = res.json()['sha'] if res.status_code == 200 else None
    
    content = df.to_json(orient='records', indent=4)
    data = {
        "message": f"Mise à jour {file}",
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    requests.put(url, headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=data)

# --- INTERFACE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.title("⛵ Vesta Skipper 2026")

menu = st.sidebar.radio("Menu", ["📅 Planning", "📇 Contacts", "📊 Stats", "📝 Livre de Bord"])

# --- SECTION PLANNING ---
if menu == "📅 Planning":
    st.header("Planning des Sorties")
    df_p = charger_data("planning.json")
    
    with st.expander("➕ Ajouter une sortie"):
        with st.form("form_p"):
            date = st.date_input("Date")
            client = st.text_input("Client")
            compagnie = st.selectbox("Compagnie", ["CMN", "Privé", "Autre"])
            status = st.selectbox("Paiement", ["Unpaid", "Paid"])
            if st.form_submit_button("Enregistrer"):
                # Couleur bleue pour CMN
                color = "#2e7bcf" if compagnie == "CMN" else "#2c3e50"
                nouvelle_ligne = {"Date": str(date), "Client": client, "Compagnie": compagnie, "Status": status, "Color": color}
                df_p = pd.concat([df_p, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
                sauvegarder_data("planning.json", df_p)
                st.success("Planning mis à jour !")
                st.rerun()

    if not df_p.empty:
        st.table(df_p[["Date", "Client", "Compagnie", "Status"]])

# --- SECTION CONTACTS ---
elif menu == "📇 Contacts":
    st.header("Annuaire Clients")
    df_c = charger_data("contacts.json")
    
    with st.expander("➕ Nouveau Contact"):
        with st.form("form_c"):
            nom = st.text_input("Nom")
            tel = st.text_input("Téléphone")
            email = st.text_input("Email")
            notes = st.text_area("Notes")
            if st.form_submit_button("Ajouter"):
                nouveau_c = {"Nom": nom, "Tel": tel, "Email": email, "Notes": notes}
                df_c = pd.concat([df_c, pd.DataFrame([nouveau_c])], ignore_index=True)
                sauvegarder_data("contacts.json", df_c)
                st.success("Contact enregistré !")
                st.rerun()

    if not df_c.empty:
        for i, row in df_c.iterrows():
            with st.expander(f"👤 {row['Nom']}"):
                st.write(f"📞 **Tel :** {row['Tel']}")
                st.write(f"✉️ **Email :** {row['Email']}")
                st.info(f"📝 {row.get('Notes', '')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'<a href="tel:{row["Tel"]}" style="text-decoration:none;"><button style="width:100%; border-radius:5px; background-color:#2e7bcf; color:white; border:none; padding:10px;">📞 Appeler</button></a>', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'<a href="mailto:{row["Email"]}" style="text-decoration:none;"><button style="width:100%; border-radius:5px; background-color:#28a745; color:white; border:none; padding:10px;">✉️ Mail</button></a>', unsafe_allow_html=True)

# --- SECTION STATS ---
elif menu == "📊 Stats":
    st.header("Statistiques d'Activité")
    df_p = charger_data("planning.json")
    if not df_p.empty:
        st.metric("Total Sorties", len(df_p))
        st.bar_chart(df_p['Compagnie'].value_counts())
    else:
        st.write("Aucune donnée disponible.")

# --- SECTION LIVRE DE BORD ---
elif menu == "📝 Livre de Bord":
    st.header("Historique & Maintenance")
    df_l = charger_data("logbook.json")
    # ... Affichage simplifié du logbook
    st.table(df_l)

































































































































































































































































































































































































































































































