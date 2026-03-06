import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 10px; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; font-size: 0.9rem; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin-top:5px; }
</style>""", unsafe_allow_html=True)

# --- 2. DATA ---
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

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(5); menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page=p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx="NEW"; st.session_state.page="FORM"; st.rerun()
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < now]
        
        for i, r in data.sort_values('dt').iterrows():
            soc, st_t = str(r.get('Société','')).strip(), str(r.get('Statut','🟡'))
            is_an = "ANNULÉ" in st_t.upper() or "🔴" in st_t
            p_v = to_f(r.get("PrixJour", 0))
            col_s = "#3498db" if soc.upper() == "CMN" else ("#e74c3c" if is_an else ("#2ecc71" if "OK" in st_t.upper() or "🟢" in st_t else "#f1c40f"))
            
            fiche = f"""<div class="client-card" style="border-left:12px solid {col_s}; opacity: {'0.4' if is_an else '1'};">
                <div style="float:right;font-weight:bold;">{fmt_p(p_v) if not is_an else "---"}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                🏢 {soc} | 📅 <b>{r.get('DateNav')}</b> ({r.get('NbJours')}j)<br>
                📧 {r.get('Email','')}<br>📞 {r.get('Téléphone','')}<br>
                <span style="color:{col_s};font-weight:bold;">{st_t}</span>
            </div>"""
            st.markdown(fiche, unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            if ce.button("✏️", key=f"e_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
            if cd.checkbox("🗑️", key=f"ck_{i}"):
                if st.button("Confirmer", key=f"bt_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

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
                nb_j = int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        s_u = str(r.get('Société','')).strip().upper()
                        cl = "day-cmn" if s_u == "CMN" else ("day-ok" if "OK" in st_v or "🟢" in st_v else "day-wait")
                        occu[curr.day] = cl
                        if j == 0: details.append(f"⚓ **{curr.day}**: {r.get('Nom')} ({s_u if s_u else st_v})")

    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
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
    c1, c2 = st.columns([2, 1])
    s_y = c1.selectbox("Année", [2025, 2026], index=1)
    obj = c2.number_input("Objectif €", value=15000)
    
    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)
    
    ca_total = sum(df[(df['dt'].dt.year == s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **Objectif : {ca_total/obj*100:.1f}%** ({fmt_p(ca_total)} / {fmt_p(obj)})")
    st.progress(min(ca_total/obj, 1.0))
    
    res = []
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f))
        res.append({"Mois": calendar.month_name[i], "Revenu": fmt_p(rev), "Frais": fmt_p(fr), "Net": fmt_p(rev-fr)})
    st.table(pd.DataFrame(res).set_index('Mois'))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    
    # 1. GESTION DU FORMULAIRE (S'affiche en haut si edit_f_idx n'est pas None)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        if idx == "NEW":
            init = {"Date": datetime.now().strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
            st.subheader("➕ NOUVEAU FRAIS")
        else:
            init = df_f.loc[idx].to_dict()
            st.subheader("✏️ MODIFIER LE FRAIS")
            
        with st.form(key=f"form_frais_{idx}"):
            d = st.text_input("Date (JJ/MM/AAAA)", init.get("Date"))
            m = st.text_input("Montant (€)", str(init.get("Montant")))
            n = st.text_area("Note / Description", init.get("Note"))
            
            c_s, c_a = st.columns(2)
            if c_s.form_submit_button("✅ SAUVEGARDER"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW":
                    df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k, v in row.items(): df_f.at[idx, k] = v
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_f_idx = None
                st.rerun()
            if c_a.form_submit_button("❌ ANNULER"):
                st.session_state.edit_f_idx = None
                st.rerun()
        st.markdown("---")

    # 2. BOUTON AJOUTER (Visible seulement si on n'est pas en train d'éditer)
    if st.session_state.edit_f_idx is None:
        if st.button("➕ AJOUTER UN FRAIS", use_container_width=True):
            st.session_state.edit_f_idx = "NEW"
            st.rerun()

    # 3. LISTE DES FRAIS
    if not df_f.empty:
        # On trie pour avoir les plus récents en haut
        df_f_view = df_f.sort_index(ascending=False)
        for i, r in df_f_view.iterrows():
            st.markdown(f"""
                <div class="client-card" style="border-left:12px solid #95a5a6;">
                    <div style="float:right; font-weight:bold; color:#e74c3c;">{fmt_p(r.get('Montant'))}</div>
                    <b>📅 {r.get('Date')}</b><br>
                    <div style="font-size:0.9rem; margin-top:5px;">{r.get('Note')}</div>
                </div>
            """, unsafe_allow_html=True)
            
            ce, cd = st.columns([1, 2])
            # Utilisation d'un callback ou d'un bouton direct avec rerun
            if ce.button("✏️ Modifier", key=f"btn_edit_f_{i}"):
                st.session_state.edit_f_idx = i
                st.rerun()
                
            if cd.checkbox("🗑️ Supprimer", key=f"chk_del_f_{i}"):
                if st.button("Confirmer", key=f"btn_conf_f_{i}"):
                    df_f = df_f.drop(i)
                    sauvegarder_data(df_f, "frais.json")
                    st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if idx != "NEW" else {"Titre": "", "Contenu": ""}
        with st.form("n_form"):
            t = st.text_input("Titre", init.get("Titre"))
            c = st.text_area("Contenu", init.get("Contenu"))
            if st.form_submit_button("SAUVEGARDER"):
                row = {"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_n_idx=None; st.rerun()
    if st.button("➕ NOTE", use_container_width=True): st.session_state.edit_n_idx="NEW"; st.rerun()
    for i, r in df_n.iterrows():
        st.markdown(f'<div class="client-card"><b>{r.get("Titre")}</b> ({r.get("Date")})<br>{r.get("Contenu")}</div>', unsafe_allow_html=True)
        ce, cd = st.columns([1, 2])
        if ce.button("✏️", key=f"ne_{i}"): st.session_state.edit_n_idx=i; st.rerun()
        if cd.checkbox("🗑️", key=f"nc_{i}"):
            if st.button("Confirmer", key=f"nb_{i}"): df_n.drop(i).pipe(sauvegarder_data, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit_client"):
        st_v = st.selectbox("Statut *", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p, n, s = st.text_input("Prénom *", init.get("Prénom","")), st.text_input("Nom *", init.get("Nom","")), st.text_input("Société *", init.get("Société",""))
        d, j = st.text_input("Date (JJ/MM/AAAA) *", init.get("DateNav","")), st.text_input("Nb Jours *", init.get("NbJours","1"))
        t, em = st.text_input("Téléphone", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix Jour", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            if not all([p, n, s, d, j]): st.error("⚠️ Remplir les champs *")
            else:
                row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
                if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df.at[idx,k]=v
                sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page="LISTE"; st.rerun()
























































































































































































































