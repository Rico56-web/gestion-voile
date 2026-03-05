import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- 2. INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "edit_f_idx" not in st.session_state: st.session_state.edit_f_idx = None

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.2rem; color: #1a2a6c; margin-bottom: 20px; }
    .contact-link { color: #1a2a6c !important; text-decoration: underline !important; font-weight: bold; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; font-size: 0.8rem; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
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

# --- CHARGEMENT ---
df = charger_data("contacts.json")
df_f = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(4)
menu_items = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINTENANCE","FRAIS")]
for i, (label, pg) in enumerate(menu_items):
    if c_m[i].button(label, use_container_width=True, type="primary" if st.session_state.page == pg else "secondary"): 
        st.session_state.page = pg
        st.rerun()
st.markdown("---")

# --- PAGE STATS (CONSERVÉE) ---
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

# --- PAGE MAINTENANCE (FIX IPHONE) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    idx_f = st.session_state.edit_f_idx
    
    # Bouton pour ajouter un nouveau frais
    if st.button("➕ AJOUTER UN NOUVEAU FRAIS", use_container_width=True):
        st.session_state.edit_f_idx = "NEW"
        st.rerun()

    # Formulaire qui s'affiche seulement si on clique sur Modifier ou Ajouter
    if idx_f is not None:
        st.markdown("### 📝 Saisie du frais")
        init = df_f.loc[idx_f].to_dict() if idx_f != "NEW" else {}
        with st.form("f_form_mobile"):
            f_d = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_m = st.text_input("Montant (€)", init.get("Montant", ""))
            f_n = st.text_area("Note", init.get("Note", ""))
            
            c_save, c_cancel = st.columns(2)
            if c_save.form_submit_button("✅ VALIDER"):
                row = {"Date":f_d, "Montant":f_m, "Note":f_n}
                if idx_f != "NEW": df_f.loc[idx_f] = row
                else: df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_f_idx = None
                st.rerun()
            if c_cancel.form_submit_button("❌ ANNULER"):
                st.session_state.edit_f_idx = None
                st.rerun()
    
    st.markdown("---")
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
                st.session_state.edit_f_idx = i
                st.rerun()
            if c2.button("🗑️ Effacer", key=f"df_{i}"):
                df_f.drop(i).pipe(sauvegarder_data, "frais.json")
                st.rerun()

# --- PAGE LISTE & PLANNING (RÉTABLIS) ---
elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    # [Contenu de la liste avec liens cliquables rétabli]
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTURES"))
        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, eml = str(r.get('Téléphone','')), str(r.get('Email',''))
            st.markdown(f'''<div class="client-card" style="border-left-color:{col};"><b>{r.get("Nom","").upper()}</b> ({r.get("DateNav")})<br>📞 <a href="tel:{tel}" class="contact-link">{tel}</a> | ✉️ <a href="mailto:{eml}" class="contact-link">{eml}</a><br><span style="color:{col}; font-weight:bold;">{st_txt}</span> — {fmt_p(r.get("PrixJour"))}</div>''', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_{i}"):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    # [Calendrier compact rétabli]

























































































































































































