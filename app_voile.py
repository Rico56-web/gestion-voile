import requests, base64, json, time, os, html, io
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
from datetime import datetime, date, timedelta
import calendar
import streamlit.components.v1 as components

def bouton_imprimer_fiche(date, contenu, statut):
    # Prépare le contenu HTML pour l'impression
    html_content = f"""
    <html>
    <head><title>Impression Note - Vesta Skipper</title></head>
    <body style='font-family: sans-serif;'>
        <h1>Note du {date}</h1>
        <p><b>Statut :</b> {statut}</p>
        <hr>
        <pre style='font-size: 1.2rem;'>{contenu}</pre>
    </body>
    </html>
    """
    # Ce script ouvre une fenêtre et lance l'impression
    js = f"""
    <script>
    function printNote() {{
        var win = window.open('', '', 'height=500, width=500');
        win.document.write({repr(html_content)});
        win.document.close();
        win.print();
    }}
    </script>
    <button onclick="printNote()" style="padding: 5px 10px; border-radius: 5px; cursor: pointer; background: #f0f2f6; border: 1px solid #d1d5db;">
        🖨️ Imprimer la fiche
    </button>
    """
    components.html(js, height=45)

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
import shutil
import os

def executer_backup_auto():
    """Crée une copie de sécurité des fichiers vitaux s'ils existent."""
    fichiers_a_sauver = ['contacts.json', 'maintenance.json', 'logbook.json']
    
    # Créer un dossier backup s'il n'existe pas
    if not os.path.exists('backups'):
        os.makedirs('backups')
        
    for fichier in fichiers_a_sauver:
        if os.path.exists(fichier):
            # On crée une copie dans le dossier backups
            shutil.copy2(fichier, f"backups/{fichier}.bak")

# --- APPEL DE LA FONCTION ---
# À placer tout au début de ton code principal (après le st.set_page_config)
executer_backup_auto()
#===============================================================
# --- CHARGEMENT ET TRI GLOBAL (À placer en haut de votre script) ---
df = charger_data_safe('contacts.json')

if not df.empty:
    # 1. On crée une clé de tri invisible YYYYMMDD
    def create_sort_key(d):
        try:
            p = str(d).split('/')
            return f"{p[2]}{p[1]}{p[0]}" # ex: 20260525
        except: return "00000000"

    df['tmp_sort'] = df['DateNav'].apply(create_sort_key)
    
    # 2. On trie du plus récent au plus ancien
    df = df.sort_values(by='tmp_sort', ascending=False).reset_index(drop=True)
    
    # 3. On nettoie pour ne pas polluer le reste du code
    df = df.drop(columns=['tmp_sort'])
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

# --- BARRE DE NAVIGATION HARMONISÉE ---
menu = ["PLANNING", "CONTACTS", "STATS", "MAINT", "LOG", "NOTES", "FACT"]
icones = {
    "PLANNING": "📅", "CONTACTS": "👤", "STATS": "📊", 
    "MAINT": "🛠️", "LOG": "📖", "NOTES": "📝", "FACT": "📑"
}

cols_nav = st.columns(len(menu))
for i, name in enumerate(menu):
    # ICI : On s'assure que si on clique sur "NOTES", la page devient "MEMOS"
    # Et si on clique sur "FACT", la page devient "FACT"
    target = "MEMOS" if name == "NOTES" else name
    
    is_active = st.session_state.page == target
    if cols_nav[i].button(f"{icones[name]}\n{name}", key=f"nav_{name}", use_container_width=True, type="primary" if is_active else "secondary"):
        st.session_state.page = target
        st.rerun()
st.divider()
# =================================================================
# --- 2. MENU MÉMOS (VERSION FINALE) ---
# =================================================================
if st.session_state.page == "MEMOS":
    st.markdown("<h2 style='text-align: center; color: #34495E;'>⚓ Mémos & Check-lists de Bord</h2>", unsafe_allow_html=True)
    
    df_memos = charger_data_safe('memos.json')

    # Initialisation de l'état d'édition si absent
    if 'memo_edit_id' not in st.session_state: 
        st.session_state.memo_edit_id = None

    # --- A. AJOUT NOUVELLE NOTE ---
    with st.expander("➕ CRÉER UNE NOUVELLE CHECK-LIST", expanded=df_memos.empty):
        with st.form("new_memo_form"):
            c1, c2 = st.columns(2)
            m_date = c1.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
            m_urg = c2.selectbox("Urgence", ["Normal", "Urgent"])
            m_txt = st.text_area("Contenu (une ligne par tâche)")
            if st.form_submit_button("💾 ENREGISTRER"):
                if m_txt.strip():
                    new_r = pd.DataFrame([{"Date": m_date, "Description": m_txt, "Statut": m_urg, "Paiement": "N/A", "Archive": "Non Archivé"}])
                    df_memos = pd.concat([df_memos, new_r], ignore_index=True)
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()

    # --- B. AFFICHAGE DES FICHES ---
    df_show = df_memos[df_memos['Archive'] == "Non Archivé"]
    
    for idx, row in df_show.sort_index(ascending=False).iterrows():
        stat_val = str(row.get('Statut', 'Normal'))
        pay_val = str(row.get('Paiement', 'N/A'))

        # --- CAS 1 : FORMULAIRE DE MODIFICATION (SI SÉLECTIONNÉ) ---
        if st.session_state.memo_edit_id == idx:
            with st.container():
                st.info(f"Édition de la note du {row['Date']}")
                with st.form(key=f"form_edit_{idx}"):
                    e_desc = st.text_area("Description", value=row['Description'], height=150)
                    c1, c2 = st.columns(2)
                    e_pay = c1.selectbox("Paiement", ["N/A", "À Payer", "Payé"], index=0)
                    e_stat = c2.selectbox("Statut", ["Normal", "Urgent", "Fait"], index=0)
                    
                    cb1, cb2 = st.columns(2)
                    if cb1.form_submit_button("✅ VALIDER"):
                        df_memos.at[idx, 'Description'] = e_desc
                        df_memos.at[idx, 'Paiement'] = e_pay
                        df_memos.at[idx, 'Statut'] = e_stat
                        sauvegarder_data(df_memos, 'memos.json')
                        st.session_state.memo_edit_id = None
                        st.rerun()
                    if cb2.form_submit_button("❌ ANNULER"):
                        st.session_state.memo_edit_id = None
                        st.rerun()

        # --- CAS 2 : AFFICHAGE NORMAL (AVEC BOUTON MODIFIER) ---
        else:
            if stat_val == "Urgent": h_c, bg_c = "#E74C3C", "#FDEDEC" 
            elif stat_val == "Fait": h_c, bg_c = "#27AE60", "#EAFAF1"
            else: h_c, bg_c = "#2980B9", "#EBF5FB"

            st.markdown(f"""
                <div style="background-color:{bg_c}; border-left: 10px solid {h_c}; padding: 15px; border-radius: 10px;">
                    <span style="font-weight: bold;">📅 {row['Date']} | 💰 {pay_val}</span>
                </div>
            """, unsafe_allow_html=True)

            # Liste interactive (Checkbox)
            lignes = str(row.get('Description', '')).split('\n')
            data_tasks = [{"Fait": l.startswith("✅ | "), "Tâche": l.replace("✅ | ", "").replace("❌ | ", "")} for l in lignes if l.strip()]
            
            if data_tasks:
                edited_df = st.data_editor(pd.DataFrame(data_tasks), key=f"ed_{idx}", hide_index=True, use_container_width=True)
                if not edited_df.equals(pd.DataFrame(data_tasks)):
                    new_desc = "\n".join([f"{'✅ | ' if r['Fait'] else ''}{r['Tâche']}" for _, r in edited_df.iterrows()])
                    df_memos.at[idx, 'Description'] = new_desc
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()

            # --- BARRE D'OUTILS (C'est ici que se trouve le bouton Modifier) ---
            cols = st.columns(4)
            if cols[0].button("✏️ Modifier", key=f"btn_edit_{idx}"):
                st.session_state.memo_edit_id = idx
                st.rerun()
                
            if cols[1].button("📦 Archiver", key=f"btn_arch_{idx}"):
                df_memos.at[idx, 'Archive'] = "Archivé"
                sauvegarder_data(df_memos, 'memos.json')
                st.rerun()
            
            with cols[2]:
                bouton_imprimer_fiche(row['Date'], row['Description'], stat_val)

            # Suppression simple ou double confirmation
            if cols[3].button("🗑️ Suppr", key=f"btn_del_{idx}"):
                df_memos = df_memos.drop(idx).reset_index(drop=True)
                sauvegarder_data(df_memos, 'memos.json')
                st.rerun()
            
            st.divider()
# =================================================================
# --- 5. BLOC CONTACTS (V108 - AFFICHAGE COMPLET & SÉCURITÉ) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    from datetime import datetime
    import pandas as pd

    # --- CHARGEMENT DES DONNÉES ---
    df_raw = charger_data('contacts.json')
    
    # --- NAVIGATION ---
    n1, n2, n3, n4, n5 = st.columns([1, 1, 1, 1, 1.5])
    if n1.button("🟢 EN COURS", use_container_width=True, type="primary" if st.session_state.vue_contact == "En cours" else "secondary"): 
        st.session_state.vue_contact = "En cours"; st.rerun()
    if n2.button("⏳ DEMANDES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Attente" else "secondary"): 
        st.session_state.vue_contact = "Attente"; st.rerun()
    if n3.button("⭐ HABITUÉS", use_container_width=True, type="primary" if st.session_state.vue_contact == "Relances" else "secondary"): 
        st.session_state.vue_contact = "Relances"; st.rerun()
    if n4.button("✅ ARCHIVES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Archives" else "secondary"): 
        st.session_state.vue_contact = "Archives"; st.rerun()
    with n5: bouton_export_excel(df_raw, "Planning_Vesta_2026")

    st.divider()

    if not df_raw.empty:
        df_c = df_raw.copy().fillna("")
        df_c['orig_idx'] = df_c.index
        df_c['dt_sort'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
        
        # --- FILTRES & RECHERCHE ---
        c_search, c_yr, c_new = st.columns([2, 1, 1])
        search = c_search.text_input("🔍 Rechercher...", "", key="search_bar_contacts").upper()
        annee_sel = c_yr.selectbox("Saison", [2025, 2026, 2027], index=1)
        
        # --- 📈 DASHBOARD FINANCIER ---
        mask_ca = (df_c['dt_sort'].dt.year == annee_sel) & (~df_c['Statut'].str.lower().str.contains("annule|refuse"))
        df_ca = df_c[mask_ca]
        total_prevu = df_ca['Prix'].apply(to_f).sum()
        total_encaisse = df_ca['Acompte'].apply(to_f).sum()
        
        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.metric(f"CA Prévu {annee_sel}", f"{int(total_prevu)} €")
        col_f2.metric("Acomptes encaissés", f"{int(total_encaisse)} €")
        col_f3.metric("Reste à percevoir", f"{max(0, int(total_prevu - total_encaisse))} €")
        st.divider()

        if c_new.button("➕ NOUVEAU CLIENT", use_container_width=True):
            new_r = {"Prénom": "NOUVEAU", "Nom": "CLIENT", "Statut": "En attente", "Paiement": "Unpaid", "Relancer": "Non", "DateNav": f"01/06/{annee_sel}", "Société": "PERSO", "Jours": 1, "Prix": 0, "Acompte": 0, "Notes": "", "Téléphone": "", "Email": "", "Pers": 1}
            df_new = pd.concat([pd.DataFrame([new_r]), df_raw], ignore_index=True)
            sauvegarder_data(df_new, 'contacts.json'); st.session_state.edit_idx = 0; st.session_state.page = "MODIFIER_CONTACT"; st.rerun()

        # --- LOGIQUE ONGLETS ---
        statut_clean = df_c['Statut'].str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        rel_clean = df_c['Relancer'].fillna("Non").str.upper()
        
        if st.session_state.vue_contact == "Archives": mask_aff = (statut_clean.str.contains("termine|annule|refuse")) & (rel_clean != "OUI")
        elif st.session_state.vue_contact == "Relances": mask_aff = (rel_clean == "OUI")
        elif st.session_state.vue_contact == "Attente": mask_aff = (statut_clean == "liste d'attente")
        else: mask_aff = ~(statut_clean.str.contains("termine|annule|refuse")) & (statut_clean != "liste d'attente")

        df_aff = df_c[mask_aff & ((df_c['dt_sort'].dt.year == annee_sel) | (df_c['dt_sort'].isna()))].copy()
        if search: df_aff = df_aff[df_aff['Nom'].str.contains(search) | df_aff['Prénom'].str.contains(search) | df_aff['Société'].str.contains(search)]
        df_aff = df_aff.sort_values(by='dt_sort', ascending=True)

        # --- BOUCLE FICHES ---
        for _, row in df_aff.iterrows():
            idx = row['orig_idx']
            p_tot = to_f(row.get('Prix', 0))
            p_aco = to_f(row.get('Acompte', 0))
            nb_jours = row.get('Jours', 1)
            nb_pers = row.get('Pers', 1)
            
            # Design Fiche
            soc = str(row.get('Société', 'PERSO')).upper()
            colors = {"CMN": ("#2980B9", "#EBF5FB"), "CLICK": ("#27AE60", "#EAFAF1"), "VOG": ("#8E44AD", "#F5EEF8"), "PERSO": ("#F1C40F", "#FEF9E7")}
            border_col, bg_card = colors.get(soc, ("#7F8C8D", "#FDFEFE"))
            badge_vip = "⭐ " if str(row.get('Relancer', 'Non')).upper() == "OUI" else ""

            # Affichage enrichi (Prix, Acompte, Jours, Personnes)
            st.markdown(f"""
            <div style="background:{bg_card}; padding:15px; border-radius:12px; border-left:10px solid {border_col}; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); margin-bottom:10px; color: black;">
                <div style="display:flex; justify-content:space-between;">
                    <b>{badge_vip}{row['Prénom']} {row['Nom']}</b>
                    <span style="font-size:0.8rem; font-weight:bold; color:{border_col};">{soc}</span>
                </div>
                <div style="margin-top:5px; font-size:0.9rem;">
                    📅 {row['DateNav'] if row['DateNav'] else 'Date à définir'} | 👥 {int(nb_pers)} pers. | ⏱️ {nb_jours} j.<br>
                    💰 <b>Total: {int(p_tot)}€</b> | 💳 Acompte: {int(p_aco)}€ | 📉 <b>Reste: {int(p_tot-p_aco)}€</b>
                </div>
                <div style="font-style:italic; font-size:0.8rem; color:gray; margin-top:5px;">Statut: {row['Statut']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- ACTIONS ---
            c1, c2, c3 = st.columns(3)
            if c1.button("✏️ ÉDITER", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "MODIFIER_CONTACT"; st.rerun()

            if st.session_state.vue_contact == "Relances":
                if c2.button("🔄 RE-RÉSERVER", key=f"dup_{idx}", use_container_width=True):
                    df_db = charger_data('contacts.json')
                    new_e = row.to_dict()
                    new_e.update({"DateNav": datetime.now().strftime("%d/%m/%Y"), "Statut": "En attente", "Paiement": "Unpaid", "Prix": 0, "Acompte": 0, "Notes": "Habitué - Nouvelle résa"})
                    for k in ['orig_idx', 'dt_sort']: new_e.pop(k, None)
                    df_db = pd.concat([pd.DataFrame([new_e]), df_db], ignore_index=True)
                    sauvegarder_data(df_db, 'contacts.json'); st.session_state.edit_idx = 0; st.session_state.page = "MODIFIER_CONTACT"; st.rerun()
            else:
                if f"confirm_del_{idx}" not in st.session_state:
                    if c2.button("🗑️ SUPPRIMER", key=f"del_{idx}", use_container_width=True):
                        st.session_state[f"confirm_del_{idx}"] = True; st.rerun()
                else:
                    st.warning("Confirmer ?")
                    cx, cy = st.columns(2)
                    if cx.button("✅ OUI", key=f"y_{idx}", use_container_width=True):
                        df_db = charger_data('contacts.json').drop(idx).reset_index(drop=True)
                        sauvegarder_data(df_db, 'contacts.json'); del st.session_state[f"confirm_del_{idx}"]; st.rerun()
                    if cy.button("❌ NON", key=f"n_{idx}", use_container_width=True):
                        del st.session_state[f"confirm_del_{idx}"]; st.rerun()

            if st.session_state.vue_contact == "En cours" and c3.button("🏁 FINIR", key=f"fin_{idx}", use_container_width=True):
                df_all = charger_data('contacts.json')
                df_all.loc[idx, ['Statut', 'Paiement']] = ["Terminé", "Paid"]
                sauvegarder_data(df_all, 'contacts.json'); st.rerun()

# ===============================================================
# --- 6. PAGE MODIFIER CONTACT : VERSION COMPLÈTE (V110) ---
# =================================================================
if st.session_state.page == "MODIFIER_CONTACT":
    st.markdown('<h3 style="text-align:center;">✏️ Modifier le Contact</h3>', unsafe_allow_html=True)
    
    idx_to_edit = st.session_state.get('edit_idx')
    df_m = charger_data('contacts.json') # Utilisation de ta fonction standard

    if idx_to_edit is not None and not df_m.empty and idx_to_edit in df_m.index:
        row = df_m.loc[idx_to_edit]
        
        with st.form("form_edit_v2026"):
            # --- Ligne 1 : Identité ---
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=str(row.get('Prénom', '')))
            new_nom = c2.text_input("Nom", value=str(row.get('Nom', '')))
            
            # --- Ligne 2 : Logistique (Dates, Jours, Pers) ---
            c3, c4, c5, c6 = st.columns([2, 1, 1, 1])
            new_date = c3.text_input("Date (JJ/MM/AAAA)", value=str(row.get('DateNav', '')))
            
            # Récupération sécurisée des numériques (float ou int)
            try: val_jours = float(row.get('Jours', 1.0))
            except: val_jours = 1.0
            try: val_pers = int(float(row.get('Pers', 1.0)))
            except: val_pers = 1
                
            new_jours = c4.number_input("Jours", value=val_jours, step=0.5)
            new_pers = c5.number_input("Pers.", value=val_pers, step=1)
            
            liste_soc = ["PERSO", "CLICK", "CMN", "VOG"]
            curr_soc = str(row.get('Société', 'PERSO')).upper().strip()
            soc_idx = liste_soc.index(curr_soc) if curr_soc in liste_soc else 0
            new_soc = c6.selectbox("Société", liste_soc, index=soc_idx)
            
            # --- Ligne 3 : Statuts ---
            s1, s2, s3 = st.columns([2, 1, 1])
            s_list = ["En attente", "Confirmé", "Liste d'attente", "Terminé", "Annulé", "Refusé"]
            curr_s = str(row.get('Statut', 'En attente')).strip()
            
            # On cherche l'index exact ou approchant
            if curr_s in s_list: s_idx = s_list.index(curr_s)
            else: s_idx = next((i for i, s in enumerate(s_list) if s.lower() in curr_s.lower()), 0)
            
            new_statut = s1.selectbox("Statut Mission", s_list, index=s_idx)
            
            p_list = ["Unpaid", "Paid", "Acompte OK"]
            curr_p = str(row.get('Paiement', 'Unpaid'))
            p_idx = p_list.index(curr_p) if curr_p in p_list else 0
            new_pay = s2.selectbox("Paiement", p_list, index=p_idx)
            
            val_r = str(row.get('Relancer', 'Non')).strip().capitalize()
            new_relance = s3.selectbox("Habitué ?", ["Non", "Oui"], index=1 if val_r == "Oui" else 0)

            # --- Ligne 4 : Finances ---
            f1, f2, f3 = st.columns(3)
            try: val_prix = int(float(row.get('Prix', 0)))
            except: val_prix = 0
            try: val_acompte = int(float(row.get('Acompte', 0)))
            except: val_acompte = 0
                
            new_prix = f1.number_input("Prix Total (€)", value=val_prix)
            new_acompte = f2.number_input("Acompte encaissé (€)", value=val_acompte)
            f3.markdown(f"<br><b style='color:gray;'>Reste : {new_prix - new_acompte} €</b>", unsafe_allow_html=True)

            # --- Ligne 5 : Contact & Notes ---
            new_tel = st.text_input("Téléphone", value=str(row.get('Téléphone', '')))
            new_mail = st.text_input("Email", value=str(row.get('Email', '')))
            new_notes = st.text_area("Notes", value=str(row.get('Notes', '')))

            # --- Validation ---
            if st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True):
                df_m.at[idx_to_edit, 'Prénom'] = new_pre.upper()
                df_m.at[idx_to_edit, 'Nom'] = new_nom.upper()
                df_m.at[idx_to_edit, 'DateNav'] = new_date
                df_m.at[idx_to_edit, 'Jours'] = new_jours
                df_m.at[idx_to_edit, 'Pers'] = new_pers
                df_m.at[idx_to_edit, 'Société'] = new_soc
                df_m.at[idx_to_edit, 'Statut'] = new_statut
                df_m.at[idx_to_edit, 'Paiement'] = new_pay
                df_m.at[idx_to_edit, 'Relancer'] = new_relance
                df_m.at[idx_to_edit, 'Prix'] = new_prix
                df_m.at[idx_to_edit, 'Acompte'] = new_acompte
                df_m.at[idx_to_edit, 'Téléphone'] = new_tel
                df_m.at[idx_to_edit, 'Email'] = new_mail
                df_m.at[idx_to_edit, 'Notes'] = new_notes
                
                sauvegarder_data(df_m, 'contacts.json')
                st.success("✅ Modifications enregistrées !")
                st.session_state.page = "CONTACTS"
                st.rerun()

    else:
        st.error("Erreur de chargement du contact.")
        if st.button("🔄 Retour"):
            st.session_state.page = "CONTACTS"
            st.rerun()

    if st.button("⬅️ ANNULER ET RETOUR"):
        st.session_state.page = "CONTACTS"
        st.rerun()
# =================================================================
# --- 6. PAGE PLANNING (V19.2 - CALIBRÉ SUR TON LOGBOOK) ---
# =================================================================
if st.session_state.page == "PLANNING":
    # --- 1. DASHBOARD VIGIE : CROUESTY ---
    st.markdown("## ⚓ Tableau de Bord - Port Crouesty")

    # Widget Météo Windy (Version Embed autorisée)
    st.markdown("""
        <iframe 
            width="100%" 
            height="350" 
            src="https://www.windy.com/embed2.html?lat=47.545&lon=-2.894&detailLat=47.545&detailLon=-2.894&width=650&height=350&zoom=10&level=surface&overlay=wind&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=kt&metricTemp=%C2%B0C&radarRange=-1" 
            frameborder="0">
        </iframe>
    """, unsafe_allow_html=True)
    

    col_v1, col_v2, col_v3 = st.columns(3)
    
    # --- A. ALERTE MAINTENANCE (MOTARR) ---
    df_log = charger_data_safe('logbook.json')
    derniere_heure = 0
    if not df_log.empty:
        # On ignore les lignes à 0.0 pour avoir le vrai dernier relevé
        df_valid = df_log[df_log['MotArr'] > 0]
        if not df_valid.empty:
            derniere_heure = to_f(df_valid['MotArr'].max())
        else:
            derniere_heure = to_f(df_log['MotArr'].max())
    
    # Récupération du seuil (ex: 100h)
    params = charger_params()
    seuil_v = params.get('prochaine_vidange', 100)
    heures_restantes = seuil_v - (derniere_heure % seuil_v) if seuil_v > 0 else 0
    
    if heures_restantes < 15:
        col_v1.error(f"🛠️ Vidange : {heures_restantes:.1f}h !")
    else:
        col_v1.success(f"⚙️ Moteur : {derniere_heure:.1f}h OK")

    # --- B. FACTURATION EN ATTENTE ---
    df_f = charger_data_safe('contacts.json')
    nb_unpaid = 0
    if not df_f.empty and 'Paiement' in df_f.columns:
        nb_unpaid = len(df_f[df_f['Paiement'] == "Unpaid"])
    col_v2.metric("Factures Unpaid", f"{nb_unpaid}", delta=f"{nb_unpaid}" if nb_unpaid > 0 else "OK", delta_color="inverse")

    # --- C. MARÉES ---
    col_v3.link_button("🌊 Marées Crouesty", "https://maree.info/104", use_container_width=True)
    
    st.divider()

    # --- 2. HEADER PLANNING ---
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING DES SORTIES</h1></div>', unsafe_allow_html=True)
    
    if st.button("📂 ACCÉDER AUX ARCHIVES", key="k_arch_p", use_container_width=True):
        st.session_state.last_page = "PLANNING"
        st.session_state.page = "ARCHIVES"
        st.rerun()

    st.divider()

    # --- 3. INITIALISATION TEMPORELLE & SÉLECTEURS ---
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
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

    # --- 4. TRAITEMENT DES DONNÉES ---
    jours_occ = {}
    total_mois = 0
    missions_list = []
    df_p = charger_data('contacts.json')

    if not df_p.empty:
        df_p = df_p.fillna("")
        for idx, r in df_p.iterrows():
            try:
                nom_client = str(r.get('Nom', '')).strip().upper()
                if nom_client in ["", "CONTACT", "NAN"]: continue
                
                d_brute = str(r.get('DateNav', '')).strip().split(' ')[0]
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

                if "CMN" in soc: color = "#3498db"
                elif any(x in statut for x in ["annul", "refus"]): color = "#bdc3c7"
                elif dt_start < aujourdhui: color = "#34495e"
                else: color = "#27ae60"

                for i in range(n_j):
                    curr = dt_start + timedelta(days=i)
                    if curr.month == sel_m and curr.year == sel_y:
                        jours_occ[curr.day] = {"c": color}

                if (dt_start.year == sel_y and dt_start.month == sel_m) or (dt_end.year == sel_y and dt_end.month == sel_m):
                    missions_list.append({
                        'r': r, 'idx': idx, 'start': dt_start, 'end': dt_end, 
                        'n_j': n_j, 'color': color, 'prix': prix_val, 'statut': statut
                    })
                    if dt_start.month == sel_m and not any(x in statut for x in ["annul", "refus"]):
                        total_mois += prix_val
            except: continue

    # --- 5. AFFICHAGE CALENDRIER HTML ---
    import calendar
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

    # --- 6. LISTE DES MISSIONS ---
    st.markdown(f"### 📋 Missions de {sel_m_nom}")
    if missions_list:
        missions_list.sort(key=lambda x: x['start'])
        for m in missions_list:
            col1, col2 = st.columns([1, 3.5])
            with col1:
                st.markdown(f"""<div style='background:{m['color']}; color:white; border-radius:5px; text-align:center; padding:5px;'>
                    <span style='font-size:0.75rem;'>{m['start'].strftime('%d/%m')}</span><br><b>{m['prix']:.0f} €</b>
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
# --- PAGE STATS : DASHBOARD HARMONISÉ VESTA (V2026) ---
# =================================================================
if st.session_state.page == "STATS":
    st.markdown('<h2 style="text-align:center;">📊 Dashboard Intégral Vesta</h2>', unsafe_allow_html=True)

    # 1. Chargement des données
    df_actif = charger_data_safe('contacts.json')
    df_m = charger_data_safe('maintenance.json') 
    df_log = charger_data_safe('logbook.json')
    params = charger_params()
    
    # 2. FILTRES DE NAVIGATION
    c_sel1, c_sel2, c_sel3 = st.columns([2, 1, 1])
    mode_bilan = c_sel1.radio("Mode de calcul :", ["Réel (Encaissé)", "Prévisionnel (Saison)"], horizontal=True)
    sel_y = c_sel2.selectbox("Saison :", [2025, 2026, 2027], index=1)
    etat_flux_maint = c_sel3.selectbox("État Maintenance :", ["Fait", "À prévoir"])

    # --- A. PRÉPARATION ET NETTOYAGE DES DONNÉES ---
    # Conversion des dates et prix pour les contacts
    df_actif['dt_vrai'] = pd.to_datetime(df_actif['DateNav'], dayfirst=True, errors='coerce')
    df_f = df_actif[df_actif['dt_vrai'].dt.year == sel_y].copy()
    
    for col in ['Prix', 'Acompte']:
        if col in df_f.columns:
            df_f[col] = df_f[col].apply(to_f)
        else:
            df_f[col] = 0.0

    # --- LOGIQUE DE CALCUL HARMONISÉE ---
    # 1. Calcul du Réel Encaissé (Prix si PAID, sinon Acompte)
    df_f['Montant_Encaisse'] = df_f.apply(
        lambda x: x['Prix'] if str(x.get('Paiement', '')).strip().upper() == "PAID" else x['Acompte'], 
        axis=1
    )
    
    # 2. Calcul du Prévisionnel (Total des Prix)
    total_ca_saison = df_f['Prix'].sum()
    total_encaisse_reel = df_f['Montant_Encaisse'].sum()
    reste_a_percevoir = total_ca_saison - total_encaisse_reel
    
    # Sélection de la valeur à afficher selon le mode choisi
    if mode_bilan == "Réel (Encaissé)":
        total_ca_display = total_encaisse_reel
        df_rec_f = df_f[df_f['Montant_Encaisse'] > 0].copy() # On affiche ce qui a généré du cash
    else:
        total_ca_display = total_ca_saison
        df_rec_f = df_f.copy() # On affiche tout

    nb_sorties = len(df_f[df_f['Prix'] > 0])

    # Dépenses
    df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
    df_m_y = df_m[(df_m['dt_maint'].dt.year == sel_y) & (df_m['Statut'] == etat_flux_maint)].copy()
    total_dep = sum(to_f(x) for x in df_m_y['M_Num']) if not df_m_y.empty else 0.0

    # Logbook
    df_log['dt_log'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
    df_log_y = df_log[df_log['dt_log'].dt.year == sel_y].copy()
    total_h_moteur = df_log_y['TotalMot'].sum() if 'TotalMot' in df_log_y.columns else 0.0
    total_gazole = df_log_y['VolumeGazole'].sum() if 'VolumeGazole' in df_log_y.columns else 0.0

    # --- B. BLOC INDICATEURS (LE COCKPIT) ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    # Le Solde Net est toujours calculé sur le mode choisi
    solde_net = total_ca_display - total_dep
    m1.metric("💰 Solde Net", f"{solde_net:,.0f} €")
    m2.metric("⚓ Sorties", f"{nb_sorties}")
    m3.metric("⚙️ Heures Mot.", f"{total_h_moteur:.1f} h")
    m4.metric("⛽ Gazole", f"{total_gazole:,.0f} L")

    # Ligne de performance secondaire
    p1, p2, p3, p4 = st.columns(4)
    prog_ca = min(100, int((total_ca_display/6500)*100)) if total_ca_display > 0 else 0
    p1.metric("🎯 Objectif (6.5k)", f"{prog_ca}%")
    
    # Reste à percevoir (Très important pour ton suivi)
    p2.metric("📩 Reste à percevoir", f"{reste_a_percevoir:,.0f} €", delta=f"Total: {total_ca_saison:,.0f}", delta_color="off")
    
    h_moteur_abs = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if not df_log.empty else 0.0
    h_rest = params.get('prochaine_vidange', 2500.0) - h_moteur_abs
    p3.metric("🔧 Vidange", f"{h_rest:.1f} h")
    
    conso_h = total_gazole / total_h_moteur if total_h_moteur > 0 else 0
    p4.metric("📉 Conso", f"{conso_h:.1f} L/h")

    # --- C. GRAPHIQUE COMPARATIF ---
    st.divider()
    ordre_mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    df_graph = pd.DataFrame({'Mois': range(1, 13), 'NomMois': ordre_mois})
    
    if not df_f.empty:
        # On groupe par la valeur choisie (Réel ou Prévisionnel)
        val_col = 'Montant_Encaisse' if mode_bilan == "Réel (Encaissé)" else 'Prix'
        r_m = df_f.groupby(df_f['dt_vrai'].dt.month)[val_col].sum()
        df_graph = df_graph.merge(r_m.rename('Recettes'), left_on='Mois', right_index=True, how='left')
        act_m = df_f.groupby(df_f['dt_vrai'].dt.month).size()
        df_graph = df_graph.merge(act_m.rename('Sorties'), left_on='Mois', right_index=True, how='left')

    if not df_m_y.empty:
        d_m = df_m_y.groupby(df_m_y['dt_maint'].dt.month)['M_Num'].apply(lambda x: sum(to_f(v) for v in x))
        df_graph = df_graph.merge(d_m.rename('Dépenses'), left_on='Mois', right_index=True, how='left')
    
    df_graph = df_graph.fillna(0)

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df_graph['NomMois'], y=df_graph['Recettes'], name='Recettes (€)', marker_color='#2ecc71'), secondary_y=False)
    fig.add_trace(go.Bar(x=df_graph['NomMois'], y=df_graph['Dépenses'], name='Dépenses (€)', marker_color='#e74c3c'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_graph['NomMois'], y=df_graph['Sorties'], name='Nb Sorties', line=dict(color='#3498db', width=3)), secondary_y=True)

    fig.update_layout(height=350, barmode='group', margin=dict(l=0,r=0,t=20,b=0), legend=dict(orientation="h", y=1.2))
    st.plotly_chart(fig, use_container_width=True)

    # --- TABLEAU RÉCAPITULATIF DES RESTES À PERCEVOIR ---
    st.divider()
    st.markdown("### 🔍 Détail des sommes restant à percevoir")
    
    # Calcul du reste individuel
    df_reste = df_f.copy()
    
    for c in ['Nom', 'Prenom']:
        if c not in df_reste.columns: df_reste[c] = ""

    df_reste['Reste'] = df_reste['Prix'] - df_reste['Montant_Encaisse']
    
    # Filtrage : On ne garde que ce qui n'est pas totalement payé
    df_a_percevoir = df_reste[df_reste['Reste'] > 0.01].copy()
    
    if not df_a_percevoir.empty:
        # Tri par date
        df_a_percevoir = df_a_percevoir.sort_values('dt_vrai')
        
        # Sélection des colonnes demandées
        tableau_reste = df_a_percevoir[['DateNav', 'Nom', 'Prenom', 'Prix', 'Acompte', 'Reste']]
        
        # Calcul du total des sommes dues
        total_du = df_a_percevoir['Reste'].sum()
        
        # Affichage du tableau
        st.dataframe(
            tableau_reste, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "DateNav": "Date",
                "Nom": "Nom",
                "Prenom": "Prénom",
                "Prix": st.column_config.NumberColumn("Total (€)", format="%.2f"),
                "Acompte": st.column_config.NumberColumn("Reçu (€)", format="%.2f"),
                "Reste": st.column_config.NumberColumn("À percevoir (€)", format="%.2f"),
            }
        )
        
        # --- LIGNE DE TOTAL ---
        st.markdown(f"""
            <div style="text-align:right; background-color:#f8d7da; color:#721c24; padding:10px; border-radius:5px; font-weight:bold; font-size:1.1em;">
                TOTAL DES SOMMES À RÉCUPÉRER : {total_du:,.2f} €
            </div>
        """, unsafe_allow_html=True)
        
    else:
        st.success("✅ Aucune somme en attente de perception pour cette sélection.")

    # --- D. DÉTAILS CHRONO ---
    st.divider()
    col_t1, col_t2 = st.columns(2)

    with col_t1:
        st.markdown(f"**📥 DÉTAIL RECETTES ({mode_bilan})**")
        if not df_rec_f.empty:
            # Affichage intelligent des colonnes
            cols_show = ['DateNav', 'Nom', 'Paiement', 'Prix']
            if mode_bilan == "Réel (Encaissé)":
                cols_show = ['DateNav', 'Nom', 'Acompte', 'Prix', 'Paiement']
            
            df_display_rec = df_rec_f.sort_values('dt_vrai')[cols_show]
            st.dataframe(df_display_rec, use_container_width=True, hide_index=True)
            st.markdown(f"<div style='text-align:right; font-weight:bold; color:#2ecc71;'>TOTAL : {total_ca_display:,.2f} €</div>", unsafe_allow_html=True)
        else:
            st.info("Aucune donnée sur cette sélection.")

    with col_t2:
        st.markdown(f"**📤 DÉTAIL MAINTENANCE ({etat_flux_maint})**")
        if not df_m_y.empty:
            df_display_maint = df_m_y.sort_values('dt_maint')[['Date', 'Objet', 'M_Num']]
            st.dataframe(df_display_maint, use_container_width=True, hide_index=True)
            st.markdown(f"<div style='text-align:right; font-weight:bold; color:#e74c3c;'>TOTAL : {total_dep:,.2f} €</div>", unsafe_allow_html=True)
        else:
            st.info("Aucune dépense.")
# =================================================================
# --- 8. PAGE MAINTENANCE (GESTION VIDANGE & TRAVAUX) ---
# =================================================================
if st.session_state.page == "MAINT":
    import pandas as pd
    import io
    import streamlit.components.v1 as components
    from datetime import datetime

    # --- 1. FONCTION D'IMPRESSION ---
    def bouton_imprimer_fiche_maint(titre, date, details, statut):
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 30px; color: #2C3E50; }}
                .header {{ border-bottom: 3px solid #2980B9; padding-bottom: 10px; margin-bottom: 20px; }}
                .statut {{ display: inline-block; padding: 5px 15px; border-radius: 20px; background: #eee; font-weight: bold; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; white-space: pre-wrap; font-size: 1.1em; }}
            </style>
        </head>
        <body>
            <div class='header'>
                <h1>🛠️ {titre}</h1>
                <p><b>Date :</b> {date} | <span class='statut'>État : {statut}</span></p>
            </div>
            <div class='content'>{details}</div>
            <p style='font-size: 0.8em; color: gray; margin-top: 40px;'>Vesta Skipper 2026</p>
        </body>
        </html>
        """
        js = f"""
        <script>
        function printFiche() {{
            var win = window.open('', '', 'height=600, width=800');
            win.document.write({repr(html_content)});
            win.document.close();
            setTimeout(function(){{ win.print(); }}, 500);
        }}
        </script>
        <button onclick="printFiche()" style="padding: 5px 10px; border-radius: 5px; cursor: pointer; background: #ffffff; border: 1px solid #d1d5db; width: 100%;">
            🖨️ Imprimer
        </button>
        """
        components.html(js, height=45)

    # --- 2. CHARGEMENT DES DONNÉES ---
    df_m = charger_data_safe('maintenance.json')
    df_log = charger_data_safe('logbook.json')
    releve_h = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if not df_log.empty else 0.0
    
    params = charger_params()
    if 'prochaine_vidange' not in params:
        params['prochaine_vidange'] = 2450.0
        sauvegarder_params(params)

    if 'maint_edit_id' not in st.session_state:
        st.session_state.maint_edit_id = None

    st.title("🛠️ MAINTENANCE & VIDANGE")

    # --- 3. TABLEAU DE BORD VIDANGE ---
    heures_restantes = params['prochaine_vidange'] - releve_h
    color_v = "#2e7d32" if heures_restantes > 15 else "#c62828"
    
    col_v1, col_v2 = st.columns([2, 1])
    with col_v1:
        st.markdown(f"""
            <div style="background-color: {color_v}15; border: 2px solid {color_v}; padding: 15px; border-radius: 10px; text-align: center;">
                <h3 style="margin:0; color: {color_v};">{heures_restantes:.1f} h restantes</h3>
                <p style="margin:0;">Cible vidange : <b>{params['prochaine_vidange']:.1f} h</b> | Actuel : {releve_h:.1f} h</p>
            </div>
        """, unsafe_allow_html=True)
    with col_v2:
        new_target = st.number_input("Ajuster cible (h)", value=float(params['prochaine_vidange']), step=10.0)
        if new_target != params['prochaine_vidange']:
            params['prochaine_vidange'] = new_target
            sauvegarder_params(params)
            st.rerun()

    st.divider()
    
    # --- 7. DASHBOARD CARBURANT (Plus visible) ---
    st.markdown("### ⛽ Suivi Carburant")
    df_carb = charger_data_safe('carburant.json')
    
    col_c1, col_c2, col_c3 = st.columns(3)
    if not df_carb.empty:
        total_l = df_carb['Litres'].sum()
        total_e = df_carb['Prix'].sum()
        dernier_pu = df_carb['PU'].iloc[-1] if 'PU' in df_carb.columns else 0
        col_c1.metric("Total Litres", f"{total_l:.0f} L")
        col_c2.metric("Total Dépensé", f"{total_e:.2f} €")
        col_c3.metric("Dernier Prix/L", f"{dernier_pu:.3f} €")

    with st.expander("➕ Enregistrer un plein / Voir l'historique", expanded=False):
        with st.form("form_fuel"):
            c1, c2, c3 = st.columns(3)
            d_f = c1.date_input("Date du plein")
            l_f = c2.number_input("Litres", min_value=0.0)
            p_f = c3.number_input("Total TTC (€)", min_value=0.0)
        
            if st.form_submit_button("Enregistrer le plein"):
                new_f = {"Date": d_f.strftime("%d/%m/%Y"), "Litres": l_f, "Prix": p_f, "PU": p_f/l_f if l_f > 0 else 0}
                df_carb = pd.concat([df_carb, pd.DataFrame([new_f])], ignore_index=True)
                sauvegarder_data(df_carb, 'carburant.json')
                st.rerun()

        if not df_carb.empty:
            st.table(df_carb.tail(5)) # Affiche les 5 derniers pleins
            
    # --- INITIALISATION DES ÉTATS DE VISIBILITÉ ---
    if 'show_form_classique' not in st.session_state: st.session_state.show_form_classique = False
    if 'show_form_vidange' not in st.session_state: st.session_state.show_form_vidange = False

    # --- 4. BOUTONS D'APPEL ---
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("🔧 NOUVELLE INTERVENTION", use_container_width=True):
        st.session_state.show_form_classique = True
        st.session_state.show_form_vidange = False
        st.rerun()
    
    if col_btn2.button("🛢️ RÉVISION MOTEUR", use_container_width=True):
        st.session_state.show_form_vidange = True
        st.session_state.show_form_classique = False
        st.rerun()

    # --- 5. FORMULAIRE CLASSIQUE ---
    if st.session_state.show_form_classique:
        with st.form("form_new_maint"):
            st.subheader("🔧 Nouvelle Intervention")
            f_obj = st.text_input("Désignation")
            c1, c2, c3 = st.columns(3)
            f_d = c1.date_input("Date", datetime.now())
            f_m = c2.number_input("Montant (€)", min_value=0.0)
            f_t = c3.selectbox("Catégorie", ["Maintenance", "Sécurité", "Port", "Assurances", "Autres"])
            f_notes = st.text_area("Notes détaillées")
            f_statut = st.selectbox("Statut", ["À prévoir", "Fait"])
            
            b_col1, b_col2 = st.columns(2)
            if b_col1.form_submit_button("✅ ENREGISTRER", use_container_width=True, type="primary"):
                new_row = {"Date": f_d.strftime("%d/%m/%Y"), "Objet": f_obj, "M_Num": f_m, "Statut": f_statut, "Type": f_t, "Notes": f_notes}
                df_m = pd.concat([df_m, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_m, 'maintenance.json')
                st.session_state.show_form_classique = False
                st.rerun()
            
            if b_col2.form_submit_button("❌ FERMER", use_container_width=True):
                st.session_state.show_form_classique = False # On force la fermeture ici
                st.rerun()

    # --- 6. FORMULAIRE VIDANGE ---
    if st.session_state.show_form_vidange:
        with st.form("form_vidange_moteur"):
            st.subheader("🛢️ Révision Moteur")
            c_v1, c_v2 = st.columns(2)
            v_date = c_v1.date_input("Date", datetime.now())
            v_heures = c_v2.number_input("Heures moteur", value=float(releve_h))
            
            st.markdown("**Check-list :**")
            col_c1, col_c2, col_c3 = st.columns(3)
            chk_huile = col_c1.checkbox("Vidange Huile")
            chk_f_huile = col_c1.checkbox("Filtre Huile")
            chk_f_gasoil = col_c2.checkbox("Filtre Gasoil")
            chk_f_pre = col_c2.checkbox("Pré-filtre")
            chk_courroie = col_c3.checkbox("Courroies")
            chk_impeller = col_c3.checkbox("Impeller")
            
            v_cout = st.number_input("Coût fournitures (€)", min_value=0.0)
            v_notes = st.text_area("Observations")
            inc_h = st.selectbox("Prochaine vidange (+h)", [50, 100, 150, 200], index=1)
            
            bv_col1, bv_col2 = st.columns(2)
            if bv_col1.form_submit_button("✅ VALIDER RÉVISION", use_container_width=True, type="primary"):
                travaux = [t for t, c in zip(["Huile", "F-Huile", "F-Gasoil", "Pré-filtre", "Courroies", "Impeller"], 
                                             [chk_huile, chk_f_huile, chk_f_gasoil, chk_f_pre, chk_courroie, chk_impeller]) if c]
                details = f"Révision à {v_heures}h. Travaux : {', '.join(travaux)}. Notes : {v_notes}"
                new_row = {"Date": v_date.strftime("%d/%m/%Y"), "Objet": f"RÉVISION MOTEUR ({v_heures}h)", "M_Num": v_cout, "Statut": "Fait", "Type": "Maintenance", "Notes": details}
                params['prochaine_vidange'] = round(v_heures + inc_h, 1)
                sauvegarder_params(params)
                df_m = pd.concat([df_m, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_m, 'maintenance.json')
                st.session_state.show_form_vidange = False
                st.rerun()

            if bv_col2.form_submit_button("❌ FERMER", use_container_width=True):
                st.session_state.show_form_vidange = False # On force la fermeture ici
                st.rerun()



    # --- 7. SYSTÈME DE FILTRES ---
    st.divider()
    col_menu1, col_menu2, col_menu3 = st.columns([2, 1.2, 1.2])
    filter_statut = col_menu1.radio("Afficher :", ["Tout", "⏳ À faire", "✅ Fait"], horizontal=True)
    mode_m = col_menu2.radio("Période :", ["À ce jour", "Année complète"], horizontal=True)
    sel_y = col_menu3.selectbox("Année :", [2025, 2026, 2027], index=1)

    if not df_m.empty:
        df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_filtre = df_m[df_m['dt_maint'].dt.year == sel_y].copy()
        
        if mode_m == "À ce jour":
            aujourdhui = pd.Timestamp.now().normalize()
            df_filtre = df_filtre[df_filtre['dt_maint'] <= aujourdhui]

        if filter_statut == "⏳ À faire":
            df_filtre = df_filtre[df_filtre['Statut'] == "À prévoir"]
        elif filter_statut == "✅ Fait":
            df_filtre = df_filtre[df_filtre['Statut'] == "Fait"]

        df_filtre = df_filtre.sort_values('dt_maint', ascending=False)

        if df_filtre.empty:
            st.info("Aucune fiche pour ces filtres.")
        else:
            for idx, row in df_filtre.iterrows():
                est_fait = (row['Statut'] == "Fait")
                border_color = "#27AE60" if est_fait else "#F39C12"
                bg_color = "#EAFAF1" if est_fait else "#FEF5E7"
                icon_stat = "✅" if est_fait else "⏳"

                if st.session_state.maint_edit_id == idx:
                    with st.form(key=f"edit_maint_{idx}"):
                        e_obj = st.text_input("Désignation", value=row['Objet'])
                        c1, c2 = st.columns(2)
                        e_dat = c1.text_input("Date", value=row['Date'])
                        e_mon = c2.number_input("Montant (€)", value=float(row['M_Num']))
                        e_not = st.text_area("Notes", value=row.get('Notes', ''))
                        e_sta = st.selectbox("Statut", ["À prévoir", "Fait"], index=1 if est_fait else 0)
                        
                        cb1, cb2 = st.columns(2)
                        if cb1.form_submit_button("✅ SAUVER"):
                            df_m.at[idx, 'Objet'] = e_obj
                            df_m.at[idx, 'Date'] = e_dat
                            df_m.at[idx, 'M_Num'] = e_mon
                            df_m.at[idx, 'Notes'] = e_not
                            df_m.at[idx, 'Statut'] = e_sta
                            sauvegarder_data(df_m.drop(columns=['dt_maint']), 'maintenance.json')
                            st.session_state.maint_edit_id = None
                            st.rerun()
                        if cb2.form_submit_button("❌ ANNULER"):
                            st.session_state.maint_edit_id = None
                            st.rerun()
                else:
                    st.markdown(f"""
                        <div style="background-color:{bg_color}; border-left: 10px solid {border_color}; padding: 15px; border-radius: 10px; margin-bottom: 5px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: bold; font-size: 1.1em;">{icon_stat} {row['Objet']}</span>
                                <span style="color: #555;">📅 {row['Date']}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                                <small>Catégorie : <b>{row['Type']}</b></small>
                                <small>Coût : <b>{row['M_Num']} €</b></small>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if row.get('Notes'): st.caption(f"📝 {row['Notes']}")

                    bc1, bc2, bc3, bc4 = st.columns(4)
                    if bc1.button("✏️ Modif", key=f"ed_m_{idx}"):
                        st.session_state.maint_edit_id = idx
                        st.rerun()
                    with bc2:
                        bouton_imprimer_fiche_maint(row['Objet'], row['Date'], row.get('Notes', 'N/A'), row['Statut'])
                    
                    label_toggle = "⏳ À prévoir" if est_fait else "✅ Marquer FAIT"
                    if bc3.button(label_toggle, key=f"st_m_{idx}"):
                        df_m.at[idx, 'Statut'] = "À prévoir" if est_fait else "Fait"
                        sauvegarder_data(df_m.drop(columns=['dt_maint']), 'maintenance.json')
                        st.rerun()

                    if bc4.button("🗑️ Suppr", key=f"pre_m_{idx}"):
                        df_m = df_m.drop(idx)
                        sauvegarder_data(df_m.drop(columns=['dt_maint']), 'maintenance.json')
                        st.rerun()
                        
     # --- 8. EXPORT EXCEL ---
    if not df_m.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_m.drop(columns=['dt_maint'], errors='ignore').to_excel(writer, index=False)
        st.download_button("📥 Télécharger Historique Complet (Excel)", data=buffer.getvalue(), 
                           file_name=f"Maintenance_Vesta_Skipper.xlsx", use_container_width=True)

# =================================================================
# --- 7. PAGE FACTURATION (FACT) ---
# =================================================================
if st.session_state.page == "FACT":
    st.markdown("<h2 style='text-align: center;'>📑 Suivi de Facturation</h2>", unsafe_allow_html=True)
    
    # Chargement des données fraîches
    df_fact = charger_data_safe('contacts.json')

    if df_fact.empty:
        st.info("Aucune donnée de facturation.")
    else:
        # --- CALCULS SÉCURISÉS ---
        total_ca = sum(df_fact['Prix'].apply(to_f))
        total_enc = sum(df_fact['Acompte'].apply(to_f))
        reste_a_percevoir = max(0, total_ca - total_enc)

        m1, m2, m3 = st.columns(3)
        # Formatage avec espace pour les milliers
        m1.metric("Total CA", f"{total_ca:,.0f} €".replace(",", " "))
        m2.metric("Encaissé", f"{total_enc:,.0f} €".replace(",", " "))
        m3.metric("Reste à percevoir", f"{reste_a_percevoir:,.0f} €".replace(",", " "), 
                  delta=f"-{reste_a_percevoir:,.0f}" if reste_a_percevoir > 0 else None, 
                  delta_color="inverse")

        st.divider()

        # --- FILTRAGE ET TRI CHRONOLOGIQUE (MAI AVANT JUIN) ---
        if 'Paiement' not in df_fact.columns: 
            df_fact['Paiement'] = "Unpaid"
        
        # On utilise une colonne temporaire pour le tri réel
        df_fact['dt_temp'] = pd.to_datetime(df_fact['DateNav'], dayfirst=True, errors='coerce')
        # ascending=True pour l'ordre normal (chronologique)
        df_fact = df_fact.sort_values(by='dt_temp', ascending=True).drop(columns=['dt_temp'])

        t1, t2 = st.tabs(["⏳ À ENCAISSER", "✅ PAYÉ"])

        def afficher_onglet(status_filtre):
            df_vue = df_fact[df_fact['Paiement'] == status_filtre]
            
            if df_vue.empty:
                st.write(f"Rien à afficher dans '{status_filtre}'.")
            else:
                # Date du jour pour comparer les retards
                aujourdhui = pd.Timestamp.now().normalize()

                for idx, row in df_vue.iterrows():
                    # Infos société
                    soc = str(row.get('Société', 'PERSO')).upper()
                    is_cmn = "CMN" in soc
                    
                    # Logique de détection du retard
                    date_nav = pd.to_datetime(row.get('DateNav',''), dayfirst=True, errors='coerce')
                    retard = (status_filtre == "Unpaid") and (date_nav < aujourdhui)
                    
                    # Préparation des styles
                    label_retard = "<span style='color:#E74C3C; font-weight:bold; font-size:0.8rem;'>⚠️ RETARD</span>" if retard else ""
                    card_bg = "#E3F2FD" if is_cmn else "#F9F9F9"
                    border_color = "#E74C3C" if retard else ("#3498db" if is_cmn else "#7F8C8D")
                    
                    # Rendu de la fiche
                    st.markdown(f"""
                        <div style="background:{card_bg}; border-left:10px solid {border_color}; padding:15px; border-radius:8px; margin-bottom:10px; color:black; border: 1px solid #ddd;">
                            <div style="display:flex; justify-content:space-between;">
                                <b>{row.get('Nom','')} {row.get('Prénom','')}</b>
                                <span style="font-size:1.1rem; font-weight:bold;">{to_f(row.get('Prix',0)):.0f} €</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <small>📅 {row.get('DateNav','')} | 🏢 {soc}</small>
                                {label_retard}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    c1, c2, _ = st.columns([2, 2, 6])
                    
                    if status_filtre == "Unpaid":
                        if c1.button(f"💰 Encaisser", key=f"pay_btn_{idx}"):
                            df_fact.at[idx, 'Paiement'] = "Paid"
                            df_fact.at[idx, 'Acompte'] = df_fact.at[idx, 'Prix']
                            sauvegarder_data(df_fact, 'contacts.json')
                            st.success("Encaissé !")
                            time.sleep(0.5)
                            st.rerun()

                    if c2.button(f"✏️ Voir", key=f"edit_f_{idx}"):
                        st.session_state.edit_idx = idx
                        st.session_state.page = "MODIFIER_CONTACT"
                        st.rerun()

        with t1: 
            afficher_onglet("Unpaid")
        with t2: 
            afficher_onglet("Paid")
# =================================================================
# --- 11. PAGE ARCHIVES & SÉCURITÉ ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    st.title("📂 Archives & Sécurité")
    
    if st.button("⬅️ Retour au Planning"):
        st.session_state.page = "PLANNING"
        st.rerun()

    # --- SECTION 1 : CONSULTATION DES HISTORIQUES ---
    st.markdown("### 🔍 Consultation des historiques")
    t1, t2, t3 = st.tabs(["🛠️ Frais", "📅 Planning", "📖 Logbook"])
    
    with t1: 
        st.subheader("Archives Maintenance")
        st.dataframe(charger_data_safe('archives_maintenance.json'), use_container_width=True)
    
    with t2: 
        st.subheader("Archives Planning")
        st.dataframe(charger_data_safe('archives_planning.json'), use_container_width=True)
    
    with t3: 
        st.subheader("Archives Logbook")
        st.dataframe(charger_data_safe('archives_logbook.json'), use_container_width=True)

    st.divider()

    # --- SECTION 2 : COFFRE-FORT (SAUVEGARDE LOCALE) ---
    st.markdown("### 🛡️ Coffre-fort de sauvegarde")
    with st.expander("💾 Télécharger les données sur mon ordinateur", expanded=True):
        st.write("Cliquez sur les boutons ci-dessous pour exporter vos données actuelles au format Excel (CSV).")
        
        # Liste des fichiers critiques à sauvegarder
        fichiers_cible = {
            "Contacts & Facturation": "contacts.json",
            "Maintenance & Frais": "maintenance.json",
            "Livre de Bord (Logbook)": "logbook.json"
        }
        
        col_bak1, col_bak2, col_bak3 = st.columns(3)
        cols = [col_bak1, col_bak2, col_bak3]

        for i, (nom_affichage, nom_fichier) in enumerate(fichiers_cible.items()):
            df_bak = charger_data_safe(nom_fichier)
            
            if not df_bak.empty:
                # Encodage utf-8-sig pour que Excel gère bien les accents (Ex: Prénom, Confirmé)
                csv_data = df_bak.to_csv(index=False).encode('utf-8-sig')
                
                # Nom du fichier avec date du jour pour un meilleur classement
                date_str = datetime.now().strftime("%d_%m_%Y")
                file_final = f"VESTA_{nom_fichier.replace('.json', '')}_{date_str}.csv"
                
                cols[i].download_button(
                    label=f"📥 {nom_affichage}",
                    data=csv_data,
                    file_name=file_final,
                    mime='text/csv',
                    use_container_width=True
                )
            else:
                cols[i].caption(f"⚠️ {nom_affichage} est vide.")

    st.caption("Note : Il est conseillé de faire une sauvegarde manuelle après chaque grosse mise à jour de vos données.")
# =================================================================
# --- 12. PAGE LIVRE DE BORD (LOG) - VERSION EXPERT AVEC ACTIONS ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>📖 Livre de Bord & Statistiques</h1></div>', unsafe_allow_html=True)

    df_log = charger_data_safe('logbook.json')
    
    # Initialisation des états
    if 'saisie_ouverte' not in st.session_state: st.session_state.saisie_ouverte = False
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None

    # --- 1. FONCTIONS D'ACTION ---
    def supprimer_log(index):
        df_temp = charger_data_safe('logbook.json')
        df_temp = df_temp.drop(index).reset_index(drop=True)
        sauvegarder_data(df_temp, 'logbook.json')
        st.toast("✅ Entrée supprimée", icon="🗑️")
        st.rerun()

    # --- 2. MODAL / FORMULAIRE D'ÉDITION ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        row_to_edit = df_log.iloc[idx]
        
        with st.expander("📝 MODIFIER LA NAVIGATION", expanded=True):
            with st.form(key="form_edit_log"):
                st.subheader(f"Modification de l'entrée du {row_to_edit['Date']}")
                c1, c2 = st.columns(2)
                e_nav = c1.text_input("Nom du Voyage", value=row_to_edit['Navigation'])
                e_meteo = c2.text_input("Météo", value=row_to_edit.get('Meteo', ''))
                e_notes = st.text_area("Observations", value=row_to_edit.get('Notes', ''))
                
                col1, col2, col3 = st.columns(3)
                e_mot = col1.number_input("Heures Moteur (Total)", value=float(row_to_edit['TotalMot']))
                e_voile = col2.number_input("Heures Voile", value=float(row_to_edit['H_Voile']))
                e_mil = col3.number_input("Distance (NM)", value=float(row_to_edit['TotalMil']))
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True, type="primary"):
                    df_log.at[idx, 'Navigation'] = e_nav
                    df_log.at[idx, 'Meteo'] = e_meteo
                    df_log.at[idx, 'Notes'] = e_notes
                    df_log.at[idx, 'TotalMot'] = e_mot
                    df_log.at[idx, 'H_Voile'] = e_voile
                    df_log.at[idx, 'TotalMil'] = e_mil
                    sauvegarder_data(df_log, 'logbook.json')
                    st.session_state.edit_idx = None
                    st.rerun()
                
                if b2.form_submit_button("❌ ANNULER", use_container_width=True):
                    st.session_state.edit_idx = None
                    st.rerun()

    # --- 3. SAISIE RAPIDE (NOUVELLE NAVIGATION) ---
    if not st.session_state.saisie_ouverte and st.session_state.edit_idx is None:
        st.button("➕ NOUVELLE NAVIGATION", on_click=lambda: st.session_state.update({"saisie_ouverte": True}), use_container_width=True)
    
    if st.session_state.saisie_ouverte:
        with st.expander("🚀 Formulaire de Saisie", expanded=True):
            with st.form(key="form_nav_expert"):
                # ... (Conserver ton code de formulaire existant ici) ...
                # N'oublie pas de bien inclure le bouton "Annuler" qui met st.session_state.saisie_ouverte = False
                pass # Remplacer par ton bloc de formulaire original

    # --- 4. AFFICHAGE GROUPÉ AVEC BOUTONS D'ACTION ---
    if not df_log.empty:
        st.divider()
        df_v = df_log.copy()
        df_v['dt'] = pd.to_datetime(df_v['Date'], dayfirst=True, errors='coerce')
        # On garde l'index original pour les actions
        df_v['original_index'] = df_v.index 
        df_v = df_v.sort_values(by=['dt', 'Navigation'], ascending=[False, False])

        for nav_name, group in df_v.groupby('Navigation', sort=False):
            # En-tête du groupe (Voyage)
            t_mil = group['TotalMil'].sum()
            st.markdown(f"""
                <div style="background:#2c3e50; color:white; padding:10px; border-radius:8px 8px 0 0; margin-top:15px; border-bottom:2px solid #3498db;">
                    <b>🚢 {nav_name or "Navigation"}</b> | Total: {t_mil:.1f} NM
                </div>
            """, unsafe_allow_html=True)
            
            for _, row in group.iterrows():
                idx_orig = row['original_index']
                
                # Container pour chaque ligne de log
                with st.container():
                    # Colonne 1: Infos / Colonne 2: Boutons
                    col_info, col_btn = st.columns([0.85, 0.15])
                    
                    with col_info:
                        st.markdown(f"""
                            <div style="background:white; border-left:4px solid #3498db; padding:8px 15px; border-bottom:1px solid #eee;">
                                <div style="display:flex; justify-content:space-between;">
                                    <b>📅 {row['Date']}</b>
                                    <span style="font-size:0.8em; color:#bdc3c7;">NM: {row['TotalMil']:.1f}</span>
                                </div>
                                <div style="font-size:0.9em; color:#2c3e50;">☁️ {row.get('Meteo','-')} | 📝 <small>{row.get('Notes','')}</small></div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    with col_btn:
                        # Boutons d'action compacts
                        sub1, sub2 = st.columns(2)
                        if sub1.button("✏️", key=f"edit_{idx_orig}", help="Modifier"):
                            st.session_state.edit_idx = idx_orig
                            st.rerun()
                        
                        if sub2.button("🗑️", key=f"del_{idx_orig}", help="Supprimer"):
                            supprimer_log(idx_orig)

    # --- 5. EXPORT CSV ---
    if not df_log.empty:
        st.divider()
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Télécharger le Livre de Bord", data=csv, file_name='livre_de_bord_vesta.csv', mime='text/csv', use_container_width=True)
    # =================================================================
# --- 11. PAGE ARCHIVES (VERSION CORRIGÉE & COMPLÈTE) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    st.title("📂 Archives & Historique")
    
    # Bouton de retour rapide
    if st.button("⬅️ Retour au Planning"):
        st.session_state.page = "PLANNING"
        st.rerun()

    # --- SECTION 1 : CONSULTATION DES DONNÉES ARCHIVÉES ---
    st.markdown("### 🔍 Consultation des historiques")
    t1, t2, t3, t4 = st.tabs(["🛠️ Frais", "📅 Planning", "📖 Logbook", "👤 Contacts"])
    
    with t1: 
        st.subheader("Archives Maintenance")
        st.dataframe(charger_data_safe('archives_maintenance.json'), use_container_width=True)
    
    with t2: 
        st.subheader("Archives Planning")
        st.dataframe(charger_data_safe('archives_planning.json'), use_container_width=True)
    
    with t3: 
        st.subheader("Archives Logbook")
        st.dataframe(charger_data_safe('archives_logbook.json'), use_container_width=True)

    with t4:
        st.subheader("Archives Contacts (Saisons passées)")
        # On tente de charger l'archive spécifique 2026 créée par la clôture
        st.dataframe(charger_data_safe('archives_contacts_2026.json'), use_container_width=True)

    st.divider()

    # --- SECTION 2 : OUTILS DE FIN DE SAISON ---
    st.markdown("### 🏁 Clôture de Saison 2026")
    
    with st.expander("🚨 ZONE DE DANGER : Archiver la saison en cours", expanded=False):
        st.warning("""
            **Attention :** Cette action va déplacer toutes les fiches marquées comme **'Paid'** depuis ta liste de contacts active vers le fichier des archives 2026. 
            Cela permet de vider ton menu Facturation pour la saison suivante.
        """)
        
        if st.button("🔒 EXÉCUTER L'ARCHIVAGE DES CONTACTS RÉGLÉS", use_container_width=True, type="primary"):
            # 1. Chargement des contacts actuels
            df_f = charger_data_safe('contacts.json')
            
            if not df_f.empty:
                # 2. Séparation Payé / Non Payé
                # On s'assure que la colonne Paiement existe
                if 'Paiement' not in df_f.columns:
                    df_f['Paiement'] = "Unpaid"
                
                df_paid = df_f[df_f['Paiement'] == "Paid"]
                df_unpaid = df_f[df_f['Paiement'] != "Paid"]
                
                if not df_paid.empty:
                    # 3. Sauvegarde dans l'archive 2026
                    # On récupère l'archive existante pour ne pas écraser si on clique plusieurs fois
                    df_hist = charger_data_safe('archives_contacts_2026.json')
                    df_new_hist = pd.concat([df_hist, df_paid], ignore_index=True)
                    sauvegarder_data(df_new_hist, 'archives_contacts_2026.json')
                    
                    # 4. Mise à jour du fichier actif (on ne garde que les impayés)
                    sauvegarder_data(df_unpaid, 'contacts.json')
                    
                    st.success(f"✅ {len(df_paid)} fiches archivées avec succès dans 'archives_contacts_2026.json'.")
                    st.rerun()
                else:
                    st.info("Aucune fiche marquée comme 'Paid' (Payée) n'a été trouvée.")
            else:
                st.error("Le fichier de contacts est vide.")

    # Petit rappel de sécurité en bas de page
    st.caption("Note : Les fichiers d'archives sont stockés au format JSON sur votre dépôt GitHub.")

# --- FIN DU FICHIER ---









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































