import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin-bottom: -5px; }
    .nom-style { font-size: 1.1rem; text-transform: uppercase; color: #666; margin-bottom: 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE NETTOYAGE ULTIME ---
def to_f(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def parse_d(d_str):
    try: return datetime.strptime(str(d_str).strip(), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            data = json.loads(base64.b64decode(content).decode('utf-8'))
            df_raw = pd.DataFrame(data)
            # Nettoyage immédiat des noms de colonnes
            df_raw.columns = [str(c).strip() for c in df_raw.columns]
            return df_raw
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})

# Authentification
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Code d'accès", type="password")
    if st.button("Connexion"):
        if pwd == "SKIPPER2026": st.session_state.auth = True; st.rerun()
        else: st.error("Code incorrect")
    st.stop()

# Chargement
df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
m = st.columns(8)
pages = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SECU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True): st.session_state.page = p; st.rerun()

# --- 4. LOGIQUE DES PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher Nom ou Prénom").lower()
    
    if not df.empty:
        # Détection intelligente des colonnes Nom/Prénom
        c_nom = next((c for c in df.columns if 'nom' in c.lower() and 'pré' not in c.lower()), "Nom")
        c_pre = next((c for c in df.columns if 'pré' in c.lower() or 'pre' in c.lower()), "Prénom")
        
        mask = (df[c_nom].astype(str).str.lower().str.contains(search, na=False)) | \
               (df[c_pre].astype(str).str.lower().str.contains(search, na=False))
        
        for i, r in df[mask].iterrows():
            with st.container():
                st.markdown(f'<div class="prenom-style">{r.get(c_pre, "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="nom-style">{str(r.get(c_nom, "")).upper()}</div>', unsafe_allow_html=True)
                st.write(f"🏢 {r.get('Société','')} | 📅 {r.get('DateNav','')} | 💰 {r.get('Prix','0')} €")
                st.divider()

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 RÉSULTAT NET</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # --- DÉTECTION AUTOMATIQUE DU PRIX ---
        # On cherche une colonne qui contient "prix", "montant" ou "eur"
        col_prix = next((c for c in df.columns if any(x in c.lower() for x in ['prix', 'montant', 'eur'])), None)
        
        if col_prix:
            # Calcul du CA Encaissé (Statut OK et Paiement Paid)
            # On cherche les colonnes de statut/paiement de façon souple
            c_stat = next((c for c in df.columns if 'statut' in c.lower()), 'Statut')
            c_paie = next((c for c in df.columns if 'paie' in c.lower()), 'Paiement')
            
            mask = (df[c_stat].astype(str) == "OK") & (df[c_paie].astype(str) == "Paid")
            ca = df[mask][col_prix].apply(to_f).sum()
            
            frais = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Encaissé (Paid)", f"{ca} €")
            c2.metric("Maintenance", f"{frais} €")
            c3.metric("NET FINAL", f"{ca - frais} €")
            
            st.markdown("---")
            # Tableau Mensuel sans index
            if 'DateNav' in df.columns:
                df['Mois'] = df['DateNav'].apply(lambda x: parse_d(x).month)
                st_m = df.groupby('Mois')[col_prix].sum().reset_index()
                st.table(st_m.set_index('Mois'))
        else:
            st.error(f"Erreur : Aucune colonne de prix détectée. Colonnes présentes : {list(df.columns)}")

    # Boutons Modifier / Effacer
    c_b1, c_b2 = st.columns(2)
    with c_b1: 
        if st.button("✏️ MODIFIER"): st.info("Déverrouillé")
    with c_b2:
        if st.button("🗑️ EFFACER"):
            if st.checkbox("Confirmer ?"): st.warning("Suppression en attente")

elif st.session_state.page == "FACTURES":
    st.markdown('<div class="page-title">📄 FACTURES</div>', unsafe_allow_html=True)
    if not df.empty:
        col_soc = next((c for c in df.columns if 'soc' in c.lower() or 'bur' in c.lower()), None)
        col_prix = next((c for c in df.columns if 'prix' in c.lower() or 'montant' in c.lower()), None)
        
        if col_soc and col_prix:
            soc_sel = st.selectbox("Client", df[col_soc].unique())
            total = df[df[col_soc] == soc_sel][col_prix].apply(to_f).sum()
            st.metric(f"Total {soc_sel}", f"{total} €")
        else:
            st.error("Impossible de trouver les colonnes Société ou Prix.")

elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    with st.form("m"):
        d, o, m = st.date_input("Date"), st.text_input("Objet"), st.number_input("Montant")
        if st.form_submit_button("Ajouter"):
            new = pd.DataFrame([{"Date": d.strftime("%d/%m/%Y"), "Objet": o, "Montant": m}])
            sauvegarder_data(pd.concat([df_maint, new]), "maintenance.json")
            st.rerun()
    st.table(df_maint)

# Autres pages (Squelettes pour éviter les crashs)
elif st.session_state.page in ["LOGS", "SECU", "NOTES"]:
    st.markdown(f'<div class="page-title">{st.session_state.page}</div>', unsafe_allow_html=True)
    st.write("Contenu en cours de chargement...")






















































































































































































































































































































































































