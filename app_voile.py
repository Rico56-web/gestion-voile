import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & LOGIN ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div style="background:#1a2a6c;color:white;padding:20px;border-radius:10px;text-align:center;">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "1234": # <--- Ton code à modifier si besoin
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Code incorrect ❌")
    st.stop()

# Initialisation stable des variables
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin-top:5px; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES (GITHUB) ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    st.cache_data.clear()

def to_f(v): 
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")
def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# Callbacks pour la stabilité mobile
def nav_to(p): st.session_state.page = p
def set_view(v): st.session_state.view_mode = v
def edit_nav(i): st.session_state.edit_idx = i; st.session_state.page = "FORM"
def edit_f(i): st.session_state.edit_f_idx = i
def edit_n(i): st.session_state.edit_n_idx = i

df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(5)
btns = [("📋","LISTE"), ("🗓️","PLANNING"), ("💰","BUDGET"), ("🔧","FRAIS"), ("📝","NOTES")]
for i, (l, p) in enumerate(btns):
    cols[i].button(l, on_click=nav_to, args=(p,), use_container_width=True, type="primary" if st.session_state.page==p else "secondary")

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("🚀 FUTURES", on_click=set_view, args=("FUTURES",), use_container_width=True)
    c2.button("📂 PASSÉES", on_click=set_view, args=("PASSÉES",), use_container_width=True)
    st.button("➕ NOUVELLE FICHE", on_click=edit_nav, args=("NEW",), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        data = df[df['dt'] >= datetime.now().replace(hour=0,minute=0,second=0)] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < datetime.now().replace(hour=0,minute=0,second=0)]
        for i, r in data.sort_values('dt').iterrows():
            soc, stt = str(r.get('Société','')).strip(), str(r.get('Statut','🟡'))
            col = "#3498db" if soc.upper() == "CMN" else ("#2ecc71" if "OK" in stt or "🟢" in stt else "#f1c40f")
            tel = str(r.get('Téléphone','')).strip()
            cln = "".join(filter(str.isdigit, tel))
            st.markdown(f"""<div class="client-card" style="border-left:12px solid {col}">
                <div style="float:right;font-weight:bold;">{fmt_p(r.get('PrixJour'))}</div>
                <b>{r.get('Prénom')} {r.get('Nom').upper()}</b> ({soc})<br>
                📅 {r.get('DateNav')} ({r.get('NbJours')}j)<br>
                📧 <a href="mailto:{r.get('Email')}">{r.get('Email')}</a><br>
                📞 <a href="tel:{cln}">{tel}</a><br>
                <a href="https://wa.me/{cln}" target="_blank" class="wa-btn">💬 WhatsApp</a><br>
                <b>{stt}</b></div>""", unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            ce.button("✏️", key=f"ed_{i}", on_click=edit_nav, args=(i,))
            if cd.checkbox("🗑️", key=f"del_{i}"):
                if st.button("Confirmer", key=f"conf_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y, m = st.columns(2)
    sel_y = y.selectbox("An", [2025, 2026], index=1)
    sel_m = m.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu = {}
    for _, r in df.iterrows():
        if "🔴" not in str(r.get('Statut','')):
            ds = parse_d(r.get('DateNav'))
            for j in range(int(to_f(r.get('NbJours',1)))):
                cur = ds + timedelta(days=j)
                if cur.year == sel_y and cur.month == sel_m:
                    occu[cur.day] = "day-cmn" if "CMN" in str(r.get('Société','')).upper() else "day-ok"
    cal = calendar.monthcalendar(sel_y, sel_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d!=0 else ""}</td>'
        h += '</tr>'
    st.markdown(h+'</table>', unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS</div>', unsafe_allow_html=True)
    sy = st.selectbox("Année", [2025, 2026], index=1)
    df['dt'] = df['DateNav'].apply(parse_d)
    ca = sum(df[(df['dt'].dt.year==sy) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.metric("Total Encaissé", fmt_p(ca))
    res = []
    for i in range(1,13):
        m_r = sum(df[(df['dt'].dt.year==sy) & (df['dt'].dt.month==i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        res.append({"Mois": calendar.month_name[i], "Revenu": fmt_p(m_r)})
    st.table(pd.DataFrame(res).set_index('Mois'))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {"Date":"","Montant":"0","Note":""}
        with st.form("ff"):
            d, m, n = st.text_input("Date", init.get("Date")), st.text_input("Montant", str(init.get("Montant"))), st.text_area("Note", init.get("Note"))
            if st.form_submit_button("SAUVER"):
                row = {"Date":d, "Montant":m, "Note":n}
                if idx=="NEW": df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_f.at[idx,k]=v
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx=None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_f_idx=None; st.rerun()
    else:
        st.button("➕ AJOUTER FRAIS", on_click=edit_f, args=("NEW",), use_container_width=True)
        for i, r in df_f.sort_index(ascending=False).iterrows():
            st.info(f"**{r.get('Date')} - {fmt_p(r.get('Montant'))}**\n\n{r.get('Note')}")
            if st.button("✏️", key=f"fe_{i}"): st.session_state.edit_f_idx=i; st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if idx != "NEW" else {"Titre":"","Contenu":""}
        with st.form("fn"):
            t, c = st.text_input("Titre", init.get("Titre")), st.text_area("Contenu", init.get("Contenu"))
            if st.form_submit_button("SAUVER"):
                row = {"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_n_idx=None; st.rerun()
    else:
        st.button("➕ NOTE", on_click=edit_n, args=("NEW",), use_container_width=True)
        for i, r in df_n.sort_index(ascending=False).iterrows():
            st.warning(f"**{r.get('Titre')}** ({r.get('Date')})\n\n{r.get('Contenu')}")
            if st.button("✏️", key=f"ne_{i}"): st.session_state.edit_n_idx=i; st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("f_nav"):
        stt = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"])
        p, n, s = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Société", init.get("Société",""))
        d, j = st.text_input("Date", init.get("DateNav","")), st.text_input("Jours", str(init.get("NbJours","1")))
        t, em = st.text_input("Tel", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix", str(init.get("PrixJour","0")))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":stt}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    st.button("Retour", on_click=nav_to, args=("LISTE",))
































































































































































































































