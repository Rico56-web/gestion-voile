import streamlit as st
import pandas as pd
import json, base64, requests, calendar
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

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

# Initialisation des états
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_s_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

if "cible_annuelle" not in st.session_state:
    st.session_state.cible_annuelle = 15000.0

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
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

df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
m_cols = st.columns(7)
menu = [
    ("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), 
    ("📖 LOG","LOGBOOK"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")
]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        for i, r in data.sort_values('dt').iterrows():
            soc, statut, nb_j = str(r.get('Société','')).upper(), str(r.get('Statut','🟡 Attente')), str(r.get('NbJours','1'))
            badge_color = "#2ecc71" if "🟢" in statut or "OK" in statut.upper() else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            tel = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            st.markdown(f"""<div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                <div class="status-badge" style="color:{badge_color}; border-color:{badge_color}; background:{badge_color}15;">{statut}</div>
                <b>{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} <b>({nb_j}j)</b><br>
                📧 <a href="mailto:{r.get('Email','')}">{r.get('Email','')}</a><br>
                📞 <a href="tel:{tel}">{r.get('Téléphone','')}</a>
            </div>""", unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            if ce.button("✏️", key=f"ed_l_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if cd.checkbox("🗑️", key=f"del_l_{i}"):
                if st.button("Confirmer", key=f"conf_l_{i}"): 
                    df = df.drop(i)
                    sauvegarder_data(df, "contacts.json")
                    st.rerun()

elif st.session_state.page == "LOGBOOK":
    st.markdown('<div class="page-title">📖 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    with st.form("f_log_complet"):
        st.subheader("🚩 DÉPART")
        c1, c2 = st.columns(2)
        d_lieu = c1.text_input("Port / Mouillage (Départ)", key="d_l")
        d_met = c2.selectbox("Météo (Départ)", ["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"], key="d_m")
        c3, c4 = st.columns(2)
        d_h = c3.number_input("Heures Moteur (Départ)", step=0.1, key="d_h")
        d_mi = c4.number_input("Loch / Milles (Départ)", step=0.1, key="d_mi")
        
        st.markdown("--- ⛵ **EN COURS** ---")
        obs = st.text_area("Observations (Virements, dauphins, technique...)", height=100)
        
        st.markdown("--- 🏁 **ARRIVÉE** ---")
        c5, c6 = st.columns(2)
        a_lieu = c5.text_input("Port / Mouillage (Arrivée)", key="a_l")
        a_met = c6.selectbox("Météo (Arrivée)", ["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"], key="a_m")
        c7, c8 = st.columns(2)
        a_h = c7.number_input("Heures Moteur (Arrivée)", step=0.1, key="a_h")
        a_mi = c8.number_input("Loch / Milles (Arrivée)", step=0.1, key="a_mi")

        if st.form_submit_button("⚓ ENREGISTRER L'ÉTAPE", use_container_width=True):
            st.success(f"Log enregistré : {a_mi - d_mi:.1f} milles parcourus.")

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y, p_m = y_col.selectbox("An", [2025, 2026, 2027], index=1), m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, details_list = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s, nb_j_val = parse_d(r.get('DateNav','')), int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j_val):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc_u = str(r.get('Société','')).strip().upper()
                        occu[curr.day] = "day-cmn" if soc_u == "CMN" else ("day-ok" if "OK" in str(r.get('Statut','')) else "day-wait")
                        if j == 0: details_list.append({"day": curr.day, "text": f"⚓ **{curr.day}**: {r.get('Nom')} ({soc_u}) **({nb_j_val}j)**"})
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    for item in sorted(details_list, key=lambda x: x['day']): st.write(item['text'])

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026, 2027], index=1)
    obj = st.number_input("Cible annuelle (€)", value=float(st.session_state.cible_annuelle), step=1000.0, key="cible_input")
    st.session_state.cible_annuelle = obj
    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)
    ca_total_ok = sum(df[(df['dt'].dt.year == s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **Réalisé (OK) : {int(ca_total_ok)} / {int(obj)}**")
    st.progress(min(ca_total_ok/obj, 1.0) if obj > 0 else 0.0)
    st.markdown("---")
    res, t_rev, t_fra, t_net, t_pre = [], 0, 0, 0, 0
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) &








































































































































































































































































