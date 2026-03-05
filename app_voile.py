import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- STYLE CSS COMPLET ---
st.markdown("""
    <style>
    .header-container { text-align: center; margin-bottom: 10px; padding: 5px; background-color: #f8f9fa; border-radius: 10px; border: 1px solid #e1e8ed; }
    .main-title { color: #1a2a6c; font-size: 1.2rem; font-weight: bold; text-transform: uppercase; }
    .page-title { background: #1a2a6c; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; font-size: 0.9rem; }
    div.stButton > button { border-radius: 8px; height: 50px; font-size: 0.7rem !important; font-weight: bold; }
    
    /* Fiches Liste & Maint */
    .client-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 15px solid #ccc; position: relative; }
    .frais-card { background: white; padding: 12px; border-radius: 10px; margin-bottom: 8px; border: 1px solid #ddd; border-left: 10px solid #1a2a6c; }
    
    /* Calendrier */
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .cal-table th { background: #f8f9fa; font-size: 0.7rem; padding: 8px; border: 1px solid #eee; }
    .cal-table td { border: 1px solid #eee; height: 50px; text-align: center; font-size: 1rem; font-weight: bold; }
    
    /* Détails sous calendrier */
    .day-detail { padding: 10px; border-radius: 8px; margin-bottom: 8px; background: #ffffff; border: 1px solid #eee; border-left: 10px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    
    /* Stats */
    .recap-box { background: #f1f2f6; padding: 15px; border-radius: 8px; border: 1px solid #dfe4ea; margin-bottom: 15px; text-align: center; }
    .stats-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .stats-table th { background: #1a2a6c; color: white; padding: 10px; text-align: left; }
    .stats-table td { padding: 10px; border-bottom: 1px solid #eee; }
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
keys = {"page": "LISTE", "auth": False, "view_mode": "FUTUR", "cal_month": datetime.now().month, "cal_year": datetime.now().year, 
        "confirm_del": None, "confirm_del_frais": None, "edit_frais_idx": None, "form_frais_open": False, "edit_idx": None}
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
    if st.button("🔧\nMAINT", use_container_width=True, type="primary" if st.session_state.page == "FRAIS" else "secondary"): st.session_state.page = "FRAIS"; st.rerun()
st.markdown("---")

# --- PAGES ---

if st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING COMPLET</div>', unsafe_allow_html=True)
    c_prev, c_mon, c_next = st.columns([1,2,1])
    if c_prev.button("◀️"):
        st.session_state.cal_month -= 1
        if st.session_state.cal_month < 1: st.session_state.cal_month = 12; st.session_state.cal_year -= 1
        st.rerun()
    c_mon.markdown(f"<center><h3>{st.session_state.cal_month:02d} / {st.session_state.cal_year}</h3></center>", unsafe_allow_html=True)
    if c_next.button("▶️"):
        st.session_state.cal_month += 1
        if st.session_state.cal_month > 12: st.session_state.cal_month = 1; st.session_state.cal_year += 1
        st.rerun()

    occu = {}
    if not df.empty:
        for _, r in df.iterrows():
            d_start = parse_date(r.get('DateNav', ''))
            for j in range(to_int(r.get('NbJours', 1))):
                d_curr = d_start + timedelta(days=j)
                if d_curr.month == st.session_state.cal_month and d_curr.year == st.session_state.cal_year:
                    ds = d_curr.strftime('%d/%m/%Y')
                    if ds not in occu: occu[ds] = []
                    occu[ds].append(r)

    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for week in cal:
        h_c += '<tr>'
        for day in week:
            if day == 0: h_c += '<td></td>'
            else:
                ds = f"{day:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                bg, color = "white", "black"
                if ds in occu:
                    is_ok = any("OK" in str(x.get('Statut','')).upper() or "🟢" in str(x.get('Statut','')) for x in occu[ds])
                    bg = "#2ecc71" if is_ok else "#f1c40f"
                    color = "white"
                h_c += f'<td style="background:{bg}; color:{color};">{day}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)

    st.markdown("### 📋 Détails du mois")
    if occu:
        for d_key in sorted(occu.keys(), key=lambda x: int(x[:2])):
            for res in occu[d_key]:
                st_txt = res.get('Statut', '🟡 Attente')
                c_side = "#2ecc71" if "OK" in str(st_txt).upper() or "🟢" in str(st_txt) else "#f1c40f"
                st.markdown(f'<div class="day-detail" style="border-left-color:{c_side};"><b>{d_key}</b> : {res.get("Prénom","")} {res.get("Nom","")} ({res.get("Société","")}) <br> <small>Statut: {st_txt}</small></div>', unsafe_allow_html=True)
    else: st.info("Aucun engagement ce mois-ci.")

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
    if st.session_state.confirm_del_frais is not None:
        if st.button("CONFIRMER SUPPRESSION"):
            df_frais = df_frais.drop(st.session_state.confirm_del_frais); sauvegarder_data(df_frais, "frais.json")
            st.session_state.confirm_del_frais = None; st.rerun()
    
    if st.session_state.form_frais_open or st.session_state.edit_frais_idx is not None:
        idx = st.session_state.edit_frais_idx
        init = df_frais.loc[idx].to_dict() if (idx is not None and not df_frais.empty) else {}
        with st.form("f_maint"):
            f_dat = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            f_typ = st.selectbox("Type", ["Moteur", "Voiles", "Accastillage", "Electronique", "Coque", "Divers"], index=0)
            f_mon = st.text_input("Montant (€)", str(init.get("Montant", "0")))
            f_not = st.text_area("Note / Travaux", init.get("Note", ""))
            if st.form_submit_button("💾 ENREGISTRER"):
                row = {"Date": f_dat, "Type": f_typ, "Montant": f_mon, "Note": f_not}
                if idx is not None: df_frais.loc[idx] = row
                else: df_frais = pd.concat([df_frais, pd.DataFrame([row])], ignore_index=True)
                sauvegarder_data(df_frais, "frais.json"); st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
        if st.button("Annuler"): st.session_state.edit_frais_idx = None; st.session_state.form_frais_open = False; st.rerun()
    else:
        st.button("➕ AJOUTER UNE FICHE", on_click=lambda: setattr(st.session_state, 'form_frais_open', True), use_container_width=True)
        if not df_frais.empty:
            for i, r in df_frais.iloc[::-1].iterrows():
                st.markdown(f'<div class="frais-card"><div style="float:right; font-weight:bold; color:#c62828;">{to_float(r["Montant"]):.2f}€</div><b>{r["Type"]}</b> - {r["Date"]}<br><p style="font-size:0.85rem;">{r.get("Note","")}</p></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                c1.button("✏️", key=f"ef_{i}", on_click=lambda x=i: setattr(st.session_state, 'edit_frais_idx', x))
                c2.button("🗑️", key=f"df_{i}", on_click=lambda x=i: setattr(st.session_state, 'confirm_del_frais', x))

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN 2026+</div>', unsafe_allow_html=True)
    annee = st.selectbox("Année", [2026, 2027], index=0)
    total_ca = 0; total_fr = 0; stats = []
    for m in range(1, 13):
        ca = 0; fr = 0
        if not df.empty:
            df['dt'] = df['DateNav'].apply(parse_date)
            ca = sum(df[(df['dt'].dt.month == m) & (df['dt'].dt.year == annee) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_float))
        if not df_frais.empty:
            df_frais['dt'] = df_frais['Date'].apply(parse_date)
            fr = sum(df_frais[(df_frais['dt'].dt.month == m) & (df_frais['dt'].dt.year == annee)]['Montant'].apply(to_float))
        stats.append({"Mois": calendar.month_name[m], "CA": ca, "Frais": fr, "Net": ca-fr})
        total_ca += ca; total_fr += fr
    
    st.markdown(f'<div class="recap-box"><h3>BILAN {annee}</h3><b>CA: {total_ca:.0f}€ | FRAIS: {total_fr:.0f}€ | NET: {total_ca-total_fr:.0f}€</b></div>', unsafe_allow_html=True)
    st.table(pd.DataFrame(stats))

elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 LISTE DES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTUR", use_container_width=True): st.session_state.view_mode = "FUTUR"; st.rerun()
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"; st.rerun()
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()
    
    if not df.empty:
        df['dt_obj'] = df['DateNav'].apply(parse_date)
        data = df[df['dt_obj'] >= datetime.now()].sort_values('dt_obj') if st.session_state.view_mode == "FUTUR" else df[df['dt_obj'] < datetime.now()].sort_values('dt_obj', ascending=False)
        for i, r in data.iterrows():
            st_txt = str(r.get('Statut', '🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            st.markdown(f'<div class="client-card" style="border-left-color:{col};"><div style="float:right;"><b>{r.get("PrixJour","0")}€</b></div><b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br><small>{r.get("Société","")} | 📅 {r.get("DateNav","")}</small></div>', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"edit_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx is not None else {}
    with st.form("f_nav"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Refusé"], index=0)
        f_nom = st.text_input("Nom", init.get("Nom", ""))
        f_pre = st.text_input("Prénom", init.get("Prénom", ""))
        f_soc = st.text_input("Société", init.get("Société", ""))
        f_dat = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav", ""))
        f_nbj = st.number_input("Nombre de jours", min_value=1, value=to_int(init.get("NbJours", 1)))
        f_pri = st.text_input("Prix Total", init.get("PrixJour", "0"))
        if st.form_submit_button("💾 SAUVEGARDER"):
            row = {"Nom": f_nom, "Prénom": f_pre, "Société": f_soc, "DateNav": f_dat, "NbJours": str(f_nbj), "PrixJour": f_pri, "Statut": f_st}
            if idx is not None: df.loc[idx] = row
            else: df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            sauvegarder_data(df); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()






































































































































































