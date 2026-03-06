import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")

for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin: 5px 0; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 40px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS GITHUB ---
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
            soc = str(r.get('Société','')).strip()
            st_txt = str(r.get('Statut','🟡'))
            mail = str(r.get('Email','')).strip()
            tel = str(r.get('Téléphone',''))
            tel_c = "".join(filter(str.isdigit, tel))
            is_an = "ANNULÉ" in st_txt.upper() or "🔴" in st_txt
            opac = "0.4" if is_an else "1"
            p_v = to_f(r.get("PrixJour", 0))
            p_s = fmt_p(p_v)
            al = f'<div style="color:#e74c3c;font-weight:bold;font-size:0.8rem;margin-top:5px;border:1px dashed #e74c3c;padding:2px;text-align:center;">⚠️ PRIX MANQUANT</div>' if p_v <= 0 and not is_an else ""
            if soc.upper() == "CMN": col_s = "#3498db"
            elif is_an: col_s = "#e74c3c"
            else: col_s = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else "#f1c40f"
            l_s = f"🏢 <b>{soc}</b><br>" if soc else ""
            l_m = f"📧 <a href='mailto:{mail}' style='color:#1a2a6c;'>{mail}</a><br>" if mail else ""
            fiche = f"""<div class="client-card" style="border-left:12px solid {col_s}; opacity: {opac};">
                <div style="float:right;font-weight:bold;color:{'#e74c3c' if p_v<=0 and not is_an else '#1a2a6c'};">{p_s if not is_an else "---"}</div>
                <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                {l_s}{l_m}📅 <b>{r.get('DateNav')}</b> ({r.get('NbJours')}j)<br>
                📞 <a href="tel:{tel}" style="color:#1a2a6c;font-weight:bold;text-decoration:none;">{tel}</a><br>
                <a href="https://wa.me/{tel_c}" target="_blank" class="wa-btn">💬 WHATSAPP</a><br>
                <span style="color:{col_s};font-weight:bold;">{st_txt}</span>{al}</div>"""
            st.markdown(fiche, unsafe_allow_html=True)
            c_e, c_d = st.columns([1, 2])
            if c_e.button("✏️", key=f"e_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
            if c_d.checkbox("🗑️", key=f"ck_{i}"):
                if st.button("Confirmer", key=f"bt_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y, m = st.columns(2); p_y, p_m = y.selectbox("An", [2025, 2026], index=1), m.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, txt_p = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            st_val = str(r.get('Statut','')).upper()
            if "ANNULÉ" not in st_val and "🔴" not in st_val:
                d_s = parse_d(r.get('DateNav',''))
                if d_s.year == p_y and d_s.month == p_m:
                    s_u = str(r.get('Société','')).strip().upper()
                    cl = "day-cmn" if s_u == "CMN" else ("day-ok" if "OK" in st_val or "🟢" in st_val else "day-wait")
                    txt_p.append(f"⚓ **{r.get('DateNav')}** : {r.get('Nom')} ({s_u if s_u else r.get('Statut')})")
                    for j in range(int(float(r.get('NbJours', 1)))):
                        tg = d_s + timedelta(days=j)
                        if tg.month == p_m: occu[tg.day] = cl
    cal = calendar.monthcalendar(p_y, p_m); h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    for t in txt_p: st.write(t)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS</div>', unsafe_allow_html=True)
    c_o1, c_o2 = st.columns([2, 1]); s_y = c_o1.selectbox("Année", [2025, 2026], index=1); obj = c_o2.number_input("Cible €", value=10000, step=1000)
    df['dt'], df_f['dt'] = df['DateNav'].apply(parse_d), df_f['Date'].apply(parse_d)
    ca_an = sum(df[(df['dt'].dt.year==s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📊 **{ca_an/obj*100:.1f}%** ({fmt_p(ca_an)} / {fmt_p(obj)})"); st.progress(min(ca_an/obj, 1.0))
    mois_fr = ["Janv.", "Févr.", "Mars", "Avril", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
    res = []
    for i, m_n in enumerate(mois_fr):
        c_m = sum(df[(df['dt'].dt.year==s_y) & (df['dt'].dt.month==i+1) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        f_m = sum(df_f[(df_f['dt'].dt.year==s_y) & (df_f['dt'].dt.month==i+1)]['Montant'].apply(to_f))
        res.append({"Mois": m_n, "Rev": fmt_p(c_m), "Frais": fmt_p(f_m), "Net": fmt_p(c_m-f_m)})
    st.table(pd.DataFrame(res).set_index('Mois'))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENACE & FRAIS</div>', unsafe_allow_html=True)
    
    # Bouton pour ajouter un nouveau frais
    if st.button("➕ AJOUTER UN FRAIS", use_container_width=True):
        st.session_state.edit_f_idx = "NEW"
        st.rerun()

    # Formulaire d'ajout ou de modification
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        # Pré-remplissage si modification
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {"Date": datetime.now().strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
        
        with st.form("form_frais"):
            st.write("📝 Détails du frais" if idx == "NEW" else "✏️ Modifier le frais")
            d = st.text_input("Date (JJ/MM/AAAA)", init.get("Date"))
            m = st.text_input("Montant (€)", init.get("Montant"))
            n = st.text_area("Description / Note", init.get("Note"))
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("SAUVEGARDER"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW":
                    df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k, v in row.items(): df_f.at[idx, k] = v
                sauvegarder_data(df_f, "frais.json")
                st.session_state.edit_f_idx = None
                st.rerun()
            if c2.form_submit_button("ANNULER"):
                st.session_state.edit_f_idx = None
                st.rerun()

    # Affichage de la liste des frais
    if not df_f.empty:
        # Tri par date (le plus récent en haut)
        for i, r in df_f.sort_index(ascending=False).iterrows():
            st.markdown(f"""
                <div class="client-card" style="border-left: 12px solid #95a5a6;">
                    <div style="float:right; font-weight:bold; color:#e74c3c;">{fmt_p(r.get('Montant'))}</div>
                    <b>📅 {r.get('Date')}</b><br>
                    <div style="font-size:0.9rem; margin-top:5px;">{r.get('Note')}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Boutons d'action
            col_ed, col_del = st.columns([1, 2])
            if col_ed.button("✏️", key=f"f_ed_{i}"):
                st.session_state.edit_f_idx = i
                st.rerun()
            
            if col_del.checkbox("🗑️", key=f"f_ck_{i}"):
                if st.button("Confirmer la suppression", key=f"f_bt_{i}"):
                    df_f = df_f.drop(i)
                    sauvegarder_data(df_f, "frais.json")
                    st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.button("➕ NOTE", use_container_width=True): st.session_state.edit_n_idx="NEW"; st.rerun()
    if st.session_state.edit_n_idx:
        with st.form("n"):
            t, c = st.text_input("Titre"), st.text_area("Contenu")
            if st.form_submit_button("OK"):
                pd.concat([df_n, pd.DataFrame([{"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}])], ignore_index=True).pipe(sauvegarder_data, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
    for i, r in df_n.iterrows():
        st.markdown(f'<div class="client-card"><b>{r.get("Titre")}</b><br>{r.get("Contenu")}</div>', unsafe_allow_html=True)

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx; init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit"):
        st_v = st.selectbox("Statut *", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p = st.text_input("Prénom *", init.get("Prénom",""))
        n = st.text_input("Nom *", init.get("Nom",""))
        s = st.text_input("Société *", init.get("Société",""))
        d = st.text_input("Date (JJ/MM/AAAA) *", init.get("DateNav",""))
        j = st.text_input("Nb Jours *", init.get("NbJours","1"))
        t = st.text_input("Téléphone", init.get("Téléphone",""))
        em = st.text_input("Email", init.get("Email",""))
        pr = st.text_input("Prix Jour", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            if not all([p, n, s, d, j]): st.error("⚠️ Remplir les champs avec *")
            else:
                row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
                if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df.at[idx,k]=v
                sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page="LISTE"; st.rerun()
























































































































































































































