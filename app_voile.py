import requests
import base64
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import calendar
import urllib.parse

# --- 🛠️ FONCTIONS DE SÉCURITÉ ---

def to_f(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def parse_d(d_str):
    try: return datetime.strptime(str(d_str), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def fmt_p(v):
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "SKIPPER2026": 
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect ❌")
    st.stop()

if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 60px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 5px; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 5px; text-decoration: none; color: white !important; font-weight: bold; margin-right: 5px; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

# --- 2. DONNÉES ---
@st.cache_data(ttl=1)
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
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_data = df.to_json(orient="records", indent=4, force_ascii=False)
        content = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
    except: st.error("Erreur de sauvegarde")

df = charger_data("contacts.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOG","LOGBOOK"), ("📄 FACT","FACTURES"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, key=f"btn_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. LOGIQUE DES PAGES ---


            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            
            # Calcul de la couleur du badge
            b_col = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            
            # Affichage de la fiche
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{b_col}; border-color:{b_col}; background:{b_col}15;">{statut}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 <b>{soc}</b> | 📅 {r.get('DateNav')}<br>
                📞 {tel} | ✉️ {mail}<br><br>
                <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appel</a>
                <a href="https://wa.me/{tel.replace(' ','')}" target="_blank" class="btn-contact" style="background:#25d366;">💬 WhatsApp</a>
                <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Mail</a>
            </div>""", unsafe_allow_html=True)

# --- REMPLACEMENT DU BLOC LISTE ET PLANNING ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    search_term = st.text_input("🔍 Rechercher par Nom ou Prénom", "").strip().lower()
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): 
        st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): 
        st.session_state.view_mode="PASSÉES"; st.rerun()
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        
        if search_term:
            data = data[(data['Nom'].str.lower().str.contains(search_term, na=False)) | 
                        (data['Prénom'].str.lower().str.contains(search_term, na=False))]
      for i, r in data.sort_values('dt').iterrows():
            soc = str(r.get('Société','')).upper()
            statut = str(r.get('Statut','🟡 Attente'))
            # --- CES LIGNES DOIVENT ÊTRE ALIGNÉES VERTICALEMENT ---
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            nb_j = int(to_f(r.get('NbJours', 1))) 
            
            # Calcul de la couleur du badge
            b_col = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{b_col}; border-color:{b_col}; background:{b_col}15;">{statut}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} <b>({nb_j} j)</b><br>
                📞 {tel} | ✉️ {mail}<br><br>
                <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appel</a>
                <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Mail</a>
            </div>""", unsafe_allow_html=True)  


elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING & CROISIÈRES</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    p_y = c1.selectbox("Année", [2025, 2026, 2027], index=1)
    p_m = c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    st.markdown("""<style>.cal-table td { height: 40px !important; font-size: 0.9rem !important; padding: 2px !important; }</style>""", unsafe_allow_html=True)

    occu = {}
    df_mois = pd.DataFrame()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        df_mois = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
        
        # --- LOGIQUE DE COLORATION MULTI-JOURS ---
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                date_debut = r['dt']
                nb_jours = int(to_f(r.get('NbJours', 1)))
                soc = str(r.get('Société','')).upper()
                
                for j in range(nb_jours):
                    jour_courant = date_debut + timedelta(days=j)
                    if jour_courant.year == p_y and jour_courant.month == p_m:
                        occu[jour_courant.day] = "day-cmn" if soc == "CMN" else "day-ok"

    # Affichage Calendrier
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {style}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

    # Liste Contacts avec Durée
    st.markdown("---")
    st.subheader(f"👥 Détails {calendar.month_name[p_m]}")
    if not df_mois.empty:
        for _, r in df_mois.iterrows():
            nom_c = f"{r.get('Prénom','')} {r.get('Nom','').upper()}"
            soc = str(r.get('Société','')).upper()
            nb_j = int(to_f(r.get('NbJours', 1)))
            
            col_n, col_w = st.columns([3, 1])
            col_n.markdown(f"**{r.get('DateNav')}** : {nom_c} (_{soc}_) - **{nb_j} j**")
            
            tel = str(r.get('Téléphone','')).strip().replace(" ","")
            if tel and tel != "nan":
                if tel.startswith("0"): tel = "33" + tel[1:]
                col_w.markdown(f'<a href="https://wa.me/{tel}" target="_blank" style="background:#25d366; color:white; padding:2px 8px; border-radius:10px; text-decoration:none; font-size:0.7rem;">💬 WA</a>', unsafe_allow_html=True)
    else:
        st.info("Aucune navigation ce mois-ci.")

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">💰 STATISTIQUES ANNUELLES</div>', unsafe_allow_html=True)
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        df['Annee'] = df['dt'].dt.year
        df['Mois'] = df['dt'].dt.month
        
        # Tableau récapitulatif
        years = [2026, 2027, 2028]
        stats_data = []
        for y in years:
            temp_df = df[df['Annee'] == y]
            ca = temp_df['PrixJour'].apply(to_f).sum()
            nb = len(temp_df)
            stats_data.append({"Année": y, "Nombre de jours": nb, "Chiffre d'Affaires": f"{int(ca)} €"})
        
        st.table(pd.DataFrame(stats_data))

elif st.session_state.page == "FACTURES":
    st.markdown('<div class="page-title">🧾 GÉNÉRATION DE FACTURE</div>', unsafe_allow_html=True)
    if df.empty: st.warning("Aucune donnée.")
    else:
        soc_list = sorted(df['Société'].unique().astype(str).tolist())
        soc_sel = st.selectbox("Client", ["Tous"] + soc_list)
        df_f = df[df['Société'] == soc_sel] if soc_sel != "Tous" else df
        total = df_f['PrixJour'].apply(to_f).sum()
        st.metric(f"Total {soc_sel}", f"{int(total)} €")
        
        txt = f"Récapitulatif {soc_sel} :\n"
        for _, r in df_f.iterrows():
            txt += f"- {r['DateNav']} : {r['PrixJour']} €\n"
        st.text_area("Copier le texte :", txt + f"\nTOTAL : {int(total)} €")

elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
    st.info("Espace de suivi des entretiens et réparations.")

elif st.session_state.page == "LOGBOOK":
    st.markdown('<div class="page-title">📖 LOGBOOK (JOURNAL)</div>', unsafe_allow_html=True)
    st.write("Historique détaillé des navigations.")
    st.dataframe(df[['DateNav', 'Nom', 'Société', 'Statut']] if not df.empty else pd.DataFrame())

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES PERSONNELLES</div>', unsafe_allow_html=True)
    st.text_area("Bloc-notes :", placeholder="Écrivez vos rappels ici...")






















































































































































































































































































































































