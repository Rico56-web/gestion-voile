import streamlit as st
import pandas as pd
import json, base64, requests, calendar
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "SKIPPER2026": 
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect ❌")
    st.stop()

# Initialisation des états
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_s_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    
    /* Fiche Client Améliorée */
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    
    /* Badge Statut Apparent */
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    
    /* Bouton WA Discret */
    .wa-btn-discret { color: #555 !important; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; text-decoration: none !important; font-size: 0.75rem; display: inline-block; margin-top: 8px; background: #fdfdfd; }
    .wa-btn-discret:hover { background: #f0f0f0; }
    
    .secu-item { display: flex; align-items: center; justify-content: space-between; background: #f9f9f9; padding: 8px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #eee; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    if file == "secu.json": return pd.DataFrame([{"Item": "Vannes de coque"}, {"Item": "Niveaux Moteur"}, {"Item": "Météo OK"}])
    return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    st.cache_data.clear()

def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

df = charger_data("contacts.json")
df_s = charger_data("secu.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
m_cols = st.columns(6)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p
        st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # Filtres Futures / Passées
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"):
        st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"):
        st.session_state.view_mode="PASSÉES"; st.rerun()
        
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        
        for i, r in data.sort_values('dt').iterrows():
            soc = str(r.get('Société','')).strip().upper()
            statut = str(r.get('Statut','🟡 Attente'))
            # Couleur du badge selon statut
            badge_color = "#2ecc71" if "🟢" in statut or "OK" in statut.upper() else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            border_color = "#3498db" if soc == "CMN" else "#ccc"
            
            tel_clean = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            mail = r.get('Email','')

            st.markdown(f"""
                <div class="client-card" style="border-left: 10px solid {border_color};">
                    <div class="status-badge" style="color: {badge_color}; border-color: {badge_color}; background: {badge_color}15;">
                        {statut}
                    </div>
                    <b style="font-size:1.1rem; color:#1a2a6c;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                    🏢 <b>{soc}</b> | 📅 {r.get('DateNav')}<br>
                    📧 <a href="mailto:{mail}" style="color:#1a2a6c;">{mail}</a><br>
                    📞 <a href="tel:{tel_clean}" style="color:#1a2a6c; font-weight:bold;">{r.get('Téléphone','')}</a><br>
                    <a href="https://wa.me/{tel_clean}" target="_blank" class="wa-btn-discret">💬 WhatsApp</a>
                </div>
            """, unsafe_allow_html=True)
            
            # Boutons Actions
            ce, cd = st.columns([1, 2])
            if ce.button("✏️ Modifier", key=f"ed_l_{i}"):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if cd.checkbox("🗑️ Effacer", key=f"del_l_{i}"):
                if st.button("Confirmer suppression", key=f"conf_l_{i}"):
                    df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 GESTION SÉCURITÉ</div>', unsafe_allow_html=True)
    # Mode édition/ajout d'item
    if st.session_state.edit_s_idx is not None:
        idx = st.session_state.edit_s_idx
        val = df_s.loc[idx, "Item"] if idx != "NEW" else ""
        with st.form("edit_secu"):
            new_val = st.text_input("Point de contrôle :", val)
            if st.form_submit_button("✅ Enregistrer"):
                if idx == "NEW": df_s = pd.concat([df_s, pd.DataFrame([{"Item": new_val}])], ignore_index=True)
                else: df_s.at[idx, "Item"] = new_val
                sauvegarder_data(df_s, "secu.json"); st.session_state.edit_s_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_s_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER UN POINT", on_click=lambda: st.session_state.update({"edit_s_idx":"NEW"}), use_container_width=True)
        for i, r in df_s.iterrows():
            c_check, c_ed, c_del = st.columns([6, 1, 1])
            c_check.checkbox(r["Item"], key=f"s_{i}")
            if c_ed.button("✏️", key=f"es_{i}"): st.session_state.edit_s_idx = i; st.rerun()
            if c_del.button("🗑️", key=f"ds_{i}"): df_s.drop(i).pipe(sauvegarder_data, "secu.json"); st.rerun()

# Les autres pages (PLANNING, BUDGET, FRAIS, NOTES, FORM) conservent leur logique initiale.

















































































































































































































































