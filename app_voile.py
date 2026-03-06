import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- 1. CONFIGURATION & INITIALISATION ---
st.set_page_config(page_title="Vesta Skipper Pro", layout="wide")
for key, val in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 20px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-left: 12px solid #ccc; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .frais-card { background: #fff; padding: 15px; border-radius: 8px; border-left: 10px solid #c62828; margin-bottom: 12px; border: 1px solid #eee; }
    .note-card { background: #fff9c4; padding: 15px; border-radius: 8px; border-left: 10px solid #fbc02d; margin-bottom: 12px; border: 1px solid #fdd835; color: #333; }
    .recap-line { background: #f8f9fa; padding: 15px; border-radius: 10px; border: 2px solid #1a2a6c; text-align: center; font-weight: bold; font-size: 1.2rem; color: #1a2a6c; margin-bottom: 5px; }
    .contact-link { color: #1a2a6c !important; text-decoration: underline !important; font-weight: bold; }
    .wa-btn { background-color:#25D366; color:white !important; padding:6px 12px; border-radius:6px; text-decoration:none !important; font-weight:bold; font-size:0.85rem; display:inline-block; margin: 8px 0; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; margin-bottom: 20px; }
    .cal-table th { background: #1a2a6c; color: white; padding: 8px; border: 1px solid #ddd; font-size: 0.8rem; text-align: center; }
    .cal-table td { height: 45px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: middle; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-wait { background-color: #f1c40f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=10)
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
        requests.put(url, headers=headers, json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
        return True
    except: return False

def to_f(v):
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0
def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")
def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# --- CHARGEMENT ---
df, df_f, df_n = charger_data("contacts.json"), charger_data("frais.json"), charger_data("notes.json")

# --- MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER PRO</div>', unsafe_allow_html=True)
c_m = st.columns(5)
menu_items = [("📋 LISTE","LISTE"), ("🗓️ PLANNING","PLANNING"), ("💰 STATS","BUDGET"), ("🔧 MAINT.","FRAIS"), ("📝 NOTES","NOTES")]
for i, (label, pg) in enumerate(menu_items):
    if c_m[i].button(label, key=f"m_{pg}", use_container_width=True, type="primary" if st.session_state.page == pg else "secondary"): 
        st.session_state.page = pg; st.rerun()
st.markdown("---")

# --- LOGIQUE DES PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTURES" else "secondary"): st.session_state.view_mode = "FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode == "PASSÉES" else "secondary"): st.session_state.view_mode = "PASSÉES"; st.rerun()
    if st.button("➕ NOUVELLE FICHE", use_container_width=True): st.session_state.edit_idx = "NEW"; st.session_state.page = "FORM"; st.rerun()
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTURES"))
        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col_s = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel_b = str(r.get('Téléphone',''))
            tel_c = "".join(filter(str.isdigit, tel_b))
            st.markdown(f'''<div class="client-card" style="border-left:12px solid {col_s};">
                <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                📅 <b>{r.get("DateNav","")}</b> — ⏱️ <b>{r.get("NbJours","1")} jours</b><br>
                📞 <a href="tel:{tel_b}" class="contact-link">{tel_b}</a><br>
                <a href="https://wa.me/{tel_c}" target="_blank" class="wa-btn">💬 WHATSAPP</a><br>
                ✉️ <a href="mailto:{r.get('Email','')}" class="contact-link">{r.get('Email','')}</a><br>
                <span style="color:{col_s}; font-weight:bold;">{st_txt}</span>
            </div>''', unsafe_allow_html=True)
            col_e1, col_e2 = st.columns([1, 4])
            if col_e1.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if col_e2.checkbox("Confirmer la suppression", key=f"del_chk_{i}"):
                if st.button(f"🗑️ Supprimer {r.get('Nom')}", key=f"del_btn_{i}"):
                    df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING DÉTAILLÉ</div>', unsafe_allow_html=True)
    y_c, m_c = st.columns(2)
    p_y = y_c.selectbox("Année", [2025, 2026], index=1)
    p_m = m_c.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, details = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            d_s = parse_d(r.get('DateNav',''))
            if d_s.year == p_y and d_s.month == p_m:
                cl = "day-ok" if "OK" in str(r.get('Statut','')).upper() or "🟢" in str(r.get('Statut','')) else "day-wait"
                details.append(f"📌 **{r.get('DateNav')}** : {r.get('Prénom')} {r.get('Nom')} ({r.get('NbJours')}j)")
                for j in range(int(float(r.get('NbJours', 1)))):
                    tg = d_s + timedelta(days=j)
                    if tg.month == p_m: occu[tg.day] = (i, r, cl)
    cal = calendar.monthcalendar(p_y, p_m)
    html = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        html += '<tr>'
        for d in wk:
            bg = f'class="{occu[d][2]}"' if d in occu else ''
            html += f'<td {bg}>{d if d != 0 else ""}</td>'
        html += '</tr>'
    st.markdown(html + '</table>', unsafe_allow_html=True)
    if details: st.info("\n".join(details))

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATISTIQUES MENSUELLES</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026], index=1)
    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)
    
    stats = []
    for m in range(1, 13):
        ca = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == m) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == m)]['Montant'].apply(to_f))
        stats.append({"Mois": calendar.month_name[m], "CA": fmt_p(ca), "Frais": fmt_p(fr), "Net": fmt_p(ca-fr)})
    st.table(pd.DataFrame(stats))

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
    if st.button("➕ AJOUTER UN FRAIS", use_container_width=True): st.session_state.edit_f_idx = "NEW"; st.rerun()
    
    if st.session_state.edit_f_idx is not None:
        with st.form("f_form"):
            f_d = st.text_input("Date (JJ/MM/AAAA)", datetime.now().strftime("%d/%m/%Y"))
            f_m = st.text_input("Montant (€)")
            f_n = st.text_area("Description / Note")
            if st.form_submit_button("VALIDER"):
                new_f = pd.DataFrame([{"Date":f_d, "Montant":f_m, "Note":f_n}])
                df_f = pd.concat([df_f, new_f], ignore_index=True)
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
    
    if not df_f.empty:
        for i, r in df_f.sort_index(ascending=False).iterrows():
            st.markdown(f'''<div class="frais-card"><b>{r.get("Date")} — {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>''', unsafe_allow_html=True)
            if st.checkbox("Supprimer ce frais", key=f"f_chk_{i}"):
                if st.button("Confirmer", key=f"f_del_{i}"):
                    df_f = df_f.drop(i); sauvegarder_data(df_f, "frais.json"); st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 MÉMOS & NOTES</div>', unsafe_allow_html=True)
    if st.button("➕ NOUVELLE NOTE", use_container_width=True): st.session_state.edit_n_idx = "NEW"; st.rerun()
    
    if st.session_state.edit_n_idx is not None:
        with st.form("n_form"):
            n_t, n_c = st.text_input("Titre"), st.text_area("Contenu", height=150)
            if st.form_submit_button("SAUVEGARDER"):
                new_n = pd.DataFrame([{"Titre": n_t, "Contenu": n_c, "Date": datetime.now().strftime("%d/%m/%Y")}])
                df_n = pd.concat([df_n, new_n], ignore_index=True)
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx = None; st.rerun()

    if not df_n.empty:
        for i, r in df_n.iterrows():
            st.markdown(f'<div class="note-card"><b>{r.get("Titre")}</b> ({r.get("Date")})<br>{r.get("Contenu")}</div>', unsafe_allow_html=True)
            if st.checkbox("Supprimer la note", key=f"n_chk_{i}"):
                if st.button("Confirmer", key=f"n_del_{i}"):
                    df_n = df_n.drop(i); sauvegarder_data(df_n, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">✍️ ÉDITION NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    with st.form("f_edit"):
        f_st = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=0)
        f_pre, f_nom = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom",""))
        f_tel, f_em = st.text_input("Téléphone", init.get("Téléphone","")), st.text_input("Email", init.get("Email",""))
        f_dat, f_nbj, f_pri = st.text_input("Date (JJ/MM/AAAA)", init.get("DateNav","")), st.text_input("Nb Jours", init.get("NbJours","1")), st.text_input("Prix (€)", init.get("PrixJour","0"))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":f_pre, "Nom":f_nom, "Téléphone":f_tel, "Email":f_em, "DateNav":f_dat, "NbJours":f_nbj, "PrixJour":f_pri, "Statut":f_st}
            if idx == "NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k, v in row.items(): df.at[idx, k] = v
            sauvegarder_data(df, "contacts.json"); st.session_state.page = "LISTE"; st.rerun()
    if st.button("Retour"): st.session_state.page = "LISTE"; st.rerun()






































































































































































































