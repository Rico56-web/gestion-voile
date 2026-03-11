import requests
import base64
import streamlit as st
import pandas as pd
import json

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 2px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    .fiche-container { border: 2px solid #1a2a6c; border-radius: 10px 10px 0 0; padding: 15px; background: #ffffff; margin-top: 10px; }
    .action-container { border: 2px solid #1a2a6c; border-top: none; border-radius: 0 0 10px 10px; padding: 10px; background: #f8f9fa; margin-bottom: 25px; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; line-height: 1; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #d35400; font-weight: bold; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE CALCUL & DATA ---
def to_f(val):
    """ Convertit n'importe quelle saisie en nombre flottant propre """
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').replace('€', '').strip())
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            df.columns = [c.strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, 
                 json={"message": "Update data", "content": content, "sha": sha})

# --- 3. INITIALISATION ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

# Navigation
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
m = st.columns(8)
pages = [("📋 CONTACTS","CONTACTS"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p
        st.session_state.edit_idx = None # Ferme l'édition si on change de page
        st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">📇 GESTION DES CONTACTS</div>', unsafe_allow_html=True)
    
    # --- MODE ÉDITION (La fiche détaillée qui s'ouvre) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        row = df.loc[idx]
        st.warning(f"📝 Modification de : {row['Prénom']} {row['Nom']}")
        
        with st.form("form_edit"):
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=row['Prénom'])
            new_nom = c2.text_input("Nom", value=row['Nom'])
            new_tel = c1.text_input("Téléphone", value=row.get('Téléphone',''))
            new_mail = c2.text_input("Mail", value=row.get('Mail',''))
            new_soc = c1.text_input("Société", value=row.get('Société',''))
            new_prix = c2.text_input("Prix (€)", value=str(row.get('Prix', '0')))
            new_notes = st.text_area("Notes", value=row.get('Notes',''))
            
            col_save, col_cancel = st.columns(2)
            if col_save.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS"):
                df.at[idx, 'Prénom'] = new_pre
                df.at[idx, 'Nom'] = new_nom
                df.at[idx, 'Téléphone'] = new_tel
                df.at[idx, 'Mail'] = new_mail
                df.at[idx, 'Société'] = new_soc
                df.at[idx, 'Prix'] = new_prix
                df.at[idx, 'Notes'] = new_notes
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None
                st.success("Modifications enregistrées !")
                st.rerun()
            if col_cancel.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None
                st.rerun()
    
    # --- MODE LISTE CLASSIQUE ---
    else:
        search = st.text_input("🔍 Rechercher...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)
        
        for i, r in df[mask].iterrows():
            with st.container():
                st.markdown(f"""
                <div class="fiche-container">
                    <div class="prenom-style">{r['Prénom']}</div>
                    <div class="nom-style">{str(r['Nom']).upper()}</div>
                    <div class="contact-verif">📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')}</div>
                    <p style="margin-top:10px;">🏢 <b>{r.get('Société','')}</b> | 📅 {r.get('DateNav','')} | 💰 <b>{r.get('Prix','0')} €</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.container():
                    st.markdown('<div class="action-container">', unsafe_allow_html=True)
                    c_n, c_b = st.columns([0.8, 0.2])
                    c_n.text_area("Notes", value=r.get('Notes',''), key=f"v_n_{i}", height=65, disabled=True, label_visibility="collapsed")
                    if c_b.button("✏️ MODIFIER", key=f"btn_ed_{i}", use_container_width=True):
                        st.session_state.edit_idx = i
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. PAGE STATS (Calculs Fiables) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 RÉSULTAT NET</div>', unsafe_allow_html=True)
    
    # On applique to_f sur toute la colonne Prix pour être sûr du calcul
    ca_brut = df['Prix'].apply(to_f).sum()
    
    # On filtre sur Statut OK et Paiement Paid pour le NET réel (Exemple)
    ca_encaisse = df[(df.get('Statut') == "OK") & (df.get('Paiement') == "Paid")]['Prix'].apply(to_f).sum()
    
    frais = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Chiffre d'Affaire Global", f"{ca_brut} €")
    c2.metric("Frais Maintenance", f"{frais} €")
    c3.metric("BÉNÉFICE NET (Encaissé)", f"{ca_encaisse - frais} €", delta=f"{ca_encaisse} Encaissé")
























































































































































































































































































































































































