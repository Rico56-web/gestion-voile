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

# Initialisation des états
states = {
    "page": "LISTE", "view_mode": "FUTURES", "cible_annuelle": 15000.0,
    "edit_idx": None, "edit_s_idx": None, "edit_f_idx": None, "edit_n_idx": None
}
for k, v in states.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
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

df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")

# --- 3. MENU (8 ONGLETS) ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [
    ("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), 
    ("📖 LOG","LOGBOOK"), ("📄 FACT","FACTURE"), ("🛟 SÉCU","SECU"), 
    ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")
]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # --- BARRE DE RECHERCHE ---
    search_query = st.text_input("🔍 Rechercher un prénom ou un nom...", "").lower()
    
    # --- BOUTONS INVERSÉS ---
    c1, c2 = st.columns(2)
    # Passées à gauche
    if c1.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): 
        st.session_state.view_mode="PASSÉES"; st.rerun()
    # Archives (Futures) à droite
    if c2.button("🚀 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): 
        st.session_state.view_mode="FUTURES"; st.rerun()
    
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Logique de filtrage temporel
        data = df[df['dt'] < today] if st.session_state.view_mode=="PASSÉES" else df[df['dt'] >= today]
        
        # Filtre de recherche
        if search_query:
            data = data[
                data['Prénom'].str.lower().str.contains(search_query, na=False) | 
                data['Nom'].str.lower().str.contains(search_query, na=False)
            ]
        
        if data.empty:
            st.info("Aucune navigation trouvée.")
        else:
            # Tri : Chronologique pour les archives, Inverse pour le passé
            sort_order = True if st.session_state.view_mode=="FUTURES" else False
            for i, r in data.sort_values('dt', ascending=sort_order).iterrows():
                soc = str(r.get('Société','')).upper()
                statut = str(r.get('Statut','🟡 Attente'))
                badge_color = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")
                
                st.markdown(f"""<div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                    <div class="status-badge" style="color:{badge_color}; border-color:{badge_color}; background:{badge_color}15;">{statut}</div>
                    <b>{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                    🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} <b>({r.get('NbJours','1')}j)</b><br>
                    📞 <a href="tel:{r.get('Téléphone','')}">{r.get('Téléphone','')}</a>
                </div>""", unsafe_allow_html=True)
                ce, cd = st.columns([1, 2])
                if ce.button("✏️", key=f"ed_l_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
                if cd.checkbox("🗑️", key=f"del_l_{i}"):
                    if st.button("Confirmer", key=f"conf_l_{i}"): 
                        df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

  

elif st.session_state.page == "LOGBOOK":
    st.markdown('<div class="page-title">📖 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    with st.form("f_log_complet"):
        st.subheader("🚩 DÉPART")
        c1, c2 = st.columns(2)
        d_lieu = c1.text_input("Port / Mouillage (Départ)", key="d_l")
        d_met = c2.selectbox("Météo (Départ)", ["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"], key="d_m")
        c3, c4 = st.columns(2)
        d_h = c3.number_input("Heures Moteur (Départ)", step=0.1, key="d_h")
        d_mi = c4.number_input("Loch / Milles (Départ)", step=0.1, key="d_mi")
        
        st.markdown("--- ⛵ **EN COURS** ---")
        obs = st.text_area("Observations (Virements, dauphins, technique...)", height=100)
        
        st.markdown("--- 🏁 **ARRIVÉE** ---")
        c5, c6 = st.columns(2)
        a_lieu = c5.text_input("Port / Mouillage (Arrivée)", key="a_l")
        a_met = c6.selectbox("Météo (Arrivée)", ["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"], key="a_m")
        c7, c8 = st.columns(2)
        a_h = c7.number_input("Heures Moteur (Arrivée)", step=0.1, key="a_h")
        a_mi = c8.number_input("Loch / Milles (Arrivée)", step=0.1, key="a_mi")

        if st.form_submit_button("⚓ ENREGISTRER L'ÉTAPE", use_container_width=True):
            st.success(f"Log enregistré : {a_mi - d_mi:.1f} milles parcourus.")

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y = y_col.selectbox("An", [2025, 2026, 2027], index=1)
    p_m = m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, details_list = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s, nb_j_val = parse_d(r.get('DateNav','')), int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j_val):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc_u = str(r.get('Société','')).strip().upper()
                        occu[curr.day] = "day-cmn" if soc_u == "CMN" else ("day-ok" if "OK" in str(r.get('Statut','')) else "day-wait")
                        if j == 0: details_list.append({"day": curr.day, "text": f"⚓ **{curr.day}**: {r.get('Nom')} ({soc_u}) **({nb_j_val}j)**"})
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
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
    s_y = st.selectbox("Année", [2025, 2026, 2027], index=1)
    obj = st.number_input("Cible annuelle (€)", value=float(st.session_state.cible_annuelle), step=1000.0, key="cible_input")
    st.session_state.cible_annuelle = obj
    
    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)
    
    ca_total_ok = sum(df[(df['dt'].dt.year == s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **Réalisé (OK) : {int(ca_total_ok)} / {int(obj)}**")
    st.progress(min(ca_total_ok/obj, 1.0) if obj > 0 else 0.0)
    st.markdown("---")
    
    res, t_rev, t_fra, t_net, t_pre = [], 0, 0, 0, 0
    for i in range(1, 13):
        m_df = df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i)]
        m_f = df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]
        rev = sum(m_df[m_df['Statut'].str.contains("OK|🟢", na=False)]['PrixJour'].apply(to_f))
        fr = sum(m_f['Montant'].apply(to_f))
        prev = sum(m_df[m_df['Statut'].str.contains("OK|🟢|🟡|Attente", na=False)]['PrixJour'].apply(to_f))
        net = rev - fr
        t_rev += rev; t_fra += fr; t_net += net; t_pre += prev
        res.append({"M": i, "Rev": int(rev), "Frais": int(fr), "Net": int(net), "Prév": int(prev)})
    
    full_stats = pd.concat([pd.DataFrame(res), pd.DataFrame([{"M":"TOT","Rev":int(t_rev),"Frais":int(t_fra),"Net":int(t_net),"Prév":int(t_pre)}])], ignore_index=True).set_index('M')
    
    def style_stats(styler):
        styler.set_table_styles([{'selector': 'th', 'props': [('background-color', '#d6eaf8'), ('color', '#1a2a6c'), ('font-weight', 'bold')]}])
        styler.set_properties(subset=['Rev'], **{'color': '#27ae60', 'font-weight': 'bold'})
        styler.set_properties(subset=['Frais'], **{'color': '#e74c3c'})
        styler.set_properties(subset=['Net'], **{'background-color': '#ebf5fb', 'font-weight': 'bold'})
        styler.set_properties(subset=['Prév'], **{'color': '#f39c12'})
        return styler
    st.table(full_stats.style.pipe(style_stats))

elif st.session_state.page == "FACTURE":
    st.markdown('<div class="page-title">📄 FACTURATION CMN</div>', unsafe_allow_html=True)
    
    # Initialisation de sécurité
    df_c = pd.DataFrame() 
    
    c1, c2 = st.columns(2)
    f_y = c1.selectbox("Année", [2025, 2026, 2027], index=1, key="f_y")
    f_m = c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x], key="f_m")
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask_cmn = (df['dt'].dt.year == f_y) & (df['dt'].dt.month == f_m) & \
                   (df['Société'].str.upper() == "CMN") & (df['Statut'].str.contains("OK|🟢", na=False))
        df_c = df[mask_cmn]
    
    if not df_c.empty:
        total = sum(df_c['PrixJour'].apply(to_f))
        
        # --- CORPS DU MAIL ---
        corps = f"Bonjour Jean-Michel,\n\nCi-après le détail de la facturation des sorties CMN de ce mois ({calendar.month_name[f_m]} {f_y}) :\n\n"
        for _, r in df_c.iterrows():
            corps += f"- Le {r['DateNav']} : {fmt_p(r['PrixJour'])}\n"
        corps += f"\nTOTAL À RÉGLER : {fmt_p(total)}\n\nBonne continuation.\n\nEric CLAVREUL"
        
        txt = st.text_area("Aperçu du message", corps, height=250)
        
        # --- PARAMÈTRES ---
        dest = "tresorier@cmn-asso.fr"
        cc = "eric.clavreul@gmail.com"
        sujet = f"Facturation Skipper - {calendar.month_name[f_m]} {f_y}"
        
        # 1. LIEN CLASSIQUE (Idéal iPhone / iPad)
        params_mailto = urllib.parse.urlencode({'cc': cc, 'subject': sujet, 'body': txt})
        link_mailto = f"mailto:{dest}?{params_mailto}"
        
        st.markdown(f'''
            <a href="{link_mailto}" style="background-color:#1a2a6c; color:white; padding:15px; 
            display:block; text-align:center; text-decoration:none; border-radius:10px; font-weight:bold; margin-bottom:10px;">
            📱 ENVOYER VIA MON SMARTPHONE
            </a>
        ''', unsafe_allow_html=True)

        # 2. LIEN GMAIL WEB (Idéal PC / Navigateur)
        # On utilise une URL spécifique à Gmail qui force l'ouverture en ligne
        gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={dest}&cc={cc}&sujet={urllib.parse.quote(sujet)}&body={urllib.parse.quote(txt)}"
        
        st.markdown(f'''
            <a href="{gmail_url}" target="_blank" style="background-color:#db4437; color:white; padding:15px; 
            display:block; text-align:center; text-decoration:none; border-radius:10px; font-weight:bold;">
            💻 ENVOYER VIA GMAIL (ORDINATEUR)
            </a>
        ''', unsafe_allow_html=True)
        
    else: 
        st.info(f"Aucune prestation CMN validée pour {calendar.month_name[f_m]} {f_y}.")

elif st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 SÉCURITÉ</div>', unsafe_allow_html=True)
    if st.session_state.edit_s_idx is not None:
        idx = st.session_state.edit_s_idx
        v_init = df_s.loc[idx, "Item"] if (idx != "NEW" and not df_s.empty) else ""
        with st.form("f_s"):
            new_v = st.text_input("Point :", v_init)
            if st.form_submit_button("✅"):
                if idx == "NEW": df_s = pd.concat([df_s, pd.DataFrame([{"Item": new_v}])], ignore_index=True)
                else: df_s.at[idx, "Item"] = new_v
                sauvegarder_data(df_s, "secu.json"); st.session_state.edit_s_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_s_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER", on_click=lambda: st.session_state.update({"edit_s_idx":"NEW"}), use_container_width=True)
        if not df_s.empty:
            for i, r in df_s.iterrows():
                c1, c2, c3 = st.columns([6, 1, 1])
                c1.checkbox(r["Item"], key=f"s_{i}")
                if c2.button("✏️", key=f"es_{i}"): st.session_state.edit_s_idx = i; st.rerun()
                if c3.button("🗑️", key=f"ds_{i}"): df_s = df_s.drop(i); sauvegarder_data(df_s, "secu.json"); st.rerun()

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if (idx != "NEW" and not df_f.empty) else {"Date": datetime.now().strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
        with st.form("f_f"):
            d, m, n = st.text_input("Date", init.get("Date")), st.text_input("Montant", str(init.get("Montant"))), st.text_area("Note", init.get("Note"))
            if st.form_submit_button("✅"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW": df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_f.at[idx,k]=v
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER", on_click=lambda: st.session_state.update({"edit_f_idx":"NEW"}), use_container_width=True)
        if not df_f.empty:
            for i in reversed(df_f.index):
                r = df_f.loc[i]
                st.markdown(f'<div class="client-card"><b>{r.get("Date")} : {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
                if st.button("🗑️", key=f"fd_{i}"): df_f = df_f.drop(i); sauvegarder_data(df_f, "frais.json"); st.rerun()

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        with st.form("f_n"):
            t = st.text_input("Titre", df_n.loc[idx, "Titre"] if (idx != "NEW" and not df_n.empty) else "")
            c = st.text_area("Contenu", df_n.loc[idx, "Contenu"] if (idx != "NEW" and not df_n.empty) else "", height=200)
            if st.form_submit_button("✅"):
                row = {"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
    else:
        st.button("➕ AJOUTER", on_click=lambda: st.session_state.update({"edit_n_idx":"NEW"}), use_container_width=True)
        if not df_n.empty:
            for i in reversed(df_n.index):
                r = df_n.loc[i]
                st.markdown(f'<div class="client-card" style="padding: 20px; border-left: 5px solid #1a2a6c;"><b>{r.get("Titre")}</b><br><small>{r.get("Date")}</small><hr><div style="white-space:pre-wrap;">{r.get("Contenu")}</div></div>', unsafe_allow_html=True)
                if st.button("🗑️", key=f"nd_{i}"): df_n = df_n.drop(i); sauvegarder_data(df_n, "notes.json"); st.rerun()

elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if (idx != "NEW" and not df.empty) else {}
    with st.form("f_form"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=1)
        p, n, s = st.text_input("Prénom", init.get("Prénom","")), st.text_input("Nom", init.get("Nom","")), st.text_input("Société", init.get("Société",""))
        d, j = st.text_input("Date", init.get("DateNav","")), st.text_input("Jours", str(init.get("NbJours","1")))
        t, em, pr = st.text_input("Tél", init.get("Téléphone","")), st.text_input("Email", init.get("Email","")), st.text_input("Prix", str(init.get("PrixJour","0")))
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Email":em, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json"); st.session_state.page="LISTE"; st.rerun()
    st.button("Annuler", on_click=lambda: st.session_state.update({"page":"LISTE"}))

















































































































































































































































































