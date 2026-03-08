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

# Initialisation des pages (6 onglets maintenant)
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .date-subtitle { color: #555; font-size: 0.9rem; text-align: center; margin-bottom: 20px; font-style: italic; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin: 5px 0; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .stCheckbox { background: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 5px; border: 1px solid #eee; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
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

df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")

def nav_to(p): st.session_state.page = p
def edit_nav(i): st.session_state.edit_idx = i; st.session_state.page = "FORM"

# --- 4. ENTÊTE ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
now = datetime.now()
now_str = now.strftime("%A %d %B %Y - %H:%M")
trad = {"Monday":"Lundi","Tuesday":"Mardi","Wednesday":"Mercredi","Thursday":"Jeudi","Friday":"Vendredi","Saturday":"Samedi","Sunday":"Dimanche",
        "January":"Janvier","February":"Février","March":"Mars","April":"Avril","May":"Mai","June":"Juin","July":"Juillet","August":"Août","September":"Septembre","October":"Octobre","November":"Novembre","December":"Décembre"}
for eng, fra in trad.items(): now_str = now_str.replace(eng, fra)
st.markdown(f'<div class="date-subtitle">🕒 {now_str}</div>', unsafe_allow_html=True)

# Menu étendu (6 boutons) - On utilise 2 lignes pour mobile
m_cols1 = st.columns(3); m_cols2 = st.columns(3)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    target = m_cols1[i] if i < 3 else m_cols2[i-3]
    target.button(l, on_click=nav_to, args=(p,), use_container_width=True, type="primary" if st.session_state.page==p else "secondary")

# --- 5. PAGES ---

# [Pages LISTE, PLANNING, BUDGET, FRAIS, NOTES inchangées mais incluses pour fonctionnement]
# --- (Version courte ici pour la lisibilité, le code complet suit la logique de tri et boutons modif) ---

if st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 CHECK-LIST SÉCURITÉ</div>', unsafe_allow_html=True)
    st.info("Vérifications indispensables avant de quitter le quai.")
    
    sections = {
        "⚓ Technique & Pont": ["Niveaux (Huile/Eau)", "Vannes de coque fermées/ouvertes", "Batteries & Tension", "Stock de Gasoil", "Amarres & Pare-battages"],
        "📡 Navigation": ["Météo du jour consultée", "Marées & Courants", "VHF en veille (Canal 16)", "Cartographie à jour"],
        "👥 Équipage / Clients": ["Briefing sécurité effectué", "Gilets de sauvetage ajustés", "Emplacement matériel sécu montré", "Consignes 'Homme à la mer'"]
    }
    
    for sec, items in sections.items():
        st.subheader(sec)
        for item in items:
            st.checkbox(item, key=f"check_{item.lower().replace(' ', '_')}")
    
    st.markdown("---")
    if st.button("🔄 RÉINITIALISER LA LISTE", use_container_width=True):
        for key in st.session_state.keys():
            if key.startswith("check_"): st.session_state[key] = False
        st.rerun()

# [Les autres blocs LISTE, PLANNING, BUDGET, FRAIS, NOTES et FORM restent identiques au code précédent]
# (Note : Je ré-injecte ici les blocs critiques demandés : Tri planning et Bilan stats)

elif st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    view = st.session_state.view_mode
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if view=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if view=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    st.button("➕ NOUVELLE FICHE", on_click=edit_nav, args=("NEW",), use_container_width=True)
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        data = df[df['dt'] >= now.replace(hour=0,minute=0,second=0)] if view=="FUTURES" else df[df['dt'] < now.replace(hour=0,minute=0,second=0)]
        for i, r in data.sort_values('dt').iterrows():
            soc, st_t = str(r.get('Société','')).strip(), str(r.get('Statut','🟡'))
            col_s = "#3498db" if soc.upper() == "CMN" else ("#2ecc71" if "OK" in st_t or "🟢" in st_t else ("#e74c3c" if "🔴" in st_t else "#f1c40f"))
            tel_c = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            st.markdown(f'<div class="client-card" style="border-left:12px solid {col_s};"><div style="float:right;font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div><b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>🏢 {soc} | 📅 <b>{r.get("DateNav")}</b><br><a href="tel:{tel_c}" style="text-decoration:none;color:#1a2a6c;">📞 {r.get("Téléphone","")}</a> | <a href="https://wa.me/{tel_c}" class="wa-btn">💬 WA</a><br><span style="color:{col_s};">{st_t}</span></div>', unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            ce.button("✏️", key=f"ed_{i}", on_click=edit_nav, args=(i,))
            if cd.checkbox("🗑️", key=f"del_{i}"):
                if st.button("Confirmer", key=f"conf_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y, p_m = y_col.selectbox("An", [2025, 2026], index=1), m_col.selectbox("Mois", range(1, 13), index=now.month-1)
    occu, details_list = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s = parse_d(r.get('DateNav',''))
                for j in range(int(to_f(r.get('NbJours', 1)))):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc_u = str(r.get('Société','')).strip().upper()
                        occu[curr.day] = "day-cmn" if soc_u == "CMN" else ("day-ok" if "OK" in str(r.get('Statut','')) else "day-wait")
                        if j == 0: details_list.append({"day": curr.day, "text": f"⚓ **{curr.day}**: {r.get('Nom')} ({soc_u})"})
    cal = calendar.monthcalendar(p_y, p_m); h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    for item in sorted(details_list, key=lambda x: x['day']): st.write(item['text'])

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026], index=1)
    obj = st.number_input("Cible €", value=15000, step=100)
    df['dt'], df_f['dt'] = df['DateNav'].apply(parse_d), df_f['Date'].apply(parse_d)
    ca = sum(df[(df['dt'].dt.year==s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **{ca/obj*100:.1f}%** ({fmt_p(ca)} / {fmt_p(obj)})"); st.progress(min(ca/obj, 1.0))
    st.markdown("---")
    st.subheader("📊 Bilan Mensuel")
    res = []
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year==s_y) & (df['dt'].dt.month==i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year==s_y) & (df_f['dt'].dt.month==i)]['Montant'].apply(to_f))
        res.append({"Mois": calendar.month_name[i], "Revenu": fmt_p(rev), "Frais": fmt_p(fr), "Net": fmt_p(rev-fr)})
    st.table(pd.DataFrame(res).set_index('Mois'))
    st.markdown("---")
    st.subheader("📄 Facture CMN")
    f_m = st.selectbox("Mois à facturer", range(1, 13), index=now.month-1, format_func=lambda x: calendar.month_name[x])
    df_cmn = df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == f_m) & (df['Société'].str.upper() == "CMN") & (df['Statut'].str.contains("OK|🟢", na=False))]
    if not df_cmn.empty:
        total_cmn = sum(df_cmn['PrixJour'].apply(to_f))
        corps = f"Bonjour, prestations {calendar.month_name[f_m]} {s_y} :\n" + "\n".join([f"- Le {r['DateNav']} : {fmt_p(r['PrixJour'])}" for _, r in df_cmn.iterrows()]) + f"\nTOTAL : {fmt_p(total_cmn)}"
        st.text_area("Aperçu", corps, height=100)
        st.markdown(f'<a href="mailto:contact@cmn.fr?subject=Facture&body={urllib.parse.quote(corps)}" style="background-color:#1a2a6c;color:white;padding:12px;text-decoration:none;border-radius:8px;display:block;text-align:center;">📧 ENVOYER</a>', unsafe_allow_html=True)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {"Date": now.strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
        with st.form("f_frais"):
            d, m, n = st.text_input("Date", init.get("Date")), st.text_input("Montant", str(init.get("Montant"))), st.text_area("Note", init.get("Note"))
            if st.form_submit_button("✅ OK"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW": df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_f.at[idx,k]=v
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
    else:
        st.button("➕ FRAIS", on_click=lambda: st.session_state.update({"edit_f_idx":"NEW"}), use_container_width=True)
        for i in reversed(df_f.index):
            r = df_f.loc[i]
            st.markdown(f'<div class="client-card"><b>{r.get("Date")} : {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            ce.button("✏️", key=f"fe_{i}", on_click=lambda i=i: st.session_state.update({"edit_f_idx":i}))
            if cd.checkbox("🗑️", key=f"fdel_{i}"):
                if st.button("Confirmer", key=f"fconf_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if idx != "NEW" else {"Titre": "", "Contenu": ""}
        with st.form("f_note"):
            t, c = st.text_input("Titre", init.get("Titre")), st.text_area("Contenu", init.get("Contenu"))
            if st.form_submit_button("✅ OK"):
                row = {"Titre":t, "Contenu":c, "Date":now.strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
    else:
        st.button("➕ NOTE", on_click=lambda: st.session_state.update({"edit_n_idx":"NEW"}), use_container_width=True)
        for i in reversed(df_n.index):
            r = df_n.loc[i]; st.markdown(f'<div class="client-card"><b>{r.get("Titre")}</b> ({r.get("Date")})<br>{r.get("Contenu")}</div>', unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            ce.button("✏️", key=f"ne_{i}", on_click=lambda i=i: st.session_state.update({"edit_n_idx":i}))
            if cd.checkbox("🗑️", key=f"ndel_{i}"):
                if st.button("Confirmer", key=f"nconf_{i}"): df_n.drop(i).pipe(sauvegarder_data, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx; init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit_nav"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p, n, s = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Société", init.get("Société",""))
        d, j = st.text_input("Date", init.get("DateNav","")), st.text_input("Nb Jours", str(init.get("NbJours","1")))
        t, em = st.text_input("Tél", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix", str(init.get("PrixJour","0")))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()















































































































































































































































