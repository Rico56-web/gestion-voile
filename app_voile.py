import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- 2. INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "stat_y" not in st.session_state: st.session_state.stat_y = 2026
if "stat_m" not in st.session_state: st.session_state.stat_m = datetime.now().month
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.1rem; color: #1a2a6c; margin-bottom: 20px; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
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
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
    except Exception as e:
        st.error(f"Erreur de connexion au fichier {file}")
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
    try: return datetime.strptime(str(d).replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- AUTH ---
if not st.session_state.get("auth"):
    if st.text_input("Code secret", type="password") == st.secrets["PASSWORD"]: 
        st.session_state.auth = True
        st.rerun()
    st.stop()

# Chargement forcé
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

# --- PAGE STATS (FIXÉE) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES FINANCIÈRES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    sel_y = col1.selectbox("Année", [2024, 2025, 2026, 2027, 2028], index=2)
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre", "TOUTE L'ANNÉE"]
    sel_m = col2.selectbox("Mois", range(1, 14), format_func=lambda x: mois_noms[x-1], index=12) # Par défaut Toute l'année

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask = (df['dt'].dt.year == sel_y)
        if sel_m < 13: mask &= (df['dt'].dt.month == sel_m)
        
        # Uniquement les navigations validées (Vertes)
        df_ok = df[mask & df['Statut'].str.contains("OK|🟢", na=False)]
        ca = sum(df_ok['PrixJour'].apply(to_f))
        
        frais = 0
        if not df_f.empty:
            df_f['dt'] = df_f['Date'].apply(parse_d)
            mask_f = (df_f['dt'].dt.year == sel_y)
            if sel_m < 13: mask_f &= (df_f['dt'].dt.month == sel_m)
            frais = sum(df_f[mask_f]['Montant'].apply(to_f))

        st.markdown(f'<div class="recap-line">CA: {fmt_p(ca)} | FRAIS: {fmt_p(frais)} | NET: {fmt_p(ca-frais)}</div>', unsafe_allow_html=True)
        
        if not df_ok.empty:
            st.write("### Détail des revenus")
            st.table(df_ok[['DateNav', 'Nom', 'PrixJour']])
    else:
        st.warning("Aucune donnée de navigation trouvée.")

# --- PAGE MAINTENANCE (FIXÉE) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE DU NAVIRE</div>', unsafe_allow_html=True)
    
    idx_f = st.session_state.edit_f_idx
    with st.expander("➕ AJOUTER / MODIFIER UN FRAIS", expanded=(idx_f is not None)):
        init = df_f.loc[idx_f].to_dict() if (not df_f.empty and idx_f is not None) else {}
        with st.form("form_frais"):
            f_d = st.text_input("Date (JJ/MM/AAAA)", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant (€)", init.get("Montant", ""))
            f_n = st.text_area("Description des travaux", init.get("Note", ""))
            if st.form_submit_button("VALIDER L'ENREGISTREMENT"):
                new_row = {"Date": f_d, "Montant": f_m, "Note": f_n}
                if idx_f is not None: df_f.loc[idx_f] = new_row
                else: df_f = pd.concat([df_f, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_f_idx = None
                st.rerun()

    if not df_f.empty:
        for i, r in df_f.iloc[::-1].iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; font-weight:bold; color:#c62828;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Date")}</b><br>
                    <div style="margin-top:5px; font-size:0.95rem;">{r.get("Note")}</div>
                </div>
            ''', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"ef_{i}"):
                st.session_state.edit_f_idx = i
                st.rerun()
            if c2.button("🗑️ Supprimer", key=f"df_{i}"):
                df_f.drop(i).reset_index(drop=True).pipe(sauvegarder_data, "frais.json")
                st.rerun()
    else:
        st.info("Aucun frais de maintenance enregistré.")

# --- PAGE LISTE (ORDRE CHRONO) ---
elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 LISTE DES NAVIGATIONS</div>', unsafe_allow_html=True)
    # [Code de la liste avec tri chronologique inverse tel que validé précédemment]



















































































































































































