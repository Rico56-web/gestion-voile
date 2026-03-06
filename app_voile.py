import streamlit as st
import pandas as pd
import json, base64, requests, calendar
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; }
    .frais-card { background: #fff; padding: 12px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 8px; border: 1px solid #eee; }
    .note-card { background: #fff9c4; padding: 12px; border-radius: 8px; border-left: 10px solid #fbc02d; margin-bottom: 8px; border: 1px solid #fdd835; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.8rem; display:inline-block; margin: 5px 0; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table th { background: #1a2a6c; color: white; padding: 5px; font-size: 0.7rem; }
    .cal-table td { height: 40px; text-align: center; border: 1px solid #ddd; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
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

# --- 3. CHARGEMENT & MENU ---
df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
cols = st.columns(5)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
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
        data = df[df['dt'] >= datetime.now().replace(hour=0,minute=0,second=0)] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < datetime.now().replace(hour=0,minute=0,second=0)]
        for i, r in data.sort_values('dt').iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col_s = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel_c = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            st.markdown(f'<div class="client-card" style="border-left:12px solid {col_s};"><div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div><b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>📅 {r.get("DateNav")} ({r.get("NbJours")}j)<br>📞 <a href="tel:{r.get("Téléphone")}" style="color:#1a2a6c; font-weight:bold;">{r.get("Téléphone")}</a><br><a href="https://wa.me/{tel_c}" target="_blank" class="wa-btn">💬 WHATSAPP</a><br><span style="color:{col_s}; font-weight:bold;">{st_txt}</span></div>', unsafe_allow_html=True)
            c_ed, c_del = st.columns([1, 2])
            if c_ed.button("✏️", key=f"e_{i}"): st.session_state.edit_idx=i; st.session_state.page="FORM"; st.rerun()
            if c_del.checkbox("🗑️ Supprimer", key=f"ck_{i}"):
                if st.button("Confirmer suppression", key=f"bt_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING DÉTAILLÉ</div>', unsafe_allow_html=True)
    # Ajout du style pour la couleur CMN (Bleu)
    st.markdown("<style>.day-cmn { background-color: #3498db !important; color: white !important; }</style>", unsafe_allow_html=True)
    
    y, m = st.columns(2)
    p_y, p_m = y.selectbox("An", [2025, 2026], index=1), m.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, txt_plan = {}, []
    
    if not df.empty:
        for i, r in df.iterrows():
            d_s = parse_d(r.get('DateNav',''))
            if d_s.year == p_y and d_s.month == p_m:
                # Logique de couleur : CMN en bleu, sinon Vert (OK) ou Jaune (Attente)
                soc = str(r.get('Société','')).upper()
                if soc == "CMN":
                    cl = "day-cmn"
                else:
                    cl = "day-ok" if "OK" in str(r.get('Statut','')).upper() or "🟢" in str(r.get('Statut','')) else "day-wait"
                
                txt_plan.append(f"⚓ **{r.get('DateNav')}** : {r.get('Nom')} ({r.get('NbJours')}j) - {soc if soc else r.get('Statut')}")
                for j in range(int(float(r.get('NbJours', 1)))):
                    tg = d_s + timedelta(days=j)
                    if tg.month == p_m: occu[tg.day] = cl
                    
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            bg = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {bg}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)
    for t in txt_plan: st.write(t)
        
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 OBJECTIFS & STATS</div>', unsafe_allow_html=True)
    st.markdown("<style>td, th { white-space: nowrap !important; padding: 4px !important; font-size: 0.85rem !important; } table { width: 100% !important; }</style>", unsafe_allow_html=True)
    
    # --- SECTION OBJECTIF ANNUEL MODIFIABLE ---
    col_obj1, col_obj2 = st.columns([2, 1])
    s_y = col_obj1.selectbox("Année", [2025, 2026], index=1)
    # Champ modifiable pour l'objectif
    obj_annuel = col_obj2.number_input("Cible €", value=10000, step=1000)
    
    df['dt'], df_f['dt'] = df['DateNav'].apply(parse_d), df_f['Date'].apply(parse_d)
    
    # Calcul du CA annuel (uniquement 🟢 OK)
    mask_ca_an = (df['dt'].dt.year == s_y) & (df['Statut'].str.contains("OK|🟢", na=False))
    ca_total_an = sum(df[mask_ca_an]['PrixJour'].apply(to_f))
    
    # Calcul de la progression (max 100%)
    prog_val = min(ca_total_an / obj_annuel, 1.0) if obj_annuel > 0 else 0.0
    percent = (ca_total_an / obj_annuel * 100) if obj_annuel > 0 else 0
    
    st.write(f"📊 **Progression : {percent:.1f}%** ({fmt_p(ca_total_an)} / {fmt_p(obj_annuel)})")
    st.progress(prog_val)
    st.markdown("---")

    # --- SECTION TABLEAU MENSUEL ---
    mois_fr = ["Janv.", "Févr.", "Mars", "Avril", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
    res = []
    for i, m_name in enumerate(mois_fr):
        m_num = i + 1
        mask_m = (df['dt'].dt.year == s_y) & (df['dt'].dt.month == m_num) & (df['Statut'].str.contains("OK|🟢", na=False))
        ca_m = sum(df[mask_m]['PrixJour'].apply(to_f))
        
        mask_f_m = (df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == m_num)
        fr_m = sum(df_f[mask_f_m]['Montant'].apply(to_f))
        
        res.append({"Mois": m_name, "Revenus": fmt_p(ca_m), "Frais": fmt_p(fr_m), "Net": fmt_p(ca_m-fr_m)})
    
    st.table(pd.DataFrame(res).set_index('Mois'))


elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVEAU FRAIS", use_container_width=True): st.session_state.edit_f_idx="NEW"; st.rerun()
    if st.session_state.edit_f_idx:
        with st.form("f"):
            d, m, n = st.text_input("Date", datetime.now().strftime("%d/%m/%Y")), st.text_input("Montant"), st.text_area("Note")
            if st.form_submit_button("OK"):
                pd.concat([df_f, pd.DataFrame([{"Date":d, "Montant":m, "Note":n}])], ignore_index=True).pipe(sauvegarder_data, "frais.json"); st.session_state.edit_f_idx=None; st.rerun()
    for i, r in df_f.sort_index(ascending=False).iterrows():
        st.markdown(f'<div class="frais-card"><b>{r.get("Date")} : {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
        if st.checkbox("🗑️ Supprimer", key=f"df_{i}"):
            if st.button("Confirmer", key=f"bf_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE NOTE", use_container_width=True): st.session_state.edit_n_idx="NEW"; st.rerun()
    if st.session_state.edit_n_idx:
        with st.form("n"):
            t, c = st.text_input("Titre"), st.text_area("Contenu")
            if st.form_submit_button("OK"):
                pd.concat([df_n, pd.DataFrame([{"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}])], ignore_index=True).pipe(sauvegarder_data, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
    for i, r in df_n.iterrows():
        st.markdown(f'<div class="note-card"><b>{r.get("Titre")}</b><br>{r.get("Contenu")}</div>', unsafe_allow_html=True)
        if st.checkbox("🗑️ Supprimer", key=f"dn_{i}"):
            if st.button("Confirmer", key=f"bn_{i}"): df_n.drop(i).pipe(sauvegarder_data, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("edit"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        p, n, t = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Tél", init.get("Téléphone",""))
        d, j, pr = st.text_input("Date", init.get("DateNav","")), st.text_input("Jours", init.get("NbJours","1")), st.text_input("Prix", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Téléphone":t, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page="LISTE"; st.rerun()












































































































































































































