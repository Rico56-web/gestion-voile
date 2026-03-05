import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS AVANCÉ ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; border-bottom: 1px dotted #1a2a6c; }
    
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { background: #1a2a6c; color: white; padding: 10px; font-size: 0.8rem; border: 1px solid #ddd; }
    .cal-table td { height: 70px; text-align: center; vertical-align: top; border: 1px solid #ddd; padding: 5px; font-weight: bold; }
    .day-busy { background-color: #2ecc71 !important; color: white !important; border: 2px solid #27ae60 !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; shadow: 0 2px 4px rgba(0,0,0,0.1); border: 1px solid #eee; }
    .frais-note { background: #f9f9f9; padding: 8px; border-radius: 4px; font-size: 0.85rem; color: #555; margin-top: 8px; border-left: 3px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=2)
def charger_data(file="contacts.json"):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_f(v): 
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def parse_d(d):
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "cal_m" not in st.session_state: st.session_state.cal_m = datetime.now().month
if "cal_y" not in st.session_state: st.session_state.cal_y = datetime.now().year

if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if cols[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE PLANNING (TRI PAR MOIS & ANNÉES JUSQU'A 2028) ---
if st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING & DISPONIBILITÉS</div>', unsafe_allow_html=True)
    
    # Sélecteurs Année et Mois
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.cal_y = st.selectbox("Année", range(2024, 2029), index=range(2024, 2029).index(st.session_state.cal_y))
    with c2:
        mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        st.session_state.cal_m = st.selectbox("Mois", range(1, 13), format_func=lambda x: mois_noms[x-1], index=st.session_state.cal_m-1)

    # Logique d'occupation
    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            for j in range(int(float(r.get('NbJours',1)))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.month == st.session_state.cal_m and d_curr.year == st.session_state.cal_y:
                    occu[d_curr.day] = r

    # Génération du calendrier
    cal = calendar.monthcalendar(st.session_state.cal_y, st.session_state.cal_m)
    html = '<table class="cal-table"><tr><th>LUN</th><th>MAR</th><th>MER</th><th>JEU</th><th>VEN</th><th>SAM</th><th>DIM</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0: html += '<td></td>'
            else:
                r = occu.get(day)
                cls = ""
                content = f"{day}"
                if r is not None:
                    st_val = str(r.get('Statut',''))
                    cls = 'class="day-busy"' if "OK" in st_val.upper() or "🟢" in st_val else 'class="day-wait"'
                    content += f'<br><span style="font-size:0.6rem;">{r.get("Nom")[:8]}</span>'
                html += f'<td {cls}>{content}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    
    # Détails du mois
    if occu:
        st.markdown("### 📋 Détails des sorties")
        for d, r in sorted(occu.items()):
            tel = str(r.get('Téléphone',''))
            st.info(f"**Le {d:02d}** : {r.get('Prénom')} {r.get('Nom')} ({r.get('Société')}) - 📞 [Appeler](tel:{tel})")

# --- PAGE MAINTENANCE (DÉTAILS COMPLETS) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & TRAVAUX</div>', unsafe_allow_html=True)
    
    with st.expander("➕ ENREGISTRER UNE OPÉRATION / FRAIS"):
        with st.form("frais_form"):
            date_f = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            type_f = st.selectbox("Catégorie", ["Moteur", "Gréement/Voiles", "Électricité", "Coque/Pont", "Équipement Sécurité", "Divers"])
            montant_f = st.text_input("Montant (€)")
            note_f = st.text_area("Description détaillée des travaux")
            if st.form_submit_button("Sauvegarder l'intervention"):
                new_f = pd.concat([df_f, pd.DataFrame([{"Date":date_f, "Type":type_f, "Montant":montant_f, "Note":note_f}])], ignore_index=True)
                sauvegarder_data(new_f, "frais.json"); st.rerun()

    if not df_f.empty:
        # Tri par date décroissante
        df_f['dt_sort'] = df_f['Date'].apply(parse_d)
        for i, r in df_f.sort_values('dt_sort', ascending=False).iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:#c62828; font-weight:bold; font-size:1.2rem;">{r.get("Montant")} €</div>
                    <b style="font-size:1.1rem; color:#1a2a6c;">{r.get("Type").upper()}</b><br>
                    <small>📅 Date d'intervention : {r.get("Date")}</small>
                    <div class="frais-note">
                        <b>Détail :</b><br>{r.get("Note","Aucun détail renseigné.")}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("🗑️ Supprimer l'entrée", key=f"del_f_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- RESTE DU CODE (LISTE, FORM, STATS) ---
# [Le reste du code (Liste et Stats) est identique à la version précédente pour assurer la stabilité]











































































































































































