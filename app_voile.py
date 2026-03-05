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
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; font-size: 0.9rem; }
    div.stButton > button { border-radius: 8px; height: 50px; font-size: 0.7rem !important; font-weight: bold; }
    .client-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 15px solid #ccc; }
    .status-vert { border-left-color: #2ecc71 !important; } 
    .status-jaune { border-left-color: #f1c40f !important; } 
    .status-rouge { border-left-color: #e74c3c !important; } 
    .frais-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 10px solid #1a2a6c; }
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
keys = {
    "page": "LISTE", "auth": False, "view_mode": "FUTUR", 
    "confirm_del": None, "confirm_del_frais": None,
    "edit_frais_idx": None, "form_frais_open": False
}
for key, val in keys.items():
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
        st.session_state.page = "LISTE"; st.rerun()
with m2: 
    if st.button("🗓️\nPLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary"): 
        st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰\nSTATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"): 
        st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧\nMAINT", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): 
        st.session_state.page = "FRAIS"; st.session_state.form_frais_open = False; st.rerun()

st.markdown("---")

# --- PAGE MAINTENANCE (FRAIS) ---
if st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 GESTION MAINTENANCE</div>', unsafe_allow_html=True)

    # 1. Gestion des suppressions
    if st.session_state.confirm_del_frais is not None:
        idx_f = st.session_state.confirm_del_frais
        st.warning(f"⚠️ Supprimer la dépense du {df_frais.loc[idx_f, 'Date']} ?")
        c1, c2 = st.columns(2)
        if c1.button("✅ CONFIRMER", use_container_width=True):
            df_frais = df_frais.drop(idx_f); sauvegarder_data(df_frais, "frais.json"); st.session_state.confirm_del_frais = None; st.rerun()
        if c2.button("❌ ANNULER", use_container_width=True):
            st.session_state.confirm_del_frais = None; st.rerun()

    # 2. Formulaire (Ajout ou Modif)
    if st.session_state.form_frais_open or st.session_state.edit_frais_idx is not None:
        idx = st.session_state.edit_frais_idx
        init = df_frais.loc[idx].to_dict() if idx is not None else {}
        
        with st.form("form_frais"):
            st.subheader("🛠️ Détails Maintenance")
            f_dat = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_typ = st.selectbox("Type", ["Moteur", "Voiles", "Accastillage", "Electronique", "Divers"], index=["Moteur", "Voiles", "Accastillage", "Electronique", "Divers"].index(init.get("Type", "Moteur")))
            f_mon = st.text_input("Montant (€)", str(init.get("Montant", "0.0")).replace(",", "."))
            f_com = st.text_area("Note / Détail", init.get("Note", ""))
            
            if st.form_submit_button("💾 ENREGISTRER LA DÉPENSE", use_container_width=True):
                row = {"Date": f_dat, "Type": f_typ, "Montant": f_mon, "Note": f_com}
                if idx is not None: df_frais.loc[idx] = row
                else: df_frais = pd.concat([df_frais, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_frais, "frais.json")
                st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
        
        if st.button("🔙 Retour à la liste"):
            st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
    
    # 3. Liste d'affichage
    else:
        if st.button("➕ AJOUTER UNE DÉPENSE", use_container_width=True):
            st.session_state.form_frais_open = True; st.rerun()
        
        st.markdown("### Historique des interventions")
        if not df_frais.empty:
            # Tri par date (approximatif si texte, idéalement à convertir)
            for i, r in df_frais.iloc[::-1].iterrows():
                st.markdown(f'''
                    <div class="frais-card">
                        <div style="float:right; color:#c62828; font-weight:bold;">{to_float(r['Montant']):.2f}€</div>
                        <b>📅 {r['Date']}</b> | {r['Type']}<br>
                        <small>{r.get('Note', '')}</small>
                    </div>
                ''', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Modifier", key=f"ed_f_{i}", use_container_width=True):
                    st.session_state.edit_frais_idx = i; st.rerun()
                if c2.button("🗑️ Supprimer", key=f"del_f_{i}", use_container_width=True):
                    st.session_state.confirm_del_frais = i; st.rerun()
        else:
            st.info("Aucune donnée de maintenance.")

# --- LES AUTRES PAGES (LISTE CONTACTS, PLANNING, BUDGET) ---
# (Le code reste identique pour les autres sections)
elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 GESTION DES FICHES</div>', unsafe_allow_html=True)
    # ... (code précédent pour les contacts)
    if st.session_state.confirm_del is not None:
        idx_to_del = st.session_state.confirm_del
        st.warning(f"⚠️ Supprimer la fiche de **{df.loc[idx_to_del, 'Nom']}** ?")
        c1, c2 = st.columns(2)
        if c1.button("✅ OUI", use_container_width=True):
            df = df.drop(idx_to_del); sauvegarder_data(df); st.session_state.confirm_del = None; st.rerun()
        if c2.button("❌ NON", use_container_width=True):
            st.session_state.confirm_del = None; st.rerun()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 FUTURES", type="primary" if st.session_state.view_mode=="FUTUR" else "secondary", use_container_width=True): st.session_state.view_mode="FUTUR"; st.rerun()
    with c2:
        if st.button("📂 ARCHIVES", type="primary" if st.session_state.view_mode=="ARCHIVES" else "secondary", use_container_width=True): st.session_state.view_mode="ARCHIVES"; st.rerun()
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    if not df.empty:
        df['dt_obj'] = df['DateNav'].apply(parse_date)
        data = df[df['dt_obj'] >= datetime.now().replace(hour=0,minute=0,second=0)].sort_values('dt_obj') if st.session_state.view_mode == "FUTUR" else df[df['dt_obj'] < datetime.now().replace(hour=0,minute=0,second=0)].sort_values('dt_obj', ascending=False)
        for i, r in data.iterrows():
            st_text = str(r.get('Statut', '🟡 Attente'))
            css_status = "status-vert" if "OK" in st_text.upper() or "🟢" in st_text else ("status-rouge" if "REFUS" in st_text.upper() or "🔴" in st_text else "status-jaune")
            st.markdown(f'<div class="client-card {css_status}"><div class="status-header"><b>{st_text}</b></div><div style="float:right; font-weight:bold;">{to_float(r.get("PrixJour",0)):.2f}€</div><div><b>{r.get("Prénom","")} {r.get("Nom","")}</b></div><small>🏢 {r.get("Société","")} | 📅 {r.get("DateNav","")} ({r.get("NbJours",1)} j.)</small></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Gérer", key=f"ed_{i}", use_container_width=True): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if c2.button("🗑️ Suppr.", key=f"del_{i}", use_container_width=True): st.session_state.confirm_del = i; st.rerun()

elif st.session_state.page == "FORM":
    # ... (code formulaire contact identique)
    st.markdown('<div class="page-title">📝 FICHE DÉTAILLÉE</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    with st.form("edit"):
        f_st = st.selectbox("STATUT", ["🟢 OK", "🟡 Attente", "🔴 Refusé/Annulé"])
        f_nom = st.text_input("NOM", init.get("Nom", "")).upper()
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("SOCIÉTÉ", init.get("Société", "")).upper()
        f_dat = st.text_input("Date", init.get("DateNav", ""))
        f_nbj = st.number_input("Nb Jours", min_value=1, value=to_int(init.get("NbJours", 1)))
        f_prix = st.text_input("Prix Total (€)", str(init.get("PrixJour", "0")))
        if st.form_submit_button("💾 ENREGISTRER"):
            row = {"Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "DateNav": f_dat, "NbJours": str(f_nbj), "PrixJour": f_prix, "Statut": f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("🔙 Retour"): st.session_state.page = "LISTE"; st.rerun()

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES</div>', unsafe_allow_html=True)
    df_ok = df[df['Statut'].str.contains("OK|🟢", case=False, na=False)]
    total_ca = sum(df_ok['PrixJour'].apply(to_float))
    total_frais = sum(df_frais['Montant'].apply(to_float)) if not df_frais.empty else 0
    st.markdown(f'<div class="recap-box">CA: {total_ca:.2f}€ | Frais: -{total_frais:.2f}€<hr><b>NET: {(total_ca - total_frais):.2f}€</b></div>', unsafe_allow_html=True)




























































































































































