import requests
import base64
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import calendar

# --- 🛠️ FONCTIONS DE SÉCURITÉ ---
def to_f(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def parse_d(d_str):
    try: return datetime.strptime(str(d_str), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

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

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 2px; font-size: 0.9rem; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 5px; text-decoration: none; color: white !important; font-weight: bold; margin-right: 5px; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

# --- 2. GESTION DES DONNÉES ---
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
        st.success("Données enregistrées !")
    except: st.error("Erreur de sauvegarde")

df = charger_data("contacts.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("👥 CONTACTS","CONTACTS"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","STATS"), ("📖 LOGS","LOGS"), ("📄 FACT","FACTURES"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","MAINT"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, key=f"btn_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. LOGIQUE DES PAGES ---

if st.session_state.page == "CONTACTS":
    st.markdown('<div class="page-title">👥 MES CONTACTS</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE NAVIGATION", use_container_width=True):
        st.session_state.edit_idx = "NEW"; st.session_state.page = "FORM"; st.rerun()

    search_term = st.text_input("🔍 Rechercher...", "").strip().lower()
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
            data = data[(data['Nom'].str.lower().str.contains(search_term, na=False)) | (data['Prénom'].str.lower().str.contains(search_term, na=False))]
        
        for i, r in data.sort_values('dt').iterrows():
            soc = str(r.get('Société','')).upper()
            statut = str(r.get('Statut','🟡 Attente'))
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            nb_j = int(to_f(r.get('NbJours', 1)))
            b_col = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{b_col}; border-color:{b_col}; background:{b_col}15;">{statut}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                Société : <b>{soc}</b> | Date : {r.get('DateNav')} <b>({nb_j} j)</b><br>
                📞 {tel} | ✉️ {mail}<br><br>
                <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appel</a>
                <a href="https://wa.me/{tel.replace(' ','')}" target="_blank" class="btn-contact" style="background:#25d366;">WhatsApp</a>
            </div>""", unsafe_allow_html=True)
            
            ce, cd, cs = st.columns([1, 1, 5])
            if ce.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
            if cd.button("🗑️", key=f"del_{i}"): df=df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING DE NAVIGATION</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    p_y = c1.selectbox("Année", [2026, 2027, 2028], index=0)
    p_m = c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    occu = {}
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_debut = r['dt']
                n_jours = int(to_f(r.get('NbJours', 1)))
                s_name = str(r.get('Société','')).upper()
                for j in range(n_jours):
                    curr = d_debut + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        occu[curr.day] = "day-cmn" if s_name == "CMN" else "day-ok"

    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {style}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

    # --- LISTE DES CONTACTS DU MOIS SÉLECTIONNÉ ---
    st.markdown("---")
    st.subheader(f"👥 Sorties de {calendar.month_name[p_m]} {p_y}")
    if not df.empty:
        df_m = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
        if not df_m.empty:
            for _, r in df_m.iterrows():
                st.write(f"📅 **{r['DateNav']}** : {r['Prénom']} {r['Nom'].upper()} ({int(to_f(r['NbJours']))} j) - _{r['Société']}_")
        else:
            st.info("Aucune navigation ce mois-ci.")

elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">💰 STATISTIQUES & CHIFFRE D\'AFFAIRES</div>', unsafe_allow_html=True)
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        res = []
        for y in [2025, 2026, 2027, 2028]:
            sub = df[df['dt'].dt.year == y]
            ca = sub['PrixJour'].apply(to_f).sum()
            res.append({"Année": y, "Nb Navigations": len(sub), "CA (€)": f"{int(ca)} €"})
        st.table(pd.DataFrame(res))

elif st.session_state.page == "LOGS":
    st.markdown('<div class="page-title">📖 HISTORIQUE & PAIEMENTS</div>', unsafe_allow_html=True)
    if not df.empty:
        df_display = df[['DateNav', 'Nom', 'Prénom', 'Société', 'Statut', 'Paiement']].copy()
        st.dataframe(df_display.sort_values('DateNav', ascending=False), use_container_width=True)

elif st.session_state.page == "FACTURES":
    st.markdown('<div class="page-title">📄 GESTION DE LA FACTURATION</div>', unsafe_allow_html=True)
    if not df.empty:
        soc_list = sorted(df['Société'].unique().tolist())
        sel_soc = st.selectbox("Filtrer par société", soc_list)
        df_f = df[df['Société'] == sel_soc]
        total = df_f['PrixJour'].apply(to_f).sum()
        st.metric(f"Total à facturer - {sel_soc}", f"{int(total)} €")

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FORMULAIRE NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    row = df.iloc[idx] if idx != "NEW" and idx is not None else {}
    with st.form("form_v"):
        f1, f2 = st.columns(2)
        nom = f1.text_input("Nom", row.get('Nom',''))
        pre = f2.text_input("Prénom", row.get('Prénom',''))
        dat = f1.text_input("Date (JJ/MM/AAAA)", row.get('DateNav',''))
        jou = f2.number_input("Jours", 1, 30, int(to_f(row.get('NbJours',1))))
        soc = f1.selectbox("Société", ["CMN", "PARTICULIER", "AUTRE"], index=0 if row.get('Société')=="CMN" else 1)
        pri = f2.text_input("Prix Total (€)", row.get('PrixJour','0'))
        tel = f1.text_input("Téléphone", row.get('Téléphone',''))
        mai = f2.text_input("Mail", row.get('Mail',''))
        sta = f1.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=1 if "OK" in str(row.get('Statut')) else 0)
        pay = f2.selectbox("Paiement", ["Unpaid", "Paid"], index=1 if row.get('Paiement')=="Paid" else 0)
        
        if st.form_submit_button("VALIDER"):
            new = {"Nom":nom, "Prénom":pre, "DateNav":dat, "NbJours":jou, "Société":soc, "PrixJour":pri, "Téléphone":tel, "Mail":mai, "Statut":sta, "Paiement":pay}
            if idx == "NEW": df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
            else: 
                for k,v in new.items(): df.at[idx,k] = v
            sauvegarder_data(df, "contacts.json")
            st.session_state.page="CONTACTS"; st.rerun()
    if st.button("RETOUR"): st.session_state.page="CONTACTS"; st.rerun()



































































































































































































































































































































































