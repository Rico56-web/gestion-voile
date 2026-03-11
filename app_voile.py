import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 🛠️ FONCTIONS ---
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

st.markdown("""<style>
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 3px 8px; border-radius: 15px; font-weight: bold; font-size: 0.75rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 2px; font-size: 0.9rem; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .stButton>button { padding: 2px 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. GITHUB ---
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

# --- 3. MENU ---
m_cols = st.columns(8)
menu = [("👥 CONTACTS","CONTACTS"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">👥 MES CONTACTS</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVEAU", use_container_width=True):
        st.session_state.edit_idx="NEW"; st.session_state.page="FORM"; st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        data = df[df['dt'] >= datetime.now().replace(hour=0,minute=0,second=0)] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < datetime.now().replace(hour=0,minute=0,second=0)]
        
        for i, r in data.sort_values('dt').iterrows():
            statut = str(r.get('Statut','🟡 Attente'))
            b_col = "#2ecc71" if "OK" in statut.upper() else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            
            # --- ORDRE STRICT : Nom, Prénom / Tél, Mail / Date, Jours / Société, Prix ---
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if str(r.get('Société'))=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{b_col}; border-color:{b_col}; background:{b_col}15;">{statut}</div>
                <b style="font-size:1.2rem;">{r.get('Nom','').upper()} {r.get('Prénom','')}</b><br>
                📞 {r.get('Téléphone','')} | ✉️ {r.get('Mail','')} <br>
                📅 {r.get('DateNav','')} | ⏳ {int(to_f(r.get('NbJours',1)))} jours<br>
                🏢 {r.get('Société','')} | 💰 {r.get('PrixJour','0')} €
            </div>""", unsafe_allow_html=True)
            
            # Boutons sur la même ligne et petits
            col_notes, col_btn = st.columns([0.85, 0.15])
            with col_notes:
                note_val = st.text_area("Notes", value=r.get('Notes',''), key=f"nt_{i}", height=68, label_visibility="collapsed")
                if note_val != r.get('Notes',''):
                    df.at[i, 'Notes'] = note_val
                    sauvegarder_data(df, "contacts.json")
            with col_btn:
                if st.button("✏️", key=f"ed_{i}", use_container_width=True): 
                    st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
                if st.button("🗑️", key=f"dl_{i}", use_container_width=True): 
                    df=df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">💰 STATS ANNUELLES</div>', unsafe_allow_html=True)
    sel_y = st.selectbox("Année", [2026, 2027, 2028])
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        df_y = df[df['dt'].dt.year == sel_y]
        stats_m = []
        for m in range(1, 13):
            df_m = df_y[df_y['dt'].dt.month == m]
            p_col = 'Paiement' if 'Paiement' in df_m.columns else None
            prevu = df_m[df_m['Statut'].str.contains("Attente", na=False)]['PrixJour'].apply(to_f).sum()
            df_ok = df_m[(df_m['Statut'].str.contains("OK", na=False)) & (df_m[p_col] == "Paid")] if p_col else pd.DataFrame()
            fait = df_ok['PrixJour'].apply(to_f).sum() if not df_ok.empty else 0
            frais = df_m['Frais'].apply(to_f).sum() if 'Frais' in df_m.columns else 0
            stats_m.append({"Mois": m, "Prévu (€)": int(prevu), "Fait (€)": int(fait), "Frais (€)": int(frais), "NET (€)": int(fait - frais)})
        st.table(pd.DataFrame(stats_m))

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    p_y = c1.selectbox("Année", [2026, 2027, 2028])
    p_m = c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    occu = {}
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_deb = r['dt']
                for j in range(int(to_f(r.get('NbJours', 1)))):
                    curr = d_deb + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        occu[curr.day] = "day-cmn" if str(r.get('Société'))=="CMN" else "day-ok"

    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {style}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    
    # RETOUR DE LA LISTE DU MOIS
    st.markdown("---")
    st.subheader(f"Détails de {calendar.month_name[p_m]} {p_y}")
    df_list = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
    if not df_list.empty:
        for _, r in df_list.iterrows():
            st.write(f"📅 **{r['DateNav']}** : {r['Prénom']} {r['Nom'].upper()} ({int(to_f(r['NbJours']))} j) - {r['Société']}")
    else:
        st.info("Aucune navigation ce mois-ci.")

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FORMULAIRE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    row = df.iloc[idx] if idx != "NEW" else {}
    with st.form("form_v"):
        c1, c2 = st.columns(2)
        f_nom = c1.text_input("Nom", row.get('Nom',''))
        f_pre = c2.text_input("Prénom", row.get('Prénom',''))
        f_dat = c1.text_input("Date (JJ/MM/AAAA)", row.get('DateNav',''))
        f_jou = c2.number_input("Nombre de jours", 1, 30, int(to_f(row.get('NbJours',1))))
        f_soc = c1.selectbox("Société", ["CMN", "PARTICULIER", "AUTRE"], index=0 if row.get('Société')=="CMN" else 1)
        f_pri = c2.text_input("Prix Total (€)", row.get('PrixJour','0'))
        f_fra = c1.text_input("Frais (€)", row.get('Frais','0'))
        f_tel = c2.text_input("Téléphone", row.get('Téléphone',''))
        f_mai = c1.text_input("Email", row.get('Mail',''))
        f_sta = c2.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=1 if "OK" in str(row.get('Statut')) else 0)
        f_pay = c1.selectbox("Paiement", ["Unpaid", "Paid"], index=1 if row.get('Paiement')=="Paid" else 0)
        if st.form_submit_button("VALIDER"):
            new_entry = {"Nom":f_nom, "Prénom":f_pre, "DateNav":f_dat, "NbJours":f_jou, "Société":f_soc, "PrixJour":f_pri, "Frais":f_fra, "Téléphone":f_tel, "Mail":f_mai, "Statut":f_sta, "Paiement":f_pay, "Notes":row.get('Notes','')}
            if idx == "NEW": df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            else: 
                for k,v in new_entry.items(): df.at[idx,k] = v
            sauvegarder_data(df, "contacts.json")
            st.session_state.page="CONTACTS"; st.rerun()
    if st.button("RETOUR"): st.session_state.page="CONTACTS"; st.rerun()






































































































































































































































































































































































