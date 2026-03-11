import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. STYLE CSS ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; }
    .fiche-complete { border: 2px solid #1a2a6c; border-radius: 12px; overflow: hidden; margin-bottom: 25px; background-color: white; }
    .zone-infos { padding: 18px; background: white; }
    .zone-actions { padding: 15px; background: #f1f3f6; border-top: 1px solid #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.85rem; font-weight: bold; color: white; margin-left: 5px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def to_f(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace('€', '').replace(' ', '').strip())
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Statuts", "content": content, "sha": sha})

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)
m = st.columns(6)
pages = [("📋 CONTACTS","CONTACTS"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.session_state.edit_idx = None; st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    
    # --- FORMULAIRE DE MODIFICATION ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        
        # Sécurité pour les index des selectbox
        list_statut = ["En attente", "OK", "Refusé"]
        idx_statut = list_statut.index(r.get('Statut')) if r.get('Statut') in list_statut else 0
        
        list_paye = ["Pas payé", "Payé"]
        idx_paye = list_paye.index(r.get('Paiement')) if r.get('Paiement') in list_paye else 0

        with st.form("form_edit_contact"):
            st.subheader(f"Détails : {r.get('Prénom','')} {r.get('Nom','')}")
            c1, c2, c3 = st.columns(3)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_prix = c3.text_input("Prix (€)", value=str(r.get('Prix','0')))
            
            s1, s2 = st.columns(2)
            u_statut = s1.selectbox("Statut Mission", list_statut, index=idx_statut)
            u_paiement = s2.selectbox("Paiement", list_paye, index=idx_paye)
            
            u_notes = st.text_area("Notes", value=r.get('Notes',''))
            
            # BOUTONS DU FORMULAIRE (Indispensables ici)
            col_b1, col_b2 = st.columns(2)
            if col_b1.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'Prénom'] = u_pre
                df.at[idx, 'Nom'] = u_nom
                df.at[idx, 'Prix'] = to_f(u_prix)
                df.at[idx, 'Statut'] = u_statut
                df.at[idx, 'Paiement'] = u_paiement
                df.at[idx, 'Notes'] = u_notes
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None
                st.rerun()
                
            if col_b2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None
                st.rerun()

    # --- LISTE DES CONTACTS ---
    else:
        for i, r in df.iterrows():
            col_s = {"OK": "#2ecc71", "En attente": "#f1c40f", "Refusé": "#e74c3c"}.get(r.get('Statut'), "#95a5a6")
            col_p = "#2ecc71" if r.get('Paiement') == "Payé" else "#e74c3c"
            
            st.markdown(f"""
            <div class="fiche-complete">
                <div class="zone-infos">
                    <div style="float:right;">
                        <span class="statut-badge" style="background:{col_s};">{r.get('Statut', 'En attente')}</span>
                        <span class="statut-badge" style="background:{col_p};">{r.get('Paiement', 'Pas payé')}</span>
                    </div>
                    <div class="prenom-style">{r.get('Prénom','')} {str(r.get('Nom','')).upper()}</div>
                    <p>💰 <b>{r.get('Prix', 0)} €</b> | 🏢 {r.get('Société','')}</p>
                </div>
                <div class="zone-actions">
            """, unsafe_allow_html=True)
            
            cn, cb = st.columns([0.7, 0.3])
            cn.write(f"**Notes :** {r.get('Notes','')}")
            if cb.button("✏️ DÉTAILS / STATUT", key=f"btn_{i}", use_container_width=True):
                st.session_state.edit_idx = i
                st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

# --- 5. PAGE STATS (Logique Financière) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 BILAN FINANCIER 2026</div>', unsafe_allow_html=True)
    if not df.empty:
        # ACQUIS : OK + Payé
        acquis = df[(df['Statut']=="OK") & (df['Paiement']=="Payé")]['Prix'].apply(to_f).sum()
        # PRÉVISIONNEL : En attente OU (OK + Pas payé)
        prev = df[(df['Statut']=="En attente") | ((df['Statut']=="OK") & (df['Paiement']=="Pas payé"))]['Prix'].apply(to_f).sum()
        # FRAIS
        maint = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 ACQUIS", f"{acquis} €")
        c2.metric("⏳ PRÉVISIONNEL", f"{prev} €")
        c3.metric("🔧 FRAIS", f"{maint} €")
        st.divider()
        st.subheader("Bénéfice estimé (Acquis + Prév. - Frais)")
        st.header(f"{acquis + prev - maint} €")

































































































































































































































































































































































































