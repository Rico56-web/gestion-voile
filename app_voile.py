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
    .frais-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 10px solid #1a2a6c; }
    .status-header { font-size: 0.75rem; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; padding: 2px 6px; border-radius: 4px; display: inline-block; }
    .header-vert { background: #e8f5e9; color: #2e7d32; }
    .header-jaune { background: #fffde7; color: #f9a825; }
    .header-rouge { background: #ffebee; color: #c62828; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    .cal-table th { background: #f8f9fa; font-size: 0.7rem; padding: 5px; border: 1px solid #eee; }
    .cal-table td { border: 1px solid #eee; height: 40px; text-align: center; font-size: 0.8rem; font-weight: bold; }
    .recap-box { background: #f1f2f6; padding: 15px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 15px; text-align: center; }
    .stats-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .stats-table th { background: #1a2a6c; color: white; padding: 10px; text-align: left; }
    .stats-table td { padding: 10px; border-bottom: 1px solid #eee; }
    .stats-table tr:nth-child(even) { background: #f9f9f9; }
    .current-month { background: #fffde7 !important; border-left: 5px solid #1a2a6c; }
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
keys = {"page": "LISTE", "auth": False, "view_mode": "FUTUR", "cal_month": datetime.now().month, "cal_year": datetime.now().year, "confirm_del": None, "confirm_del_frais": None, "edit_frais_idx": None, "form_frais_open": False}
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
    if st.button("📋\nLISTE", use_container_width=True, type="primary" if st.session_state.page == "LISTE" else "secondary"): st.session_state.page = "LISTE"; st.rerun()
with m2: 
    if st.button("🗓️\nPLAN", use_container_width=True, type="primary" if st.session_state.page == "PLANNING" else "secondary"): st.session_state.page = "PLANNING"; st.rerun()
with m3: 
    if st.button("💰\nSTATS", use_container_width=True, type="primary" if st.session_state.page == "BUDGET" else "secondary"): st.session_state.page = "BUDGET"; st.rerun()
with m4: 
    if st.button("🔧\nMAINT", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): st.session_state.page = "FRAIS"; st.session_state.form_frais_open = False; st.rerun()

st.markdown("---")

# --- PAGES ---

if st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 GESTION MAINTENANCE DÉTAILLÉE</div>', unsafe_allow_html=True)
    
    if st.session_state.confirm_del_frais is not None:
        idx_f = st.session_state.confirm_del_frais
        st.warning(f"⚠️ Supprimer cette dépense ?")
        c1, c2 = st.columns(2)
        if c1.button("✅ OUI"):
            df_frais = df_frais.drop(idx_f)
            sauvegarder_data(df_frais, "frais.json")
            st.session_state.confirm_del_frais = None; st.rerun()
        if c2.button("❌ NON"):
            st.session_state.confirm_del_frais = None; st.rerun()

    if st.session_state.form_frais_open or st.session_state.edit_frais_idx is not None:
        idx = st.session_state.edit_frais_idx
        init = df_frais.loc[idx].to_dict() if (idx is not None and not df_frais.empty) else {}
        with st.form("form_frais_complet"):
            f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_typ = st.selectbox("Type de maintenance", ["Moteur", "Voiles", "Accastillage", "Electronique", "Coque/Carénage", "Divers"], index=0)
            f_mon = st.text_input("Montant TTC (€)", str(init.get("Montant", "0.0")))
            f_not = st.text_area("Détails / Travaux effectués", init.get("Note", ""))
            if st.form_submit_button("💾 ENREGISTRER LA FICHE"):
                row = {"Date": f_dat, "Type": f_typ, "Montant": f_mon, "Note": f_not}
                if idx is not None: df_frais.loc[idx] = row
                else: df_frais = pd.concat([df_frais, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_frais, "frais.json")
                st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
        if st.button("🔙 Annuler"):
            st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
    else:
        if st.button("➕ AJOUTER UNE FICHE MAINTENANCE", use_container_width=True):
            st.session_state.form_frais_open = True; st.rerun()
        
        if not df_frais.empty:
            # Tri par date décroissante pour l'affichage
            df_frais['dt_temp'] = df_frais['Date'].apply(parse_date)
            for i, r in df_frais.sort_values('dt_temp', ascending=False).iterrows():
                st.markdown(f'''
                    <div class="frais-card">
                        <div style="float:right; color:#c62828; font-weight:bold;">{to_float(r["Montant"]):.2f}€</div>
                        <div style="font-weight:bold; color:#1a2a6c;">{r["Type"]}</div>
                        <small>📅 {r["Date"]}</small><br>
                        <div style="margin-top:5px; font-size:0.85rem;">{r.get("Note","")}</div>
                    </div>
                ''', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Modifier", key=f"ef_{i}"):
                    st.session_state.edit_frais_idx = i; st.rerun()
                if c2.button("🗑️ Supprimer", key=f"df_{i}"):
                    st.session_state.confirm_del_frais = i; st.rerun()

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 BILAN ACTIVITÉ (2026 ET FUTUR)</div>', unsafe_allow_html=True)
    annee_choisie = st.selectbox("Choisir l'année :", [2026, 2027, 2028], index=0)
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    stats_mois = []; total_ca = total_fr = 0
    for m in range(1, 13):
        ca_m = 0
        if not df.empty:
            df['dt_obj'] = df['DateNav'].apply(parse_date)
            mask = (df['dt_obj'].dt.month == m) & (df['dt_obj'].dt.year == annee_choisie) & (df['Statut'].str.contains("OK|🟢", case=False, na=False))
            ca_m = sum(df[mask]['PrixJour'].apply(to_float))
        fr_m = 0
        if not df_frais.empty:
            df_frais['dt_obj'] = df_frais['Date'].apply(parse_date)
            mask_fr = (df_frais['dt_obj'].dt.month == m) & (df_frais['dt_obj'].dt.year == annee_choisie)
            fr_m = sum(df_frais[mask_fr]['Montant'].apply(to_float))
        stats_mois.append({"Mois": mois_noms[m-1], "CA": ca_m, "Frais": fr_m, "Net": ca_m - fr_m, "is_now": (m == datetime.now().month and annee_choisie == 2026)})
        total_ca += ca_m; total_fr += fr_m
    st.markdown(f'<div class="recap-box"><h3 style="margin:0;">BILAN {annee_choisie}</h3><p style="font-size:1.2rem;">CA : {total_ca:.2f}€ | Frais : -{total_fr:.2f}€<br><b style="color:#2e7d32; font-size:1.5rem;">NET : {(total_ca - total_fr):.2f}€</b></p></div>', unsafe_allow_html=True)
    html = '<table class="stats-table"><tr><th>MOIS</th><th>CA (OK)</th><th>MAINT.</th><th>RÉSULTAT</th></tr>'
    for s in stats_mois:
        row_class = 'class="current-month"' if s['is_now'] else ''
        html += f'<tr {row_class}><td><b>{s["Mois"]}</b></td><td>{s["CA"]:.2f}€</td><td>-{s["Frais"]:.2f}€</td><td style="font-weight:bold; color:{"#2e7d32" if s["Net"]>=0 else "#c62828"};">{s["Net"]:.2f}€</td></tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)

# ... (Le reste du code pour LISTE, FORM et PLANNING reste identique)



































































































































































