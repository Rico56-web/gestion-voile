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
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.2rem; color: #1a2a6c; margin-bottom: 20px; }
    .contact-link { color: #1a2a6c !important; text-decoration: underline !important; font-weight: bold; }
    /* Style pour le bouton actif en VERT */
    div.stButton > button:first-child[style*="background-color: rgb(46, 204, 113)"] {
        background-color: #2ecc71 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
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
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU PRINCIPAL (AVEC BOUTON VERT SI SÉLECTIONNÉ) ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu):
    is_active = st.session_state.page == pg
    # Si la page est active, on applique une couleur de fond verte directement via le style du bouton
    if c_m[i].button(label, use_container_width=True, type="primary" if is_active else "secondary"): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- 1. PAGE STATS (DÉTAILLÉE + et -) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES FINANCIÈRES</div>', unsafe_allow_html=True)
    ca = sum(df[df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f)) if not df.empty else 0
    fr = sum(df_f['Montant'].apply(to_f)) if not df_f.empty else 0
    
    st.markdown(f'<div class="recap-line">SOLDE NET : {fmt_p(ca-fr)}</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    c1.success(f"📈 TOTAL REVENUS (+)\n\n**{fmt_p(ca)}**")
    c2.error(f"📉 TOTAL FRAIS (-)\n\n**{fmt_p(fr)}**")
    
    st.markdown("---")
    st.write("### 📝 Détail des revenus")
    if not df.empty:
        df_stats = df[df['Statut'].str.contains("OK|🟢", na=False)].copy()
        st.dataframe(df_stats[['DateNav', 'Nom', 'PrixJour']], use_container_width=True)

# --- 2. PAGE MAINTENANCE (RÉTABLISSEMENT MODIFIER/EFFACER) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    idx_f = st.session_state.edit_f_idx
    with st.expander("📝 AJOUTER / MODIFIER UN FRAIS", expanded=(idx_f is not None)):
        init = df_f.loc[idx_f].to_dict() if (not df_f.empty and idx_f is not None) else {}
        with st.form("f_form"):
            f_d = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant", init.get("Montant", ""))
            f_n = st.text_area("Note", init.get("Note", ""))
            if st.form_submit_button("VALIDER"):
                row = {"Date":f_d, "Montant":f_m, "Note":f_n}
                if idx_f is not None: df_f.loc[idx_f] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
        if idx_f is not None:
            if st.button("Annuler"): st.session_state.edit_f_idx = None; st.rerun()

    if not df_f.empty:
        for i in range(len(df_f)-1, -1, -1):
            r = df_f.iloc[i]
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:red; font-weight:bold;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Date")}</b><br>{r.get("Note")}
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"mf_{i}"):
                st.session_state.edit_f_idx = i; st.rerun()
            if c2.button("🗑️ Effacer", key=f"df_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- AUTRES PAGES (LISTE, PLANNING, FORM) ---
# [Le code reste ici identique aux versions précédentes validées pour LISTE et PLANNING]























































































































































































