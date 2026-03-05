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
    .main-title { color: #1a2a6c; font-size: 1.5rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .contact-link { color: #1a2a6c !important; text-decoration: none !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=2)
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
if "del_frais_idx" not in st.session_state: st.session_state.del_frais_idx = None
if "edit_frais_idx" not in st.session_state: st.session_state.edit_frais_idx = None

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
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS")]
for i, (label, pg) in enumerate(menu):
    if c_m[i].button(label, use_container_width=True): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE STATS (REVENUS EN EUROS) ---
if st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN FINANCIER</div>', unsafe_allow_html=True)
    if not df.empty:
        df_ok = df[df['Statut'].str.contains("OK|🟢", na=False)].copy()
        total_ca = sum(df_ok['PrixJour'].apply(to_f))
        total_frais = sum(df_f['Montant'].apply(to_f)) if not df_f.empty else 0
        
        st.metric("NET ESTIMÉ", fmt_p(total_ca - total_frais), f"CA: {fmt_p(total_ca)}")
        
        st.write("### 📈 Détail des revenus (Confirmés)")
        df_disp = df_ok[['DateNav', 'Nom', 'Société', 'PrixJour']].copy()
        df_disp['PrixJour'] = df_disp['PrixJour'].apply(fmt_p)
        st.table(df_disp)

# --- PAGE MAINTENANCE (MODIFIER/SUPPRIMER/DÉTAILS) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & TRAVAUX</div>', unsafe_allow_html=True)
    
    # Formulaire Ajout / Modification
    with st.expander("➕ ENREGISTRER UN FRAIS / TRAVAUX", expanded=(st.session_state.edit_frais_idx is not None)):
        idx_f = st.session_state.edit_frais_idx
        init_f = df_f.loc[idx_f].to_dict() if idx_f is not None else {}
        with st.form("f_form"):
            date_f = st.text_input("Date", init_f.get("Date", datetime.now().strftime("%d/%m/%Y")))
            type_f = st.selectbox("Type", ["Moteur", "Voiles", "Electricité", "Coque", "Divers"], index=0)
            montant_f = st.text_input("Montant (€)", init_f.get("Montant", ""))
            note_f = st.text_area("Note / Détails", init_f.get("Note", ""))
            
            sub_col1, sub_col2 = st.columns(2)
            if sub_col1.form_submit_button("💾 SAUVEGARDER"):
                row = {"Date": date_f, "Type": type_f, "Montant": montant_f, "Note": note_f}
                if idx_f is not None: df_f.loc[idx_f] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_frais_idx = None
                st.rerun()
            if idx_f is not None and sub_col2.form_submit_button("Annuler"):
                st.session_state.edit_frais_idx = None
                st.rerun()

    if not df_f.empty:
        # Tri par date décroissante pour la maintenance
        df_f['dt'] = df_f['Date'].apply(parse_d)
        for i, r in df_f.sort_values('dt', ascending=False).iterrows():
            st.markdown(f'''
                <div class="frais-card">
                    <div style="float:right; color:#c62828; font-weight:bold; font-size:1.1rem;">-{fmt_p(r.get("Montant"))}</div>
                    <b>{r.get("Type")}</b> — {r.get("Date")}<br>
                    <div style="background:#f9f9f9; padding:8px; margin-top:8px; font-size:0.9rem; border-left:3px solid #ccc;">
                        {r.get("Note","Aucun détail")}
                    </div>
                </div>
            ''', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"editf_{i}"):
                st.session_state.edit_frais_idx = i
                st.rerun()
                
            if st.session_state.del_frais_idx == i:
                st.warning("Confirmer la suppression ?")
                cy, cn = st.columns(2)
                if cy.button("✅ OUI", key=f"yf_{i}"):
                    df_f.drop(i).pipe(sauvegarder_data, "frais.json")
                    st.session_state.del_frais_idx = None
                    st.rerun()
                if cn.button("❌ NON", key=f"nf_{i}"):
                    st.session_state.del_frais_idx = None
                    st.rerun()
            else:
                if c2.button("🗑️ Supprimer", key=f"delf_{i}"):
                    st.session_state.del_frais_idx = i
                    st.rerun()

# --- RESTE DU CODE (LISTE, PLAN, FORM) ---
# [Le code pour Liste et Planning reste identique pour préserver les fonctionnalités validées précédemment]













































































































































































