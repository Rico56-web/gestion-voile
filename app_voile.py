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
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "cible_annuelle" not in st.session_state: st.session_state.cible_annuelle = 15000.0
for k in ["edit_idx", "edit_s_idx", "edit_f_idx", "edit_n_idx"]:
    if k not in st.session_state: st.session_state[k] = None

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
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

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("📖 LOG","LOGBOOK"), ("📄 FACT","FACTURE"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, key=f"btn_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # --- BARRE DE RECHERCHE ---
    search_term = st.text_input("🔍 Rechercher par Nom ou Prénom", "").strip().lower()
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Filtre Passées / Futures
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        
        # --- LOGIQUE DE RECHERCHE ---
        if search_term:
            data = data[
                (data['Nom'].str.lower().str.contains(search_term, na=False)) | 
                (data['Prénom'].str.lower().str.contains(search_term, na=False))
            ]
        
        if data.empty:
            st.info("Aucun résultat pour cette recherche.")
        else:
            for i, r in data.sort_values('dt', ascending=(st.session_state.view_mode=="FUTURES")).iterrows():
                soc = str(r.get('Société','')).upper()
                statut = str(r.get('Statut','🟡 Attente'))
                tel = str(r.get('Téléphone', r.get('Tel', ''))).strip()
                mail = str(r.get('Mail', '')).strip()
                tel_link = tel.replace(" ", "").replace(".", "").replace("-", "")
                if tel_link.startswith("0"): tel_link = "33" + tel_link[1:]
                badge_color = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")

                st.markdown(f"""<div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                    <div class="status-badge" style="color:{badge_color}; border-color:{badge_color}; background:{badge_color}15;">{statut}</div>
                    <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                    🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} ({r.get('NbJours','1')}j)<br>
                    📞 {tel} | ✉️ {mail}<br><br>
                    <a href="tel:{tel_link}" class="btn-contact" style="background:#3498db;">📞 Appel</a>
                    <a href="https://wa.me/{tel_link}" target="_blank" class="btn-contact" style="background:#25d366;">💬 WhatsApp</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Mail</a>
                </div>""", unsafe_allow_html=True)
                ce, cd = st.columns([1, 4])
                if ce.button("✏️ Modifier", key=f"ed_l_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
                if cd.checkbox("🗑️", key=f"del_l_{i}"):
                    if st.button("Confirmer suppression", key=f"conf_l_{i}"): df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING & DÉTAILS</div>', unsafe_allow_html=True)
    
    y_col, m_col = st.columns(2)
    p_y = y_col.selectbox("An", [2025, 2026, 2027], index=1)
    p_m = m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    occu = {}
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        # On filtre les données du mois sélectionné pour la liste du dessous
        df_mois = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
        
        for _, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s, nb_j = r['dt'], int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc = str(r.get('Société','')).upper()
                        occu[curr.day] = ("day-cmn" if soc == "CMN" else "day-ok", f"{r.get('Prénom','')} {r.get('Nom','')[:1]}.")

    # --- AFFICHAGE DU CALENDRIER ---
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style, txt = (occu[d][0], f'<br><span style="font-size:0.7rem;">{occu[d][1]}</span>') if d in occu else ('', '')
            h += f'<td class="{style}">{d if d != 0 else ""}{txt}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

    # --- LISTE DES NOMS DU MOIS (SOUS LE PLANNING) ---
    st.markdown("---")
    st.subheader(f"👥 Détails de {calendar.month_name[p_m]}")
    
    if not df.empty and not df_mois.empty:
        for i, r in df_mois.iterrows():
            statut = str(r.get('Statut','🟡'))
            soc = str(r.get('Société','')).upper()
            tel = str(r.get('Téléphone', r.get('Tel', ''))).strip()
            
            # Petite ligne compacte pour le planning
            st.markdown(f"""
            <div style="background:white; padding:10px; border-radius:5px; border-left:5px solid {"#3498db" if soc=="CMN" else "#2ecc71"}; margin-bottom:5px; border:1px solid #eee;">
                <b>{r.get('DateNav')}</b> : {r.get('Prénom','')} {r.get('Nom','').upper()} 
                ({r.get('NbJours','1')}j) - <i>{soc}</i> | 📞 {tel}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Aucune navigation prévue ce mois-ci.")

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026, 2027], index=1)
    obj = st.number_input("Cible annuelle (€)", value=float(st.session_state.cible_annuelle), step=1000.0)
    st.session_state.cible_annuelle = obj
    if not df.empty: df['dt'] = df['DateNav'].apply(parse_d)
    if not df_f.empty: df_f['dt'] = df_f['Date'].apply(parse_d)
    res, t_rev, t_fra, t_net, t_pre = [], 0, 0, 0, 0
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f)) if not df.empty else 0
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f)) if not df_f.empty else 0
        prev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢|🟡", na=False))]['PrixJour'].apply(to_f)) if not df.empty else 0
        t_rev += rev; t_fra += fr; t_net += (rev-fr); t_pre += prev
        res.append({"M": i, "Rev": int(rev), "Frais": int(fr), "Net": int(rev-fr), "Prév": int(prev)})
    st.write(f"📈 **Réalisé (OK) : {int(t_rev)} / {int(obj)}**")
    st.progress(min(t_rev/obj, 1.0) if obj > 0 else 0.0)
    st.table(pd.DataFrame(res).set_index('M'))
    st.markdown(f'<div style="background:#1a2a6c;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">TOTAL NET : {fmt_p(t_net)}</div>', unsafe_allow_html=True)

elif st.session_state.page in ["SECU", "FRAIS", "NOTES"]:
    st.markdown(f'<div class="page-title">{st.session_state.page}</div>', unsafe_allow_html=True)
    c_df = df_s if st.session_state.page == "SECU" else (df_f if st.session_state.page == "FRAIS" else df_n)
    c_idx = st.session_state.edit_s_idx if st.session_state.page == "SECU" else (st.session_state.edit_f_idx if st.session_state.page == "FRAIS" else st.session_state.edit_n_idx)
    c_file = "secu.json" if st.session_state.page == "SECU" else ("frais.json" if st.session_state.page == "FRAIS" else "notes.json")
    
    if c_idx is not None:
        init = c_df.loc[c_idx].to_dict() if (c_idx != "NEW" and not c_df.empty) else {}
        with st.form("edit_c"):
            if st.session_state.page == "SECU": 
                row = {"Item": st.text_input("Point", init.get("Item", ""))}
            elif st.session_state.page == "FRAIS": 
                row = {"Date": st.text_input("Date", init.get("Date", "")), "Montant": st.text_input("Montant", init.get("Montant", "0")), "Note": st.text_area("Note", init.get("Note", ""))}
            else: 
                row = {"Titre": st.text_input("Titre", init.get("Titre", "")), "Contenu": st.text_area("Contenu", init.get("Contenu", "")), "Date": datetime.now().strftime("%d/%m/%Y")}
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                if c_idx == "NEW": 
                    c_df = pd.concat([c_df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): c_df.at[c_idx, k] = v
                sauvegarder_data(c_df, c_file)
                st.session_state.update({"edit_s_idx":None, "edit_f_idx":None, "edit_n_idx":None})
                st.rerun()
    else:
        st.button("➕ AJOUTER", on_click=lambda: st.session_state.update({f"edit_{st.session_state.page[0].lower()}_idx":"NEW"}), use_container_width=True)
        for i, r in c_df.iterrows():
            st.markdown(f'<div class="client-card">{r.values[0]}</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("✏️ Modifier", key=f"ed_{st.session_state.page}_{i}"): 
                st.session_state.update({f"edit_{st.session_state.page[0].lower()}_idx":i})
                st.rerun()
            if c2.button("🗑️", key=f"del_{st.session_state.page}_{i}"): 
                c_df = c_df.drop(i)
                sauvegarder_data(c_df, c_file)
                st.rerun()

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if (idx != "NEW" and not df.empty) else {}
    
    with st.form("f_form"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=1)
        c1, c2 = st.columns(2)
        p, n = c1.text_input("Prénom", init.get("Prénom","")), c2.text_input("Nom", init.get("Nom",""))
        s = st.text_input("Société", init.get("Société",""))
        c3, c4 = st.columns(2)
        d, j = c3.text_input("Date (JJ/MM/AAAA)", init.get("DateNav","")), c4.text_input("Jours", str(init.get("NbJours","1")))
        t = st.text_input("Tél", init.get("Téléphone", init.get("Tel", "")))
        ml = st.text_input("Mail", init.get("Mail", ""))
        pr = st.text_input("Prix", str(init.get("PrixJour","0")))
        
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Mail":ml, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": 
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json")
            st.session_state.page="LISTE"
            st.rerun()
            
    if st.button("Annuler"):
        st.session_state.page = "LISTE"
        st.rerun()







































































































































































































































































































