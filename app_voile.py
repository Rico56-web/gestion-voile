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
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.85rem; font-weight: bold; color: white; }
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
    
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Détails : {r['Prénom']} {r['Nom']}")
            c1, c2, c3 = st.columns(3)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_prix = c3.text_input("Prix (€)", value=str(r.get('Prix','0')))
            
            # --- NOUVEAUX STATUTS ---
            s1, s2 = st.columns(2)
            u_statut = s1.selectbox("Statut Mission", ["En attente", "OK", "Refusé"], index=["En attente", "OK", "Refusé"].index(r.get('Statut', 'En attente')))
            u_paiement = s2.selectbox("Paiement", ["Pas payé", "Payé"], index=["Pas payé", "Payé"].index(r.get('Paiement', 'Pas payé')))
            
            u_notes = st.text_area("Notes", value=r.get('Notes',''))
            
            if st.form_submit_button("💾 SAUVEGARDER"):
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Prix'] = u_pre, u_nom, to_f(u_prix)
                df.at[idx, 'Statut'], df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = u_statut, u_paiement, u_notes
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None; st.rerun()
    else:
        for i, r in df.iterrows():
            # Couleurs de badge
            color_s = {"OK": "#2ecc71", "En attente": "#f1c40f", "Refusé": "#e74c3c"}.get(r.get('Statut'), "#95a5a6")
            color_p = "#2ecc71" if r.get('Paiement') == "Payé" else "#e74c3c"
            
            st.markdown(f"""
            <div class="fiche-complete">
                <div class="zone-infos">
                    <div style="float:right;">
                        <span class="statut-badge" style="background:{color_s};">{r.get('Statut', 'En attente')}</span>
                        <span class="statut-badge" style="background:{color_p};">{r.get('Paiement', 'Pas payé')}</span>
                    </div>
                    <div class="prenom-style">{r['Prénom']} {str(r['Nom']).upper()}</div>
                    <p>💰 <b>{r.get('Prix', 0)} €</b> | 🏢 {r.get('Société','')}</p>
                </div>
                <div class="zone-actions">
            """, unsafe_allow_html=True)
            c_n, c_b = st.columns([0.7, 0.3])
            c_n.write(f"**Notes :** {r.get('Notes','')}")
            if c_b.button("✏️ DÉTAILS / STATUT", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

# --- 5. PAGE STATS (LOGIQUE FINANCIÈRE) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 BILAN FINANCIER 2026</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 1. ACQUIS : Statut OK ET Payé
        mask_acquis = (df['Statut'] == "OK") & (df['Paiement'] == "Payé")
        acquis = df[mask_acquis]['Prix'].apply(to_f).sum()
        
        # 2. PRÉVISIONNEL : (En attente) OU (OK mais Pas payé)
        # On exclut les "Refusé"
        mask_prev = ((df['Statut'] == "En attente") | ((df['Statut'] == "OK") & (df['Paiement'] == "Pas payé")))
        previsionnel = df[mask_prev]['Prix'].apply(to_f).sum()
        
        # 3. MAINTENANCE
        maint = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
        
        # AFFICHAGE
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 ACQUIS (Net encaissé)", f"{acquis} €")
        c2.metric("⏳ PRÉVISIONNEL", f"{previsionnel} €")
        c3.metric("🔧 FRAIS (Maint.)", f"{maint} €")
        
        st.divider()
        st.subheader("Total Estimé (Acquis + Prév.)")
        st.header(f"{acquis + previsionnel - maint} €")
































































































































































































































































































































































































