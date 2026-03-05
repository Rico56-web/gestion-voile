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
    .header-container { text-align: center; margin-bottom: 10px; padding: 5px; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e1e8ed; }
    .main-title { color: #1a2a6c; font-size: 1.2rem; font-weight: bold; text-transform: uppercase; }
    
    .page-title { 
        background: #1a2a6c; color: white; padding: 10px; 
        border-radius: 8px; text-align: center; font-weight: bold; 
        margin-bottom: 15px; font-size: 0.9rem;
    }
    
    div.stButton > button { 
        border-radius: 8px; height: 50px; font-size: 0.7rem !important; font-weight: bold;
    }
    
    .contact-btn {
        display: inline-block; padding: 8px 12px; border-radius: 5px;
        text-decoration: none; font-size: 0.7rem; font-weight: bold;
        text-align: center; margin-right: 5px; margin-top: 5px;
    }
    .btn-tel { background-color: #2ecc71; color: white !important; }
    .btn-mail { background-color: #3498db; color: white !important; }
    
    .client-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .status-vert { border-left-color: #2ecc71 !important; } 
    .status-jaune { border-left-color: #f1c40f !important; } 
    .status-rouge { border-left-color: #e74c3c !important; } 
    .cmn-style { background-color: #f0f7ff !important; }
    
    .status-header { font-size: 0.75rem; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; padding: 2px 6px; border-radius: 4px; display: inline-block; }
    .header-vert { background: #e8f5e9; color: #2e7d32; }
    .header-jaune { background: #fffde7; color: #f9a825; }
    .header-rouge { background: #ffebee; color: #c62828; }
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
        data = {"message": f"Update {file}", "content": content_b64, "sha": sha, "branch": "main"}
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
for key, val in {"page": "LISTE", "auth": False, "cal_month": datetime.now().month, "cal_year": datetime.now().year, "view_mode": "FUTUR", "confirm_del": None}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.auth:
    pwd = st.text_input("Code secret", type="password")
    if pwd == st.secrets["PASSWORD"]: st.session_state.auth = True; st.rerun()
    st.stop()

df = charger_data("contacts.json")
df_frais = charger_data("frais.json")

# --- MENU ---
st.markdown('<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    if st.button("📋\nLISTE", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"): 
        st.session_state.page = "LISTE"; st.session_state.confirm_del = None; st.rerun()
with m2: 
    if st.button("🗓️\nPLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary"): 
        st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰\nSTATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"): 
        st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧\nMAINT", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): 
        st.session_state.page = "FRAIS"; st.rerun()

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 GESTION DES FICHES</div>', unsafe_allow_html=True)
    
    # Confirmation de suppression
    if st.session_state.confirm_del is not None:
        idx_to_del = st.session_state.confirm_del
        st.warning(f"⚠️ Supprimer la fiche de **{df.loc[idx_to_del, 'Nom']}** ?")
        c1, c2 = st.columns(2)
        if c1.button("✅ OUI, SUPPRIMER", use_container_width=True):
            df = df.drop(idx_to_del)
            sauvegarder_data(df)
            st.session_state.confirm_del = None
            st.rerun()
        if c2.button("❌ ANNULER", use_container_width=True):
            st.session_state.confirm_del = None
            st.rerun()
        st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 FUTURES", type="primary" if st.session_state.view_mode=="FUTUR" else "secondary", use_container_width=True): 
            st.session_state.view_mode="FUTUR"; st.rerun()
    with c2:
        if st.button("📂 ARCHIVES", type="primary" if st.session_state.view_mode=="ARCHIVES" else "secondary", use_container_width=True): 
            st.session_state.view_mode="ARCHIVES"; st.rerun()

    if st.button("➕ NOUVELLE FICHE", use_container_width=True): 
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    if not df.empty:
        df['dt_obj'] = df['DateNav'].apply(parse_date)
        auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        data = df[df['dt_obj'] >= auj].sort_values('dt_obj') if st.session_state.view_mode == "FUTUR" else df[df['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
        
        for i, r in data.iterrows():
            st_text = str(r.get('Statut', '🟡 Attente'))
            css_status = "status-vert" if "OK" in st_text.upper() or "🟢" in st_text else ("status-rouge" if "REFUS" in st_text.upper() or "🔴" in st_text else "status-jaune")
            css_header = "header-vert" if "vert" in css_status else ("header-rouge" if "rouge" in css_status else "header-jaune")
            
            st.markdown(f'''
                <div class="client-card {css_status}">
                    <div class="status-header {css_header}">{st_text}</div>
                    <div style="float:right; font-weight:bold;">{to_float(r.get("PrixJour",0)):.2f}€</div>
                    <div style="margin-top:5px;"><b style="font-size:1rem;">{r.get("Prénom","")} {r.get("Nom","")}</b></div>
                    <small>🏢 {r.get("Société","")} | 📅 {r.get("DateNav","")} ({r.get("NbJours",1)} j.)</small><br>
                </div>
            ''', unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button("✏️ Gérer", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if c2.button("🗑️ Suppr.", key=f"del_{i}", use_container_width=True):
                st.session_state.confirm_del = i
                st.rerun()

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE DÉTAILLÉE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    
    with st.form("edit"):
        opts = ["🟢 OK", "🟡 Attente", "🔴 Refusé/Annulé"]
        curr = init.get("Statut", "🟡 Attente")
        idx_opt = 0 if ("OK" in str(curr).upper() or "🟢" in str(curr)) else (2 if ("REFUS" in str(curr).upper() or "🔴" in str(curr)) else 1)
        f_st = st.selectbox("STATUT", opts, index=idx_opt)
        
        f_nom = st.text_input("NOM", init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", init.get("Société", "")).upper()
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        
        # --- LE NOMBRE DE JOURS EST ICI ---
        f_nbj = st.number_input("Nombre de jours", min_value=1, max_value=30, value=to_int(init.get("NbJours", 1)))
        
        f_prix = st.text_input("Prix Total (€)", str(init.get("PrixJour", "0")).replace(",", "."))
        f_tel = st.text_input("Téléphone", init.get("Téléphone", ""))
        f_mail = st.text_input("Email", init.get("Email", ""))
        
        if st.form_submit_button("💾 ENREGISTRER LA FICHE", use_container_width=True):
            row = {
                "Nom": f_nom, "Prénom": f_pre, "Téléphone": f_tel, "Email": f_mail, 
                "Société": f_soc, "DateNav": f_dat, "NbJours": str(f_nbj), 
                "PrixJour": f_prix, "Milles": str(init.get("Milles",0)), 
                "HeuresMoteur": str(init.get("HeuresMoteur",0)), "Statut": f_st
            }
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    
    if st.button("🔙 Retour"): st.session_state.page = "LISTE"; st.rerun()

# --- AUTRES SECTIONS (PLANNING, BUDGET, FRAIS) ---
# (Le code suivant reste identique aux versions précédentes pour assurer le fonctionnement global)
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    # ... (reste du code planning)


























































































































































