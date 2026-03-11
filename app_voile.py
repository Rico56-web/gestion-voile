import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- 2. FONCTIONS DE SAUVEGARDE RÉELLE ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"nocache": time.time()})
        if res.status_code == 200:
            content = res.json()['content']
            return pd.DataFrame(json.loads(base64.b64decode(content).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_sur_github(df, file):
    """ Envoie les données modifiées sur GitHub pour qu'elles persistent """
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    
    # 1. Récupérer le SHA (obligatoire pour modifier un fichier existant)
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    # 2. Encoder le nouveau contenu
    new_content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    
    # 3. Envoyer la mise à jour
    payload = {"message": f"Mise à jour {file}", "content": new_content, "sha": sha}
    put_res = requests.put(url, headers={"Authorization": f"token {token}"}, json=payload)
    return put_res.status_code in [200, 201]

# --- 3. GESTION DES ÉTATS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

# On charge les données une seule fois par exécution
df = charger_data("contacts.json")

# --- 4. NAVIGATION & ENTÊTE ---
st.markdown('<h1 style="text-align:center; color:#1a2a6c;">⚓ SKIPPER VESTA 2026</h1>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
cols = st.columns(6)
menu = [("📋 CONTACTS","CONTACTS"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (l, p) in enumerate(menu):
    if cols[i].button(l, use_container_width=True): 
        st.session_state.page = p
        st.session_state.edit_idx = None
        st.rerun()

# --- 5. LOGIQUE CONTACTS ---
if st.session_state.page == "CONTACTS":

    # --- MODE DÉTAIL / MODIFICATION ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.iloc[idx] # Utilisation de iloc pour l'indexation physique
        
        st.info(f"📍 Édition de la fiche : {r['Prénom']} {r['Nom']}")
        
        with st.form("edit_contact"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom', ''))
            u_nom = c2.text_input("Nom", value=r.get('Nom', ''))
            u_tel = c1.text_input("Téléphone", value=r.get('Téléphone', ''))
            u_mail = c2.text_input("Email", value=r.get('Mail', ''))
            u_prix = st.text_input("Prix (€)", value=str(r.get('Prix', '0')))
            u_notes = st.text_area("Notes / Livre de bord", value=r.get('Notes', ''), height=200)
            
            b1, b2 = st.columns(2)
            if b1.form_submit_button("💾 ENREGISTRER DÉFINITIVEMENT"):
                # Mise à jour du DataFrame local
                df.at[idx, 'Prénom'] = u_pre
                df.at[idx, 'Nom'] = u_nom
                df.at[idx, 'Téléphone'] = u_tel
                df.at[idx, 'Mail'] = u_mail
                df.at[idx, 'Prix'] = u_prix
                df.at[idx, 'Notes'] = u_notes
                
                # Sauvegarde sur GitHub
                if sauvegarder_sur_github(df, "contacts.json"):
                    st.success("✅ Données sauvegardées sur GitHub !")
                    time.sleep(1) # Petit délai pour laisser GitHub respirer
                    st.session_state.edit_idx = None
                    st.rerun()
                else:
                    st.error("❌ Erreur lors de la sauvegarde.")

            if b2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None
                st.rerun()

    # --- MODE AFFICHAGE LISTE ---
    else:
        for i, r in df.iterrows():
            with st.container():
                # On utilise ici l'encadré global
                st.markdown(f"""
                <div style="border:2px solid #1a2a6c; border-radius:10px; margin-bottom:20px; background:white; overflow:hidden;">
                    <div style="padding:15px;">
                        <span style="font-size:1.5rem; font-weight:bold; color:#1a2a6c;">{r['Prénom']} {r['Nom'].upper()}</span><br>
                        <b>💰 Prix: {r.get('Prix','0')} €</b><br>
                        📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')}
                    </div>
                    <div style="padding:15px; background:#f1f3f6; border-top:1px solid #1a2a6c;">
                        <b>Notes :</b><br>
                        <p style="font-style:italic; color:#444;">{r.get('Notes','(Aucune note)')}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"✏️ MODIFIER DÉTAILS - {r['Prénom']}", key=f"btn_{i}"):
                    st.session_state.edit_idx = i
                    st.rerun()




























































































































































































































































































































































































