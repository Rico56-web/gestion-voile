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

# Initialisation des états de navigation et d'édition
for k, v in {"page":"LISTE", "view_mode":"FUTURES", "edit_idx":None, "edit_s_idx":None, "edit_f_idx":None, "edit_n_idx":None}.items():
    if k not in st.session_state: st.session_state[k] = v

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    .wa-btn-discret { color: #555 !important; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; text-decoration: none !important; font-size: 0.75rem; display: inline-block; margin-top: 8px; background: #fdfdfd; }
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
    if file == "secu.json": return pd.DataFrame([{"Item": "Vannes de coque"}, {"Item": "Niveaux Moteur"}, {"Item": "Météo OK"}])
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
df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER</div>', unsafe_allow_html=True)
m_cols = st.columns(6)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

# --- PAGE LISTE ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        
        for i, r in data.sort_values('dt').iterrows():
            soc = str(r.get('Société','')).strip().upper()
            statut = str(r.get('Statut','🟡 Attente'))
            # --- AJOUT DU NOMBRE DE JOURS ---
            nb_j = str(r.get('NbJours','1'))
            
            badge_color = "#2ecc71" if "🟢" in statut or "OK" in statut.upper() else ("#e74c3c" if "🔴" in statut else "#f1c40f")
            border_color = "#3498db" if soc == "CMN" else "#ccc"
            tel = "".join(filter(str.isdigit, str(r.get('Téléphone',''))))
            
            st.markdown(f"""
                <div class="client-card" style="border-left: 10px solid {border_color};">
                    <div class="status-badge" style="color:{badge_color}; border-color:{badge_color}; background:{badge_color}15;">{statut}</div>
                    <b style="font-size:1.1rem; color:#1a2a6c;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                    🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} <b>({nb_j}j)</b><br>
                    📧 <a href="mailto:{r.get('Email','')}">{r.get('Email','')}</a><br>
                    📞 <a href="tel:{tel}">{r.get('Téléphone','')}</a><br>
                    <a href="https://wa.me/{tel}" target="_blank" class="wa-btn-discret">💬 WhatsApp</a>
                </div>
            """, unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            if ce.button("✏️", key=f"ed_l_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            if cd.checkbox("🗑️", key=f"del_l_{i}"):
                if st.button("Confirmer", key=f"conf_l_{i}"): df.drop(i).pipe(sauvegarder_data, "contacts.json"); st.rerun()
                    
# --- PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    y_col, m_col = st.columns(2)
    p_y, p_m = y_col.selectbox("An", [2025, 2026, 2027], index=1), m_col.selectbox("Mois", range(1, 13), index=datetime.now().month-1)
    occu, details_list = {}, []
    if not df.empty:
        for i, r in df.iterrows():
            if "🔴" not in str(r.get('Statut','')):
                d_s = parse_d(r.get('DateNav',''))
                nb_j_val = int(to_f(r.get('NbJours', 1))) # On récupère le nombre de jours ici
                for j in range(nb_j_val):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc_u = str(r.get('Société','')).strip().upper()
                        occu[curr.day] = "day-cmn" if soc_u == "CMN" else ("day-ok" if "OK" in str(r.get('Statut','')) else "day-wait")
                        # Ajout du (Xj) dans la liste sous le calendrier
                        if j == 0: 
                            details_list.append({"day": curr.day, "text": f"⚓ **{curr.day}**: {r.get('Nom')} ({soc_u}) **({nb_j_val}j)**"})
    
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

# --- PAGE STATS ---
elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    
    # Sélection de l'année
    annee_actuelle = 2026
    s_y = st.selectbox("Année", [annee_actuelle - 1, annee_actuelle, annee_actuelle + 1], index=1)
    obj = st.number_input("Cible annuelle (€)", value=15000)

    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)

    ca_total_ok = sum(df[(df['dt'].dt.year == s_y) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    st.write(f"📈 **Réalisé (OK) : {int(ca_total_ok)} / {int(obj)}**")
    st.progress(min(ca_total_ok/obj, 1.0))
    
    st.markdown("---")
    
    # Préparation des données
    res, t_rev, t_fra, t_net, t_pre = [], 0, 0, 0, 0
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f))
        prev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢|🟡|Attente", na=False))]['PrixJour'].apply(to_f))
        net = rev - fr
        t_rev += rev; t_fra += fr; t_net += net; t_pre += prev
        res.append({"M": i, "Rev": int(rev), "Frais": int(fr), "Net": int(net), "Prév": int(prev)})

    df_stats = pd.DataFrame(res)
    total_row = pd.DataFrame([{"M": "TOT", "Rev": int(t_rev), "Frais": int(t_fra), "Net": int(t_net), "Prév": int(t_pre)}])
    full_stats = pd.concat([df_stats, total_row], ignore_index=True).set_index('M')

# --- APPLICATION DES COULEURS (AVEC EN-TÊTE BLEU) ---
    def style_stats(styler):
        # 1. Style de l'en-tête (Ligne des légendes)
        styler.set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#d6eaf8'), ('color', '#1a2a6c'), ('font-weight', 'bold')]}
        ])
        # 2. Couleurs de texte par colonne
        styler.set_properties(subset=['Rev'], **{'color': '#27ae60', 'font-weight': 'bold'}) # Vert
        styler.set_properties(subset=['Frais'], **{'color': '#e74c3c'}) # Rouge
        styler.set_properties(subset=['Net'], **{'background-color': '#ebf5fb', 'font-weight': 'bold'}) # Bleu très clair pour les données
        styler.set_properties(subset=['Prév'], **{'color': '#f39c12'}) # Orange
        return styler

    # Affichage du tableau stylisé
    st.table(full_stats.style.pipe(style_stats))
    st.table(full_stats.style.pipe(style_stats))

    st.markdown("---")
    st.subheader("📄 Facture CMN")
    f_m = st.selectbox("Mois Facture", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    df_c = df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == f_m) & (df['Société'].str.upper() == "CMN") & (df['Statut'].str.contains("OK|🟢", na=False))]
    if not df_c.empty:
        corps = f"Prestations {calendar.month_name[f_m]} {s_y} :\n" + "\n".join([f"- Le {r['DateNav']} : {fmt_p(r['PrixJour'])}" for _, r in df_c.iterrows()])
        st.text_area("Aperçu", corps, height=100)
        st.markdown(f'<a href="mailto:tresorier@cmn-asso.fr?subject=Facture&body={urllib.parse.quote(corps)}" style="background-color:#1a2a6c;color:white;padding:12px;display:block;text-align:center;text-decoration:none;border-radius:8px;">📧 ENVOYER AU TRÉSORIER</a>', unsafe_allow_html=True)


# --- PAGE SÉCU ---
elif st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛟 GESTION SÉCURITÉ</div>', unsafe_allow_html=True)
    if st.session_state.edit_s_idx is not None:
        idx = st.session_state.edit_s_idx
        val = df_s.loc[idx, "Item"] if idx != "NEW" else ""
        with st.form("edit_s"):
            new_v = st.text_input("Point :", val)
            if st.form_submit_button("✅ OK"):
                if idx == "NEW": df_s = pd.concat([df_s, pd.DataFrame([{"Item": new_v}])], ignore_index=True)
                else: df_s.at[idx, "Item"] = new_v
                sauvegarder_data(df_s, "secu.json"); st.session_state.edit_s_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_s_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER UN POINT", on_click=lambda: st.session_state.update({"edit_s_idx":"NEW"}), use_container_width=True)
        for i, r in df_s.iterrows():
            c1, c2, c3 = st.columns([6, 1, 1])
            c1.checkbox(r["Item"], key=f"s_{i}")
            if c2.button("✏️", key=f"es_{i}"): st.session_state.edit_s_idx = i; st.rerun()
            if c3.button("🗑️", key=f"ds_{i}"): df_s.drop(i).pipe(sauvegarder_data, "secu.json"); st.rerun()

# --- PAGE FRAIS (Maintenance) ---
elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">🔧 MAINTENANCE</div>', unsafe_allow_html=True)
    if st.session_state.edit_f_idx is not None:
        idx = st.session_state.edit_f_idx
        init = df_f.loc[idx].to_dict() if idx != "NEW" else {"Date": datetime.now().strftime("%d/%m/%Y"), "Montant": "0", "Note": ""}
        with st.form("f_f"):
            d, m, n = st.text_input("Date", init.get("Date")), st.text_input("Montant", str(init.get("Montant"))), st.text_area("Note", init.get("Note"))
            if st.form_submit_button("✅ OK"):
                row = {"Date": d, "Montant": m, "Note": n}
                if idx == "NEW": df_f = pd.concat([df_f, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_f.at[idx,k]=v
                sauvegarder_data(df_f, "frais.json"); st.session_state.edit_f_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_f_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER FRAIS", on_click=lambda: st.session_state.update({"edit_f_idx":"NEW"}), use_container_width=True)
        for i in reversed(df_f.index):
            r = df_f.loc[i]
            st.markdown(f'<div class="client-card"><b>{r.get("Date")} : {fmt_p(r.get("Montant"))}</b><br>{r.get("Note")}</div>', unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            if ce.button("✏️", key=f"fe_{i}"): st.session_state.edit_f_idx = i; st.rerun()
            if cd.checkbox("🗑️", key=f"fd_{i}"):
                if st.button("Confirmer", key=f"fc_{i}"): df_f.drop(i).pipe(sauvegarder_data, "frais.json"); st.rerun()

# --- PAGE NOTES ---
elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 NOTES</div>', unsafe_allow_html=True)
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if idx != "NEW" else {"Titre": "", "Contenu": ""}
        with st.form("f_n"):
            t, c = st.text_input("Titre", init.get("Titre")), st.text_area("Contenu", init.get("Contenu"), height=200)
            if st.form_submit_button("✅ OK"):
                row = {"Titre":t, "Contenu":c, "Date":datetime.now().strftime("%d/%m/%Y")}
                if idx=="NEW": df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): df_n.at[idx,k]=v
                sauvegarder_data(df_n, "notes.json"); st.session_state.edit_n_idx=None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_n_idx = None; st.rerun()
    else:
        st.button("➕ AJOUTER UNE NOTE", on_click=lambda: st.session_state.update({"edit_n_idx":"NEW"}), use_container_width=True)
        for i in reversed(df_n.index):
            r = df_n.loc[i]
            # Affichage en mode "Carte large" avec texte complet
            st.markdown(f"""
                <div class="client-card" style="padding: 20px; border-left: 5px solid #1a2a6c;">
                    <b style="font-size:1.2rem; color:#1a2a6c;">{r.get("Titre")}</b> 
                    <span style="font-size:0.8rem; color:grey; float:right;">{r.get("Date")}</span>
                    <hr style="margin: 10px 0; border: 0.5px solid #eee;">
                    <div style="white-space: pre-wrap; font-size:1rem; line-height:1.4;">{r.get("Contenu")}</div>
                </div>
            """, unsafe_allow_html=True)
            ce, cd = st.columns([1, 2])
            if ce.button("✏️", key=f"ne_{i}"): st.session_state.edit_n_idx = i; st.rerun()
            if cd.checkbox("🗑️", key=f"nd_{i}"):
                if st.button("Confirmer suppression", key=f"nc_{i}"): df_n.drop(i).pipe(sauvegarder_data, "notes.json"); st.rerun()

# --- PAGE FORMULAIRE (Contact/Nav) ---
elif st.session_state.page == "FORM":
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if idx != "NEW" else {}
    liste_statuts = ["🟢 OK", "🟡 Attente", "🔴 Annulé"]
    val_actuelle = init.get("Statut", "🟡 Attente")
    try: idx_dep = liste_statuts.index(val_actuelle)
    except: idx_dep = 1
    with st.form("f_form"):
        st_v = st.selectbox("Statut", liste_statuts, index=idx_dep)
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































































































































































































































































