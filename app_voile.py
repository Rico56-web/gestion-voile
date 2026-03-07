import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- VERROUILLAGE PAR MOT DE PASSE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div style="background:#1a2a6c;color:white;padding:20px;border-radius:10px;text-align:center;">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "1234": # <--- CHANGE TON CODE ICI
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Code incorrect ❌")
    st.stop()

# Initialisation stable des variables
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin-top:5px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    st.cache_data.clear()

def to_f(v): 
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")
def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# Callbacks indispensables pour iPhone
def nav_to(p): st.session_state.page = p
def set_view(v): st.session_state.view_mode = v
def edit_nav(i): 
    st.session_state.edit_idx = i
    st.session_state.page = "FORM"

# Chargement
df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(5)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    cols[i].button(l, on_click=nav_to, args=(p,), use_container_width=True, type="primary" if st.session_state.page==p else "secondary")

# --- 4. PAGE LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("🚀 FUTURES", on_click=set_view, args=("FUTURES",), use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary")
    c2.button("📂 PASSÉES", on_click=set_view, args=("PASSÉES",), use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary")
    st.button("➕ NOUVELLE FICHE", on_click=edit_nav, args=("NEW",), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < now]
        
        for i, r in data.sort_values('dt').iterrows():
            soc, st_t = str(r.get('Société','')).strip(), str(r.get('Statut','🟡'))
            is_an = "ANNULÉ" in st_t.upper() or "🔴" in st_t
            p_v = to_f(r.get("PrixJour", 0))
            col_s = "#3498db" if soc.upper() == "CMN" else ("#e74c3c" if is_an else ("#2ecc71" if "OK" in st_t.upper() or "🟢" in st_t else "#f1c40f"))
            
            # Liens cliquables
            tel = str(r.get('Téléphone','')).strip()
            mail = str(r.get('Email','')).strip()
            tel_clean = "".join(filter(str.isdigit, tel))
            
            fiche = f"""<div class="client-card" style="border-left:12px solid {col_s}; opacity: {'0.4' if is_an else '1'};">
                <div style="float:right;font-weight:bold;">{fmt_p(p_v) if not is_an else "---"}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 {soc} | 📅 <b>{r.get('DateNav')}</b> ({r.get('NbJours')}j)<br>
                📧 <a href="mailto:{mail}" style="color:#1a2a6c;text-decoration:none;">{mail}</a><br>
                📞 <a href="tel:{tel_clean}" style="color:#1a2a6c;text-decoration:none;font-weight:bold;">{tel}</a><br>
                <a href="https://wa.me/{tel_clean}" target="_blank" class="wa-btn">💬 WHATSAPP</a><br>
                <span style="color:{col_s};font-weight:bold;">{st_t}</span></div>"""
            st.markdown(fiche, unsafe_allow_html=True)
            
            ce, cd = st.columns([1, 2])
            ce.button("✏️ Modifier", key=f"nav_e_{i}", on_click=edit_nav, args=(i,))
            if cd.checkbox("🗑️", key=f"nav_c_{i}"):
                if st.button("Confirmer", key=f"nav_b_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

# --- 5. PAGE FORMULAIRE (IMPORTANT) ---
elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 ÉDITION FICHE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit_nav"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p, n, s = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Société", init.get("Société",""))
        d, j = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav","")), st.text_input("Nb Jours", str(init.get("NbJours","1")))
        t, em = st.text_input("Téléphone", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix Jour", str(init.get("PrixJour","0")))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json")
            st.session_state.page="LISTE"
            st.rerun()
    st.button("Retour", on_click=nav_to, args=("LISTE",))

# --- Reste des pages (Planning, Budget, Frais, Notes) ---
# ... (Elles doivent être recollées ici pour être complètes)






























































































































































































































