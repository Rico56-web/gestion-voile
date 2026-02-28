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
    .header-container { text-align: center; margin-bottom: 10px; padding: 5px; background-color: #f8f9fa; border-radius: 10px; }
    .main-title { color: #1a2a6c; font-size: 1.1rem; font-weight: bold; }
    
    /* Boutons Menu avec texte */
    div.stButton > button { 
        border-radius: 8px; height: 45px; padding: 0px;
        font-size: 0.7rem !important; font-weight: bold;
    }
    
    /* Cartes */
    .client-card { background: white; padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #ddd; border-left: 8px solid #ccc; }
    .cmn-style { border-left-color: #3498db !important; background-color: #f0f7ff !important; }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    
    .recap-box { background: #f1f2f6; padding: 10px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 10px; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .cal-table td { border: 1px solid #eee; height: 35px; text-align: center; font-size: 0.75rem; font-weight: bold; }
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
    except: return 1
def parse_date(d):
    try: return datetime.strptime(str(d).strip().replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
for key, val in {"page": "LISTE", "auth": False, "cal_month": datetime.now().month, "cal_year": datetime.now().year, "view_mode": "FUTUR"}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# --- MENU AVEC TEXTE ---
st.markdown('<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    if st.button("📋\nLISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
with m2: 
    if st.button("🗓️\nPLAN", use_container_width=True): st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰\nSTATS", use_container_width=True): st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧\nMAINT", use_container_width=True): st.session_state.page = "FRAIS"; st.rerun()

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 FUTUR", type="primary" if st.session_state.view_mode=="FUTUR" else "secondary"): st.session_state.view_mode="FUTUR"; st.rerun()
    with c2:
        if st.button("📂 ARCHIVES", type="primary" if st.session_state.view_mode=="ARCHIVES" else "secondary"): st.session_state.view_mode="ARCHIVES"; st.rerun()

    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if st.session_state.view_mode == "FUTUR":
        data = df[df['dt_obj'] >= auj].sort_values('dt_obj')
    else:
        data = df[df['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
    
    for i, r in data.iterrows():
        soc = str(r.get('Société', '')).upper()
        cl = "cmn-style" if "CMN" in soc else ("status-ok" if "🟢" in str(r.get('Statut','')) else "status-attente")
        st.markdown(f'<div class="client-card {cl}"><div style="float:right; font-weight:bold;">{to_float(r.get("PrixJour",0)):.2f}€</div><b>{r.get("Prénom","")} {r.get("Nom","")}</b><br><small>🏢 {soc} | 📅 {r.get("DateNav","")}<br>⚓ {r.get("Milles",0)} NM | ⏱️ {r.get("HeuresMoteur",0)}h</small></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.button("✏️ Gérer", key=f"ed_{i}", on_click=lambda idx=i: [st.session_state.update({"edit_idx": idx, "page": "FORM"})], use_container_width=True)
        if c2.button("🗑️ Suppr.", key=f"del_{i}", use_container_width=True):
            df = df.drop(i); sauvegarder_data(df); st.rerun()

elif st.session_state.page == "PLANNING":
    cp, cm, cn = st.columns([1,2,1])
    if cp.button("◀️"): st.session_state.cal_month -= 1; st.rerun()
    cm.markdown(f"<center><b>{st.session_state.cal_month}/{st.session_state.cal_year}</b></center>", unsafe_allow_html=True)
    if cn.button("▶️"): st.session_state.cal_month += 1; st.rerun()

    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        for j in range(to_int(r.get('NbJours', 1))):
            d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
            if d_c not in occu: occu[d_c] = []
            occu[d_c].append(r)

    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><tr><th>L</th><th>M</th><th>M</th><th>J</th><th>V</th><th>S</th><th>D</th></tr>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td></td>'
            else:
                ds = f"{d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                bg = "#3498db" if any("CMN" in str(x.get('Société','')).upper() for x in occu.get(ds,[])) else ("#2ecc71" if ds in occu else "white")
                h_c += f'<td style="background:{bg}; color:{"white" if bg!="white" else "black"};">{d}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)
    
    st.markdown("---")
    days = sorted([int(k.split('/')[0]) for k in occu.keys() if f"/{st.session_state.cal_month:02d}" in k])
    if days:
        sel = st.selectbox("Voir l'équipage du jour :", days)
        for r in occu.get(f"{sel:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}", []):
            st.info(f"⚓ {r.get('Prénom')} {r.get('Nom')} ({r.get('Société')})")

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="section-confirm">SOLDE ENCAISSÉ</div>', unsafe_allow_html=True)
    df_ok = df[df['Statut'].str.contains("🟢", na=False)]
    ca = sum(df_ok['PrixJour'].apply(to_float))
    fr = sum(df_frais['Montant'].apply(to_float)) if not df_frais.empty else 0
    st.markdown(f'<div class="recap-box">💰 CA: {ca:.2f}€<br>🔧 Frais: {fr:.2f}€<hr><b>NET: {ca-fr:.2f}€</b></div>', unsafe_allow_html=True)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="section-confirm">MAINTENANCE / FRAIS</div>', unsafe_allow_html=True)
    with st.form("frais"):
        d = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
        t = st.selectbox("Type", ["Moteur", "Entretien", "Divers"])
        m = st.text_input("Montant (€)", "0.0")
        if st.form_submit_button("AJOUTER"):
            nf = pd.DataFrame([{"Date": d, "Type": t, "Montant": m.replace(",", ".")}])
            df_frais = pd.concat([df_frais, nf], ignore_index=True)
            sauvegarder_data(df_frais, "frais.json"); st.rerun()
    
    for i, r in df_frais.iloc[::-1].iterrows():
        st.write(f"**{r['Date']}** - {r['Type']} : {r['Montant']}€")
        if st.button("🗑️", key=f"dfr_{i}"):
            df_frais = df_frais.drop(i); sauvegarder_data(df_frais, "frais.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    with st.form("edit"):
        f_nom = st.text_input("NOM", init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", init.get("Société", "")).upper()
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.number_input("Jours", 1, 30, to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix Total (€)", str(init.get("PrixJour", "0")).replace(",", "."))
        f_mi = st.number_input("Milles", value=to_float(init.get("Milles", 0)))
        f_he = st.number_input("Heures", value=to_float(init.get("HeuresMoteur", 0)))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "DateNav": f_dat, "NbJours": str(f_nbj), "PrixJour": f_prix, "Milles": str(f_mi), "HeuresMoteur": str(f_he), "Statut": init.get("Statut", "🟢 OK")}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()














































































































































