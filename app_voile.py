import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 🛠️ FONCTIONS CORE ---
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Code :", type="password")
    if st.button("CONNECT"):
        if password == "SKIPPER2026": 
            st.session_state.authenticated = True
            st.rerun()
    st.stop()

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"

# --- STYLE CSS (FICHES & BOUTONS) ---
st.markdown("""<style>
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 3px 8px; border-radius: 15px; font-weight: bold; font-size: 0.75rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 2px; font-size: 0.9rem; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    div[data-testid="stExpander"] { border: none !important; }
</style>""", unsafe_allow_html=True)

# --- 2. GITHUB & DATA ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
        requests.put(url, headers={"Authorization": f"token {token}"}, json={"message":"update", "content":content, "sha":sha})
        st.cache_data.clear()
    except: st.error("Erreur save")

df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

# --- 3. MENU ---
m_cols = st.columns(8)
menu = [("👥 CONTACTS","CONTACTS"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">👥 CONTACTS & NAVIGATIONS</div>', unsafe_allow_html=True)
    search = st.text_input("🔍 Rechercher (Nom ou Prénom)", "").strip().lower()
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx="NEW"; st.session_state.page="FORM"; st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        data = df[df['dt'] >= datetime.now().replace(hour=0,minute=0,second=0)] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < datetime.now().replace(hour=0,minute=0,second=0)]
        if search:
            data = data[data['Nom'].str.lower().str.contains(search, na=False) | data['Prénom'].str.lower().str.contains(search, na=False)]

        for i, r in data.sort_values('dt').iterrows():
            statut = str(r.get('Statut','🟡 Attente'))
            b_col = "#2ecc71" if "OK" in statut.upper() else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if str(r.get('Société')).upper()=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{b_col}; border-color:{b_col}; background:{b_col}15;">{statut}</div>
                <span style="font-size:1.3rem; color:#1a2a6c; font-weight:bold;">{r.get('Prénom','')}</span><br>
                <b style="font-size:1.1rem; text-transform:uppercase;">{r.get('Nom','')}</b><br><br>
                📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')} <br>
                📅 {r.get('DateNav','')} | ⏳ {int(to_f(r.get('NbJours',1)))} jours<br>
                🏢 {r.get('Société','')} | 💰 {r.get('PrixJour','0')} €
            </div>""", unsafe_allow_html=True)
            
            c_notes, c_edit, c_del = st.columns([0.8, 0.1, 0.1])
            with c_notes:
                nv = st.text_area("Notes", r.get('Notes',''), key=f"n_{i}", height=68, label_visibility="collapsed")
                if nv != r.get('Notes',''): 
                    df.at[i, 'Notes'] = nv; sauvegarder_data(df, "contacts.json")
            with c_edit:
                if st.button("✏️", key=f"e_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
            with c_del:
                if st.button("🗑️", key=f"d_{i}"): df=df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
    with st.form("fm"):
        c1, c2, c3 = st.columns(3)
        d = c1.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
        l = c2.text_input("Objet")
        m = c3.text_input("Montant (€)")
        if st.form_submit_button("VALIDER FRAIS"):
            df_maint = pd.concat([df_maint, pd.DataFrame([{"Date":d,"Libellé":l,"Montant":m}])], ignore_index=True)
            sauvegarder_data(df_maint, "maintenance.json"); st.rerun()
    st.dataframe(df_maint, use_container_width=True)

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    y = st.selectbox("Année", [2026, 2027, 2028])
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        if not df_maint.empty: df_maint['dt'] = df_maint['Date'].apply(parse_d)
        st_l = []
        for m in range(1, 13):
            dm = df[(df['dt'].dt.year == y) & (df['dt'].dt.month == m)]
            pre = dm[dm['Statut'].str.contains("Attente", na=False)]['PrixJour'].apply(to_f).sum()
            ok = dm[(dm['Statut'].str.contains("OK", na=False)) & (dm.get('Paiement','') == "Paid")]['PrixJour'].apply(to_f).sum()
            fr = df_maint[(df_maint['dt'].dt.year == y) & (df_maint['dt'].dt.month == m)]['Montant'].apply(to_f).sum() if not df_maint.empty else 0
            st_l.append({"Mois": m, "Prévu": int(pre), "Fait": int(ok), "Frais": int(fr), "NET": int(ok-fr)})
        st.table(pd.DataFrame(st_l))

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FORMULAIRE CLIENT</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    row = df.iloc[idx] if idx != "NEW" else {}
    with st.form("f"):
        c1, c2 = st.columns(2)
        f_pre = c1.text_input("Prénom", row.get('Prénom',''))
        f_nom = c2.text_input("Nom", row.get('Nom',''))
        f_dat = c1.text_input("Date (JJ/MM/AAAA)", row.get('DateNav',''))
        f_jou = c2.number_input("Jours", 1, 30, int(to_f(row.get('NbJours',1))))
        f_soc = c1.text_input("Société", row.get('Société',''))
        f_pri = c2.text_input("Prix Total (€)", row.get('PrixJour','0'))
        f_tel = c1.text_input("Tél", row.get('Téléphone',''))
        f_mai = c2.text_input("Mail", row.get('Mail',''))
        f_sta = c1.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=1 if "OK" in str(row.get('Statut')) else 0)
        f_pay = c2.selectbox("Paiement", ["Unpaid", "Paid"], index=1 if row.get('Paiement')=="Paid" else 0)
        if st.form_submit_button("ENREGISTRER"):
            new = {"Nom":f_nom, "Prénom":f_pre, "DateNav":f_dat, "NbJours":f_jou, "Société":f_soc, "PrixJour":f_pri, "Téléphone":f_tel, "Mail":f_mai, "Statut":f_sta, "Paiement":f_pay, "Notes":row.get('Notes','')}
            if idx == "NEW": df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            else: 
                for k,v in new.items(): df.at[idx,k] = v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="CONTACTS"; st.rerun()
    if st.button("ANNULER"): st.session_state.page="CONTACTS"; st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    p_y, p_m = c1.selectbox("An", [2026,2027,2028]), c2.selectbox("Mois", range(1,13), index=datetime.now().month-1)
    occu = {}
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                for j in range(int(to_f(r.get('NbJours',1)))):
                    d_c = r['dt'] + timedelta(days=j)
                    if d_c.year == p_y and d_c.month == p_m:
                        occu[d_c.day] = "day-cmn" if str(r.get('Société')).upper()=="CMN" else "day-ok"
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {style}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    st.markdown("---")
    df_m = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
    for _, r in df_m.iterrows(): st.write(f"📅 **{r['DateNav']}** : {r['Prénom']} {r['Nom'].upper()} - {r['Société']}")








































































































































































































































































































































































