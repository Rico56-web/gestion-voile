import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 🛠️ UTILS ---
def to_f(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def parse_d(d_str):
    try: return datetime.strptime(str(d_str), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# Style CSS pour respecter les consignes visuelles
st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin-bottom: -10px; }
    .nom-style { font-size: 1.1rem; text-transform: uppercase; color: #666; margin-bottom: 10px; }
    .info-line { font-size: 1rem; margin-bottom: 5px; }
    .cal-table { width: 100%; border-collapse: collapse; text-align: center; }
    .cal-table td { height: 40px; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white; }
    .day-cmn { background-color: #3498db !important; color: white; }
</style>""", unsafe_allow_html=True)

# --- 2. GESTION GITHUB ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            decoded = base64.b64decode(content).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})

# Chargement des bases
df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

# --- 3. MENU ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
tabs = st.columns(4)
if tabs[0].button("📋 LISTE"): st.session_state.page = "LISTE"
if tabs[1].button("🗓️ PLAN"): st.session_state.page = "PLANNING"
if tabs[2].button("🔧 MAINT"): st.session_state.page = "MAINT"
if tabs[3].button("📊 STATS"): st.session_state.page = "STATS"

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📇 FICHES CONTACTS</div>', unsafe_allow_html=True)
    
    # Recherche Nom OU Prénom
    search = st.text_input("🔍 Rechercher un contact (Nom ou Prénom)").lower()
    
    if not df.empty:
        filtered = df[df['Nom'].str.lower().contains(search, na=False) | df['Prénom'].str.lower().contains(search, na=False)]
        
        for i, r in filtered.iterrows():
            with st.container():
                st.markdown(f"""<div class="client-card">
                    <div class="prenom-style">{r['Prénom']}</div>
                    <div class="nom-style">{str(r['Nom']).upper()}</div>
                    <div class="info-line">📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')}</div>
                    <div class="info-line">📅 {r.get('DateNav','')} | ⏳ {r.get('NbJours','1')} Jours</div>
                    <div class="info-line">🏢 {r.get('Société','')} | 💰 {r.get('Prix','0')} €</div>
                </div>""", unsafe_allow_html=True)
                
                # Zone Notes + Boutons alignés
                c_txt, c_btn1, c_btn2 = st.columns([0.8, 0.1, 0.1])
                c_txt.text_input("Notes", value=r.get('Notes',''), key=f"note_{i}", label_visibility="collapsed")
                c_btn1.button("✏️", key=f"edit_{i}")
                if c_btn2.button("🗑️", key=f"del_{i}"):
                    # Logique de suppression ici
                    pass
                st.markdown("---")

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    
    # Calendrier Coloré
    now = datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    
    # Logique de couleurs (Bleu CMN, Vert Autres)
    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d = parse_d(r['DateNav'])
            if d.month == now.month and d.year == now.year:
                color = "day-cmn" if str(r['Société']).upper() == "CMN" else "day-ok"
                for j in range(int(to_f(r.get('NbJours', 1)))):
                    occu[(d + timedelta(days=j)).day] = color

    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            cls = occu.get(d, "") if d != 0 else ""
            h += f'<td class="{cls}">{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

    # Liste textuelle en dessous
    st.subheader("Navigations du mois")
    month_data = df[df['DateNav'].apply(lambda x: parse_d(x).month == now.month)]
    for _, r in month_data.sort_values('DateNav').iterrows():
        dot = "🔵" if str(r['Société']).upper() == "CMN" else "🟢"
        st.write(f"{dot} **{r['DateNav']}** : {r['Prénom']} {str(r['Nom']).upper()} ({r['Société']})")

elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    with st.form("form_maint"):
        d_m = st.date_input("Date")
        obj_m = st.text_input("Objet")
        prix_m = st.number_input("Montant (€)", min_value=0.0)
        if st.form_submit_button("Enregistrer Frais"):
            new_f = pd.DataFrame([{"Date": d_m.strftime("%d/%m/%Y"), "Objet": obj_m, "Montant": prix_m}])
            sauvegarder_data(pd.concat([df_maint, new_f]), "maintenance.json")
            st.rerun()
    st.table(df_maint)

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 STATS & NET</div>', unsafe_allow_html=True)
    
    # NET = (Somme Prix si Statut=OK et Paiement=Paid) - (Somme Frais Maint)
    ca = df[(df['Statut'].str.contains("OK", na=False)) & (df['Paiement'] == "Paid")]['Prix'].apply(to_f).sum()
    frais = df_maint['Montant'].apply(to_f).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Revenus (OK/Paid)", f"{ca} €")
    c2.metric("Frais (Maint)", f"{frais} €")
    c3.metric("NET FINAL", f"{ca - frais} €")










































































































































































































































































































































































