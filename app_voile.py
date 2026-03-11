import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin-bottom: -5px; }
    .nom-style { font-size: 1.1rem; text-transform: uppercase; color: #666; margin-bottom: 10px; }
    .cal-table { width: 100%; border-collapse: collapse; text-align: center; background: white; }
    .cal-table td { height: 45px; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white; }
    .day-cmn { background-color: #3498db !important; color: white; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DATA GITHUB ---
def to_f(val):
    try: return float(str(val).replace(',', '.').replace(' ', '').strip()) if val else 0.0
    except: return 0.0

def parse_d(d_str):
    try: return datetime.strptime(str(d_str), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            return pd.DataFrame(json.loads(base64.b64decode(content).decode('utf-8')))
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
pages = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOG","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True): st.session_state.page = p; st.rerun()

# --- 4. LOGIQUE DES PAGES ---

# --- LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher Nom ou Prénom").lower()
    if not df.empty:
        mask = (df['Nom'].astype(str).str.lower().str.contains(search, na=False)) | (df['Prénom'].astype(str).str.lower().str.contains(search, na=False))
        for i, r in df[mask].iterrows():
            with st.container():
                st.markdown(f'<div class="prenom-style">{r.get("Prénom", "")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="nom-style">{str(r.get("Nom", "")).upper()}</div>', unsafe_allow_html=True)
                st.write(f"📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')}")
                st.write(f"📅 {r.get('DateNav','')} | ⏳ {r.get('NbJours','1')} j")
                st.write(f"🏢 {r.get('Société','')} | 💰 {r.get('Prix','0')} €")
                c1, c2, c3 = st.columns([0.8, 0.1, 0.1])
                c1.text_input("Notes", value=r.get('Notes',''), key=f"n_{i}", label_visibility="collapsed")
                c2.button("✏️", key=f"e_{i}")
                c3.button("🗑️", key=f"d_{i}")
                st.divider()

# --- PLANNING ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d_s = parse_d(r.get('DateNav', ''))
            if d_s.month == now.month:
                clr = "day-cmn" if str(r.get('Société','')).upper() == "CMN" else "day-ok"
                for j in range(int(to_f(r.get('NbJours', 1)))):
                    occu[(d_s + timedelta(days=j)).day] = clr
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            s = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {s}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    st.markdown("---")
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for _, r in df[df['dt'].dt.month == now.month].sort_values('dt').iterrows():
            st.write(f"{'🔵' if r['Société'].upper()=='CMN' else '🟢'} **{r['DateNav']}** : {r['Prénom']} {r['Nom'].upper()}")

# --- STATS (Calcul NET + Tableau sans index) ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 STATISTIQUES & RÉSULTATS</div>', unsafe_allow_html=True)
    
    # Calcul du NET
    ca = df[(df.get('Statut','')=="OK") & (df.get('Paiement','')=="Paid")]['Prix'].apply(to_f).sum()
    frais = df_maint['Montant'].apply(to_f).sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Encaissé (Paid)", f"{ca} €")
    col2.metric("Maintenance", f"{frais} €")
    col3.metric("NET", f"{ca - frais} €")

    st.markdown("---")
    # Tableau Stats Mensuel sans colonne index (commence par Mois)
    if not df.empty:
        df['Mois'] = df['DateNav'].apply(lambda x: parse_d(x).month)
        st_m = df.groupby('Mois')['Prix'].sum().reset_index()
        st.table(st_m.set_index('Mois')) # Supprime la colonne 0,1,2...

    # Boutons Modifier / Effacer avec Verrouillage
    c_m1, c_m2 = st.columns(2)
    if c_m1.button("✏️ MODIFIER LES STATS"):
        st.warning("Mode modification activé. Attention aux doublons.")
    
    if c_m2.button("🗑️ EFFACER LES DONNÉES"):
        if st.checkbox("Confirmer la suppression totale ?"):
            st.error("Action irréversible.")

# --- LOGS (Livre de bord) ---
elif st.session_state.page == "LOGS":
    st.markdown('<div class="page-title">📖 LIVRE DE BORD</div>', unsafe_allow_html=True)
    if not df.empty:
        st.dataframe(df[['DateNav', 'Prénom', 'Nom', 'Société', 'Notes']], use_container_width=True)

# --- FACTURES ---
elif st.session_state.page == "FACTURES":
    st.markdown('<div class="page-title">📄 FACTURES</div>', unsafe_allow_html=True)
    if not df.empty:
        soc = st.selectbox("Client", df['Société'].unique())
        total = df[df['Société'] == soc]['Prix'].apply(to_f).sum()
        st.write(f"Récapitulatif pour **{soc}**")
        st.metric("Total à facturer", f"{total} €")

# --- SÉCURITÉ ---
elif st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 SÉCURITÉ</div>', unsafe_allow_html=True)
    st.info("Check-list sécurité : Gilets, Balise, VHF, Météo OK.")

# --- MAINTENANCE ---
elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    with st.form("fm"):
        d, o, m = st.date_input("Date"), st.text_input("Objet"), st.number_input("Montant")
        if st.form_submit_button("🔨 Ajouter"):
            new = pd.DataFrame([{"Date": d.strftime("%d/%m/%Y"), "Objet": o, "Montant": m}])
            sauvegarder_data(pd.concat([df_maint, new]), "maintenance.json")
            st.rerun()
    st.table(df_maint)

# --- NOTES ---
elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    note_libre = st.text_area("Bloc-notes général", height=400)
    if st.button("Enregistrer les notes"):
        st.success("Notes sauvegardées (Simulation)")



















































































































































































































































































































































































