import streamlit as st
import pandas as pd
import json, base64, requests, calendar
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

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
states = {
    "page": "LISTE", "view_mode": "FUTURES", "cible_annuelle": 15000.0,
    "edit_idx": None, "edit_s_idx": None, "edit_f_idx": None, "edit_n_idx": None, "edit_log_idx": None
}
for k, v in states.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 0.9rem; border: 2px solid; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 60px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 5px; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 5px; text-decoration: none; color: white !important; font-weight: bold; margin-right: 5px; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: 
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
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

# Chargement
df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")
df_log = charger_data("livre_de_bord.json")
df_arch = charger_data("archives_factures.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("📖 LIVRE","LOGBOOK"), ("📄 FACT","FACTURE"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, key=f"m_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # Séparation Passées / Futures
    c1, c2 = st.columns(2)
    if c1.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): 
        st.session_state.view_mode="PASSÉES"; st.rerun()
    if c2.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): 
        st.session_state.view_mode="FUTURES"; st.rerun()
    
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] < today] if st.session_state.view_mode=="PASSÉES" else df[df['dt'] >= today]
        
        for i, r in data.sort_values('dt', ascending=(st.session_state.view_mode=="FUTURES")).iterrows():
            statut = str(r.get('Statut','🟡 Attente'))
            soc = str(r.get('Société','')).upper()
            tel = str(r.get('Tel','')).strip()
            mail = str(r.get('Mail','')).strip()
            
            # Nettoyage du numéro pour WhatsApp (enlève espaces, points, etc.)
            tel_clean = tel.replace(" ", "").replace(".", "").replace("-", "")
            if tel_clean.startswith("0"): tel_clean = "33" + tel_clean[1:]
            
            st.markdown(f"""
            <div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                <div class="status-badge">{statut}</div>
                <b style="font-size:1.2rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                📅 {r.get('DateNav')} ({r.get('NbJours','1')}j) | 🏢 {soc}<br>
                <span style="color:#555;">📞 {tel}</span><br>
                <span style="color:#555;">✉️ {mail}</span><br><br>
                <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                    <a href="tel:{tel_clean}" style="background:#3498db; color:white; padding:10px 15px; border-radius:5px; text-decoration:none; font-weight:bold;">📞 Appel</a>
                    <a href="https://wa.me/{tel_clean}" target="_blank" style="background:#25d366; color:white; padding:10px 15px; border-radius:5px; text-decoration:none; font-weight:bold;">💬 WhatsApp</a>
                    <a href="mailto:{mail}" style="background:#e67e22; color:white; padding:10px 15px; border-radius:5px; text-decoration:none; font-weight:bold;">✉️ Mail</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            ce, cd = st.columns([1, 3])
            if ce.button("✏️ MODIFIER", key=f"ed_l_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if cd.checkbox("🗑️ Supprimer", key=f"del_l_{i}"):
                if st.button("Confirmer suppression", key=f"conf_l_{i}"): 
                    df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "LOGBOOK":
    st.markdown('<div class="page-title">📖 LIVRE DE BORD</div>', unsafe_allow_html=True)
    if df_log.empty: df_log = pd.DataFrame(columns=["Date", "LieuD", "HeuresD", "MillesD", "Obs", "LieuA", "HeuresA", "MillesA", "Dist", "DeltaH"])
    idx_log = st.session_state.edit_log_idx
    init_log = df_log.loc[idx_log].to_dict() if (idx_log is not None and not df_log.empty) else {}
    with st.form("f_livre_bord"):
        st.subheader("🚩 ÉTAPE")
        c1, c2 = st.columns(2); date_l = c1.text_input("Date", init_log.get("Date", datetime.now().strftime("%d/%m/%Y"))); d_lieu = c2.text_input("Départ", init_log.get("LieuD", ""))
        c3, c4 = st.columns(2); d_h = c3.number_input("H Moteur Dép", value=float(init_log.get("HeuresD", 0.0))); d_mi = c4.number_input("Loch Dép", value=float(init_log.get("MillesD", 0.0)))
        obs = st.text_area("Observations", init_log.get("Obs", ""))
        c5, c6 = st.columns(2); a_lieu = c5.text_input("Arrivée", init_log.get("LieuA", "")); a_h = c6.number_input("H Moteur Arr", value=float(init_log.get("HeuresA", 0.0)))
        a_mi = st.number_input("Loch Arr", value=float(init_log.get("MillesA", 0.0)))
        if st.form_submit_button("⚓ ENREGISTRER"):
            row = {"Date":date_l, "LieuD":d_lieu, "HeuresD":d_h, "MillesD":d_mi, "Obs":obs, "LieuA":a_lieu, "HeuresA":a_h, "MillesA":a_mi, "Dist":a_mi-d_mi, "DeltaH":a_h-d_h}
            if idx_log is None: df_log = pd.concat([df_log, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df_log.at[idx_log, k] = v
                st.session_state.edit_log_idx = None
            sauvegarder_data(df_log, "livre_de_bord.json"); st.rerun()
    if not df_log.empty:
        for i in reversed(df_log.index):
            l = df_log.loc[i]
            with st.expander(f"📅 {l['Date']} | {l['LieuD']} ➔ {l['LieuA']}"):
                b1, b2, b3 = st.columns(3)
                b1.metric("DISTANCE", f"{float(l.get('Dist',0)):.1f} MN")
                b2.metric("MOTEUR", f"{float(l.get('DeltaH',0)):.1f} H")
                b3.metric("LOCH FIN", f"{float(l.get('MillesA',0)):.0f}")
                st.write(f"📝 {l['Obs']}")
                if st.button("✏️ Modifier étape", key=f"ed_log_{i}"): st.session_state.edit_log_idx = i; st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING DÉTAILLÉ</div>', unsafe_allow_html=True)
    y, m = st.columns(2)[0].selectbox("Année", [2025, 2026, 2027], index=1), st.columns(2)[1].selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu = {}
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s, nb_j = r['dt'], int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j):
                    curr = d_s + timedelta(days=j)
                    if curr.year == y and curr.month == m:
                        occu[curr.day] = ("day-cmn" if str(r.get('Société','')).upper() == "CMN" else "day-ok", f"{r.get('Prénom','')} {r.get('Nom','')[:1]}.")
    cal = calendar.monthcalendar(y, m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style, txt = (occu[d][0], f'<br><span style="font-size:0.7rem;">{occu[d][1]}</span>') if d in occu else ('', '')
            h += f'<td class="{style}">{d if d != 0 else ""}{txt}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026, 2027], index=1)
    res, t_rev, t_fra, t_pre = [], 0, 0, 0
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢"))]['PrixJour'].apply(to_f)) if not df.empty else 0
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f)) if not df_f.empty else 0
        pre = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢|🟡"))]['PrixJour'].apply(to_f)) if not df.empty else 0
        t_rev += rev; t_fra += fr; t_pre += pre
        res.append({"Mois": i, "Réalisé": int(rev), "Frais": int(fr), "Net": int(rev-fr), "Prévu": int(pre)})
    df_res = pd.DataFrame(res)
    st.table(df_res.set_index('Mois'))
    st.markdown(f"""<div style="background:#1a2a6c; color:white; padding:15px; border-radius:10px; display:flex; justify-content:space-between; font-weight:bold;">
        <span>TOTAL RÉALISÉ : {fmt_p(t_rev)}</span>
        <span>TOTAL FRAIS : {fmt_p(t_fra)}</span>
        <span>TOTAL NET : {fmt_p(t_rev-t_fra)}</span>
    </div>""", unsafe_allow_html=True)

elif st.session_state.page in ["SECU", "FRAIS", "NOTES"]:
    st.markdown(f'<div class="page-title">{st.session_state.page}</div>', unsafe_allow_html=True)
    # Logique générique pour gérer l'édition partout
    cur_df = df_s if st.session_state.page == "SECU" else (df_f if st.session_state.page == "FRAIS" else df_n)
    cur_idx = st.session_state.edit_s_idx if st.session_state.page == "SECU" else (st.session_state.edit_f_idx if st.session_state.page == "FRAIS" else st.session_state.edit_n_idx)
    cur_file = "secu.json" if st.session_state.page == "SECU" else ("frais.json" if st.session_state.page == "FRAIS" else "notes.json")
    
    if cur_idx is not None:
        init = cur_df.loc[cur_idx].to_dict() if (cur_idx != "NEW" and not cur_df.empty) else {}
        with st.form("edit_form"):
            if st.session_state.page == "SECU": 
                v = st.text_input("Point", init.get("Item", ""))
                row = {"Item": v}
            elif st.session_state.page == "FRAIS":
                d, m, n = st.text_input("Date", init.get("Date", "")), st.text_input("Montant", init.get("Montant", "0")), st.text_area("Note", init.get("Note", ""))
                row = {"Date": d, "Montant": m, "Note": n}
            else:
                t, c = st.text_input("Titre", init.get("Titre", "")), st.text_area("Contenu", init.get("Contenu", ""))
                row = {"Titre": t, "Contenu": c, "Date": datetime.now().strftime("%d/%m/%Y")}
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                if cur_idx == "NEW": cur_df = pd.concat([cur_df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): cur_df.at[cur_idx, k] = v
                sauvegarder_data(cur_df, cur_file)
                st.session_state.update({"edit_s_idx":None, "edit_f_idx":None, "edit_n_idx":None}); st.rerun()
    else:
        st.button("➕ AJOUTER", on_click=lambda: st.session_state.update({f"edit_{st.session_state.page[0].lower()}_idx":"NEW"}), use_container_width=True)
        for i, r in cur_df.iterrows():
            with st.container():
                st.markdown(f'<div class="client-card">{r.values[0]}</div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Modifier", key=f"ed_{st.session_state.page}_{i}"): 
                    st.session_state.update({f"edit_{st.session_state.page[0].lower()}_idx": i}); st.rerun()
                if c2.button("🗑️", key=f"del_{st.session_state.page}_{i}"): 
                    cur_df = cur_df.drop(i); sauvegarder_data(cur_df, cur_file); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if (idx != "NEW" and not df.empty) else {}
    with st.form("f_form"):
        st.subheader("📝 FICHE NAVIGATION")
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        c1, c2 = st.columns(2); p = c1.text_input("Prénom", init.get("Prénom","")); n = c2.text_input("Nom", init.get("Nom",""))
        c3, c4 = st.columns(2); d = c3.text_input("Date (DD/MM/YYYY)", init.get("DateNav","")); j = c4.text_input("Nb Jours", init.get("NbJours","1"))
        s = st.text_input("Société", init.get("Société",""))
        c5, c6 = st.columns(2); tel = c5.text_input("Tél", init.get("Tel","")); mail = c6.text_input("Mail", init.get("Mail",""))
        pr = st.text_input("Prix Total (€)", init.get("PrixJour","0"))
        if st.form_submit_button("💾 ENREGISTRER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v, "Tel":tel, "Mail":mail}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()

































































































































































































































































































