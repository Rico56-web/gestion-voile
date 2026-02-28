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
    .header-container { text-align: center; margin-bottom: 15px; padding: 8px; background-color: #f8f9fa; border-radius: 12px; border: 1px solid #e1e8ed; }
    .main-title { color: #1a2a6c; margin-bottom: 2px; font-size: 1.3rem; font-weight: bold; text-transform: uppercase; }
    .today-date { color: #e74c3c; font-size: 0.9rem; font-weight: 600; }
    
    .section-confirm { 
        background: #1a2a6c; color: white; padding: 10px; 
        border-radius: 8px; text-align: center; font-weight: bold; 
        margin-bottom: 20px; font-size: 0.9rem; letter-spacing: 1px;
        text-transform: uppercase;
    }
    
    div.stButton > button { 
        border-radius: 8px; height: 38px; padding: 0px 5px;
        border: 1px solid #dcdde1; background-color: white; 
        color: #2f3640; font-weight: bold; font-size: 0.75rem; 
    }
    
    .stButton button[kind="primary"] {
        background-color: #1a2a6c !important;
        color: white !important;
        border: none !important;
    }

    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-top: 10px; }
    .cal-table th { font-size: 0.65rem; padding: 6px 0; background: #f8f9fa; border: 1px solid #eee; color: #7f8c8d; text-align: center; }
    .cal-table td { border: 1px solid #eee; height: 45px; text-align: center; font-size: 0.8rem; font-weight: bold; vertical-align: middle; }
    
    .client-card { background-color: #ffffff; padding: 12px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #e1e8ed; border-left: 10px solid #ccc; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    .contact-bar a { text-decoration: none; color: white !important; background: #1a2a6c; padding: 8px 12px; border-radius: 8px; display: inline-block; margin-right: 5px; font-size: 0.8rem; font-weight: bold; }
    .btn-marine button { background-color: #1a2a6c !important; color: white !important; border: none !important; height: 45px !important; font-size: 0.85rem !important; }
    .btn-delete button { background-color: #e74c3c !important; color: white !important; border: none !important; }
    
    .recap-box { background: #f1f2f6; padding: 10px; border-radius: 10px; border: 1px solid #dfe4ea; margin-bottom: 15px; }
    .recap-val { font-size: 1.1rem; font-weight: bold; color: #2f3542; }
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
    try: 
        val = int(float(str(v)))
        return val if val >= 1 else 1
    except: return 1
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)
def fmt_euro(v):
    return f"{to_float(v):.2f}".replace(",", ".")

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTUR"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "auth" not in st.session_state: st.session_state.auth = False
if "cal_month" not in st.session_state: st.session_state.cal_month = datetime.now().month
if "cal_year" not in st.session_state: st.session_state.cal_year = datetime.now().year
if "stat_year" not in st.session_state: st.session_state.stat_year = datetime.now().year

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")
cols = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Milles", "HeuresMoteur"]
for c in cols:
    if c not in df.columns: df[c] = ""

# --- BANDEAU TITRE ---
st.markdown(f'<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div><div class="today-date">🗓️ {datetime.now().strftime("%d/%m/%Y")}</div></div>', unsafe_allow_html=True)

# --- MENU PRINCIPAL ---
m1, m2, m3, m4 = st.columns(4)
with m1:
    if st.button("📋 LISTE", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"): 
        st.session_state.page = "LISTE"; st.rerun()
with m2:
    if st.button("🗓️ PLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary"): 
        st.session_state.page = "PLANNING"; st.rerun()
with m3:
    if st.button("💰 STATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"): 
        st.session_state.page = "BUDGET"; st.rerun()
with m4:
    if st.button("🔧 FRAIS", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): 
        st.session_state.page = "FRAIS"; st.rerun()

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="section-confirm">📋 LISTE DES FICHES</div>', unsafe_allow_html=True)
    c_fut, c_arc = st.columns(2)
    with c_fut:
        if st.button("🚀 PROCHAINES", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTUR" else "secondary"): 
            st.session_state.view_mode = "FUTUR"; st.rerun()
    with c_arc:
        if st.button("📂 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_mode == "ARCHIVES" else "secondary"): 
            st.session_state.view_mode = "ARCHIVES"; st.rerun()
    
    search = st.text_input("🔍 Rechercher...", value="").upper()
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_f = df[df['Nom'].str.contains(search, na=False, case=False) | df['Société'].str.contains(search, na=False, case=False)].copy()
    data = df_f[df_f['dt_obj'] >= auj].sort_values('dt_obj', ascending=True) if st.session_state.view_mode == "FUTUR" else df_f[df_f['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
    
    for i, r in data.iterrows():
        soc_nom = str(r.get('Société', '')).upper()
        cl = "cmn-style" if "CMN" in soc_nom else ("status-ok" if "🟢" in str(r['Statut']) else "status-attente")

        st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{fmt_euro(r["PrixJour"])}€</div><b>{r["Prénom"]} {r["Nom"]}</b><br><span style="color:#d35400; font-weight:bold;">🏢 {r["Société"]}</span><br><small>📅 {r["DateNav"]} | ⚓ {r["Milles"]} NM | ⏱️ {r["HeuresMoteur"]}h</small></div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="btn-marine">', unsafe_allow_html=True)
            if st.button(f"✏️ Gérer", key=f"edit_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
            if st.button(f"🗑️ Supprimer", key=f"del_{i}", use_container_width=True):
                df = df.drop(i); sauvegarder_data(df); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="section-confirm">🗓️ PLANNING DES SORTIES</div>', unsafe_allow_html=True)
    cp, cm, cn = st.columns([1, 2, 1])
    with cp:
        if st.button("◀️", key="p_prev"):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
            st.rerun()
    with cm:
        mois_n = ["Janv.", "Févr.", "Mars", "Avril", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
        st.markdown(f'<div class="nav-label">{mois_n[st.session_state.cal_month-1]} {st.session_state.cal_year}</div>', unsafe_allow_html=True)
    with cn:
        if st.button("▶️", key="p_next"):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
            st.rerun()

    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        if d_o.year == st.session_state.cal_year:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
                
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><thead><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr></thead><tbody>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td style="background:#f9f9f9;"></td>'
            else:
                ds = f"{d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                dat = occu.get(ds, [])
                bg, color = "white", "black"
                if dat:
                    first = dat[0]
                    if "CMN" in str(first['Société']).upper(): bg, color = "#3498db", "white"
                    elif "🟢" in str(first['Statut']): bg, color = "#2ecc71", "white"
                    else: bg, color = "#f1c40f", "black"
                h_c += f'<td style="background:{bg}; color:{color};">{d}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</tbody></table>', unsafe_allow_html=True)

    jours_occupes = [int(k.split('/')[0]) for k in occu.keys() if f"/{st.session_state.cal_month:02d}/{st.session_state.cal_year}" in k]
    if jours_occupes:
        st.markdown("---")
        sel_d = st.selectbox("Détails du jour :", sorted(list(set(jours_occupes))))
        ds_sel = f"{sel_d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
        for r in occu.get(ds_sel, []):
            st.info(f"⚓ **{r['Prénom']} {r['Nom']}**\n🏢 {r['Société']}\n⏱️ {r['HeuresMoteur']}h | ⚓ {r['Milles']} NM")

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="section-confirm">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    cp, cm, cn = st.columns([1, 2, 1])
    with cp:
        if st.button("◀️ ", key="s_prev"): st.session_state.stat_year -= 1; st.rerun()
    with cm:
        st.markdown(f'<div class="nav-label">ANNÉE {st.session_state.stat_year}</div>', unsafe_allow_html=True)
    with cn:
        if st.button("▶️ ", key="s_next"): st.session_state.stat_year += 1; st.rerun()

    df['dt'] = df['DateNav'].apply(parse_date)
    df_y = df[(df['dt'].dt.year == st.session_state.stat_year) & (df['Statut'].str.contains("🟢"))]
    
    total_frais = 0
    if not df_frais.empty:
        df_frais['dt_f'] = df_frais['Date'].apply(parse_date)
        total_frais = df_frais[df_frais['dt_f'].dt.year == st.session_state.stat_year]['Montant'].sum()
    
    total_ca = sum(df_y['PrixJour'].apply(to_float))
    benefice = total_ca - total_frais

    st.markdown(f"""
        <div class="recap-box">
            <div style="display:flex; justify-content:space-between;"><span>Chiffre Affaires:</span><span class="recap-val">{fmt_euro(total_ca)} €</span></div>
            <div style="display:flex; justify-content:space-between; color:#e74c3c;"><span>Total Frais:</span><span class="recap-val">- {fmt_euro(total_frais)} €</span></div>
            <hr style="margin:5px 0;">
            <div style="display:flex; justify-content:space-between; color:#27ae60;"><span>RÉSULTAT NET:</span><span class="recap-val">{fmt_euro(benefice)} €</span></div>
        </div>
    """, unsafe_allow_html=True)
    
    ht = '<table class="cal-table"><thead><tr><th>Mois</th><th>Jours</th><th>NM</th><th>CA €</th></tr></thead><tbody>'
    for i, m in enumerate(["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"], 1):
        df_m = df_y[df_y['dt'].dt.month == i]
        if not df_m.empty:
            ht += f'<tr><td>{m}</td><td>{sum(df_m["NbJours"].apply(to_int))}</td><td>{sum(df_m["Milles"].apply(to_float)):.1f}</td><td>{fmt_euro(sum(df_m["PrixJour"].apply(to_float)))}</td></tr>'
    st.markdown(ht + '</tbody></table>', unsafe_allow_html=True)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="section-confirm">🔧 FRAIS ET MAINTENANCE</div>', unsafe_allow_html=True)
    with st.form("f_frais"):
        d, t, m = st.text_input("Date (JJ/MM/AAAA)"), st.selectbox("Type", ["Moteur", "Entretien", "Divers"]), st.number_input("Montant", 0.0, step=10.0)
        if st.form_submit_button("VALIDER"):
            new_f = pd.DataFrame([{"Date": d, "Type": t, "Montant": m}])
            df_frais = pd.concat([df_frais, new_f], ignore_index=True)
            sauvegarder_data(df_frais, "frais.json"); st.rerun()
    
    if not df_frais.empty:
        for i, r in df_frais.iloc[::-1].iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{r['Date']}** - {r['Type']} : **{fmt_euro(r['Montant'])}€**")
            with c2:
                if st.button("🗑️", key=f"fdel_{i}"):
                    df_frais = df_frais.drop(i); sauvegarder_data(df_frais, "frais.json"); st.rerun()
            st.markdown("---")

elif st.session_state.page == "FORM":
    st.markdown('<div class="section-confirm">✏️ FICHE DÉTAILLÉE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=0)
        f_nom = st.text_input("NOM", value=str(init.get("Nom", ""))).upper()
        f_pre = st.text_input("Prénom", value=str(init.get("Prénom", "")))
        f_soc = st.text_input("SOCIÉTÉ", value=str(init.get("Société", ""))).upper()
        f_milles = st.number_input("Milles", value=to_float(init.get("Milles", 0)))
        f_heures = st.number_input("Heures Moteur", value=to_float(init.get("HeuresMoteur", 0)))
        f_tel = st.text_input("Téléphone", value=str(init.get("Téléphone", "")))
        f_mail = st.text_input("Email", value=str(init.get("Email", "")))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=str(init.get("DateNav", "")))
        f_nbj = st.number_input("Nombre Jours", value=to_int(init.get("NbJours", 1)), min_value=1)
        f_prix = st.text_input("Montant Total (€)", value=str(init.get("PrixJour", "")))
        
        if st.form_submit_button("💾 ENREGISTRER", use_container_width=True):
            row = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix.replace(",", "."), "Milles": str(f_milles), "HeuresMoteur": str(f_heures)}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 Retour"): st.session_state.page = "LISTE"; st.rerun()











































































































































