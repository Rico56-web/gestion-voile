import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS (PRO & LISIBLE) ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    
    /* Fiches Liste */
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
    
    /* Calendrier Visuel */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-table th { background: #f1f2f6; padding: 10px; font-size: 0.8rem; border: 1px solid #ddd; }
    .cal-table td { height: 60px; text-align: center; vertical-align: middle; border: 1px solid #ddd; font-weight: bold; position: relative; }
    .day-busy { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    
    /* Stats & Maintenance */
    .recap-box { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #1a2a6c; text-align: center; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 12px; border-radius: 8px; border-left: 8px solid #c62828; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
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
for key, val in {"page":"LISTE", "auth":False, "cal_m":datetime.now().month, "cal_y":datetime.now().year}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.auth:
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

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 GESTION DES NAVIGATIONS</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"
        st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for i, r in df.sort_values('dt', ascending=False).iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, mail = str(r.get('Téléphone','')), str(r.get('Email',''))
            
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold; color:#1a2a6c;">{r.get("PrixJour","0")}€</div>
                    <b style="font-size:1.1rem;">{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                    <small>🏢 {r.get("Société","")}</small><br>
                    📅 <b>{r.get("DateNav","")}</b> | ⏱️ <b>{r.get("NbJours","1")} jour(s)</b><br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel if tel else "Appeler"}</a> | 
                    ✉️ <a href="mailto:{mail}" class="contact-link">{mail if mail else "Email"}</a><br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"e_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if c2.button("🗑️ Supprimer", key=f"d_{i}"): 
                df.drop(i).pipe(sauvegarder_data); st.rerun()

# --- PAGE PLANNING (RETOUR CALENDRIER) ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING VISUEL</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"):
        st.session_state.cal_m -= 1
        if st.session_state.cal_m < 1: st.session_state.cal_m=12; st.session_state.cal_y-=1
        st.rerun()
    c2.markdown(f"<center><h3>{st.session_state.cal_m:02d} / {st.session_state.cal_y}</h3></center>", unsafe_allow_html=True)
    if c3.button("▶️"):
        st.session_state.cal_m += 1
        if st.session_state.cal_m > 12: st.session_state.cal_m=1; st.session_state.cal_y+=1
        st.rerun()

    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            for j in range(int(float(r.get('NbJours',1)))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.month == st.session_state.cal_m and d_curr.year == st.session_state.cal_y:
                    occu[d_curr.day] = r

    cal = calendar.monthcalendar(st.session_state.cal_y, st.session_state.cal_m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0: html += '<td></td>'
            else:
                bg = 'class="day-busy"' if day in occu else ''
                html += f'<td {bg}>{day}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    
    if occu:
        st.markdown("---")
        for d, r in sorted(occu.items()):
            st.write(f"**Jour {d}** : {r.get('Prénom')} {r.get('Nom')} ({r.get('Société')})")

# --- PAGE STATS (BUDGET) ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN FINANCIER 2026</div>', unsafe_allow_html=True)
    ca = sum(df[df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f)) if not df.empty else 0
    fr = sum(df_f['Montant'].apply(to_f)) if not df_f.empty else 0
    st.markdown(f'''
        <div class="recap-box">
            <h2 style="color:#1a2a6c;">NET : {ca - fr:.2f}€</h2>
            <p>Revenus (OK) : {ca:.2f}€ | Maintenance : {fr:.2f}€</p>
        </div>
    ''', unsafe_allow_html=True)
    if not df.empty:
        st.write("### Détail par Navigation")
        st.dataframe(df[['DateNav', 'Nom', 'PrixJour', 'Statut']])

# --- PAGE MAINTENANCE (FRAIS) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE DU BATEAU</div>', unsafe_allow_html=True)
    with st.expander("➕ AJOUTER UN FRAIS"):
        with st.form("add_f"):
            d = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            t = st.selectbox("Type", ["Moteur", "Voiles", "Electricité", "Divers"])
            m = st.text_input("Montant (€)")
            n = st.text_area("Note / Détails")
            if st.form_submit_button("Enregistrer"):
                new_f = pd.concat([df_f, pd.DataFrame([{"Date":d, "Type":t, "Montant":m, "Note":n}])], ignore_index=True)
                sauvegarder_data(new_f, "frais.json"); st.rerun()
    
    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:#c62828; font-weight:bold;">-{r.get("Montant")}€</div>
                    <b>{r.get("Type")}</b> - {r.get("Date")}<br>
                    <p style="font-size:0.9rem; margin-top:5px;">{r.get("Note","")}</p>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("🗑️", key=f"df_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- PAGE FORMULAIRE (NAV) ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    st.markdown(f'<div class="page-title">{"MODIFIER" if idx is not None else "NOUVELLE"} NAVIGATION</div>', unsafe_allow_html=True)
    with st.form("nav"):
        st_val = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        nom = st.text_input("Nom", init.get("Nom",""))
        pre = st.text_input("Prénom", init.get("Prénom",""))
        soc = st.text_input("Société", init.get("Société",""))
        tel = st.text_input("Téléphone", init.get("Téléphone",""))
        eml = st.text_input("Email", init.get("Email",""))
        dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", datetime.now().strftime("%d/%m/%Y")))
        nbj = st.number_input("Nombre de jours", min_value=1, value=int(float(init.get("NbJours", 1))))
        pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom":nom, "Prénom":pre, "Société":soc, "Téléphone":tel, "Email":eml, "DateNav":dat, "NbJours":str(nbj), "PrixJour":pri, "Statut":st_val}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Annuler"): st.session_state.page = "LISTE"; st.rerun()










































































































































































