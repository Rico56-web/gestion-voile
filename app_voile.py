import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

# --- VERROUILLAGE PAR MOT DE PASSE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "VOTRE_MOT_DE_PASSE": # Remplacez par votre code
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Code incorrect ❌")
    st.stop() # Arrête le script ici tant qu'on n'est pas identifié
# Initialisation stable des variables d'état
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin: 5px 0; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
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

# Chargement initial
df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")

# --- 3. FONCTIONS CALLBACKS (STABILITÉ MOBILE) ---
def nav_to(p): st.session_state.page = p
def set_view(v): st.session_state.view_mode = v
def edit_nav(i): st.session_state.edit_idx = i; st.session_state.page = "FORM"
def edit_frais(i): st.session_state.edit_f_idx = i
def edit_note(i): st.session_state.edit_n_idx = i

# --- 4. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(5); menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    cols[i].button(l, on_click=nav_to, args=(p,), use_container_width=True, type="primary" if st.session_state.page==p else "secondary")

# --- 5. PAGES ---

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
            tel_c = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            al = f'<div style="color:#e74c3c;font-weight:bold;font-size:0.8rem;margin-top:5px;border:1px dashed #e74c3c;padding:2px;text-align:center;">⚠️ PRIX MANQUANT</div>' if p_v <= 0 and not is_an else ""
            fiche = f"""<div class="client-card" style="border-left:12px solid {col_s}; opacity: {'0.4' if is_an else '1'};">
                <div style="float:right;font-weight:bold;">{fmt_p(p_v) if not is_an else "---"}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 {soc} | 📅 <b>{r.get('DateNav')}</b> ({r.get('NbJours')}j)<br>
                📧 {r.get('Email','')}<br>📞 {r.get('Téléphone','')}<br>
                <a href="https://wa.me/{tel_c}" target="_blank" class="wa-btn">💬 WHATSAPP</a><br>
                <span style="color:{col_s};font-weight:bold;">{st_t}</span>{al}</div>"""
            st.markdown(fiche, unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            ce.button("✏️", key=f"nav_e_{i}", on_click=edit_nav, args=(i,))
            if cd.checkbox("🗑️", key=f"nav_c_{i}"):
                if st.button("Confirmer", key=f"nav_b_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y = y_col.selectbox("An", [2025, 2026], index=1)
    p_m = m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, details = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            st_v = str(r.get('Statut','')).upper()
            if "ANNULÉ" not in st_v and "🔴" not in st_v:
                d_s = parse_d(r.get('DateNav',''))
                for j in range(int(to_f(r.get('NbJours', 1)))):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc_u = str(r.get('Société','')).strip().upper()
                        cl = "day-cmn" if soc_u == "CMN" else ("day-ok" if "OK" in st_v or "🟢" in st_v else "day-wait")
                        occu[curr.day] = cl
                        if j == 0: details.append(f"⚓ **{curr.day}**: {r.get('Nom')} ({soc_u if soc_u else st_v})")
    cal = calendar.monthcalendar(p_y, p_m); h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    for t in sorted(details): st.write(t)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1]); s_y = c1.selectbox("Année", [2025, 2026], index=1); obj = c2.number_input("Cible €", value=15000)
    df['dt'], df_f['dt'] = df['DateNav'].apply(parse_d), df_f['Date'].apply(parse_d)
    ca = sum(df[(df['dt'].dt.year==s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **{ca/obj*100:.1f}%** ({fmt_p(ca)} / {fmt_p(obj)})"); st.progress(min(ca/obj, 1.0))
    res = []
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year==s_y) & (df['dt'].dt.month==i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year==s_y) & (df_f['dt'].dt.month==i)]['Montant'].apply(to_f))
        res.append({"Mois": calendar.month_name[i], "Revenu": fmt_p(rev), "Frais": fmt_p(fr), "Net": fmt_p(rev-fr)})
    st.table(pd.DataFrame(res).set_index('Mois'))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {"Date": datetime.now().strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
        with st.form("form_frais_fix"):
            d = st.text_input("Date", init.get("Date"))
            m = st.text_input("Montant", str(init.get("Montant")))
            n = st.text_area("Note", init.get("Note"))
            cs, ca = st.columns(2)
            if cs.form_submit_button("✅ SAUVEGARDER"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW": df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k,v in row.items(): df_f.at[idx,k]=v
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
            if ca.form_submit_button("❌ ANNULER"): st.session_state.edit_f_idx = None; st.rerun()
        st.markdown("---")
    st.button("➕ AJOUTER UN FRAIS", on_click=edit_frais, args=("NEW",), use_container_width=True)
    for i in reversed(df_f.index):
        r = df_f.loc[i]
        st.markdown(f'<div class="client-card"><b>{r.get("Date")} : {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
        ce, cd = st.columns([1, 2])
        ce.button("✏️", key=f"fe_{i}", on_click=edit_frais, args=(i,))
        if cd.checkbox("🗑️", key=f"fc_{i}"):
            if st.button("Confirmer", key=f"fb_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if idx != "NEW" else {"Titre": "", "Contenu": ""}
        with st.form("form_note_fix"):
            t = st.text_input("Titre", init.get("Titre"))
            c = st.text_area("Contenu", init.get("Contenu"))
            cs, ca = st.columns(2)
            if cs.form_submit_button("✅ SAUVEGARDER"):
                row = {"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
            if ca.form_submit_button("❌ ANNULER"): st.session_state.edit_n_idx=None; st.rerun()
        st.markdown("---")
    st.button("➕ NOTE", on_click=edit_note, args=("NEW",), use_container_width=True)
    for i in reversed(df_n.index):
        r = df_n.loc[i]
        st.markdown(f'<div class="client-card"><b>{r.get("Titre")}</b> ({r.get("Date")})<br>{r.get("Contenu")}</div>', unsafe_allow_html=True)
        ce, cd = st.columns([1, 2])
        ce.button("✏️", key=f"ne_{i}", on_click=edit_note, args=(i,))
        if cd.checkbox("🗑️", key=f"nc_{i}"):
            if st.button("Confirmer", key=f"nb_{i}"): df_n.drop(i).pipe(sauvegarder_data, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx; init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit_nav_fix"):
        st_v = st.selectbox("Statut *", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p, n, s = st.text_input("Prénom *", init.get("Prénom","")), st.text_input("Nom *", init.get("Nom","")), st.text_input("Société *", init.get("Société",""))
        d, j = st.text_input("Date (JJ/MM/AAAA) *", init.get("DateNav","")), st.text_input("Nb Jours *", init.get("NbJours","1"))
        t, em = st.text_input("Téléphone", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix Jour", str(init.get("PrixJour","0")))
        if st.form_submit_button("SAUVEGARDER"):
            if not all([p, n, s, d, j]): st.error("⚠️ Remplir les champs *")
            else:
                row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
                if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df.at[idx,k]=v
                sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    st.button("Retour", on_click=nav_to, args=("LISTE",))



























































































































































































































