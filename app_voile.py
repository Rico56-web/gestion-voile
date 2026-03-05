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
        text-decoration: none; font-size: 0.8rem; font-weight: bold;
        text-align: center; margin-right: 5px; margin-top: 5px;
    }
    .btn-tel { background-color: #2ecc71; color: white !important; }
    .btn-mail { background-color: #3498db; color: white !important; }
    
    /* Cartes avec bordures de couleur selon statut */
    .client-card { background: white; padding: 10px; border-radius: 8px; margin-bottom: 5px; border: 1px solid #ddd; border-left: 10px solid #ccc; }
    .status-vert { border-left-color: #2ecc71 !important; } /* OK */
    .status-jaune { border-left-color: #f1c40f !important; } /* Attente */
    .status-rouge { border-left-color: #e74c3c !important; } /* Annulé/Refusé */
    .cmn-style { background-color: #f0f7ff !important; }
    
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    .cal-table th { background: #f8f9fa; font-size: 0.7rem; padding: 5px; border: 1px solid #eee; }
    .cal-table td { border: 1px solid #eee; height: 40px; text-align: center; font-size: 0.8rem; font-weight: bold; }
    
    .recap-box { background: #f1f2f6; padding: 10px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 15px; }
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

# --- MENU PRINCIPAL ---
st.markdown('<div class="header-container"><div class="main-title">⚓ VESTA SKIPPER</div></div>', unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
with m1: 
    st.button("📋\nLISTE", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary", on_click=lambda: st.session_state.update({"page": "LISTE"}))
with m2: 
    st.button("🗓️\nPLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary", on_click=lambda: st.session_state.update({"page": "PLANNING"}))
with m3: 
    st.button("💰\nSTATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary", on_click=lambda: st.session_state.update({"page": "BUDGET"}))
with m4: 
    st.button("🔧\nMAINT", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary", on_click=lambda: st.session_state.update({"page": "FRAIS"}))

st.markdown("---")

# --- PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 GESTION DES FICHES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 FUTURES", type="primary" if st.session_state.view_mode=="FUTUR" else "secondary", use_container_width=True): 
            st.session_state.view_mode="FUTUR"; st.rerun()
    with c2:
        if st.button("📂 ARCHIVES", type="primary" if st.session_state.view_mode=="ARCHIVES" else "secondary", use_container_width=True): 
            st.session_state.view_mode="ARCHIVES"; st.rerun()

    if st.button("➕ NOUVELLE FICHE", use_container_width=True): 
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    df['dt_obj'] = df['DateNav'].apply(parse_date)
    auj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    data = df[df['dt_obj'] >= auj].sort_values('dt_obj') if st.session_state.view_mode == "FUTUR" else df[df['dt_obj'] < auj].sort_values('dt_obj', ascending=False)
    
    for i, r in data.iterrows():
        # Détection du statut pour la couleur
        statut_brut = str(r.get('Statut', '🟡 Attente'))
        css_status = "status-jaune"
        if "🟢" in statut_brut or "OK" in statut_brut.upper(): css_status = "status-vert"
        if "🔴" in statut_brut or "REFUS" in statut_brut.upper() or "ANNUL" in statut_brut.upper(): css_status = "status-rouge"
        
        cl_cmn = "cmn-style" if "CMN" in str(r.get('Société','')).upper() else ""
        tel = str(r.get('Téléphone', '')).replace(' ', '')
        mail = str(r.get('Email', ''))
        
        st.markdown(f'''
            <div class="client-card {css_status} {cl_cmn}">
                <div style="float:right; font-weight:bold;">{to_float(r.get("PrixJour",0)):.2f}€</div>
                <b>{r.get("Prénom","")} {r.get("Nom","")}</b><br>
                <small>🏢 {r.get("Société","")} | 📅 {r.get("DateNav","")}</small><br>
                <div style="color:#555; font-size:0.8rem; margin-top:2px;">Statut: <b>{statut_brut}</b></div>
                <div style="margin-top:5px;">
                    {"<a href='tel:"+tel+"' class='contact-btn btn-tel'>📞 APPELER</a>" if tel and tel != 'nan' else ""}
                    {"<a href='mailto:"+mail+"' class='contact-btn btn-mail'>✉️ EMAIL</a>" if mail and mail != 'nan' else ""}
                </div>
            </div>
        ''', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        if c1.button("✏️ Gérer", key=f"ed_{i}", use_container_width=True):
            st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
        if c2.button("🗑️ Suppr.", key=f"del_{i}", use_container_width=True):
            df = df.drop(i); sauvegarder_data(df); st.rerun()

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE DÉTAILLÉE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    
    with st.form("edit"):
        f_nom = st.text_input("NOM", init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_tel = st.text_input("Téléphone", init.get("Téléphone", ""))
        f_mail = st.text_input("Email", init.get("Email", ""))
        f_soc = st.text_input("SOCIÉTÉ", init.get("Société", "")).upper()
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_prix = st.text_input("Prix Total (€)", str(init.get("PrixJour", "0")).replace(",", "."))
        
        # Le statut est bien ici
        liste_statuts = ["🟢 OK", "🟡 Attente", "🔴 Refusé/Annulé"]
        current_st = init.get("Statut", "🟡 Attente")
        if current_st not in liste_statuts: current_st = "🟡 Attente"
        f_st = st.selectbox("STATUT DE LA FICHE", liste_statuts, index=liste_statuts.index(current_st))
        
        if st.form_submit_button("💾 ENREGISTRER LA FICHE", use_container_width=True):
            row = {
                "Nom": f_nom, "Prénom": f_pre, "Téléphone": f_tel, "Email": f_mail, 
                "Société": f_soc, "DateNav": f_dat, "NbJours": str(init.get("NbJours",1)), 
                "PrixJour": f_prix, "Milles": str(init.get("Milles",0)), 
                "HeuresMoteur": str(init.get("HeuresMoteur",0)), "Statut": f_st
            }
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    
    if st.button("🔙 Retour sans enregistrer"): st.session_state.page = "LISTE"; st.rerun()

# --- (Les autres pages PLANNING, BUDGET, FRAIS restent inchangées) ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    # ... (reste du code planning identique)






















































































































































