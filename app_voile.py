import requests, base64, json, time, os, html, io
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
from datetime import datetime, date, timedelta
import calendar

# --- INITIALISATION DU SESSION STATE ---
if 'log_edit_idx' not in st.session_state:
    st.session_state.log_edit_idx = None
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'page' not in st.session_state: 
    st.session_state.page = "CONTACTS"
if 'vue_contact' not in st.session_state:
    st.session_state.vue_contact = "En cours"

# --- FONCTIONS UTILITAIRES GLOBALES ---
def to_f(val):
    if pd.isna(val) or val == "": 
        return 0.0
    try: 
        return float(str(val).replace('€','').replace(' ','').replace(',','.').strip())
    except: 
        return 0.0

def bouton_export_excel(df, nom_fichier):
    """Fonction standardisée pour l'archivage et l'export Excel"""
    if df.empty:
        return st.warning(f"Aucune donnée à exporter pour {nom_fichier}")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label=f"📊 EXPORTER {nom_fichier.upper()} (EXCEL)",
        data=buffer.getvalue(),
        file_name=f"Vesta_{nom_fichier}_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# =================================================================
# --- 1. FONCTIONS DE SÉCURITÉ, GITHUB & PARAMS ---
# =================================================================

def clean_num(val, default=0):
    try:
        if pd.isna(val) or str(val).lower() in ["nan", "", "none"]: return default
        clean_val = str(val).replace('€','').replace(' ','').replace(',','.').strip()
        return int(float(clean_val))
    except: return default

def charger_data(file):
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
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        content_str = df.to_json(orient="records", indent=4)
        content_b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
        requests.put(url, headers={"Authorization": f"token {token}"}, 
                     json={"message": f"Update {file}", "content": content_b64, "sha": sha})
    except Exception as e: st.error(f"Erreur sauvegarde {file} : {e}")

# --- NOUVELLES FONCTIONS POUR LA VIDANGE ---
def charger_params():
    """Charge les réglages de vidange pour les menus STATS et MAINT"""
    df = charger_data('params.json')
    if not df.empty:
        return df.iloc[0].to_dict()
    return {"prochaine_vidange": 2450.0, "cible_vidange": 250.0}

def sauvegarder_params(dict_params):
    """Sauvegarde les réglages moteur"""
    df = pd.DataFrame([dict_params])
    sauvegarder_data(df, 'params.json')

def charger_data_safe(fichier):
    df = charger_data(fichier)
    return df if not df.empty else pd.DataFrame()

# =================================================================
# --- CONFIGURATION & STYLE ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

now = datetime.now()
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
date_bandeau = f"&#128197; {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"

st.markdown(f"""<style>
    .main-header {{ font-size: 1.8rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }}
    .date-header {{ text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }}
</style>""", unsafe_allow_html=True)

# =================================================================
# --- NAVIGATION ---
# =================================================================
if not st.session_state.get('authenticated', False):
    st.markdown('<div class="main-header">⚓ VESTA 2026</div>', unsafe_allow_html=True)
    pw = st.text_input("Code d'accès :", type="password")
    if st.button("ACCÉDER", use_container_width=True):
        if pw == "Skipper2026":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect.")
    st.stop()

st.markdown('<div class="main-header">⚓ VESTA 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

# Barre de navigation mise à jour
menu = ["PLANNING", "CONTACTS", "STATS", "MAINT", "LOG", "NOTES", "FACT"]
icones = {
    "PLANNING": "📅", "CONTACTS": "👤", "STATS": "📊", 
    "MAINT": "🛠️", "LOG": "📖", "NOTES": "📝", "FACT": "📑"
}

cols_nav = st.columns(len(menu))
for i, name in enumerate(menu):
    # Gestion des redirections de noms
    page_target = "MEMOS" if name == "NOTES" else ("FACTURES" if name == "FACT" else name)
    
    is_active = st.session_state.page == page_target
    if cols_nav[i].button(f"{icones[name]}\n{name}", key=f"nav_{name}", use_container_width=True, type="primary" if is_active else "secondary"):
        st.session_state.page = page_target
        st.rerun()


st.divider()

# =================================================================
# --- 2. MENU MÉMOS (NOTES LIBRES) ---
# =================================================================
if st.session_state.page == "MEMOS":
    st.markdown("### 📝 Mémos & Notes de Bord")
    df_memos = charger_data_safe('memos.json')

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.expander("➕ AJOUTER UN MÉMO", expanded=False):
            with st.form("new_memo_form"):
                m_date = st.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
                m_desc = st.text_area("Description / Rappel")
                m_statut = st.selectbox("Statut", ["Normal", "Urgent", "Fait"])
                if st.form_submit_button("Enregistrer"):
                    new_m = pd.DataFrame([{"Date": m_date, "Description": m_desc, "Statut": m_statut}])
                    df_memos = pd.concat([df_memos, new_m], ignore_index=True)
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()
    with c2:
        bouton_export_excel(df_memos, "memos")

    if not df_memos.empty:
        # Tri inverse pour voir les plus récents en haut
        for idx, row in df_memos.sort_index(ascending=False).iterrows():
            bg_color = "#D5F5E3" if row['Statut'] == "Fait" else ("#FADBD8" if row['Statut'] == "Urgent" else "#FEF9E7")
            st.markdown(f"""
            <div style="background:{bg_color}; padding:12px; border-radius:10px; border-left:5px solid #34495E; margin-bottom:10px; color:black;">
                <small>{row['Date']} — <b>{row['Statut'].upper()}</b></small><br>
                {row['Description']}
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"🗑️ Supprimer #{idx}", key=f"del_m_{idx}"):
                df_memos = df_memos.drop(idx).reset_index(drop=True)
                sauvegarder_data(df_memos, 'memos.json')
                st.rerun()
# =================================================================
# --- 5. BLOC CONTACTS (V102 - COMPLET : RELANCES & COULEURS) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    # --- CHARGEMENT DES DONNÉES ---
    df_raw = charger_data('contacts.json')
    
    # --- NAVIGATION ET EXCEL (ARCHIVAGE) ---
    # Ajout d'une colonne pour le 4ème onglet "RELANCES"
    n1, n2, n3, n4, n5 = st.columns([1, 1, 1, 1, 1.5])
    
    if n1.button("🟢 EN COURS", use_container_width=True, type="primary" if st.session_state.vue_contact == "En cours" else "secondary"): 
        st.session_state.vue_contact = "En cours"; st.rerun()
    if n2.button("⌛ ATTENTE", use_container_width=True, type="primary" if st.session_state.vue_contact == "Attente" else "secondary"): 
        st.session_state.vue_contact = "Attente"; st.rerun()
    if n3.button("📞 RELANCES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Relances" else "secondary"): 
        st.session_state.vue_contact = "Relances"; st.rerun()
    if n4.button("✅ ARCHIVES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Archives" else "secondary"): 
        st.session_state.vue_contact = "Archives"; st.rerun()

    with n5:
        bouton_export_excel(df_raw, "Planning_General")

    st.divider()

    # --- FILTRAGE & RECHERCHE ---
    if not df_raw.empty:
        df_c = df_raw.copy().fillna("")
        df_c['orig_idx'] = df_c.index
        df_c['dt_sort'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
        
        c_search, c_yr, c_new = st.columns([2, 1, 1])
        search = c_search.text_input("🔍 Rechercher (Nom, Prénom, Société...)", "", key="search_bar_contacts").upper()
        annee_sel = c_yr.selectbox("Saison", [2025, 2026, 2027], index=1, key="saison_contacts")
        
        if c_new.button("➕ NOUVEAU", use_container_width=True):
            new_r = {
                "Prénom": "NOUVEAU", "Nom": "CLIENT", "Statut": "En attente", 
                "Paiement": "Unpaid", "Relancer": "Non", "DateNav": datetime.now().strftime("%d/%m/%Y"), 
                "Société": "PERSO", "Jours": 1, "Prix": 0, "Acompte": 0, "Notes": "", "Téléphone": "", "Email": "", "Pers": 1
            }
            df_new = pd.concat([pd.DataFrame([new_r]), df_raw], ignore_index=True)
            sauvegarder_data(df_new, 'contacts.json')
            st.session_state.edit_idx = 0 
            st.session_state.page = "MODIFIER_CONTACT"
            st.rerun()

        # Application des filtres
        mask = (df_c['dt_sort'].dt.year == annee_sel) | (df_c['dt_sort'].isna())
        if search:
            mask = mask & (df_c['Nom'].astype(str).str.upper().str.contains(search) | 
                           df_c['Prénom'].astype(str).str.upper().str.contains(search) | 
                           df_c['Société'].astype(str).str.upper().str.contains(search))
        df_c = df_c[mask].copy()

        # --- LOGIQUE DE SÉPARATION DES ONGLETS ---
        statut_clean = df_c['Statut'].str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        relance_clean = df_c['Relancer'].fillna("Non").str.upper()
        
        if st.session_state.vue_contact == "Archives":
            mask_aff = (statut_clean.str.contains("termine|annule|refuse")) & (relance_clean != "OUI")
            tri_ordre = False 
        elif st.session_state.vue_contact == "Relances":
            # Uniquement ceux qui sont Terminés ET marqués "A recontacter : Oui"
            mask_aff = (statut_clean.str.contains("termine")) & (relance_clean == "OUI")
            tri_ordre = True
        elif st.session_state.vue_contact == "Attente":
            # Uniquement la vraie liste d'attente (pas les terminés)
            mask_aff = (statut_clean == "liste d'attente")
            tri_ordre = True  
        else: # EN COURS
            mask_aff = ~(statut_clean.str.contains("termine|annule|refuse")) & (statut_clean != "liste d'attente")
            tri_ordre = True

        df_aff = df_c[mask_aff].copy().sort_values(by='dt_sort', ascending=tri_ordre)

        # --- BOUCLE D'AFFICHAGE DES FICHES ---
        for _, row in df_aff.iterrows():
            idx = row['orig_idx']
            p_total, p_aco = to_f(row.get('Prix', 0)), to_f(row.get('Acompte', 0))
            reste = p_total - p_aco
            
            # Couleurs de société (avec Jaune pour PERSO)
            soc_name = str(row.get('Société', 'PERSO')).upper()
            if soc_name == "CMN": border_col, bg_card, text_soc = "#2980B9", "#EBF5FB", "🔵 CMN"
            elif soc_name == "CLICK": border_col, bg_card, text_soc = "#27AE60", "#EAFAF1", "🟢 CLICK"
            elif soc_name == "VOG": border_col, bg_card, text_soc = "#8E44AD", "#F5EEF8", "🟣 VOG"
            elif soc_name == "PERSO": border_col, bg_card, text_soc = "#F1C40F", "#FEF9E7", "🟡 PERSO"
            else: border_col, bg_card, text_soc = "#7F8C8D", "#FDFEFE", "⚪ " + soc_name

            # Icônes de paiement
            pay_status = str(row.get('Paiement', 'Unpaid')).upper()
            pay_icon = "✅" if pay_status == "PAID" else "⏳"
            
            # Style spécial si c'est une relance
            style_relance = "border: 2px dashed #E67E22;" if st.session_state.vue_contact == "Relances" else ""

            st.markdown(f"""
            <div style="background:{bg_card}; padding:15px; border-radius:12px; border-left:10px solid {border_col}; 
                        box-shadow: 4px 4px 10px rgba(0,0,0,0.08); margin-bottom:15px; color: black; {style_relance}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:1.2rem; font-weight:bold; color:#2C3E50;">{row['Prénom']} {row['Nom']}</span>
                    <span style="background:{border_col}; color:{'black' if soc_name == 'PERSO' else 'white'}; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:bold;">{text_soc}</span>
                </div>
                <div style="margin-top:8px; font-size:0.95rem;">
                    📅 <b>{row['DateNav']}</b> | 👥 {row['Pers']} pers | ☀️ {row['Jours']}j<br>
                    <div style="margin-top:5px; padding:5px; background:rgba(255,255,255,0.6); border-radius:5px;">
                        💰 {int(p_total)}€ | 💸 {int(p_aco)}€ | <b style="color:{'#C0392B' if reste > 0 else '#27AE60'};">⌛ Reste : {int(reste)}€</b>
                    </div>
                    <div style="margin-top:5px; font-weight:bold;">{pay_icon} {pay_status} | 🏁 {row['Statut']}</div>
                    <hr style="margin:10px 0; border: 0.5px solid rgba(0,0,0,0.1);">
                    <i style="color:#566573;">📝 {row['Notes']}</i>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- BOUTONS ---
            c1, c2, c3 = st.columns([1, 1, 1])
            if c1.button("✏️ ÉDITER", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.session_state.page = "MODIFIER_CONTACT"
                st.rerun()

            if f"confirm_del_{idx}" not in st.session_state:
                if c2.button("🗑️ SUPPRIMER", key=f"del_{idx}", use_container_width=True):
                    st.session_state[f"confirm_del_{idx}"] = True
                    st.rerun()
            else:
                st.error(f"Supprimer {row['Nom']} ?")
                co1, co2 = st.columns(2)
                if co1.button("✅ OUI", key=f"y_{idx}"):
                    df_db = charger_data('contacts.json').drop(idx).reset_index(drop=True)
                    sauvegarder_data(df_db, 'contacts.json')
                    del st.session_state[f"confirm_del_{idx}"]; st.rerun()
                if co2.button("❌ NON", key=f"n_{idx}"):
                    del st.session_state[f"confirm_del_{idx}"]; st.rerun()
            
            if st.session_state.vue_contact == "En cours":
                if c3.button("🏁 FINIR", key=f"fin_{idx}", use_container_width=True):
                    df_all = charger_data('contacts.json')
                    df_all.loc[idx, 'Statut'] = "Terminé"
                    df_all.loc[idx, 'Paiement'] = "Paid"
                    sauvegarder_data(df_all, 'contacts.json')
                    st.rerun()
    else:
        st.info("La base de données est vide.")

# =================================================================
# --- 6. PAGE MODIFIER CONTACT ---
# =================================================================
if st.session_state.page == "MODIFIER_CONTACT":
    st.markdown('<h3 style="text-align:center;">✏️ Modifier le Contact</h3>', unsafe_allow_html=True)
    
    idx_to_edit = st.session_state.get('edit_idx')
    df_m = charger_data('contacts.json')

    if idx_to_edit is not None and not df_m.empty and idx_to_edit in df_m.index:
        row = df_m.loc[idx_to_edit]
        
        with st.form("form_edit_v100"):
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=str(row.get('Prénom', '')))
            new_nom = c2.text_input("Nom", value=str(row.get('Nom', '')))
            
            c3, c4 = st.columns(2)
            new_date = c3.text_input("Date (JJ/MM/AAAA)", value=str(row.get('DateNav', '')))
            
            liste_soc = ["PERSO", "CLICK", "CMN", "VOG"]
            curr_soc = str(row.get('Société', 'PERSO')).upper().strip()
            if curr_soc not in liste_soc and curr_soc != "": liste_soc.append(curr_soc)
            soc_idx = liste_soc.index(curr_soc) if curr_soc in liste_soc else 0
            new_soc = c4.selectbox("Société", liste_soc, index=soc_idx)
            
            c5, c6 = st.columns(2)
            new_tel = c5.text_input("Téléphone", value=str(row.get('Téléphone', '')))
            new_mail = c6.text_input("Email", value=str(row.get('Email', '')))
            
            cl1, cl2 = st.columns(2)
            new_jours = cl1.number_input("Nombre de jours", value=int(clean_num(row.get('Jours', 0))), min_value=0)
            new_pers = cl2.number_input("Nombre de personnes", value=int(clean_num(row.get('Pers', 0))), min_value=0)
            
            f1, f2 = st.columns(2)
            new_prix = f1.number_input("Prix Total (€)", value=int(clean_num(row.get('Prix', 0))))
            new_aco = f2.number_input("Acompte (€)", value=int(clean_num(row.get('Acompte', 0))))
            
            s1, s2 = st.columns(2)
            s_list = ["En attente", "Confirmé", "Terminé", "Annulé", "Refusé", "Liste d'attente"]
            curr_s = str(row.get('Statut', 'En attente')).strip()
            # Matching souple pour l'index
            s_idx = next((i for i, s in enumerate(s_list) if s.lower() in curr_s.lower()), 0)
            new_statut = s1.selectbox("Statut Mission", s_list, index=s_idx)
            
            sub1, sub2 = s2.columns(2)
            p_list = ["Unpaid", "Paid"]
            p_idx = 1 if str(row.get('Paiement', '')).upper() == "PAID" else 0
            new_pay = sub1.selectbox("Paiement", p_list, index=p_idx)
            
            val_r = str(row.get('Relancer', 'Non')).strip().capitalize()
            new_relance = sub2.selectbox("À recontacter ?", ["Non", "Oui"], index=1 if val_r == "Oui" else 0)
            
            new_notes = st.text_area("Notes", value=str(row.get('Notes', '')).replace('nan',''))

            if st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True):
                maj = {
                    'Prénom': new_pre.upper(), 'Nom': new_nom.upper(), 'DateNav': new_date,
                    'Société': new_soc.upper(), 'Téléphone': new_tel.strip(), 'Email': new_mail.strip(),
                    'Jours': int(new_jours), 'Pers': int(new_pers), 'Prix': int(new_prix),
                    'Acompte': int(new_aco), 'Statut': new_statut, 'Paiement': new_pay,
                    'Relancer': new_relance, 'Notes': str(new_notes).strip()
                }
                df_m.loc[idx_to_edit, maj.keys()] = list(maj.values())
                sauvegarder_data(df_m, 'contacts.json')
                st.session_state.page = "CONTACTS"
                st.rerun()

    if st.button("⬅️ RETOUR"):
        st.session_state.page = "CONTACTS"
        st.rerun()
# =================================================================
# --- 6. PAGE PLANNING (V18.5 - OPTIMISÉ) ---
# =================================================================
if st.session_state.page == "PLANNING":
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING</h1></div>', unsafe_allow_html=True)
    
    if st.button("📂 ACCÉDER AUX ARCHIVES", key="k_arch_p", use_container_width=True):
        st.session_state.last_page = "PLANNING"
        st.session_state.page = "ARCHIVES"
        st.rerun()

    st.divider()

    # Initialisation temporelle
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    jours_occ = {}
    total_mois = 0
    missions_list = []

    if 'curr_month_idx' not in st.session_state: st.session_state.curr_month_idx = aujourdhui.month - 1
    if 'curr_year' not in st.session_state: st.session_state.curr_year = aujourdhui.year

    c_m, c_y, c_n = st.columns([1.5, 1, 0.8])
    sel_m_nom = c_m.selectbox("Mois", m_noms, index=st.session_state.curr_month_idx)
    sel_m = m_noms.index(sel_m_nom) + 1
    st.session_state.curr_month_idx = sel_m - 1
    
    sel_y = c_y.selectbox("Année", [2025, 2026, 2027, 2028], index=[2025, 2026, 2027, 2028].index(st.session_state.curr_year))
    st.session_state.curr_year = sel_y

    if c_n.button("📍 ICI", use_container_width=True):
        st.session_state.curr_month_idx = aujourdhui.month - 1
        st.session_state.curr_year = aujourdhui.year
        st.rerun()

    # --- CHARGEMENT ---
    df_p = charger_data('contacts.json')

    # --- TRAITEMENT ---
    if not df_p.empty:
        df_p = df_p.fillna("")
        
        for idx, r in df_p.iterrows():
            try:
                nom_client = str(r.get('Nom', '')).strip().upper()
                if nom_client in ["", "CONTACT", "NAN"]: continue
                
                d_brute = str(r.get('DateNav', '')).strip().split(' ')[0]
                if d_brute.lower() in ["nan", "---", "", "none"]: continue

                dt_start = None
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        dt_start = datetime.strptime(d_brute, fmt).date()
                        break
                    except: continue
                
                if not dt_start: continue 

                n_j = int(float(str(r.get('Jours', 1) or 1))) 
                statut = str(r.get('Statut', 'En attente')).lower()
                soc = str(r.get('Société', 'PERSO')).upper()
                dt_end = dt_start + timedelta(days=max(0, n_j-1))
                prix_val = to_f(r.get('Prix', 0))

                # Couleurs
                if "CMN" in soc: color = "#3498db"
                elif any(x in statut for x in ["annul", "refus"]): color = "#bdc3c7"
                elif dt_start < aujourdhui: color = "#34495e"
                else: color = "#27ae60"

                # Remplissage calendrier (uniquement si dans le mois affiché)
                for i in range(n_j):
                    curr = dt_start + timedelta(days=i)
                    if curr.month == sel_m and curr.year == sel_y:
                        jours_occ[curr.day] = {"c": color}

                # Ajout à la liste si la mission touche le mois sélectionné
                if (dt_start.year == sel_y and dt_start.month == sel_m) or (dt_end.year == sel_y and dt_end.month == sel_m):
                    missions_list.append({
                        'r': r, 'idx': idx, 'start': dt_start, 'end': dt_end, 
                        'n_j': n_j, 'color': color, 'prix': prix_val, 'statut': statut
                    })
                    # On ne compte dans le CA du mois que si la mission commence ce mois-ci et n'est pas annulée
                    if dt_start.month == sel_m and not any(x in statut for x in ["annul", "refus"]):
                        total_mois += prix_val
            except: continue

    # --- AFFICHAGE CALENDRIER ---
    h_cal = '<table style="width:100%; text-align:center; border-collapse:collapse; background:white; border:1px solid #ddd;">'
    h_cal += '<tr style="background:#f8f9fa; font-size:12px; font-weight:bold;"><td>Lu</td><td>Ma</td><td>Me</td><td>Je</td><td>Ve</td><td>Sa</td><td>Di</td></tr>'
    
    for sem in calendar.monthcalendar(sel_y, sel_m):
        h_cal += '<tr>'
        for jour in sem:
            if jour == 0:
                h_cal += '<td style="height:40px; border:1px solid #eee;"></td>'
            else:
                occ = jours_occ.get(jour, {})
                bg = occ.get("c", "transparent")
                txt_c = "white" if bg != "transparent" else "black"
                is_t = (jour == aujourdhui.day and sel_m == aujourdhui.month and sel_y == aujourdhui.year)
                st_cell = "background:#fff9c4;" if is_t else "" 
                h_cal += f'''<td style="{st_cell} border:1px solid #eee; height:40px;">
                                <div style="background:{bg}; color:{txt_c}; border-radius:50%; width:26px; height:26px; line-height:26px; margin:auto; font-weight:bold; font-size:12px;">
                                    {jour}
                                </div>
                            </td>'''
        h_cal += '</tr>'
    st.markdown(h_cal + '</table>', unsafe_allow_html=True)

    # LISTE DES MISSIONS
    st.markdown(f"### 📋 Missions de {sel_m_nom}")
    if missions_list:
        missions_list.sort(key=lambda x: x['start'])
        for m in missions_list:
            prix_p = f"{m['prix']:.0f} €"
            col1, col2 = st.columns([1, 3.5])
            with col1:
                st.markdown(f"""<div style='background:{m['color']}; color:white; border-radius:5px; text-align:center; padding:5px;'>
                    <span style='font-size:0.75rem;'>{m['start'].strftime('%d/%m')}</span><br><b>{prix_p}</b>
                </div>""", unsafe_allow_html=True)
            with col2:
                nom_affiche = f"{str(m['r'].get('Prénom','')).upper()} {str(m['r'].get('Nom','')).upper()}"
                if st.button(f"{nom_affiche} ({m['statut'].upper()})", key=f"p_btn_{m['idx']}", use_container_width=True):
                    st.session_state.edit_idx = m['idx']
                    st.session_state.page = "MODIFIER_CONTACT"
                    st.rerun()
        st.success(f"**💰 Total prévisionnel {sel_m_nom} : {total_mois:,.0f} €**".replace(",", " "))
    else:
        st.info("Aucune mission ce mois-ci.")
# =================================================================
# --- PAGE STATS : COCKPIT VESTA SKIPPER PRO 2026 ---
# =================================================================
if st.session_state.page == "STATS":
    st.markdown('<h2 style="text-align:center;">🚀 Cockpit Vesta 2026</h2>', unsafe_allow_html=True)

    # 1. Chargement des données
    df_actif = charger_data_safe('contacts.json')
    df_arch = charger_data_safe('archives_planning.json')
    df_m = charger_data_safe('maintenance.json') 
    df_log = charger_data_safe('logbook.json')
    params = charger_params() # La fonction doit être définie en haut du script
    
    # Fusion actif + archives
    df_all = pd.concat([df_actif, df_arch], ignore_index=True) if not df_arch.empty else df_actif

    # --- FONCTION LOCALE POUR LA CONVERSION ---
    def to_f_local(val):
        if pd.isna(val) or val == "": return 0.0
        try: return float(str(val).replace('€','').replace(' ','').replace(',','.').strip())
        except: return 0.0

    if not df_all.empty:
        # --- A. FILTRES ---
        c_sel1, c_sel2 = st.columns(2)
        mode_bilan = c_sel1.radio("Période :", ["À ce jour", "Année Complète"], horizontal=True)
        sel_y = c_sel2.selectbox("Année :", [2025, 2026, 2027], index=1, key="saison_stats")

        # Filtrage Revenus
        df_all['dt_vrai'] = pd.to_datetime(df_all['DateNav'], dayfirst=True, errors='coerce')
        df_f = df_all[df_all['dt_vrai'].dt.year == sel_y].copy()
        
        if mode_bilan == "À ce jour" and not df_f.empty:
            df_f = df_f[df_f['dt_vrai'] <= pd.Timestamp.now().normalize()].copy()

        def est_comptabilise(row):
            soc = str(row.get('Société', '')).upper()
            paiement = str(row.get('Paiement', '')).upper()
            statut = str(row.get('Statut', '')).upper()
            if "LISTE D'ATTENTE" in statut: return False
            # On compte si c'est CMN (pro) ou si c'est payé
            return "CMN" in soc or paiement == "PAID"

        df_final = df_f[df_f.apply(est_comptabilise, axis=1)].copy() if not df_f.empty else pd.DataFrame()
        
        # Filtrage Maintenance & Logbook
        df_m_y = pd.DataFrame()
        if not df_m.empty:
            df_m['dt_maint'] = pd.to_datetime(df_m.get('Date', ''), dayfirst=True, errors='coerce')
            df_m_y = df_m[(df_m['dt_maint'].dt.year == sel_y) & (df_m.get('Statut', '') == "Fait")].copy()
        
        df_log_y = pd.DataFrame()
        if not df_log.empty:
            df_log['dt_log'] = pd.to_datetime(df_log.get('Date', ''), dayfirst=True, errors='coerce')
            df_log_y = df_log[df_log['dt_log'].dt.year == sel_y].copy()

        # --- B. TOUS LES CALCULS ---
        total_ca = sum(to_f_local(x) for x in df_final['Prix']) if not df_final.empty else 0.0
        nb_jours = len(df_final)
        ca_moyen_jour = total_ca / nb_jours if nb_jours > 0 else 0.0
        
        # Maintenance : recherche de la colonne montant
        col_m_val = next((c for c in ['M_Num', 'Montant', 'Prix'] if c in df_m_y.columns), None)
        t_maint = sum(to_f_local(x) for x in df_m_y[col_m_val]) if col_m_val and not df_m_y.empty else 0.0
        
        # Gazoil
        col_gazoil = next((c for c in ['Cout Gazoil', 'Cout_Gazoil', 'Gazoil'] if c in df_log_y.columns), None)
        t_gasoil_eur = df_log_y[col_gazoil].sum() if col_gazoil and not df_log_y.empty else 0.0
        total_dep = t_maint + t_gasoil_eur
        
        # Performance moteur/voile
        t_milles = df_log_y['TotalMil'].sum() if 'TotalMil' in df_log_y.columns else 0
        t_mot_p = df_log_y['TotalMot'].sum() if 'TotalMot' in df_log_y.columns else (df_log_y['Moteur'].sum() if 'Moteur' in df_log_y.columns else 0)
        t_voile = df_log_y['H_Voile'].sum() if 'H_Voile' in df_log_y.columns else 0
        
        revenu_par_h_moteur = total_ca / t_mot_p if t_mot_p > 0 else 0
        ratio_maintenance = (total_dep / total_ca * 100) if total_ca > 0 else 0
        mille_par_sortie = t_milles / nb_jours if nb_jours > 0 else 0

        # Vidange Synchro
        # On calcule les heures restantes : Cible - Heures déjà faites
        h_moteur_total = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if 'MotArr' in df_log.columns else 0.0
        h_restantes = params.get('prochaine_vidange', 2450.0) - h_moteur_total

        # --- C. BILAN SANTÉ ---
        st.markdown("### 🩺 Bilan de Santé")
        b1, b2, b3 = st.columns(3)
        # Seuil de rentabilité fixé à 6500€
        progression_ca = min(100, int((total_ca/6500)*100)) if total_ca > 0 else 0
        b1.metric("🎯 Rentabilité", f"{progression_ca}%", help="Seuil 6500€")
        
        indice_eco = (t_voile / (t_mot_p + t_voile) * 100) if (t_mot_p + t_voile) > 0 else 0
        b2.metric("🌿 Indice Éco", f"{indice_eco:.0f}%", help="Ratio Voile / (Moteur + Voile)")
        
        color_vidange = "normal" if h_restantes > 10 else "inverse"
        b3.metric("⚙️ Vidange dans", f"{h_restantes:.1f}h", delta=f"Cible: {params.get('prochaine_vidange', 0):.0f}h", delta_color=color_vidange)

        # --- D. PERFORMANCE ---
        st.write("---")
        st.markdown("### 📈 Performance Opérationnelle")
        p1, p2, p3 = st.columns(3)
        p1.metric("💎 Rendement/H", f"{revenu_par_h_moteur:.1f} €/h moteur")
        p2.metric("📉 Poids Frais", f"{ratio_maintenance:.1f} %", help="Part des dépenses sur le CA")
        p3.metric("📏 Moy. Sortie", f"{mille_par_sortie:.1f} NM")

        # --- E. INDICATEURS FINANCIERS ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 CA", f"{total_ca:,.0f} €")
        c2.metric("💸 Dépenses", f"{total_dep:,.0f} €")
        c3.metric("⚖️ Net", f"{(total_ca - total_dep):,.0f} €")

        # --- F. GRAPHES ---
        st.subheader("📉 Évolution Mensuelle")
        ordre_mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        nom_mois_map = {i+1: m for i, m in enumerate(ordre_mois)}
        df_evo = pd.DataFrame(index=range(1, 13))
        
        if not df_final.empty:
            df_final['Mois'] = df_final['dt_vrai'].dt.month
            df_evo['Recettes'] = df_final.groupby('Mois')['Prix'].sum()
        if not df_m_y.empty and col_m_val:
            df_m_y['Mois'] = df_m_y['dt_maint'].dt.month
            df_evo['Dépenses'] = df_m_y.groupby('Mois')[col_m_val].sum()
        
        df_evo = df_evo.fillna(0)
        df_evo.index = df_evo.index.map(nom_mois_map)
        df_evo.index = pd.Categorical(df_evo.index, categories=ordre_mois, ordered=True)
        st.bar_chart(df_evo.sort_index(), height=220)

        # --- G. RÉPARTITION ---
        st.write("---")
        st.subheader("🍕 Répartition des Volumes")
        col_pie1, col_pie2 = st.columns(2)
        
        with col_pie1:
            if not df_final.empty and 'Société' in df_final.columns:
                st.write("**Sorties par Société**")
                df_rep_soc = df_final['Société'].value_counts().reset_index()
                df_rep_soc.columns = ['Société', 'Nombre']
                st.bar_chart(df_rep_soc.set_index('Société'), horizontal=True, height=200)
            
        with col_pie2:
            if not df_m_y.empty and 'Type' in df_m_y.columns:
                st.write("**Maintenance par Cat. (€)**")
                df_rep_maint = df_m_y.groupby('Type')[col_m_val].sum()
                st.bar_chart(df_rep_maint, horizontal=True, height=200)

        # --- H. TABLEAUX DÉTAILLÉS ---
        st.write("---")
        t1, t2 = st.tabs(["💰 Détails CA", "🛠️ Détails Dépenses"])
        
        with t1:
            if not df_final.empty:
                df_final_clean = df_final.sort_values(by='dt_vrai', ascending=False)
                cols_r = [c for c in ['DateNav', 'Société', 'Prix'] if c in df_final_clean.columns]
                st.dataframe(df_final_clean[cols_r], use_container_width=True, hide_index=True)
                st.success(f"**TOTAL RECETTES : {total_ca:,.2f} €**")
        
        with t2:
            if not df_m_y.empty:
                df_m_y_clean = df_m_y.sort_values(by='dt_maint', ascending=False)
                st.write("**🔧 Maintenance :**")
                col_nom_m = next((c for c in ['Objet', 'Titre', 'Description'] if c in df_m_y_clean.columns), 'Détail')
                cols_m = [c for c in ['Date', col_nom_m, col_m_val] if c in df_m_y_clean.columns]
                st.dataframe(df_m_y_clean[cols_m], use_container_width=True, hide_index=True)
            
            if t_gasoil_eur > 0:
                st.write("**⛽ Carburant :**")
                df_log_y_clean = df_log_y[df_log_y[col_gazoil]>0].sort_values(by='dt_log', ascending=False)
                st.dataframe(df_log_y_clean[['Date', 'PortArr', col_gazoil]], use_container_width=True, hide_index=True)
            
            st.error(f"**TOTAL DÉPENSES : {total_dep:,.2f} €**")
    else:
        st.info("Aucune donnée disponible pour générer les statistiques.")

# =================================================================
# --- 8. PAGE MAINTENANCE (GESTION VIDANGE & TRAVAUX) ---
# =================================================================
if st.session_state.page == "MAINT":
    import pandas as pd
    from datetime import datetime, timedelta

    # 1. CHARGEMENT DES DONNÉES
    df_m = charger_data_safe('maintenance.json')
    df_log = charger_data_safe('logbook.json')
    
    # Récupération du compteur réel (Valeur max à l'arrivée dans le log)
    releve_h = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if not df_log.empty else 0.0
    
    # Gestion des paramètres de vidange
    params = charger_params()
    if 'prochaine_vidange' not in params:
        params['prochaine_vidange'] = 2450.0 # Valeur par défaut
        sauvegarder_params(params)

    st.title("🛠️ MAINTENANCE & VIDANGE")

    # 2. TABLEAU DE BORD VIDANGE
    heures_restantes = params['prochaine_vidange'] - releve_h
    # Alerte rouge si moins de 10h restantes
    color_v = "#2e7d32" if heures_restantes > 10 else "#c62828"
    
    col_v1, col_v2 = st.columns([2, 1])
    
    with col_v1:
        st.markdown(f"""
            <div style="background-color: {color_v}15; border: 2px solid {color_v}; padding: 15px; border-radius: 10px; text-align: center;">
                <h3 style="margin:0; color: {color_v};">{heures_restantes:.1f} h restantes</h3>
                <p style="margin:0;">Prochaine vidange prévue à : <b>{params['prochaine_vidange']:.1f} h</b></p>
                <small>Compteur actuel : {releve_h:.1f} h</small>
            </div>
        """, unsafe_allow_html=True)

    with col_v2:
        # Permet de modifier la cible manuellement
        new_target = st.number_input("Ajuster cible (h)", value=float(params['prochaine_vidange']), step=10.0)
        if new_target != params['prochaine_vidange']:
            params['prochaine_vidange'] = new_target
            sauvegarder_params(params)
            st.rerun()

    st.divider()

    # 3. FORMULAIRE "EFFECTUER LA VIDANGE"
    with st.expander("🔧 ENREGISTRER UNE VIDANGE FAITE", expanded=False):
        with st.form("form_vidange_v2026"):
            c1, c2 = st.columns(2)
            v_date = c1.date_input("Date de la vidange", datetime.now())
            v_compteur = c2.number_input("Valeur compteur (h)", value=releve_h, step=0.1)
            
            v_travaux = st.text_area("Travaux effectués", 
                                    placeholder="Ex: Vidange, Filtre huile, Filtre gasoil, Contrôle courroie, Turbine...")
            
            st.info(f"💡 Action : La prochaine échéance sera reglée à {v_compteur + 90:.1f} h")
            
            if st.form_submit_button("VALIDER ET RECALCULER (+90h)"):
                # Ajout à l'historique maintenance
                nouvelle_vidange = {
                    "Date": v_date.strftime("%d/%m/%Y"),
                    "Objet": "VIDANGE MOTEUR",
                    "M_Num": 0.0,
                    "Statut": "Fait",
                    "Type": "Maintenance",
                    "Notes": v_travaux
                }
                df_m = pd.concat([df_m, pd.DataFrame([nouvelle_vidange])], ignore_index=True)
                sauvegarder_data(df_m, 'maintenance.json')
                
                # Mise à jour auto de la cible
                params['prochaine_vidange'] = round(v_compteur + 90.0, 1)
                sauvegarder_params(params)
                
                st.success(f"✅ Vidange enregistrée. Prochaine à {params['prochaine_vidange']} h")
                st.rerun()

    # 4. FILTRES D'AFFICHAGE DU TABLEAU
    col_sel1, col_sel2 = st.columns(2)
    mode_maint = col_sel1.radio("Période :", ["À ce jour", "Année Complète"], horizontal=True)
    sel_y = col_sel2.selectbox("Année :", [2025, 2026, 2027], index=1)

    # 5. GESTION DU TABLEAU (MODIFICATION & SUPPRESSION)
    if not df_m.empty:
        # Tri et filtrage
        df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_filtre = df_m[df_m['dt_maint'].dt.year == sel_y].copy()
        
        if mode_maint == "À ce jour":
            df_filtre = df_filtre[df_filtre['dt_maint'] <= pd.Timestamp.now().normalize()].copy()

        df_filtre = df_filtre.sort_values('dt_maint', ascending=False)

        st.subheader(f"📋 Suivi Maintenance {sel_y}")
        
        edited_df = st.data_editor(
            df_filtre.drop(columns=['dt_maint']),
            column_config={
                "Date": st.column_config.TextColumn("Date"),
                "Objet": st.column_config.TextColumn("Désignation"),
                "M_Num": st.column_config.NumberColumn("€", format="%.2f"),
                "Statut": st.column_config.SelectboxColumn("Etat", options=["À prévoir", "Fait"]),
                "Type": st.column_config.SelectboxColumn("Cat", options=["Port", "Assurances", "Maintenance", "Sécurité", "Autres"])
            },
            hide_index=False,
            use_container_width=True,
            num_rows="dynamic",
            key="maint_editor_final"
        )
        
        if st.button("💾 ENREGISTRER LES MODIFICATIONS DU TABLEAU", type="primary", use_container_width=True):
            df_non_affiches = df_m[~df_m.index.isin(df_filtre.index)].drop(columns=['dt_maint'], errors='ignore')
            df_final_save = pd.concat([df_non_affiches, edited_df], ignore_index=True)
            sauvegarder_data(df_final_save, 'maintenance.json')
            st.success("✅ Données sauvegardées")
            st.rerun()

    # 6. FORMULAIRE D'AJOUT RAPIDE (HORS VIDANGE)
    st.write("---")
    with st.expander("➕ AJOUTER UN AUTRE TRAVAIL OU FRAIS"):
        with st.form("form_add_maint", clear_on_submit=True):
            f_obj = st.text_input("Désignation")
            c1, c2 = st.columns(2)
            f_d = c1.date_input("Date", datetime.now())
            f_m = c2.number_input("Montant (€)", min_value=0.0)
            
            c3, c4 = st.columns(2)
            f_t = c3.selectbox("Catégorie", ["Port", "Assurances", "Maintenance", "Sécurité", "Autres"], index=2)
            f_s = c4.selectbox("Statut", ["À prévoir", "Fait"], index=1)
            
            if st.form_submit_button("💾 AJOUTER"):
                new_row = {"Date": f_d.strftime("%d/%m/%Y"), "Objet": f_obj, "M_Num": f_m, "Statut": f_s, "Type": f_t}
                df_final = pd.concat([df_m.drop(columns=['dt_maint'], errors='ignore'), pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_final, 'maintenance.json')
                st.rerun()

# --- EXPORT EXCEL (À PLACER TOUT EN BAS DU BLOC MAINTENANCE) ---
    if not df_m.empty:
        import io
        
        # On définit un nom de fichier par défaut au cas où
        nom_annee = sel_y if 'sel_y' in locals() else "Historique"
        
        df_export = df_m.drop(columns=['dt_maint'], errors='ignore').copy()
        
        buffer = io.BytesIO()
        try:
            # Utilisation de openpyxl (moteur standard de Streamlit)
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Maintenance')
            
            st.write("---") # Une petite ligne de séparation visuelle
            st.download_button(
                label="📥 Télécharger le suivi (Excel)",
                data=buffer.getvalue(),
                file_name=f"Maintenance_Vesta_{nom_annee}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erreur export : {e}")



# =================================================================
# --- PAGE : FACTURATION & SUIVI PAIEMENTS (FACT) ---
# =================================================================
if st.session_state.page == "FACT":
    st.title("📑 Facturation & Suivi")
    df_f = charger_data_safe('contacts.json')

    if df_f.empty:
        st.warning("Aucune donnée de facturation trouvée.")
    else:
        for col in ['Prix', 'Acompte', 'Jours', 'Pers']:
            if col in df_f.columns:
                df_f[col] = pd.to_numeric(df_f[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        col_f1, col_f2 = st.columns(2)
        filtre_paye = col_f1.selectbox("Filtrer par paiement", ["Tous", "Paid", "Unpaid"])
        search_nom = col_f2.text_input("Rechercher un client", "").lower()

        df_visu = df_f.copy()
        if filtre_paye != "Tous":
            df_visu = df_visu[df_visu['Paiement'] == filtre_paye]
        if search_nom:
            df_visu = df_visu[df_visu['Nom'].str.lower().str.contains(search_nom, na=False)]

        df_visu['dt_tri'] = pd.to_datetime(df_visu['DateNav'], dayfirst=True, errors='coerce')
        df_visu = df_visu.sort_values('dt_tri', ascending=False)

        total_du = df_visu['Prix'].sum()
        total_recu = df_visu['Acompte'].sum()
        reste_a_percevoir = total_du - total_recu

        c1, c2, c3 = st.columns(3)
        c1.metric("CA Total", f"{total_du:,.2f} €")
        c2.metric("Encaissé", f"{total_recu:,.2f} €")
        c3.metric("Reste", f"{reste_a_percevoir:,.2f} €")

        st.divider()

        for idx, r in df_visu.iterrows():
            solde = r['Prix'] - r['Acompte']
            is_paid = r['Paiement'] == "Paid"
            color_border = "#2e7d32" if is_paid else "#d32f2f"
            bg_label = "rgba(46, 125, 50, 0.1)" if is_paid else "rgba(211, 47, 47, 0.1)"
            status_text = "✅ PAYÉ" if is_paid else "⏳ EN ATTENTE"

            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 12px; border-radius: 10px; margin-bottom: 8px; border-left: 10px solid {color_border}; background: white;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div><b>{r['Nom']} {r['Prénom']}</b><br><small>📅 {r['DateNav']} | 🏢 {r.get('Société', 'PERSO')}</small></div>
                        <div style="text-align: right;"><span style="background: {bg_label}; color: {color_border}; padding: 4px 8px; border-radius: 5px; font-weight: bold;">{status_text}</span><br><b>{solde:,.2f} €</b></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            ca, cb, cc = st.columns([2, 2, 6])
            if not is_paid:
                if ca.button("💰 PAYÉ", key=f"pay_{idx}"):
                    df_f.at[idx, 'Paiement'] = "Paid"
                    df_f.at[idx, 'Acompte'] = df_f.at[idx, 'Prix']
                    sauvegarder_data(df_f, 'contacts.json')
                    st.rerun()
            if cb.button("✏️ Modifier", key=f"edit_f_{idx}"):
                st.session_state.contact_edit_idx = idx
                st.session_state.page = "CONTACTS"
                st.rerun()

# =================================================================
# --- 11. PAGE ARCHIVES ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    st.title("📂 Archives")
    if st.button("⬅️ Retour au Planning"):
        st.session_state.page = "PLANNING"
        st.rerun()

    t1, t2, t3 = st.tabs(["🛠️ Frais", "📅 Planning", "📖 Logbook"])
    with t1: st.dataframe(charger_data_safe('archives_maintenance.json'), use_container_width=True)
    with t2: st.dataframe(charger_data_safe('archives_planning.json'), use_container_width=True)
    with t3: st.dataframe(charger_data_safe('archives_logbook.json'), use_container_width=True)

# =================================================================
# --- 12. PAGE LIVRE DE BORD (LOG) - VERSION CROISIÈRE ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#1a2a6c; color:white; padding:10px; border-radius:10px;"><h1>📖 Livre de Bord</h1></div>', unsafe_allow_html=True)

    # 1. CHARGEMENT DES DONNÉES
    df_log = charger_data_safe('logbook.json')
    
    # 2. RÉCUPÉRATION DES DERNIERS COMPTEURS
    last_h, last_m = 0.0, 0.0
    if not df_log.empty:
        try:
            last_h = float(df_log['MotArr'].max())
            last_m = float(df_log['MilArr'].max())
        except: pass

    # 3. FORMULAIRE NOUVELLE NAVIGATION
    with st.expander("🚀 Enregistrer une Navigation", expanded=False):
        c1, c2, c3 = st.columns([2, 1, 2])
        f_date = c1.date_input("Date de départ", datetime.now())
        f_jours = c2.number_input("Nombre de jours", min_value=1, value=1, step=1)
        f_titre = c3.text_input("Destination / Nom de la croisière")
        f_notes = st.text_area("Notes de navigation", height=70)

        n_lignes = int(f_jours)

        if 'temp_log_df' not in st.session_state or len(st.session_state.temp_log_df) != n_lignes:
            lignes = []
            for i in range(n_lignes):
                date_etape = (f_date + timedelta(days=i)).strftime("%d/%m/%Y")
                lignes.append({
                    "Date": date_etape, "Port": "", 
                    "Mot_Dep": last_h if i == 0 else 0.0, "Mot_Arr": 0.0, 
                    "Mil_Dep": last_m if i == 0 else 0.0, "Mil_Arr": 0.0, "Voile": 0.0
                })
            st.session_state.temp_log_df = pd.DataFrame(lignes)
        else:
            for i in range(len(st.session_state.temp_log_df)):
                st.session_state.temp_log_df.at[i, "Date"] = (f_date + timedelta(days=i)).strftime("%d/%m/%Y")

        edited_steps = st.data_editor(
            st.session_state.temp_log_df,
            column_config={
                "Date": st.column_config.TextColumn("Date", disabled=True),
                "Port": "📍 Arrivée", "Mot_Dep": "Mtr Dép", "Mot_Arr": "Mtr Arr",
                "Mil_Dep": "Mil Dép", "Mil_Arr": "Mil Arr", "Voile": "⛵ Voile"
            },
            num_rows="dynamic", use_container_width=True, key="log_editor_v2026"
        )

        if st.button("💾 ENREGISTRER TOUTE LA NAVIGATION", type="primary", use_container_width=True):
            if edited_steps is not None and not edited_steps.empty:
                nouvelles = []
                for i, row in edited_steps.iterrows():
                    if row.get("Port"):
                        h_d, h_a = float(row.get("Mot_Dep", 0.0)), float(row.get("Mot_Arr", 0.0))
                        m_d, m_a = float(row.get("Mil_Dep", 0.0)), float(row.get("Mil_Arr", 0.0))
                        nouvelles.append({
                            "Date": row.get("Date"),
                            "Navigation": f_titre or "Navigation libre",
                            "PortArr": row.get("Port"),
                            "MotDep": h_d, "MotArr": h_a,
                            "TotalMot": round(h_a - h_d, 2),
                            "MilDep": m_d, "MilArr": m_a,
                            "TotalMil": round(m_a - m_d, 1),
                            "H_Voile": float(row.get("Voile", 0.0)),
                            "Notes": f_notes,
                            "Jours": n_lignes  # On stocke l'info ici pour la différenciation
                        })
                
                if nouvelles:
                    df_final = pd.concat([df_log, pd.DataFrame(nouvelles)], ignore_index=True)
                    sauvegarder_data(df_final, 'logbook.json')
                    if 'temp_log_df' in st.session_state: del st.session_state.temp_log_df
                    st.rerun()

    # 4. AFFICHAGE DE L'HISTORIQUE (DISTINCTION VISUELLE FORTE)
    if not df_log.empty:
        st.divider()
        df_visu = df_log.copy()
        df_visu['dt_sort'] = pd.to_datetime(df_visu['Date'], dayfirst=True, errors='coerce')
        df_visu = df_visu.sort_values(by='dt_sort', ascending=False)

        for idx, row in df_visu.iterrows():
            n_j = int(row.get('Jours', 1))
            
            if n_j > 1:
                # --- AFFICHAGE "CROISIÈRE" (Grande Fiche) ---
                try:
                    d_start = datetime.strptime(row['Date'], "%d/%m/%Y")
                    d_end = d_start + timedelta(days=n_j-1)
                    date_txt = f"Du {d_start.strftime('%d/%m')} au {d_end.strftime('%d/%m/%Y')}"
                except: date_txt = row['Date']

                st.markdown(f"""
                    <div style="background:#1a2a6c; color:white; padding:15px; border-radius:10px; margin-bottom:15px; border-left: 10px solid #f1c40f;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="letter-spacing: 2px; font-weight: bold;">🚢 CROISIÈRE DE {n_j} JOURS</span>
                            <span style="background:#f1c40f; color:#1a2a6c; padding:2px 10px; border-radius:15px; font-weight:bold; font-size:0.8rem;">ID: {idx}</span>
                        </div>
                        <div style="margin-top:10px; display: flex; justify-content: space-between;">
                            <div>
                                <span style="font-size: 1.4rem; font-weight: bold;">{date_txt}</span><br>
                                <span style="font-size: 1.1rem; opacity: 0.9;">📍 Arrivée : {row['PortArr']}</span><br>
                                <i style="font-size: 0.9rem; opacity: 0.7;">{row['Navigation']}</i>
                            </div>
                            <div style="text-align: right;">
                                <span style="font-size: 1.8rem; font-weight: bold; color: #f1c40f;">{row['TotalMil']} NM</span><br>
                                <span style="font-size: 1rem;">⚙️ {row['TotalMot']}h moteur</span>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            
            else:
                # --- AFFICHAGE "SORTIE JOURNÉE" (Ligne Simple Compacte) ---
                st.markdown(f"""
                    <div style="background:white; border:1px solid #dee2e6; padding:8px 15px; border-radius:5px; margin-bottom:5px; display: flex; justify-content: space-between; align-items:center;">
                        <div style="flex: 1; border-right: 2px solid #eee;">
                            <b style="color:#2c3e50;">{row['Date']}</b>
                        </div>
                        <div style="flex: 2; padding-left:15px;">
                            <span style="font-weight:bold;">⚓ {row['PortArr']}</span> 
                            <span style="color:#7f8c8d; font-size:0.8rem; margin-left:10px;">({row['Navigation']})</span>
                        </div>
                        <div style="flex: 1; text-align: right; font-weight: bold; color:#27ae60;">
                            {row['TotalMil']} NM
                        </div>
                        <div style="margin-left:15px; background:#f8f9fa; padding:2px 8px; border-radius:4px; font-size:0.7rem; color:#95a5a6;">
                            ID: {idx}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # 5. GESTION ADMINISTRATIVE (MODIFIER/SUPPRIMER)
        with st.expander("🛠️ Administration de l'historique"):
            df_admin = df_visu.copy()
            df_admin.insert(0, 'ID', df_admin.index)
            st.dataframe(df_admin[['ID', 'Date', 'PortArr', 'TotalMil']], use_container_width=True, hide_index=True)
            
            sel_id = st.number_input("Entrer l'ID pour modifier/supprimer", min_value=0, max_value=int(df_admin.index.max()), step=1)
            
            if st.button("🗑️ SUPPRIMER CETTE LIGNE", use_container_width=True):
                df_log = df_log.drop(index=sel_id).reset_index(drop=True)
                sauvegarder_data(df_log, 'logbook.json')
                st.rerun()



# --- FIN DU FICHIER ---









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































