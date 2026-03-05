import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; font-size: 0.8rem; }
    .cal-table td { height: 50px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-green { background-color: #2ecc71 !important; color: white !important; }
    .day-yellow { background-color: #f1c40f !important; color: white !important; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
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
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "cal_m" not in st.session_state: st.session_state.cal_m = datetime.now().month
if "cal_y" not in st.session_state: st.session_state.cal_y = datetime.now().year
if "del_nav_idx" not in st.session_state: st.session_state.del_nav_idx = None
if "del_frais_idx" not in st.session_state: st.session_state.del_frais_idx = None

if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE LISTE (FUTUR / ARCHIVES) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 GESTION DES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view_mode = "FUTUR"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None
        st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt_sort'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        
        if st.session_state.view_mode == "FUTUR":
            data = df[df['dt_sort'] >= now].sort_values('dt_sort', ascending=True)
        else:
            data = df[df['dt_sort'] < now].sort_values('dt_sort', ascending=False)

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, mail = str(r.get('Téléphone','')), str(r.get('Email',''))
            
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold;">{r.get("PrixJour","0")}€</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b> ({r.get("Société","")})<br>
                    📅 <b>{r.get("DateNav","")} — {r.get("NbJours","1")} j</b><br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel if tel else "Appeler"}</a> | ✉️ <a href="mailto:{mail}" class="contact-link">{mail if mail else "Email"}</a><br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            
            # Confirmation Suppression
            if st.session_state.del_nav_idx == i:
                st.warning("Supprimer ?")
                cy, cn = st.columns(2)
                if cy.button("OUI", key=f"y_n_{i}"): df.drop(i).pipe(sauvegarder_data); st.session_state.del_nav_idx=None; st.rerun()
                if cn.button("NON", key=f"n_n_{i}"): st.session_state.del_nav_idx=None; st.rerun()
            else:
                c1, c2 = st.columns(2)
                if c1.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
                if c2.button("🗑️ Supprimer", key=f"dl_{i}"): st.session_state.del_nav_idx=i; st.rerun()

# --- PAGE PLANNING (COULEURS PAR STATUT) ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING & DÉTAILS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    st.session_state.cal_y = c1.selectbox("Année", [2026, 2027, 2028], index=[2026, 2027, 2028].index(st.session_state.cal_y))
    st.session_state.cal_m = c2.selectbox("Mois", range(1, 13), index=st.session_state.cal_m-1)

    occu = {}
    if not df.empty:
        for i, r in df.iterrows():
            d_start = parse_d(r.get('DateNav',''))
            for j in range(int(float(r.get('NbJours',1)))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.month == st.session_state.cal_m and d_curr.year == st.session_state.cal_y:
                    st_val = str(r.get('Statut',''))
                    color_class = "day-green" if "OK" in st_val.upper() or "🟢" in st_val else "day-yellow"
                    occu[d_curr.day] = (i, r, color_class)

    # Grille Calendrier
    cal = calendar.monthcalendar(st.session_state.cal_y, st.session_state.cal_m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0: html += '<td></td>'
            else:
                info = occu.get(day)
                bg = f'class="{info[2]}"' if info else ''
                html += f'<td {bg}>{day}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)

    # Détails par mois (Boutons cliquables)
    st.markdown("### 📋 Détails des sorties")
    month_data = {d: v for d, v in occu.items()}
    if month_data:
        for day in sorted(month_data.keys()):
            idx, res, _ = month_data[day]
            if st.button(f"Le {day:02d} : {res.get('Prénom')} {res.get('Nom')} — {res.get('Statut')}", key=f"p_{day}_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    else: st.info("Aucune navigation ce mois-ci.")

# --- PAGE STATS (DÉTAILS COMPLETS) ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES & REVENUS</div>', unsafe_allow_html=True)
    if not df.empty:
        df_ok = df[df['Statut'].str.contains("OK|🟢", na=False)].copy()
        df_ok['Prix'] = df_ok['PrixJour'].apply(to_f)
        total_ca = df_ok['Prix'].sum()
        total_frais = df_f['Montant'].apply(to_f).sum() if not df_f.empty else 0
        
        st.metric("NET ESTIMÉ", f"{total_ca - total_frais:,.2f} €", f"Total CA: {total_ca:,.2f} €")
        
        st.write("### 📈 Détail des encaissements")
        st.table(df_ok[['DateNav', 'Nom', 'Société', 'Prix']])

# --- PAGE MAINTENANCE (DÉTAILS & SUPPRESSION) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
    with st.expander("➕ AJOUTER UN FRAIS"):
        with st.form("f_form"):
            d_f = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            t_f = st.selectbox("Type", ["Moteur", "Voiles", "Electricité", "Divers"])
            m_f = st.text_input("Montant (€)")
            n_f = st.text_area("Note / Détails")
            if st.form_submit_button("Enregistrer"):
                new = pd.concat([df_f, pd.DataFrame([{"Date":d_f, "Type":t_f, "Montant":m_f, "Note":n_f}])], ignore_index=True)
                sauvegarder_data(new, "frais.json"); st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:#c62828; font-weight:bold;">-{r.get("Montant")}€</div>
                    <b>{r.get("Type")}</b> — {r.get("Date")}<br>
                    <p style="font-size:0.9rem; margin-top:5px; border-top:1px solid #eee; padding-top:5px;">{r.get("Note","")}</p>
                </div>
            ''', unsafe_allow_html=True)
            if st.session_state.del_frais_idx == i:
                c1, c2 = st.columns(2)
                if c1.button("✅ OUI", key=f"yf_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.session_state.del_frais_idx=None; st.rerun()
                if c2.button("❌ NON", key=f"nf_{i}"): st.session_state.del_frais_idx=None; st.rerun()
            else:
                if st.button("🗑️ Supprimer", key=f"df_{i}"): st.session_state.del_frais_idx = i; st.rerun()

# --- FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    st.markdown('<div class="page-title">ÉDITION FICHE NAVIGATION</div>', unsafe_allow_html=True)
    with st.form("f"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom",""))
        f_pre = st.text_input("Prénom", init.get("Prénom",""))
        f_soc = st.text_input("Société", init.get("Société",""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone",""))
        f_eml = st.text_input("Email", init.get("Email",""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.number_input("Nb Jours", min_value=1, value=int(float(init.get("NbJours", 1))))
        f_pri = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom":f_nom, "Prénom":f_pre, "Société":f_soc, "Téléphone":f_tel, "Email":f_eml, "DateNav":f_dat, "NbJours":str(f_nbj), "PrixJour":f_pri, "Statut":f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()













































































































































































