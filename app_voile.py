import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# 1. CONFIG & LOGIN
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("Code :", type="password")
    if st.button("OK"):
        if pwd == "1234": st.session_state.auth = True; st.rerun()
        else: st.error("❌")
    st.stop()

for k, v in {"page":"LISTE", "view":"FUTURES", "e_idx":None, "f_idx":None, "n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

# 2. FONCTIONS
@st.cache_data(ttl=1)
def load(f):
    try:
        r, t = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{r}/contents/{f}", headers={"Authorization":f"token {t}"})
        return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: return pd.DataFrame()

def save(df, f):
    r, t = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    u = f"https://api.github.com/repos/{r}/contents/{f}"
    res = requests.get(u, headers={"Authorization":f"token {t}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    ct = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(u, headers={"Authorization":f"token {t}"}, json={"message":"up", "content":ct, "sha":sha})
    st.cache_data.clear()

def to_f(v): 
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")
def p_d(d):
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000,1,1)

df, df_f, df_n = load("contacts.json"), load("frais.json"), load("notes.json")

# 3. MENU
st.markdown('<style>.page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px; } .card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border-left: 10px solid #ccc; border: 1px solid #ddd; } .wa { background:#25D366; color:white!important; padding:4px 8px; border-radius:5px; text-decoration:none; font-size:0.8rem; }</style>', unsafe_allow_html=True)
c = st.columns(5)
menu = [("📋","LISTE"), ("🗓️","PLANNING"), ("💰","BUDGET"), ("🔧","FRAIS"), ("📝","NOTES")]
for i, (l, p) in enumerate(menu):
    if c[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"): st.session_state.page=p; st.rerun()

# 4. PAGES
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉ", use_container_width=True): st.session_state.view="PASSÉES"; st.rerun()
    if st.button("➕ NOUVEAU", use_container_width=True): st.session_state.e_idx="NEW"; st.session_state.page="FORM"; st.rerun()
    if not df.empty:
        df['dt'] = df['dt_p'] = df['DateNav'].apply(p_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt_p'] >= now] if st.session_state.view=="FUTURES" else df[df['dt_p'] < now]
        for i, r in data.sort_values('dt_p').iterrows():
            soc, stt = str(r.get('Société','')), str(r.get('Statut','🟡'))
            col = "#3498db" if "CMN" in soc.upper() else ("#2ecc71" if "OK" in stt or "🟢" in stt else "#f1c40f")
            tel = str(r.get('Téléphone','')).strip()
            cln = "".join(filter(str.isdigit, tel))
            st.markdown(f'<div class="card" style="border-left:10px solid {col}"><b>{r.get("Prénom")} {r.get("Nom").upper()}</b> ({soc})<br>📅 {r.get("DateNav")} ({r.get("NbJours")}j)<br>📧 <a href="mailto:{r.get("Email")}">{r.get("Email")}</a><br>📞 <a href="tel:{cln}">{tel}</a><br><a href="https://wa.me/{cln}" class="wa">💬 WhatsApp</a><br><b>{stt}</b> | {fmt(r.get("PrixJour"))}</div>', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.e_idx=i; st.session_state.page="FORM"; st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y, m = st.selectbox("An", [2025, 2026], 1), st.selectbox("Mois", range(1,13), datetime.now().month-1)
    occu = {}
    for i, r in df.iterrows():
        if "🔴" not in str(r.get('Statut','')):
            d_s = p_d(r.get('DateNav'))
            for j in range(int(to_f(r.get('NbJours',1)))):
                curr = d_s + timedelta(days=j)
                if curr.year == y and curr.month == m:
                    occu[curr.day] = "#3498db" if "CMN" in str(r.get('Société','')).upper() else "#2ecc71"
    cal = calendar.monthcalendar(y, m)
    h = '<table style="width:100%; text-align:center; border-collapse:collapse;">'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'background:{occu[d]}; color:white;' if d in occu else ''
            h += f'<td style="border:1px solid #ddd; padding:10px; {bg}">{d if d!=0 else ""}</td>'
        h += '</tr>'
    st.markdown(h+'</table>', unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS</div>', unsafe_allow_html=True)
    y = st.selectbox("Année", [2025, 2026], 1)
    df['dt'] = df['DateNav'].apply(p_d)
    rev = sum(df[(df['dt'].dt.year==y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.metric("Total encaissé", fmt(rev))
    res = []
    for i in range(1,13):
        m_r = sum(df[(df['dt'].dt.year==y) & (df['dt'].dt.month==i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        res.append({"Mois": calendar.month_name[i], "CA": fmt(m_r)})
    st.table(pd.DataFrame(res).set_index('Mois'))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.button("➕ AJOUTER"): st.session_state.f_idx="NEW"; st.rerun()
    if st.session_state.f_idx is not None:
        with st.form("f"):
            d, m, n = st.text_input("Date"), st.text_input("Montant"), st.text_area("Note")
            if st.form_submit_button("Sauver"):
                new = pd.DataFrame([{"Date":d, "Montant":m, "Note":n}])
                df_f = pd.concat([df_f, new], ignore_index=True); save(df_f, "frais.json"); st.session_state.f_idx=None; st.rerun()
    for i, r in df_f.iterrows(): st.info(f"{r.get('Date')} - {fmt(r.get('Montant'))}\n{r.get('Note')}")

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.button("➕ NOTE"): st.session_state.n_idx="NEW"; st.rerun()
    if st.session_state.n_idx is not None:
        with st.form("n"):
            t, c = st.text_input("Titre"), st.text_area("Contenu")
            if st.form_submit_button("Sauver"):
                df_n = pd.concat([df_n, pd.DataFrame([{"Titre":t, "Contenu":c}])], ignore_index=True); save(df_n, "notes.json"); st.session_state.n_idx=None; st.rerun()
    for i, r in df_n.iterrows(): st.warning(f"**{r.get('Titre')}**\n\n{r.get('Contenu')}")

elif st.session_state.page == "FORM":
    idx = st.session_state.e_idx; init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("ef"):
        stt = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"])
        p, n, s = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Société", init.get("Société",""))
        d, j = st.text_input("Date", init.get("DateNav","")), st.text_input("Jours", str(init.get("NbJours","1")))
        t, em = st.text_input("Tel", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix", str(init.get("PrixJour","0")))
        if st.form_submit_button("Sauver"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":stt}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            save(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page="LISTE"; st.rerun()































































































































































































































