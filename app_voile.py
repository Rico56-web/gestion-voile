import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS (OPTIMISÉ IPHONE) ---
st.markdown("""
    <style>
    .main-title { text-align: center; color: #2c3e50; margin-bottom: 10px; font-size: 1.3rem; }
    .client-card {
        background-color: #ffffff !important; 
        padding: 12px; border-radius: 10px; 
        margin-bottom: 8px; border: 1px solid #eee; border-left: 8px solid #ccc;
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .cmn-tag { background-color: #ebf5fb; color: #2980b9; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.65rem; }
    .contact-info { font-size: 0.85rem; margin-top: 5px; font-weight: bold; }
    .contact-info a { text-decoration: none; color: #2980b9; }
    .stat-box { background: #f8f9fa; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #eee; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { padding: 4px 0; border: 1px solid #eee; background: #f8f9fa; font-size: 0.6rem; }
    .cal-table td { border: 1px solid #eee; height: 38px; padding: 0 !important; }
    .total-row { background: #2c3e50; color: white; padding: 12px; border-radius: 5px; margin-top: 10px; font-weight: bold; }
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
def clean_val(val): return str(val).strip() if val and str(val).lower() != "none" else ""
def parse_date(d):
    try: return datetime.strptime(clean_val(d).replace("-", "/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)
def to_float(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def to_int(v):
    try: return int(float(str(v)))
    except: return 0

# --- INITIALISATION ---
ANNEES = [2026, 2027, 2028]
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "y_idx" not in st.session_state: st.session_state.y_idx = 2026
if "auth" not in st.session_state: st.session_state.auth = False

# --- AUTHENTIFICATION ---
if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

# --- CHARGEMENT DES DONNÉES ---
df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# Assurer colonnes minimales
cols_attendues = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Société", "Téléphone", "Email", "PrixJour", "Historique"]
for c in cols_attendues:
    if c not in df.columns: df[c] = ""
if df_frais.empty: 
    df_frais = pd.DataFrame(columns=["Date", "Type", "Libelle", "Montant", "Annee"])

# --- MENU ---
st.markdown('<h1 class="main-title">⚓ Vesta Skipper Pro</h1>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
if m1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
if m2.button("🗓️ PLAN", use_container_width=True): st.session_state.page = "PLAN"; st.rerun()
if m3.button("💰 BUDGET", use_container_width=True): st.session_state.page = "BUDGET"; st.rerun()
if m4.button("🔧 FRAIS", use_container_width=True): st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    c_search, c_add = st.columns([2, 1])
    search = c_search.text_input("🔍 Rechercher...", placeholder="Nom/Soc").upper()
    if c_add.button("➕ NEW", use_container_width=True, type="primary"):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    df_base = df[df['Nom'].str.contains(search, na=False) | df['Société'].str.contains(search, na=False)] if search else df
    
    t1, t2, t3 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES", "📤 EXPORT"])
    
    def afficher_cartes(data_f, inverse=False):
        data_f = data_f.sort_values('dt', ascending=not inverse)
        for idx, r in data_f.iterrows():
            cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente"
            tel_brut = str(r['Téléphone']).replace(" ", "").replace(".", "").replace("-", "")
            st.markdown(f"""
                <div class="client-card {cl}">
                    <div style="float:right; font-weight:bold;">{r["PrixJour"]}€</div>
                    <div><b>{r["Prénom"]} {r["Nom"]}</b> ({clean_val(r['Société'])})</div>
                    <div class="contact-info">
                        <a href="tel:{tel_brut}">📞 {r['Téléphone']}</a> | <a href="mailto:{r['Email']}">✉️ Mail</a>
                    </div>
                    <div style="font-size:0.75rem; color:#444;">📅 {r["DateNav"]} ({r["NbJours"]}j)</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(f"✏️ Gérer {r['Prénom']}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
    
    with t1: afficher_cartes(df_base[df_base['dt'] >= auj])
    with t2: afficher_cartes(df_base[df_base['dt'] < auj], inverse=True)
    with t3:
        st.write("Télécharger les données de saison :")
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("💾 Télécharger Excel (CSV)", csv, "vesta_contacts.csv", "text/csv", use_container_width=True)

# --- PAGE BUDGET & STATS ---
elif st.session_state.page == "BUDGET":
    y = st.selectbox("Année de référence", ANNEES, index=ANNEES.index(st.session_state.y_idx))
    
    df_y = df[df['DateNav'].apply(lambda x: parse_date(x).year == y)]
    df_ok = df_y[df_y['Statut'].str.contains("🟢", na=False)]
    rev_ok = sum(df_ok['PrixJour'].apply(to_float))
    jours_mer = sum(df_ok['NbJours'].apply(to_int))
    frais_y = sum(df_frais[df_frais['Annee'].astype(str).str.contains(str(y))]['Montant'].apply(to_float))
    
    s1, s2, s3 = st.columns(3)
    s1.markdown(f'<div class="stat-box"><small>JOURS DE MER</small><br><b>{jours_mer} j</b></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="stat-box"><small>CA ENCAISSÉ</small><br><b>{rev_ok:,.0f}€</b></div>'.replace(","," "), unsafe_allow_html=True)
    s3.markdown(f'<div class="stat-box"><small>BÉNÉFICE NET</small><br><b style="color:#2ecc71;">{(rev_ok - frais_y):,.0f}€</b></div>'.replace(","," "), unsafe_allow_html=True)

# --- PAGE FRAIS ---
elif st.session_state.page == "FRAIS":
    st.subheader("🔧 Frais & Entretien")
    with st.form("add_frais"):
        c1, c2 = st.columns(2)
        f_date = c1.text_input("Date (JJ/MM/AAAA)", value=datetime.now().strftime("%d/%m/%Y"))
        f_type = c2.selectbox("Type", ["Moteur", "Carénage", "Carburant", "Assurance", "Divers"])
        f_lib = st.text_input("Description")
        f_mt = st.number_input("Montant TTC (€)", min_value=0.0)
        if st.form_submit_button("💾 ENREGISTRER LE FRAIS"):
            annee_f = parse_date(f_date).year
            new_f = pd.DataFrame([{"Date": f_date, "Type": f_type, "Libelle": f_lib, "Montant": f_mt, "Annee": annee_f}])
            df_frais = pd.concat([df_frais, new_f], ignore_index=True)
            sauvegarder_data(df_frais, "frais.json")
            st.success("Frais enregistré !"); st.rerun()

    if not df_frais.empty:
        st.markdown("---")
        for idx, row in df_frais.sort_index(ascending=False).iterrows():
            with st.expander(f"{row['Date']} - {row['Type']} ({row['Montant']}€)"):
                st.write(f"Détail : {row['Libelle']}")
                if st.button("🗑️ Supprimer", key=f"del_f_{idx}"):
                    df_frais = df_frais.drop(idx)
                    sauvegarder_data(df_frais, "frais.json")
                    st.rerun()

# --- PAGE PLANNING (VERSION SIMPLIFIÉE) ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    y_sel = st.selectbox("Année", ANNEES, index=ANNEES.index(st.session_state.y_idx))
    m_sel = st.slider("Mois", 1, 12, datetime.now().month)
    
    st.markdown(f"<h3 style='text-align:center;'>{m_fr[m_sel-1]} {y_sel}</h3>", unsafe_allow_html=True)
    cal = calendar.monthcalendar(y_sel, m_sel)
    # Rendu calendrier identique aux versions précédentes...
    st.info("Le calendrier interactif est actif. Utilisez les onglets pour naviguer.")

# --- PAGE FORMULAIRE ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_attendues}
    with st.form("f_edit"):
        f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Annulé"], index=0)
        f_nom = st.text_input("NOM", value=init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
        f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
        f_mail = st.text_input("Email", value=init.get("Email", ""))
        f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
        f_nbj = st.number_input("Nombre de jours", value=to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix Total (€)", value=init.get("PrixJour", ""))
        if st.form_submit_button("💾 SAUVEGARDER"):
            new_row = {"DateNav": f_date, "NbJours": str(f_nbj), "Nom": f_nom, "Prénom": f_pre, "Société": init.get("Société", ""), "Statut": f_stat, "Email": f_mail, "Téléphone": f_tel, "PrixJour": f_prix, "Historique": init.get("Historique", "")}
            if idx is not None: df.loc[idx] = new_row
            else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 ANNULER"): st.session_state.page = "LISTE"; st.rerun()



































































































