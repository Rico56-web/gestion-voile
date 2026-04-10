import requests, base64, json, time, os, html, io
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import calendar

def preparer_log_safe(df):
    """Nettoie et sécurise les données du logbook pour éviter les plantages d'affichage."""
    if df.empty:
        # Retourne un DataFrame vide avec les colonnes minimales attendues
        return pd.DataFrame(columns=[
            'Date', 'PortDep', 'PortArr', 'MotDep', 'MotArr', 
            'TotalMot', 'MilDep', 'MilArr', 'TotalMil', 'Equipage'
        ])
    
    # Conversion forcée en numérique pour les calculs (évite les erreurs de type)
    cols_num = ['MotDep', 'MotArr', 'MilDep', 'MilArr', 'TotalMot', 'TotalMil']
    for col in cols_num:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    
    # S'assurer que les colonnes de texte existent pour l'affichage
    cols_texte = ['PortDep', 'PortArr', 'Equipage', 'Mouillage', 'Date']
    for col in cols_texte:
        if col not in df.columns:
            df[col] = ""
            
    return df
# =================================================================
# --- 1. CONFIGURATION & STYLE (IPHONE FIRST) ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# Date du jour en français
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
now = datetime.now()
date_bandeau = f"📅 {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"

st.markdown(f"""<style>
    .main-header {{ font-size: 1.8rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }}
    .date-header {{ text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }}
    button[data-testid="baseButton-primary"] {{ background-color: #ff4b4b !important; color: white !important; min-height: 45px; }}
    button[data-testid="baseButton-secondary"] {{ background-color: white !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; min-height: 45px; }}
    .calendar-table {{ width: 100%; border-collapse: collapse; text-align: center; }}
</style>""", unsafe_allow_html=True)

# =================================================================
# --- 2. FONCTIONS CŒUR (UNIFIÉES) ---
# =================================================================

def charger_data(file):
    """Charge les données depuis GitHub avec bypass de cache"""
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    """Sauvegarde sur GitHub avec formatage JSON propre"""
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
        requests.put(url, headers={"Authorization": f"token {token}"}, 
                     json={"message": f"Update {file}", "content": content, "sha": sha})
    except Exception as e: st.error(f"Erreur sauvegarde {file} : {e}")

def safe_val(val, default=0):
    """Extraction propre de nombres depuis du texte ou NaN"""
    try:
        if pd.isna(val) or str(val).strip() == "": return default
        clean = "".join(filter(lambda x: x.isdigit() or x == '.', str(val)))
        return float(clean) if clean else default
    except: return default

def clean_text(text):
    """Nettoyage pour éviter de casser le JSON"""
    if text is None or pd.isna(text): return ""
    return str(text).replace("\n", " ").replace('"', "'").strip()

# =================================================================
# --- 3. SESSION & SÉCURITÉ ---
# =================================================================

# Initialisation groupée pour éviter les répétitions
keys_to_init = {
    'authenticated': False, 'page': "CONTACTS", 'mode_saisie': False,
    'edit_idx': None, 'log_edit_idx': None, 'm_edit_idx': None,
    'confirm_del_idx': None, 'view_archive': False, 'curr_month_idx': now.month - 1,
    'curr_year': 2026, 'nav_key': 0
}
for key, val in keys_to_init.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if st.button("ACCÉDER", use_container_width=True):
        if pw == "Skipper2026":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect.")
    st.stop()

# =================================================================
# --- 4. BARRE LATÉRALE (SIDEBAR) ---
# =================================================================
with st.sidebar:
    st.title("🛡️ Sécurité")
    if st.expander("📥 Exporter les données"):
        for f in ['logbook.json', 'maintenance.json', 'contacts.json']:
            df_tmp = charger_data(f)
            if not df_tmp.empty:
                st.download_button(f"Sauver {f}", df_tmp.to_json(orient="records"), file_name=f, use_container_width=True)

# =================================================================
# --- 5. NAVIGATION ---
# =================================================================
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "ARCHIVES", "LOG"]
icones = {"CONTACTS": "👤", "PLANNING": "🗓️", "STATS": "📊", "MAINT": "🛠️", "FACTURES": "🧾", "ARCHIVES": "📂", "LOG": "📖"}

cols_nav = st.columns(len(menu))
for i, name in enumerate(menu):
    if cols_nav[i].button(icones[name], key=f"nav_{name}", use_container_width=True, 
                          type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()

# Chargement des données partagées
df_c = charger_data("contacts.json")

# Harmonisation automatique des paiements
if not df_c.empty and 'Paiement' in df_c.columns:
    df_c['Paiement'] = df_c['Paiement'].apply(lambda x: "Payé" if "pay" in str(x).lower() and "non" not in str(x).lower() else "Non payé")
# =================================================================
# --- 5. BLOC CONTACTS (V6 - COMPLET & SÉCURISÉ) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.title("👤 Gestion des Contacts")

    # --- INITIALISATION ---
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
    if 'confirm_del_idx_c' not in st.session_state: st.session_state.confirm_del_idx_c = None
    if 'confirm_arch_idx_c' not in st.session_state: st.session_state.confirm_arch_idx_c = None
    if 'vue_contact' not in st.session_state: st.session_state.vue_contact = "En cours"

    def clean_int(val):
        try:
            if val is None or str(val).strip() == "" or str(val).lower() == "nan": return 0
            return int(float(str(val).replace(',', '.').replace('€', '').strip()))
        except: return 0

    def format_tel_fr(tel):
        if tel is None: return ""
        digits = "".join(filter(str.isdigit, str(tel)))
        return f"{digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}" if len(digits) == 10 else str(tel)

    def formater_date_affichage(date_val):
        if pd.isna(date_val) or str(date_val).strip() in ["", "None", "nan"]: return "---"
        try:
            return datetime.strptime(str(date_val)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: return str(date_val)

    # --- NAVIGATION HAUT ---
    c1, c2, c3 = st.columns([1, 1, 1])
    if c1.button("👤 EN COURS", use_container_width=True, type="primary" if st.session_state.vue_contact == "En cours" else "secondary"):
        st.session_state.vue_contact = "En cours"; st.session_state.edit_idx = None; st.rerun()
    if c2.button("📂 ARCHIVES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Archives" else "secondary"):
        st.session_state.vue_contact = "Archives"; st.session_state.edit_idx = None; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        df_temp = charger_data('contacts.json')
        new_row = {
            "Prénom": "NOUVEAU", "Nom": "CONTACT", "Statut": "En attente", 
            "Paiement": "Non payé", "DateNav": datetime.now().strftime("%Y-%m-%d"), 
            "Société": "PERSO", "Prix": 0, "Acompte": 0, "Nbre de personnes": 1, "Nbre de jours": 1,
            "Téléphone": "", "Email": "", "Notes": ""
        }
        df_temp = pd.concat([pd.DataFrame([new_row]), df_temp], ignore_index=True)
        sauvegarder_data(df_temp, 'contacts.json')
        st.session_state.edit_idx = 0; st.rerun()

    st.markdown("---")
    df_c = charger_data('contacts.json')

    if not df_c.empty:
        # Filtre intelligent pour les archives
        mask_archives = (df_c['Statut'].str.lower().isin(["terminé", "refusé", "annulé"]))
        df_affichage = df_c[mask_archives].copy() if st.session_state.vue_contact == "Archives" else df_c[~mask_archives].copy()

        for idx, row in df_affichage.iterrows():
            statut_label = str(row.get('Statut', 'En attente')).strip()
            societe_label = str(row.get('Société', 'PERSO')).strip().upper()
            v_prix = clean_int(row.get('Prix', 0))
            v_acompte = clean_int(row.get('Acompte', 0))
            v_solde = v_prix - v_acompte

            bg_color, text_color = "#ffffff", "#333333"
            if societe_label == "CMN": bg_color, text_color = "#3498db", "#ffffff"
            elif statut_label.lower() == "ok": bg_color = "#d4edda"
            elif statut_label.lower() == "en attente": bg_color = "#fff9c4"
            elif statut_label.lower() in ["annulé", "terminé"]: bg_color = "#e2e3e5"

            # =========================================================
            # --- MODE ÉDITION ---
            # =========================================================
            if st.session_state.edit_idx == idx:
                with st.container():
                    st.markdown(f"### ✏️ Édition : {str(row.get('Nom',''))}")
                    
                    # --- Zone de confirmation SUPPRESSION ---
                    if st.session_state.confirm_del_idx_c == idx:
                        st.error(f"⚠️ SUPPRIMER DÉFINITIVEMENT {str(row.get('Nom',''))} ?")
                        cd1, cd2 = st.columns(2)
                        if cd1.button("✔️ OUI, SUPPRIMER", key=f"del_confirm_{idx}", use_container_width=True, type="primary"):
                            df_curr = charger_data('contacts.json'); df_curr = df_curr.drop(idx); sauvegarder_data(df_curr, 'contacts.json')
                            st.session_state.edit_idx = None; st.session_state.confirm_del_idx_c = None; st.rerun()
                        if cd2.button("❌ NON", key=f"del_cancel_{idx}", use_container_width=True): 
                            st.session_state.confirm_del_idx_c = None; st.rerun()

                    # --- Zone de confirmation ARCHIVAGE ---
                    if st.session_state.confirm_arch_idx_c == idx:
                        st.warning(f"📦 ARCHIVER {str(row.get('Nom',''))} ?")
                        ca1, ca2 = st.columns(2)
                        if ca1.button("✔️ OUI, ARCHIVER", key=f"arch_confirm_{idx}", use_container_width=True, type="primary"):
                            df_curr = charger_data('contacts.json'); df_curr.at[idx, 'Statut'] = "Annulé"
                            sauvegarder_data(df_curr, 'contacts.json'); st.session_state.edit_idx = None
                            st.session_state.confirm_arch_idx_c = None; st.rerun()
                        if ca2.button("❌ NON", key=f"arch_cancel_{idx}", use_container_width=True):
                            st.session_state.confirm_arch_idx_c = None; st.rerun()

                    with st.form(f"form_edit_{idx}"):
                        c1, c2 = st.columns(2)
                        e_pre = c1.text_input("Prénom", str(row.get('Prénom', '')))
                        e_nom = c2.text_input("Nom", str(row.get('Nom', '')))
                        
                        st.write("💰 **FINANCES**")
                        f1, f2, f3 = st.columns(3)
                        e_prix = f1.number_input("Prix Total (€)", value=v_prix, step=1)
                        e_acompte = f2.number_input("Acompte (€)", value=v_acompte, step=1)
                        f3.markdown(f"<br>Reste : <b style='color:red;'>{e_prix - e_acompte} €</b>", unsafe_allow_html=True)
                        
                        st.write("⛵ **NAVIGATION**")
                        c_date, c_pers, c_jours = st.columns(3)
                        try: d_init = datetime.strptime(str(row.get('DateNav'))[:10], "%Y-%m-%d")
                        except: d_init = datetime.now()
                        e_date = c_date.date_input("Date", d_init)
                        e_pers = c_pers.number_input("Pers.", value=clean_int(row.get('Nbre de personnes', 1)), step=1)
                        e_jours = c_jours.number_input("Jours", value=clean_int(row.get('Nbre de jours', 1)), step=1)
                        
                        e_tel = st.text_input("Téléphone", row.get('Téléphone', ''))
                        e_notes = st.text_area("Notes", row.get('Notes', ''))
                        
                        s1, s2, s3 = st.columns(3)
                        opts_soc = ["PERSO", "CMN", "VOG", "CLICK", "Autres"]
                        e_soc = s1.selectbox("Société", opts_soc, index=opts_soc.index(societe_label) if societe_label in opts_soc else 0)
                        opts_s = ["En attente", "Ok", "Terminé", "Refusé", "Annulé"]
                        e_st = s2.selectbox("Statut", opts_s, index=opts_s.index(statut_label) if statut_label in opts_s else 0)
                        opts_p = ["Non payé", "Payé"]
                        e_pa = s3.selectbox("Paiement", opts_p, index=opts_p.index(row.get('Paiement', 'Non payé')) if row.get('Paiement') in opts_p else 0)
                        
                        btn_save, btn_quit = st.columns(2)
                        if btn_save.form_submit_button("💾 ENREGISTRER", use_container_width=True):
                            df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'] = e_pre.upper(), e_nom.upper()
                            df_c.at[idx, 'DateNav'] = e_date.strftime("%Y-%m-%d")
                            df_c.at[idx, 'Société'], df_c.at[idx, 'Prix'] = e_soc, int(e_prix)
                            df_c.at[idx, 'Acompte'] = int(e_acompte)
                            df_c.at[idx, 'Nbre de personnes'], df_c.at[idx, 'Nbre de jours'] = int(e_pers), int(e_jours)
                            df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Notes'] = format_tel_fr(e_tel), e_notes
                            df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'] = e_st, e_pa
                            sauvegarder_data(df_c, 'contacts.json'); st.session_state.edit_idx = None; st.rerun()

                        if btn_quit.form_submit_button("❌ QUITTER", use_container_width=True):
                            if str(row.get('Nom')) == "CONTACT": df_c = df_c.drop(idx); sauvegarder_data(df_c, 'contacts.json')
                            st.session_state.edit_idx = None; st.rerun()
                    
                    # --- BOUTONS D'ACTION (HORS FORMULAIRE) ---
                    st.write("---")
                    b_arch, b_del = st.columns(2)
                    if b_arch.button("📦 ARCHIVER", key=f"btn_arch_init_{idx}", use_container_width=True):
                        st.session_state.confirm_arch_idx_c = idx; st.session_state.confirm_del_idx_c = None; st.rerun()
                    if b_del.button("🗑️ SUPPRIMER", key=f"btn_del_init_{idx}", use_container_width=True):
                        st.session_state.confirm_del_idx_c = idx; st.session_state.confirm_arch_idx_c = None; st.rerun()

            # --- MODE AFFICHAGE ---
            else:
                date_str = formater_date_affichage(row.get('DateNav'))
                st.markdown(f"""
                    <div style="border: 2px solid #4A4A4A; padding: 12px; border-radius: 12px; margin-bottom: 8px; background-color: {bg_color}; color: {text_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b style="font-size: 1.1rem;">{str(row.get('Prénom', '')).upper()} {str(row.get('Nom', '')).upper()}</b>
                            <span style="background: {'#2e7d32' if str(row.get('Paiement')).lower() == 'payé' else '#d32f2f'}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold;">{str(row.get('Paiement')).upper()}</span>
                        </div>
                        <div style="font-size: 0.9rem; margin-top: 6px; line-height: 1.3;">
                            📅 <b>{date_str}</b> | 🏢 {societe_label}<br>
                            💰 Total: <b>{v_prix}€</b> | Acc: <b>{v_acompte}€</b> | <span style="color:{'red' if v_solde > 0 else 'green'}; font-weight:bold;">Reste: {v_solde}€</span><br>
                            👥 {row.get('Nbre de personnes', 1)} pers. | ⏱️ {row.get('Nbre de jours', 1)} j. | 📞 {format_tel_fr(row.get('Téléphone', ''))}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"✏️ MODIFIER : {row.get('Nom')}", key=f"btn_open_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.rerun()

# =================================================================
# --- 6. PAGE PLANNING (V16 - INDÉPENDANCE TOTALE) ---
# =================================================================
if st.session_state.page == "PLANNING":
    from datetime import datetime, date, timedelta
    import calendar
    import json

    # --- 1. CHARGEMENT BRUT POUR ÉVITER LES FILTRES DE DF_C ---
    @st.cache_data(ttl=10)
    def load_raw_planning():
        try:
            with open('contacts.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    raw_data = load_raw_planning()

    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING 2026</h1></div>', unsafe_allow_html=True)
    
    # --- 2. NAVIGATION ---
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)

    if 'curr_month_idx' not in st.session_state: st.session_state.curr_month_idx = aujourdhui.month - 1
    if 'curr_year' not in st.session_state: st.session_state.curr_year = aujourdhui.year

    c_m, c_y, c_n = st.columns([1.5, 1, 0.8])
    sel_m_nom = c_m.selectbox("Mois", m_noms, index=st.session_state.curr_month_idx)
    sel_m = m_noms.index(sel_m_nom) + 1
    st.session_state.curr_month_idx = sel_m - 1
    sel_y = c_y.selectbox("Année", [2026, 2027, 2028], index=[2026, 2027, 2028].index(st.session_state.curr_year))
    st.session_state.curr_year = sel_y

    if c_n.button("📍 AUJOURD'HUI", use_container_width=True):
        st.session_state.curr_month_idx = aujourdhui.month - 1
        st.session_state.curr_year = aujourdhui.year
        st.rerun()

    jours_occ = {}
    missions_list = []
    total_mois = 0

     # --- 3. TRAITEMENT DES DONNÉES (CORRIGÉ POUR FICHES VIERGES) ---
    for i, r in enumerate(raw_data):
        try:
            # 1. SÉCURITÉ : On ignore les fiches sans nom ou noms par défaut
            nom_client = str(r.get('Nom', '')).strip().upper()
            prenom_client = str(r.get('Prénom', '')).strip().upper()
            
            # Si le nom est vide, égal à "CONTACT" ou "NAN", on passe à la suivante
            if nom_client in ["", "CONTACT", "NAN", "NONE"]:
                continue
            
            # 2. Extraction Date sécurisée
            d_val = str(r.get('DateNav') or r.get('Date') or '').strip().split(' ')[0]
            # ... (reste du code identique)

            statut = str(r.get('Statut', 'Ok')).lower()
            soc = str(r.get('Société', 'PERSO')).upper()
            dt_end = dt_start + timedelta(days=n_j-1)

            # Remplissage Calendrier
            for day_offset in range(n_j):
                curr = dt_start + timedelta(days=day_offset)
                if curr.month == sel_m and curr.year == sel_y:
                    if "CMN" in soc: color = "#3498db"
                    elif "annul" in statut or "refus" in statut: color = "#bdc3c7"
                    elif curr < aujourdhui: color = "#34495e"
                    else: color = "#27ae60"
                    jours_occ[curr.day] = {"c": color}

            # Ajout à la liste (si touche le mois)
            if (dt_start.year == sel_y and dt_start.month == sel_m) or (dt_end.year == sel_y and dt_end.month == sel_m):
                missions_list.append({'r': r, 'idx': i, 'start': dt_start, 'color': color if 'color' in locals() else "#27ae60"})
                if dt_start.month == sel_m and "annul" not in statut:
                    try: total_mois += float(str(r.get('Prix', 0)).replace('€','').strip())
                    except: pass
        except: continue

    # --- 4. AFFICHAGE HTML ---
    h_cal = '<table style="width:100%; text-align:center; border-collapse:collapse; background:white; border:1px solid #ddd;">'
    h_cal += '<tr style="background:#f8f9fa; font-size:11px;"><td>L</td><td>M</td><td>M</td><td>J</td><td>V</td><td>S</td><td>D</td></tr>'
    for sem in calendar.monthcalendar(sel_y, sel_m):
        h_cal += '<tr>'
        for i, jour in enumerate(sem):
            if jour == 0: h_cal += '<td style="height:40px; border:1px solid #eee;"></td>'
            else:
                occ = jours_occ.get(jour, {})
                bg = occ.get("c", "transparent")
                txt = "white" if bg != "transparent" else "black"
                is_t = (jour == aujourdhui.day and sel_m == aujourdhui.month and sel_y == aujourdhui.year)
                st_cell = "background:#f3e5ab;" if is_t else ""
                h_cal += f'<td style="{st_cell} border:1px solid #eee;"><div style="background:{bg}; color:{txt}; border-radius:50%; width:26px; height:26px; line-height:26px; margin:auto; font-size:12px; font-weight:bold;">{jour}</div></td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    st.markdown(h_cal, unsafe_allow_html=True)

    # --- 5. LISTE DÉTAILLÉE ---
    st.markdown("---")
    if missions_list:
        missions_list.sort(key=lambda x: x['start'])
        for m in missions_list:
            r = m['r']
            col_date, col_info = st.columns([1, 4])
            col_date.markdown(f"<div style='background:{m['color']}; color:white; border-radius:5px; text-align:center; padding:3px; font-weight:bold;'>{m['start'].strftime('%d/%m')}</div>", unsafe_allow_html=True)
            if col_info.button(f"{str(r.get('Prénom',''))} {str(r.get('Nom','')).upper()}", key=f"btn_fin_{m['idx']}"):
                st.session_state.edit_idx = m['idx']
                st.session_state.page = "CONTACTS"
                st.rerun()
    else:
        st.info(f"Aucune mission en {sel_m_nom} {sel_y}")

    st.success(f"**Revenus prévus : {total_mois:,.0f} €**")

# =================================================================
# --- 9. PAGE STATS (VERSION FINALE COMPLÈTE & COMPTABLEMENT JUSTE) ---
# =================================================================
if st.session_state.page == "STATS":
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import datetime

    # --- 1. FONCTIONS UTILES (Dates Robustes & Nettoyage) ---
    def conversion_date_robuste(date_str):
        if pd.isna(date_str) or date_str == "": return pd.NaT
        date_str = str(date_str).strip()
        # Liste des formats à tester (ISO, FR, FR-Année courte)
        formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%y']
        for fmt in formats:
            try: return pd.to_datetime(date_str, format=fmt)
            except: continue
        # En dernier recours
        return pd.to_datetime(date_str, errors='coerce', dayfirst=True)

    # --- 2. CHARGEMENT ÉTANCHE (ANTI-PAGE BLANCHE) ---
    df_planning_actif = charger_data('contacts.json')
    df_m_actif = charger_data('maintenance.json')
    df_m_arch = charger_data('archives_factures.json')
    # Fusion des frais (Actif + Archive pour avoir l'historique complet)
    df_frais_full = pd.concat([df_m_actif, df_m_arch], ignore_index=True)

    # --- 3. NAVIGATION & SÉLECTEUR DE BILAN ---
    st.title("📊 Bilan Vesta")
    
    # Sélecteur principal
    mode_bilan = st.radio("Type de bilan", ["A ce jour", "Par Saison"], horizontal=True, key="stats_mode_select")
    today = datetime.date.today()
    sel_y = today.year # Année par défaut

    if mode_bilan == "Par Saison":
        ANNEES_STATS = [2025, 2026, 2027]
        sel_y = st.selectbox("Saison à analyser", ANNEES_STATS, index=1, key="stats_year_select")
        st.caption(f"📅 Analyse de la trésorerie réelle (encaissée) pour l'année {sel_y}")
    else:
        st.caption(f"📅 Analyse de la trésorerie réelle au {today.strftime('%d/%m/%Y')} (Jan à Aujourd'hui)")

    # --- 4. TRAITEMENT DES DONNÉES & FILTRAGE STRICT (AMÉLIORÉ) ---
    total_rev, total_frais = 0, 0
    df_soc_final, df_frais_final, df_r_yr, df_f_yr = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # A. REVENUS (Planning) - FILTRAGE STRICT SUR "PAYÉ" (HORS "NON PAYÉ")
    if not df_planning_actif.empty:
        df_p = df_planning_actif.copy()
        
        # --- FILTRE COMPTABLE STRICT (HORS NON-PAYÉS ET STATUTS FLOUES) ---
        # On cherche les colonnes de paiement possibles
        col_paye = next((c for c in ['Paiement', 'Statut_Paye', 'Paye'] if c in df_p.columns), None)
        
        if col_paye:
            # Nettoyage et normalisation
            df_p[col_paye] = df_p[col_paye].fillna('').astype(str).str.upper().str.strip()
            
            # --- LA RÈGLE STRICTE ICI ---
            # 1. Le statut contient "PAY" (Payé, Payé par CB, etc.)
            mask_contient_paye = df_p[col_paye].str.contains('PAY', na=False)
            # 2. Le statut NE contient PAS "NON PAY" (Non Payé, Non-Payé)
            mask_ne_contient_pas_non_paye = ~df_p[col_paye].str.contains('NON PAY', na=False)
            
            # 3. Application du filtre strict "Paiement Réel"
            df_rev_encaisses = df_p[mask_contient_paye & mask_ne_contient_pas_non_paye].copy()
        else:
            # Si aucune colonne de paiement n'existe, on ne prend aucune mission (sécurité)
            df_rev_encaisses = pd.DataFrame(columns=df_p.columns)
            st.error("⚠️ Colonne de statut de paiement non trouvée dans le planning. Impossible de calculer les revenus encaissés.")

        if not df_rev_encaisses.empty:
            # --- FILTRE 2 : DATE ET ANNÉE (Utilise DateNav) ---
            # Conversion date
            df_rev_encaisses['dt_vrai'] = df_rev_encaisses['DateNav'].apply(conversion_date_robuste)
            
            # Filtre Année
            mask_y = (df_rev_encaisses['dt_vrai'].dt.year == sel_y) if mode_bilan == "Par Saison" else ((df_rev_encaisses['dt_vrai'].dt.year == today.year) & (df_rev_encaisses['dt_vrai'].dt.date <= today))
            
            # Tri chronologique inverse (plus récent en haut)
            df_r_yr = df_rev_encaisses[mask_y].sort_values('dt_vrai', ascending=False).copy()
            
            if not df_r_yr.empty:
                # Nettoyage prix
                df_r_yr['P_Num'] = pd.to_numeric(df_r_yr['Prix'], errors='coerce').fillna(0)
                total_rev = df_r_yr['P_Num'].sum()

                # Harmonisation Société (Perso, Click & Boat)
                df_r_yr['Société'] = df_r_yr['Société'].fillna('PERSO').astype(str).str.upper().str.strip()
                df_r_yr['Société'] = df_r_yr['Société'].replace({'PARTICULIER': 'PERSO', 'NAN': 'PERSO', '': 'PERSO', 'CLICK': 'CLICK & BOAT', 'CLICK&BOAT': 'CLICK & BOAT', 'CLICK AND BOAT': 'CLICK & BOAT', 'NONE': 'PERSO'})
                
                # Groupement par Société
                df_soc_final = df_r_yr.groupby('Société')['P_Num'].sum().reset_index().rename(columns={'P_Num':'CA €'}).sort_values('CA €', ascending=False)

    # B. FRAIS (Maintenance) - On considère que toute facture entrée est décaissée (décaissement réel)
    if not df_frais_full.empty:
        df_f = df_frais_full.copy()
        # Conversion date maintenance (standard dayfirst=True)
        df_f['dt_vrai'] = pd.to_datetime(df_f['Date'], errors='coerce', dayfirst=True)
        
        # Filtre Année
        mask = (df_f['dt_vrai'].dt.year == sel_y) if mode_bilan == "Par Saison" else ((df_f['dt_vrai'].dt.year == today.year) & (df_f['dt_vrai'].dt.date <= today))
        
        # Tri chronologique inverse
        df_f_yr = df_f[mask].sort_values('dt_vrai', ascending=False).copy()
        
        if not df_f_yr.empty:
            # Nettoyage frais
            df_f_yr['M_Num'] = pd.to_numeric(df_f_yr['M_Num'], errors='coerce').fillna(0)
            total_frais = df_f_yr['M_Num'].sum()
            
            # Harmonisation Type (Dépenses)
            df_f_yr['Type'] = df_f_yr['Type'].fillna('AUTRES').astype(str).str.upper().str.strip().replace({'NAN': 'AUTRES', 'NONE': 'AUTRES', '': 'AUTRES', 'GUEULETON': 'PERSO', 'MAINTENANCE': 'ENTRETIEN'})
            
            # Groupement par Type (Dépenses)
            df_frais_final = df_f_yr.groupby('Type')['M_Num'].sum().reset_index().rename(columns={'M_Num':'Total €'}).sort_values('Total €', ascending=False)

    # --- 5. RÉSUMÉ DE TRÉSORERIE RÉELLE ---
    st.subheader(f"💰 Synthèse Trésorerie réelle (Encaissé/Décaissé) {sel_y}")
    
    c1, c2, c3 = st.columns(3)
    solde = total_rev - total_frais
    c1.metric("Encaissé (Missions Payées)", f"{total_rev:,.0f} €".replace(',', ' '))
    c2.metric("Décaissé (Frais payés)", f"{total_frais:,.0f} €".replace(',', ' '))
    c3.metric("Solde Net (En banque)", f"{solde:,.0f} €".replace(',', ' '), delta_color="normal" if solde >= 0 else "inverse")

    # Graphique Pie (Camembert)
    if total_rev > 0 or total_frais > 0:
        fig = px.pie(names=['Frais', 'Revenus'], values=[total_frais, total_rev],
                     color_discrete_map={'Frais': '#EF553B', 'Revenus': '#00CC96'}, hole=0.5)
        # Ajustement mobile
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300,
                          legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

    # =================================================================
    # --- 6. INDICATEURS DE PILOTAGE STRATÉGIQUES (RÉ-INTÉGRÉS) ---
    # =================================================================
    st.divider()
    st.subheader("🚀 Indicateurs de Pilotage (Basés sur l'encaissé)")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    # KPI 1 : Marge Nette (en %)
    if total_rev > 0:
        marge_nette = (solde / total_rev) * 100
        couleur_marge = "green" if marge_nette > 30 else ("red" if marge_nette < 0 else "orange")
        kpi1.markdown(f"<div style='text-align:center;'>Marge Nette<br><span style='font-size:30px; font-weight:bold; color:{couleur_marge};'>{marge_nette:.1f} %</span></div>", unsafe_allow_html=True)
    else: kpi1.metric("Marge Nette", "0 %")

    # KPI 2 : CA Moyen / Jour (Si la colonne NbJours existe)
    ca_moyen_jour = 0
    total_jours = 0
    if not df_r_yr.empty:
        # On cherche la colonne Jours
        col_jours = next((c for c in ['Nbre de jours', 'NbJours', 'Nb jours'] if c in df_r_yr.columns), None)
        if col_jours:
            total_jours = pd.to_numeric(df_r_yr[col_jours], errors='coerce').sum()
            if total_jours > 0: ca_moyen_jour = total_rev / total_jours
    
    if ca_moyen_jour > 0:
        kpi2.markdown(f"<div style='text-align:center;'>CA / Jour (Moy)<br><span style='font-size:30px; font-weight:bold; color:black;'>{ca_moyen_jour:.0f} €</span><br><span style='font-size:12px; color:gray;'>sur {total_jours:.0f} j. Encaissés</span></div>", unsafe_allow_html=True)
    else: kpi2.metric("CA / Jour (Moy)", "0 €")

    # KPI 3 : Nombre Total de Missions Encaissées
    nb_missions = len(df_r_yr) if not df_r_yr.empty else 0
    kpi3.markdown(f"<div style='text-align:center;'>Missions Encaissées<br><span style='font-size:30px; font-weight:bold; color:black;'>{nb_missions}</span></div>", unsafe_allow_html=True)

    # KPI 4 : Taux de Dépendance (Risque Client)
    if not df_soc_final.empty and total_rev > 0:
        gros_client_ca = df_soc_final.iloc[0]['CA €']
        nom_gros_client = df_soc_final.iloc[0]['Société']
        taux_dep = (gros_client_ca / total_rev) * 100
        couleur_dep = "red" if taux_dep > 60 else ("green" if taux_dep < 30 else "orange")
        kpi4.markdown(f"<div style='text-align:center;'>Risque ({nom_gros_client})<br><span style='font-size:30px; font-weight:bold; color:{couleur_dep};'>{taux_dep:.0f} %</span></div>", unsafe_allow_html=True)
    else: kpi4.metric("Risque Client", "0 %")

    # --- 7. BILAN MENSUEL DE TRÉSORERIE ---
    if total_rev > 0 or total_frais > 0:
        st.divider()
        st.subheader("📊 Tableau de bord Mensuel (Encaissé/Décaissé)")
        
        mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
        rs_m = []
        # On boucle sur les 12 mois
        for i in range(1, 13):
            r_m = df_r_yr[df_r_yr['dt_vrai'].dt.month == i]['P_Num'].sum() if not df_r_yr.empty else 0
            f_m = df_f_yr[df_f_yr['dt_vrai'].dt.month == i]['M_Num'].sum() if not df_f_yr.empty else 0
            # J'arrondis à l'euro pour iPhone 16
            rs_m.append({'Mois': mois_noms[i-1], 'Encaissé €': round(r_m,0), 'Décaissé €': round(f_m,0), 'Solde €': round(r_m-f_m,0)})
        
        # Affichage du tableau mensuel, arrondis à l'euro
        st.dataframe(pd.DataFrame(rs_m), hide_index=True, use_container_width=True)

    # --- 8. DÉTAIL DES OPÉRATIONS DE TRÉSORERIE RÉELLES ---
    st.divider()
    st.subheader("📝 Détail des opérations réelles")
    
    # A. DÉTAIL DES REVENUS (Missions déjà encaissées)
    with st.expander("📥 Détail des Revenus Encaissés", expanded=False):
        if not df_r_yr.empty:
            df_disp = df_r_yr.copy()
            # Reconstruction sécurisée de la colonne "Client"
            nom_cols = [c for c in ['Prénom', 'Nom'] if c in df_disp.columns]
            if nom_cols:
                df_disp['Client'] = df_disp[nom_cols].fillna('').agg(' '.join, axis=1).str.title().str.strip()
            else:
                df_disp['Client'] = "Inconnu"

            # Sélection sécurisée des colonnes à afficher
            cols_to_show = [c for c in ['DateNav', 'Client', 'Société', 'P_Num'] if c in df_disp.columns]
            
            # Affichage du détail avec renommage de "Prix" en "Montant €"
            st.dataframe(df_disp[cols_to_show].rename(columns={'DateNav':'Date','P_Num':'Montant €'}), hide_index=True, use_container_width=True)
            
            st.caption(f"Total Encaissé (Missions Payées) : **{total_rev:,.0f} €**".replace(',', ' '))
        else:
            st.info("Aucun revenu perçu enregistré sur cette période.")

    # B. DÉTAIL DES DÉPENSES (Frais déjà décaissés)
    with st.expander("📤 Détail des Dépenses Décaissées", expanded=False):
        if not df_f_yr.empty:
            df_disp_f = df_f_yr.copy()
            # Sélection sécurisée des colonnes
            cols_f = [c for c in ['Date', 'Type', 'Description', 'M_Num'] if c in df_disp_f.columns]
            # Affichage
            st.dataframe(df_disp_f[cols_f].rename(columns={'Type':'Catégorie','M_Num':'Montant €'}), hide_index=True, use_container_width=True)
            st.caption(f"Total Décaissé (Frais payés) : **{total_frais:,.0f} €**".replace(',', ' '))
        else:
            st.info("Aucune dépense enregistrée sur cette période.")

    # --- 9. ARCHIVAGE (CORRIGÉ & SÉCURISÉ) ---
    if mode_bilan == "Par Saison":
        st.divider()
        if st.checkbox("Afficher les outils d'archivage", key="stats_arch_check"):
            st.subheader("⚙️ Outils de la Saison")
            st.warning(f"Attention, cette action va archiver **toutes** les données de l'année **{sel_y}**, perçues ou non.")
            # ... (logique d'archivage identique à la précédente)
    # =================================================================
    # --- 8. BOUTON ARCHIVAGE (CORRIGÉ & SÉCURISÉ) ---
    # =================================================================
    if mode_bilan == "Par Saison":
        st.divider()
        st.subheader("⚙️ Outils de la Saison")
        st.warning(f"Attention, cette action va archiver **toutes** les données de l'année **{sel_y}**.")
        
        with st.expander(f"⚙️ Archiver les données de la saison {sel_y}", expanded=False):
            st.write(f"Voulez-vous archiver les frais (vers `archives_factures.json`) et les missions (vers `archives_planning.json`) de {sel_y} ?")
            arch_btn = st.button(f"🚀 Lancer l'archivage de {sel_y}", key=f"arch_button_{sel_y}")
            
            if arch_btn:
                import json
                try:
                    # A. ARCHIVAGE FRAIS (Maintenance active vers Archive)
                    if not df_m_actif.empty:
                        # 1. Identifier les données de la saison
                        df_m_yr_raw = df_m_actif[pd.to_datetime(df_m_actif['Date'], dayfirst=True, errors='coerce').dt.year == sel_y]
                        
                        if not df_m_yr_raw.empty:
                            # 2. Sauvegarder dans archive
                            nouvelle_archive_m = pd.concat([df_m_arch, df_m_yr_raw], ignore_index=True)
                            save_data('archives_factures.json', nouvelle_archive_m.to_dict(orient='records'))
                            # 3. Supprimer de l'actif
                            nouvelle_actif_m = df_m_actif.drop(df_m_yr_raw.index)
                            save_data('maintenance.json', nouvelle_actif_m.to_dict(orient='records'))
                            st.success(f"📦 Frais {sel_y} archivés !")
                        else: st.info(f"Aucun frais à archiver pour {sel_y}.")

                    # B. ARCHIVAGE REVENUS (Planning actif vers Planning Archive)
                    if not df_planning_actif.empty:
                        # 1. Identifier les données de la saison
                        df_c_yr_raw = df_planning_actif[pd.to_datetime(df_planning_actif['DateNav'], errors='coerce', dayfirst=True).dt.year == sel_y]
                        
                        if not df_c_yr_raw.empty:
                            # 2. Sauvegarder dans archive (Crée le fichier si n'existe pas)
                            try: df_c_arch = charger_data('archives_planning.json')
                            except: df_c_arch = pd.DataFrame()
                            nouvelle_archive_c = pd.concat([df_c_arch, df_c_yr_raw], ignore_index=True)
                            save_data('archives_planning.json', nouvelle_archive_c.to_dict(orient='records'))
                            # 3. Supprimer de l'actif
                            nouvelle_actif_c = df_planning_actif.drop(df_c_yr_raw.index)
                            save_data('contacts.json', nouvelle_actif_c.to_dict(orient='records'))
                            st.success(f"📦 Missions {sel_y} archivées !")
                        else: st.info(f"Aucune mission à archiver pour {sel_y}.")
                        
                    st.info("Le script va redémarrer pour appliquer les changements.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de l'archivage : {e}")
    
    # =================================================================
    # --- 9. BOUTON ARCHIVAGE (INTÉGRÉ) ---
    # =================================================================
    if mode_bilan == "Par Saison":
        st.divider()
        st.subheader("⚙️ Outils de la Saison")
        st.warning(f"Attention, cette action va archiver **toutes** les données de l'année **{sel_y}**.")
        
        with st.expander(f"⚙️ Archiver les données de la saison {sel_y}", expanded=False):
            st.write(f"Voulez-vous archiver les frais (vers `archives_factures.json`) et les missions (vers `archives_planning.json`) de {sel_y} ?")
            arch_btn = st.button(f"🚀 Lancer l'archivage de {sel_y}", key=f"arch_button_{sel_y}")
            
            if arch_btn:
                import json
                try:
                    # A. ARCHIVAGE FRAIS (Maintenance)
                    df_m_yr_raw = df_m_actif[pd.to_datetime(df_m_actif['Date'], dayfirst=True, errors='coerce').dt.year == sel_y]
                    if not df_m_yr_raw.empty:
                        # 1. Sauvegarder dans archive
                        nouvelle_archive_m = pd.concat([df_m_arch, df_m_yr_raw], ignore_index=True)
                        save_data('archives_factures.json', nouvelle_archive_m.to_dict(orient='records'))
                        # 2. Supprimer de l'actif
                        nouvelle_actif_m = df_m_actif.drop(df_m_yr_raw.index)
                        save_data('maintenance.json', nouvelle_actif_m.to_dict(orient='records'))
                        st.success(f"📦 Frais {sel_y} archivés !")

                    # B. ARCHIVAGE REVENUS (Planning)
                    df_c_yr_raw = df_planning_actif[pd.to_datetime(df_planning_actif['DateNav'], errors='coerce', dayfirst=True).dt.year == sel_y]
                    if not df_c_yr_raw.empty:
                        # 1. Sauvegarder dans archive (Crée le fichier si n'existe pas)
                        try: df_c_arch = charger_data('archives_planning.json')
                        except: df_c_arch = pd.DataFrame()
                        nouvelle_archive_c = pd.concat([df_c_arch, df_c_yr_raw], ignore_index=True)
                        save_data('archives_planning.json', nouvelle_archive_c.to_dict(orient='records'))
                        # 2. Supprimer de l'actif
                        nouvelle_actif_c = df_planning_actif.drop(df_c_yr_raw.index)
                        save_data('contacts.json', nouvelle_actif_c.to_dict(orient='records'))
                        st.success(f"📦 Missions {sel_y} archivées !")
                        
                    st.info("Le script va redémarrer pour appliquer les changements.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Une erreur est survenue lors de l'archivage : {e}")
# =================================================================
# --- 8. PAGE MAINTENANCE (PERSISTANTE & CARNET DE SANTÉ) ---
# =================================================================
if st.session_state.page == "MAINT":
    import pandas as pd
    import json
    import os
    from datetime import datetime

    # --- A. FONCTIONS INTERNES (PERSISTANCE & EXPORT) ---
    def charger_params():
        if os.path.exists('params_maint.json'):
            with open('params_maint.json', 'r') as f:
                return json.load(f)
        return {"cible_vidange": 2450.0}

    def sauver_params(data):
        with open('params_maint.json', 'w') as f:
            json.dump(data, f)

    def preparer_download(file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return f.read()
        return ""

    # --- B. RÉCUPÉRATION DES DONNÉES ---
    params = charger_params()
    df_log = charger_data('logbook.json')
    df_m = charger_data('maintenance.json')
    
    releve_h = 0
    if not df_log.empty:
        df_log['MotArr'] = pd.to_numeric(df_log['MotArr'], errors='coerce').fillna(0)
        releve_h = df_log['MotArr'].max()

    # --- C. INTERFACE DE RÉGLAGE (DYNAMIQUE) ---
    st.title("🛠️ MAINTENANCE")
    
    col_target, col_info = st.columns([2, 1])
    with col_target:
        new_target = st.number_input("Prochaine vidange à (h) :", 
                                     value=float(params['cible_vidange']), 
                                     step=10.0, format="%.1f")
        if new_target != params['cible_vidange']:
            params['cible_vidange'] = new_target
            sauver_params(params)
    
    PROCHAINE_VIDANGE = params['cible_vidange']
    CYCLE_VIDANGE = 100.0
    heures_restantes = PROCHAINE_VIDANGE - releve_h
    
    # Calcul progression
    h_faites_dans_cycle = CYCLE_VIDANGE - heures_restantes
    percent_prog = max(0.0, min(1.0, h_faites_dans_cycle / CYCLE_VIDANGE))
# --- D. BANDEAU D'ALERTE & CARNET DE SANTÉ ---
    if heures_restantes > 15:
        color_v, bg_v = "#2e7d32", "#e8f5e9" # Vert
    elif heures_restantes > 0:
        color_v, bg_v = "#ef6c00", "#fff3e0" # Orange
    else:
        color_v, bg_v = "#c62828", "#ffebee" # Rouge

    # 1. Préparation des variables (BIEN ALIGNÉES AVEC LE "if" CI-DESSUS)
    txt_restant = f"{heures_restantes:.1f}"
    txt_releve = f"{releve_h:.1f}"
    label_unite = "restantes"

    # 2. Rendu HTML sécurisé
    html_cycle = (
        f'<div style="background-color: {bg_v}; border: 2px solid {color_v}; padding: 12px; border-radius: 12px; text-align: center; margin-top: 10px;">'
        f'<div style="color: {color_v}; font-weight: bold; font-size: 0.75rem; text-transform: uppercase;">'
        f'&#128712; État du Cycle'
        f'</div>'
        f'<div style="font-size: 1.6rem; font-weight: 900; color: {color_v}; margin: 5px 0;">'
        f'{txt_restant} h <span style="font-size:0.8rem; font-weight:normal;">{label_unite}</span>'
        f'</div>'
        f'<div style="font-size: 0.75rem; color: #555;">'
        f'Compteur actuel : <b>{txt_releve} h</b>'
        f'</div>'
        f'</div>'
    )

    st.markdown(html_cycle, unsafe_allow_html=True)
    st.progress(percent_prog)

    # LE BOUTON DOIT ÊTRE ALIGNÉ AVEC st.markdown CI-DESSUS
    if st.button("🔧 ENREGISTRER LA VIDANGE COMME FAITE", use_container_width=True, type="primary"):
        # Le contenu du bouton est décalé de 4 espaces supplémentaires
        new_v = {
            "Date": datetime.now().strftime("%d/%m/%Y"),
            "Objet": f"VIDANGE MOTEUR ({releve_h}h)",
            "Montant": 0.0,
            "M_Num": 0.0,
            "Statut": "Fait",
            "Type": "Maintenance, matériels"
        }
        df_m = pd.concat([df_m, pd.DataFrame([new_v])], ignore_index=True)
        sauvegarder_data(df_m, 'maintenance.json')
        params['cible_vidange'] = releve_h + 100.0
        sauver_params(params)
        st.success("Vidange archivée !")
        st.rerun()

        st.divider()

    # --- E. AFFICHAGE DES ENREGISTREMENTS (LE MORCEAU MANQUANT) ---
    st.subheader("📋 Historique des frais & interventions")

    if not df_m.empty:
        # Tri par date décroissante pour voir le plus récent en haut
        df_m['dt_tri'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_m_visu = df_m.sort_values('dt_tri', ascending=False)

        for idx, row in df_m_visu.iterrows():
            est_vidange = "VIDANGE" in str(row['Objet']).upper()
            
            # Style dynamique (Orange pour vidange, Gris pour le reste)
            bg_c = "#fff3e0" if est_vidange else "#f8f9fa"
            brd_c = "#ef6c00" if est_vidange else "#dee2e6"
            icon = "🛠️" if est_vidange else "📄"
            
            # Gestion du montant sécurisée
            try:
                m_val = float(row.get('M_Num', 0))
            except:
                m_val = 0.0

            html_maint = (
                f'<div style="border: 1px solid {brd_c}; border-left: 8px solid {brd_c}; padding: 10px; border-radius: 8px; margin-bottom: 8px; background-color: {bg_c};">'
                f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                f'<div style="font-size: 0.9rem; font-weight: bold;">{icon} {row["Date"]} | {row["Objet"]}</div>'
                f'<div style="font-size: 1rem; font-weight: 900;">{m_val:.0f} &euro;</div>'
                f'</div>'
                f'<div style="font-size: 0.75rem; color: #666; margin-top: 4px;">'
                f'Type: {row.get("Type", "N/A")} &bull; Statut: <b>{str(row.get("Statut", "N/A")).upper()}</b>'
                f'</div>'
                f'</div>'
            )
            st.markdown(html_maint, unsafe_allow_html=True)
    else:
        st.info("Aucun frais de maintenance enregistré dans le fichier actif.")

    # --- F. OPTIONS D'EXPORTATION ---
    with st.sidebar:
        st.markdown("---")
        if st.button("🗑️ Vider le cache maintenance"):
            if os.path.exists('maintenance.json'):
                os.remove('maintenance.json')
                st.rerun()

# ===============================================================================
# --- 9. PAGE FACTURES (ANALYSE & ENVOI CMN OPTIMISÉ) ---
# =================================================================
if st.session_state.page == "FACTURES":
    st.title("📑 Facturation & Rapports")

    # --- 1. SÉLECTION DU MOIS ---
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    
    col_m, col_a = st.columns(2)
    sel_mois = col_m.selectbox("Choisir le mois", mois_noms, index=maintenant.month - 1)
    sel_annee = col_a.selectbox("Année", [2025, 2026, 2027], index=1)

    index_mois = mois_noms.index(sel_mois) + 1

    # --- 2. FILTRAGE ET CALCULS ---
    if not df_c.empty:
        df_fact = df_c.copy()
        df_fact['dt'] = pd.to_datetime(df_fact['DateNav'], format='%d/%m/%Y', errors='coerce')
        
        mask_cmn = (df_fact['Société'].astype(str).str.upper() == "CMN") & \
                   (df_fact['dt'].dt.month == index_mois) & \
                   (df_fact['dt'].dt.year == sel_annee)
        
        df_cmn_mois = df_fact[mask_cmn].copy()
        
        if not df_cmn_mois.empty:
            st.subheader(f"Missions CMN - {sel_mois} {sel_annee}")
            
            def clean_prix(x):
                try:
                    s = "".join(c for c in str(x) if c.isdigit() or c in ".,")
                    return float(s.replace(",", "."))
                except: return 0.0

            df_cmn_mois['PrixNum'] = df_cmn_mois['Prix'].apply(clean_prix)
            total_cmn = df_cmn_mois['PrixNum'].sum()
            
            st.table(df_cmn_mois[['DateNav', 'Nom', 'Prix']].set_index('DateNav'))
            st.metric("Total à facturer", f"{total_cmn:.2f} €")
            
            # --- Préparation des variables pour le mail ---
            total_txt = f"{total_cmn:.2f}".replace(".", ",")
            
            # Construction de la liste des missions pour le corps du mail
            lignes = []
            for _, r in df_cmn_mois.iterrows():
                lignes.append(f"- {r['DateNav']} : {r['Nom']} ({r['Prix']})")
            texte_missions = "\n".join(lignes)

            destinataire = "tresorier@cmn-asso.fr, aurelienfaucheux@gmail.com"
            objet = f"Facturation Missions Vesta - {sel_mois} {sel_annee}"

            # Modèle de mail (Nettoyé de tout caractère invisible)
            modele_mail = "Bonjour,\n\nJ'espère que vous allez bien !\n\nVoici le récapitulatif des navigations de la CMN concernant le mois de {mois} {annee} :\n\n{missions}\n\nLe montant total s'élève à {total} EUR.\n\nMerci d'avance pour le règlement et à très vite sur l'eau !\n\nAmicalement,\nEric (Vesta)"

            corps_mail = modele_mail.format(
                mois=sel_mois, 
                annee=sel_annee, 
                missions=texte_missions, 
                total=total_txt
            )

            # --- 4. ZONE D'ENVOI ET COPIE ---
            st.text_area("Copier ce texte pour Gmail :", corps_mail, height=300)
            st.info(f"**Destinataire :** {destinataire}\n\n**Objet :** {objet}")
            
            import urllib.parse
            mail_link = f"mailto:{destinataire}?subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            
            st.link_button("🚀 TENTER L'ENVOI DIRECT (MAILTO)", mail_link, use_container_width=True)
            st.caption("Note : Utilisez le copier-coller si le bouton ne lance pas votre application de mail.")
            
        else:
            st.info(f"Aucune mission CMN trouvée pour {sel_mois} {sel_annee}.")
    else:
        st.warning("La base de données est vide.")
# =================================================================
# --- 11. PAGE ARCHIVES (NETTOYAGE, EXPORT & CARTES VIDANGE) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    import pandas as pd
    import io
    from datetime import datetime

    # 1. BOUTON DE RETOUR
    last = st.session_state.get('last_page', 'PLANNING')
    if st.button(f"⬅️ RETOUR VERS {last}", use_container_width=True):
        st.session_state.page = last
        st.rerun()

    st.title("📂 Centre d'Archivage Vesta")

    # --- 2. LE PANNEAU DE NETTOYAGE ---
    with st.expander("✂️ ARCHIVER UNE PÉRIODE (Nettoyage)", expanded=False):
        st.info("Sélectionnez une période pour basculer les données actives vers l'historique.")
        c1, c2 = st.columns(2)
        d_debut = c1.date_input("Du", datetime(2026, 1, 1), key="arch_d1")
        d_fin = c2.date_input("Au", datetime(2026, 12, 31), key="arch_d2")
        
        if st.button("🚀 LANCER L'ARCHIVAGE GLOBAL", use_container_width=True, type="primary"):
            df_m = charger_data('maintenance.json')
            nb_m = archiver_donnees(df_m, d_debut, d_fin, 'maintenance.json', 'archives_maintenance.json', 'Date')
            df_c = charger_data('contacts.json')
            nb_p = archiver_donnees(df_c, d_debut, d_fin, 'contacts.json', 'archives_planning.json', 'DateNav')
            df_l = charger_data('logbook.json')
            nb_l = archiver_donnees(df_l, d_debut, d_fin, 'logbook.json', 'archives_logbook.json', 'Date')
            st.success(f"Archivage réussi : {nb_m} frais, {nb_p} missions et {nb_l} navigations déplacés.")
            st.rerun()

    # --- 3. EXPORT EXCEL ---
    with st.expander("📤 TRANSFÉRER VERS PC (Excel)", expanded=False):
        df_arch_m = charger_data('archives_maintenance.json')
        df_arch_p = charger_data('archives_planning.json')
        df_arch_l = charger_data('archives_logbook.json')
        
        if not df_arch_m.empty or not df_arch_p.empty or not df_arch_l.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                if not df_arch_p.empty: df_arch_p.to_excel(writer, sheet_name='Planning', index=False)
                if not df_arch_m.empty: df_arch_m.to_excel(writer, sheet_name='Frais', index=False)
                if not df_arch_l.empty: df_arch_l.to_excel(writer, sheet_name='Livre de Bord', index=False)
            
            st.download_button(label="📊 TÉLÉCHARGER L'EXCEL GLOBAL", data=buffer.getvalue(),
                               file_name=f"Archives_Vesta_Total_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            st.warning("Aucune donnée à exporter.")

    # --- 4. AFFICHAGE DES TABLEAUX ---
    st.subheader("📜 Historique actuel")
    t1, t2, t3 = st.tabs(["🛠️ Frais", "📅 Planning", "📖 Livre de Bord"])
    
    with t1:
        st.caption("Visualisation des archives de maintenance")
        df_frais_arch = charger_data('archives_maintenance.json')
        if not df_frais_arch.empty:
            df_frais_arch['dt_t'] = pd.to_datetime(df_frais_arch['Date'], dayfirst=True, errors='coerce')
            df_frais_arch = df_frais_arch.sort_values('dt_t', ascending=False)
            for idx, row in df_frais_arch.iterrows():
                est_vidange = "VIDANGE" in str(row['Objet']).upper()
                bg_c, brd_c = ("#fff3e0", "#ef6c00") if est_vidange else ("#f1f3f4", "#9aa0a6")
                icon = "🛠️" if est_vidange else "📄"
                montant_val = float(pd.to_numeric(row.get('M_Num', 0), errors='coerce'))
                html_frais = (f'<div style="border: 1px solid {brd_c}; border-left: 10px solid {brd_c}; padding: 12px; border-radius: 10px; margin-bottom: 8px; background-color: {bg_c};">'
                              f'<div style="display: flex; justify-content: space-between;">'
                              f'<b>{icon} {row["Date"]} | {row["Objet"]}</b>'
                              f'<b>{montant_val:.0f} &euro;</b></div></div>')
                st.markdown(html_frais, unsafe_allow_html=True)
        else:
            st.write("Aucun frais archivé.")

# =================================================================
# --- 10. PAGE LOG (LIVRE DE BORD) ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#01579b; color:white; padding:10px; border-radius:10px; margin-bottom:20px;"><h1>📖 LIVRE DE BORD</h1></div>', unsafe_allow_html=True)
    
    df_log = charger_data('logbook.json')
    if df_log is None or not isinstance(df_log, pd.DataFrame):
        df_log = pd.DataFrame()

    if st.button("📂 ACCÉDER AUX ARCHIVES", use_container_width=True):
        st.session_state.page = "ARCHIVES"
        st.rerun()

    # 1. Préparation sécurisée
    df_log = preparer_log_safe(df_log)
    
    # 2. Formulaire
    is_editing = st.session_state.log_edit_idx is not None and st.session_state.log_edit_idx in df_log.index
    titre_expander = "📝 MODIFIER LA NAVIGATION" if is_editing else "➕ NOUVELLE SORTIE"
    
    with st.expander(titre_expander, expanded=is_editing):
        row = df_log.loc[st.session_state.log_edit_idx] if is_editing else {}
        with st.form("form_log_vesta", clear_on_submit=True):
            # ... (Gardez ici tout votre code de colonnes c1, c2, c3, e1-e6, etc.) ...
            # IMPORTANT: Le bouton de sauvegarde doit rester dans ce bloc indenté
            f_date = st.date_input("Date", datetime.now()) # Exemple simplifié pour l'espace
            btn_save = st.form_submit_button("💾 ENREGISTRER")
            if btn_save:
                # ... (Votre logique de sauvegarde habituelle) ...
                st.success("Enregistré !")
                st.rerun()

    # --- 3. AFFICHAGE DES FICHES (MAINTENANT DANS LE BLOC PAGE == "LOG") ---
    st.divider()
    if not df_log.empty:
        df_log['dt_tri'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
        df_visu = df_log.sort_values('dt_tri', ascending=False)
        
        if "log_confirm_del" not in st.session_state:
            st.session_state.log_confirm_del = None

        for idx, r in df_visu.iterrows():
            # Affichage de la carte
            info_gasoil = f" | &#9981; <b>{r.get('Litre Gazoil',0)}L</b>" if r.get('Plein')=="Oui" else ""
            html_card = (f'<div style="border: 1px solid #ddd; padding: 12px; border-radius: 10px; background: #f1f8ff; margin-bottom: 5px; border-left: 8px solid #01579b;">'
                         f'<b>&#128197; {r["Date"]}</b> | {r["PortDep"]} &rarr; {r["PortArr"]}</div>')
            st.markdown(html_card, unsafe_allow_html=True)
            
            # Boutons Actions
            c_a, c_b, c_c = st.columns([1, 1, 4])
            if c_a.button("✏️", key=f"edit_btn_{idx}"):
                st.session_state.log_edit_idx = idx
                st.rerun()
            
            if st.session_state.get("log_confirm_del") == idx:
                if c_b.button("✅ OUI", key=f"conf_del_{idx}", type="primary"):
                    df_log = df_log.drop(idx)
                    sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                    st.session_state.log_confirm_del = None
                    st.rerun()
            else:
                if c_b.button("🗑️", key=f"ask_del_{idx}"):
                    st.session_state.log_confirm_del = idx
                    st.rerun()
# --- FIN DU FICHIER ---


































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































