import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS DYNAMIQUE ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 20px; font-size: 1.3rem; font-weight: bold; }
    
    /* Boutons Menu Principal */
    div.stButton > button {
        border-radius: 12px; height: 55px;
        border: 1px solid #dcdde1; background-color: white;
        color: #2f3640; font-weight: bold; font-size: 0.9rem;
    }
    
    /* Cartes Clients */
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        margin-bottom: 12px; border: 1px solid #e1e8ed; border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; border: 1px solid #3498db; }
    
    .contact-bar a { 
        text-decoration: none; color: #2980b9; background: #f1f7fa; 
        padding: 8px 12px; border-radius: 8px; display: inline-block; 
        margin-right: 10px; font-size: 0.85rem; font-weight: bold;
    }
    .section-header { background: #34495e; padding: 8px; border-radius: 8px; margin-bottom: 10px; color: white; font-weight: bold; text-align: center; font-size: 0.9rem; }
    
    .cal-table { width: 100%; border-collapse: collapse; background: white; }
    .cal-table td { border: 1px solid #eee; height: 50px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=5)
def charger_data(file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        json_d = df.to_json(orient="records", indent=4, force_ascii=False)
        content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
        data = {"message": f"Update {file}", "content": content_b64, "sha": sha}
        requests.put(url, headers=headers, json=data)
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def to_int(v):
    try: return int(float(str(v)))
    except: return 0
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")
cols = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur"]
for c in cols:
    if c not in df.columns: df[c] = ""

# --- MENU PRINCIPAL ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
if m1.button("📋\nListe", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"):
    st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️\nPlan", use_container_width=True, type="primary" if st.session_state.page == "PLAN" else "secondary"):
    st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰\nStats", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"):
    st.session_state.page = "BUDGET"; st.rerun()
if m4.button("🔧\nFrais", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"):
    st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---

if st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
    st.subheader("📝 Fiche Client")
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=["🟡 Attente", "🟢 OK", "🔴 Annulé"].index(init.get("Statut", "🟡 Attente")))
        f_nom = st.text_input("NOM", value=init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", value=init.get("Société", "")).upper()
        c_a, c_b = st.columns(2)
        f_milles = c_a.number_input("Milles", value=to_float(init.get("Milles", 0)))
        f_heures = c_b.number_input("Heures Moteur", value=to_float(init.get("HeuresMoteur", 0)))
        f_tel = st.text_input("Tél", value=init.get("Téléphone", ""))
        f_mail = st.text_input("Email", value=init.get("Email", ""))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
        f_nbj = st.number_input("Jours", value=to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix Total (€)", value=init.get("PrixJour", ""))
        if st.form_submit_button("💾 ENREGISTRER"):
            row = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Milles": str(f_milles), "HeuresMoteur": str(f_heures)}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if idx is not None:
        with st.expander("⚠️ ZONE DE DANGER"):
            if st.button("🗑️ SUPPRIMER"):
                df = df.drop(idx).reset_index(drop=True); sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 Retour"): st.session_state.page = "LISTE"; st.rerun()

elif st.session_state.page == "LISTE":
    c_fut, c_arc = st.columns(2)
    if c_fut.button("🚀 PROCHAINES", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTUR" else "secondary"):
        st.session_state.view_mode = "FUTUR"; st.rerun()
    if c_arc.button("📂 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_mode == "ARCHIVES" else "secondary"):
        st.session_state.view_mode = "ARCHIVES"; st.rerun()
    
    c_search, c_add = st.columns([3, 1])
    search = c_search.text_input("🔍 Rechercher...", value="").upper()
    if c_add.button("➕ NEW", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    mask = df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)
    df_f = df[mask].copy()

    if st.session_state.view_mode == "FUTUR":
        data = df_f[df_f['dt_obj'] >= auj].sort_values('dt_obj', ascending=True)
        st.markdown('<div class="section-header">🚀 NAVIGATIONS À VENIR</div>', unsafe_allow_html=True)
    else:
        data = df_f[df_f['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
        st.markdown('<div class="section-header">📂 HISTORIQUE / ARCHIVES</div>', unsafe_allow_html=True)

    for i, r in data.iterrows():
        cl = "cmn-style" if "CMN" in str(r['Société']).upper() else ("status-ok" if "🟢" in str(r['Statut']) else "status-attente")
        st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div><b>{r["Prénom"]} {r["Nom"]}</b><br><span style="color:#d35400; font-weight:bold; font-size:0.85rem;">🏢 {r["Société"]}</span><div class="contact-bar"><a href="tel:{r["Téléphone"]}">📞 Appeler</a> <a href="mailto:{r["Email"]}">✉️ Mail</a></div><small>📅 {r["DateNav"]} | 🚢 {r["Milles"]} NM | ⚙️ {r["HeuresMoteur"]}h</small></div>', unsafe_allow_html=True)
        if st.button(f"✏️ Gérer {r['Prénom']}", key=f"btn_{i}", use_container_width=True):
            st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

elif st.session_state.page == "PLAN":
    c1, c2 = st.columns(2)
    y_p, m_p = c1.selectbox("Année", [2026, 2027, 2028]), c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        if d_o.year == y_p:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
    cal = calendar.monthcalendar(y_p, m_p)
    h_c = '<table class="cal-table"><tr><th>Lun</th><th>Mar</th><th>Mer</th><th>Jeu</th><th>Ven</th><th>Sam</th><th>Dim</th></tr>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td style="background:#f9f9f9;"></td>'
            else:
                ds = f"{d:02d}/{m_p:02d}/{y_p}"
                dat = occu.get(ds, [])
                bg = "white"
                if dat:
                    bg = "#3498db" if any("CMN" in str(x['Société']).upper() for x in dat) else ("#2ecc71" if any("🟢" in str(x['Statut']) for x in dat) else "#f1c40f")
                h_c += f'<td style="background:{bg};">{d}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    y_b = st.selectbox("Année", [2026, 2027, 2028])
    df['dt'] = df['DateNav'].apply(parse_date)
    df_y = df[(df['dt'].dt.year == y_b) & (df['Statut'].str.contains("🟢"))]
    ht = '<table class="cal-table"><tr><th>Mois</th><th>Jours</th><th>Milles</th><th>CA (€)</th></tr>'
    for i, m in enumerate(["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"], 1):
        df_m = df_y[df_y['dt'].dt.month == i]
        if not df_m.empty:
            ht += f'<tr><td>{m}</td><td>{sum(df_m["NbJours"].apply(to_int))}j</td><td>{sum(df_m["Milles"].apply(to_float)):,.0f}</td><td>{sum(df_m["PrixJour"].apply(to_float)):,.0f}€</td></tr>'
    st.markdown(ht + '</table>', unsafe_allow_html=True)

elif st.session_state.page == "FRAIS":
    with st.form("f"):
        d, t, m = st.text_input("Date"), st.selectbox("Type", ["Moteur", "Entretien", "Divers"]), st.number_input("Montant", 0.0)
        if st.form_submit_button("OK"):
            new_f = pd.DataFrame([{"Date": d, "Type": t, "Montant": m, "Annee": parse_date(d).year}])
            df_frais = pd.concat([df_frais, new_f], ignore_index=True)
            sauvegarder_data(df_frais, "frais.json"); st.rerun()
    for i, r in df_frais.iterrows():
        st.write(f"{r['Date']} - {r['Type']} : {r['Montant']}€")
        if st.button("Suppr", key=f"f_{i}"):
            df_frais = df_frais.drop(i); sauvegarder_data(df_frais, "frais.json"); st.rerun()





















































































































