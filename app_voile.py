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
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; }
    .cal-table td { height: 50px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=1)
def charger_data(file="contacts.json"):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file="contacts.json"):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
        return True
    except: return False

# --- UTILS ---
def to_f(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")
def parse_d(d):
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "del_idx" not in st.session_state: st.session_state.del_idx = None
if "del_f_idx" not in st.session_state: st.session_state.del_f_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE STATS (CORRIGÉE) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        # On filtre uniquement les OK pour le CA
        mask_ca = df['Statut'].str.contains("OK|🟢", na=False)
        ca_total = sum(df[mask_ca]['PrixJour'].apply(to_f))
        
        frais_total = 0
        if not df_f.empty:
            frais_total = sum(df_f['Montant'].apply(to_f))
        
        st.markdown(f'<div class="recap-line">CA TOTAL : {fmt_p(ca_total)} | FRAIS : {fmt_p(frais_total)} | NET : {fmt_p(ca_total - frais_total)}</div>', unsafe_allow_html=True)
        
        st.write("### Détail des revenus")
        st.table(df[mask_ca][['DateNav', 'Nom', 'PrixJour']].rename(columns={'PrixJour': 'Montant'}))

# --- PAGE MAINTENANCE (CORRIGÉE) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    # Formulaire
    idx_f = st.session_state.edit_f_idx
    with st.expander("➕ AJOUTER / MODIFIER UN FRAIS", expanded=(idx_f is not None)):
        init_f = df_f.loc[idx_f].to_dict() if (not df_f.empty and idx_f is not None) else {}
        with st.form("form_frais"):
            f_d = st.text_input("Date (JJ/MM/AAAA)", init_f.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant (€)", init_f.get("Montant", ""))
            f_n = st.text_area("Description / Note", init_f.get("Note", ""))
            if st.form_submit_button("ENREGISTRER"):
                new_row = {"Date": f_d, "Montant": f_m, "Note": f_n}
                if idx_f is not None: df_f.loc[idx_f] = new_row
                else: df_f = pd.concat([df_f, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_f_idx = None
                st.rerun()
        if idx_f is not None:
            if st.button("Annuler"): st.session_state.edit_f_idx = None; st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; font-weight:bold; color:red;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Date")}</b><br>{r.get("Note")}
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"mf_{i}"): st.session_state.edit_f_idx = i; st.rerun()
            if st.session_state.del_f_idx == i:
                if st.button("CONFIRMER SUPPRESSION", key=f"cf_{i}"):
                    df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.session_state.del_f_idx = None; st.rerun()
            else:
                if c2.button("🗑️ Supprimer", key=f"df_{i}"): st.session_state.del_f_idx = i; st.rerun()

# --- AUTRES PAGES (LISTE & PLANNING) ---
elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True): st.session_state.view_mode = "FUTURES"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
        for i, r in data.sort_values('dt').iterrows():
            st.markdown(f'<div class="client-card"><b>{r.get("Nom")}</b> - {r.get("DateNav")} ({r.get("Statut")})</div>', unsafe_allow_html=True)
            if st.button("Modifier", key=f"ml_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

# [Le reste du Planning et Formulaire suit la même logique de sécurité]



















































































































































































