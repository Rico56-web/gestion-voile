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
# --- 2. MENU MÉMOS (VERSION FINALE : BASCULE FLUIDE & ÉDITION) ---
# =================================================================
if st.session_state.page == "MEMOS":
    st.markdown("<h2 style='text-align: center; color: #34495E;'>⚓ Mémos & Check-lists de Bord</h2>", unsafe_allow_html=True)
    
    df_memos = charger_data_safe('memos.json')

    # --- AUTO-RÉPARATION ---
    for c in ['Statut', 'Paiement', 'Archive', 'Description', 'Date']:
        if c not in df_memos.columns:
            df_memos[c] = "Non Archivé" if c == "Archive" else "Normal"

    if 'memo_edit_id' not in st.session_state: 
        st.session_state.memo_edit_id = None

    # --- A. AJOUT NOUVELLE NOTE ---
    with st.expander("➕ CRÉER UNE NOUVELLE CHECK-LIST", expanded=df_memos.empty):
        with st.form("new_memo_form_final"):
            c1, c2 = st.columns(2)
            m_date = c1.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
            m_urg = c2.selectbox("Urgence de départ", ["Normal", "Urgent"])
            m_txt = st.text_area("Contenu (une ligne par tâche)")
            
            btn_save, btn_close = st.columns(2)
            if btn_save.form_submit_button("💾 ENREGISTRER LA NOTE", use_container_width=True, type="primary"):
                if m_txt.strip():
                    new_r = pd.DataFrame([{"Date": m_date, "Description": m_txt, "Statut": m_urg, "Paiement": "N/A", "Archive": "Non Archivé"}])
                    df_memos = pd.concat([df_memos, new_r], ignore_index=True)
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()

            if btn_close.form_submit_button("❌ FERMER", use_container_width=True):
                st.rerun()

    # --- B. AFFICHAGE DES FICHES ---
    df_show = df_memos[df_memos['Archive'] == "Non Archivé"]
    
    if not df_show.empty:
        # On trie pour voir les plus récents en haut
        for idx, row in df_show.sort_index(ascending=False).iterrows():
            
            # --- PRÉPARATION DES VARIABLES (Évite NameError) ---
            stat_val = str(row.get('Statut', 'Normal'))
            pay_val = str(row.get('Paiement', 'N/A'))
            
            # --- CAS 1 : FORMULAIRE DE MODIFICATION ---
            if st.session_state.memo_edit_id == idx:
                texte_edition = str(row['Description']).replace("✅ | ", "").replace("❌ | ", "")
                
                st.markdown(f"✨ **Modification en cours : Note du {row['Date']}**")
                with st.form(key=f"edit_form_loc_{idx}"):
                    e_desc = st.text_area("Éditer la liste", value=texte_edition, height=150)
                    c1, c2 = st.columns(2)
                    
                    p_opts = ["N/A", "À Payer", "Payé"]
                    s_opts = ["Normal", "Urgent", "Fait"]
                    
                    e_pay = c1.selectbox("Paiement", p_opts, index=p_opts.index(pay_val) if pay_val in p_opts else 0)
                    e_stat = c2.selectbox("Urgence", s_opts, index=s_opts.index(stat_val) if stat_val in s_opts else 0)
                    
                    col_save, col_cancel = st.columns(2)
                    if col_save.form_submit_button("✅ ENREGISTRER"):
                        df_memos.at[idx, 'Description'] = e_desc
                        df_memos.at[idx, 'Paiement'] = e_pay
                        df_memos.at[idx, 'Statut'] = e_stat
                        sauvegarder_data(df_memos, 'memos.json')
                        st.session_state.memo_edit_id = None 
                        st.rerun()
                        
                    if col_cancel.form_submit_button("❌ ANNULER"):
                        st.session_state.memo_edit_id = None
                        st.rerun()
            
            # --- CAS 2 : AFFICHAGE NORMAL ---
            else:
                # Couleurs selon statut
                if stat_val == "Urgent": h_c, bg_c = "#E74C3C", "#FDEDEC" 
                elif stat_val == "Fait": h_c, bg_c = "#27AE60", "#EAFAF1"
                else: h_c, bg_c = "#2980B9", "#EBF5FB"

                # En-tête de la fiche
                st.markdown(f"""
                    <div style="background-color:{bg_c}; border-left: 10px solid {h_c}; padding: 15px; border-radius: 10px; margin-bottom: 5px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: bold; color: #2C3E50;">📅 {row['Date']} | 💰 {pay_val}</span>
                            <span style="background-color: {h_c}; color: white; padding: 2px 10px; border-radius: 15px; font-size: 0.8rem;">{stat_val.upper()}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # Liste de tâches interactive
                lignes = str(row.get('Description', '')).split('\n')
                data_list = [{"Fait": l.startswith("✅ | "), "Tâche": l.replace("✅ | ", "").replace("❌ | ", "")} 
                             for l in lignes if l.strip()]
                
                if data_list:
                    edited_df = st.data_editor(
                        pd.DataFrame(data_list), 
                        key=f"editor_active_{idx}", 
                        hide_index=True, 
                        use_container_width=True,
                        column_config={
                            "Fait": st.column_config.CheckboxColumn("État", default=False),
                            "Tâche": st.column_config.TextColumn("Détail")
                        }
                    )

                    # Sauvegarde auto si on coche une case
                    if not edited_df.equals(pd.DataFrame(data_list)):
                        new_desc = "\n".join([f"{'✅ | ' if r['Fait'] else ''}{r['Tâche']}" for _, r in edited_df.iterrows()])
                        df_memos.at[idx, 'Description'] = new_desc
                        sauvegarder_data(df_memos, 'memos.json')
                        st.rerun()

                # --- BARRE D'OUTILS (ACTIONS) ---
                btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
                
                if btn_c1.button("✏️ Modifier", key=f"edit_btn_{idx}"):
                    st.session_state.memo_edit_id = idx
                    st.rerun()
                    
                if btn_c2.button("📦 Archive", key=f"arch_btn_{idx}"):
                    df_memos.at[idx, 'Archive'] = "Archivé"
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()
                
                with btn_c3:
                    texte_impr = str(row['Description']).replace("✅ | ", "[FAIT] ")
                    bouton_imprimer_fiche(row['Date'], texte_impr, stat_val)

                # Suppression avec double confirmation
                conf_del_key = f"del_confirm_{idx}"
                if not st.session_state.get(conf_del_key, False):
                    if btn_c4.button("🗑️ Suppr", key=f"del_pre_{idx}"):
                        st.session_state[conf_del_key] = True
                        st.rerun()
                else:
                    sub_c1, sub_c2 = btn_c4.columns(2)
                    if sub_c1.button("✅", key=f"del_yes_{idx}", type="primary"):
                        df_memos = df_memos.drop(idx).reset_index(drop=True)
                        sauvegarder_data(df_memos, 'memos.json')
                        st.session_state[conf_del_key] = False
                        st.rerun()
                    if sub_c2.button("❌", key=f"del_no_{idx}"):
                        st.session_state[conf_del_key] = False
                        st.rerun()
                
                st.divider()

    # --- PIED DE PAGE : SIGNATURE ---
    st.write("")
    if st.button("🖋️ Signer le rapport de bord"):
        signature = f"VALIDÉ PAR SKIPPER VESTA - {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        st.info(signature)


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

            # --- CAS 1 : MODE RÉEL (À ce jour) ---
            if mode_bilan == "À ce jour":
                # On ne prend que ce qui est payé ET qui n'est pas annulé/en attente
                # Le statut doit être "Terminé" ou similaire (selon tes labels)
                est_fini = "TERMINÉ" in statut or "FAIT" in statut or "ARCHIVÉ" in statut
                return paiement == "PAID" and est_fini

            # --- CAS 2 : MODE ESTIMATION (Année Complète) ---
            else:
                # On exclut uniquement les brouillons ou les annulations
                if "LISTE D'ATTENTE" in statut or "ANNULÉ" in statut: 
                    return False
                # On prend tout le reste (En cours, Confirmé, Payé, CMN, etc.)
                return True
 

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
# --- 12. PAGE LIVRE DE BORD (LOG) - VERSION EXPERT ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>📖 Livre de Bord & Statistiques</h1></div>', unsafe_allow_html=True)

    df_log = charger_data_safe('logbook.json')
    
    if 'saisie_ouverte' not in st.session_state: st.session_state.saisie_ouverte = False
    if 'display_edit' not in st.session_state: st.session_state.display_edit = False

    # --- 1. SAISIE RAPIDE AMÉLIORÉE (MÉTÉO & NOTES) ---
    if not st.session_state.saisie_ouverte:
        st.button("➕ NOUVELLE NAVIGATION", on_click=lambda: st.session_state.update({"saisie_ouverte": True}), use_container_width=True)
    
    with st.expander("🚀 Formulaire de Saisie", expanded=st.session_state.saisie_ouverte):
        with st.form(key="form_nav_expert"):
            c1, c2 = st.columns(2)
            f_date = c1.date_input("Date de début", datetime.now())
            f_jours = c2.number_input("Nombre de jours", min_value=1, value=1)
            f_but = st.text_input("Nom du Voyage")
            f_equipage = st.text_area("Équipage", height=60)
            
            # Nouveaux champs
            c_m1, c_m2 = st.columns(2)
            f_meteo = c_m1.text_input("Météo (Vent/Mer)", placeholder="ex: NW 12-15kts, belle")
            f_notes = c_m2.text_area("Observations / Souvenirs", height=60)
            
            st.markdown("---")
            last_mot = df_log['MotArr'].max() if not df_log.empty else 0.0
            last_mil = df_log['MilArr'].max() if not df_log.empty else 0.0
            
            col1, col2, col3 = st.columns(3)
            m_dep = col1.number_input("Moteur Dép.", value=float(last_mot))
            m_arr = col2.number_input("Moteur Arr.", value=float(last_mot))
            h_voile = col3.number_input("Total Voile (h)", value=0.0)
            
            ck1, ck2 = st.columns(2)
            k_dep = ck1.number_input("Milles Dép.", value=float(last_mil))
            k_arr = ck2.number_input("Milles Arr.", value=float(last_mil))

            b_creer, b_annuler = st.columns(2)
            if b_creer.form_submit_button("💾 ENREGISTRER", use_container_width=True, type="primary"):
                dates_a_creer = [(f_date + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(int(f_jours))]
                if any(d in (df_log['Date'].tolist() if not df_log.empty else []) for d in dates_a_creer):
                    st.error("⚠️ Une navigation existe déjà à ces dates.")
                else:
                    nb_j = int(f_jours)
                    nouvelles = []
                    for i in range(nb_j):
                        nouvelles.append({
                            "Date": dates_a_creer[i], "Navigation": f_but, "Coéquipiers": f_equipage,
                            "Meteo": f_meteo, "Notes": f_notes,
                            "PortDep": "Escale", "PortArr": "Escale",
                            "MotDep": round(m_dep + ((m_arr-m_dep)/nb_j * i), 2),
                            "MotArr": round(m_dep + ((m_arr-m_dep)/nb_j * (i+1)), 2),
                            "TotalMot": round((m_arr-m_dep)/nb_j, 2),
                            "MilDep": round(k_dep + ((k_arr-k_dep)/nb_j * i), 2),
                            "MilArr": round(k_dep + ((k_arr-k_dep)/nb_j * (i+1)), 2),
                            "TotalMil": round((k_arr-k_dep)/nb_j, 2), 
                            "H_Voile": round(h_voile/nb_j, 2)
                        })
                    df_log = pd.concat([df_log, pd.DataFrame(nouvelles)], ignore_index=True)
                    sauvegarder_data(df_log, 'logbook.json')
                    st.session_state.saisie_ouverte = False
                    st.rerun()
            if b_annuler.form_submit_button("❌ ANNULER"):
                st.session_state.saisie_ouverte = False
                st.rerun()

    # --- 2. AFFICHAGE GROUPÉ AVEC BILAN (IDÉE 1) ---
    if not df_log.empty:
        st.divider()
        df_v = df_log.copy()
        df_v['dt'] = pd.to_datetime(df_v['Date'], dayfirst=True, errors='coerce')
        df_v = df_v.sort_values(by=['dt', 'Navigation'], ascending=[False, False])

        for nav_name, group in df_v.groupby('Navigation', sort=False):
            # Calculs du voyage
            t_mil = group['TotalMil'].sum()
            t_mot = group['TotalMot'].sum()
            t_voile = group['H_Voile'].sum()
            total_h = t_mot + t_voile
            vitesse = round(t_mil / total_h, 1) if total_h > 0 else 0
            ratio_v = round((t_voile / total_h)*100) if total_h > 0 else 0
            
            st.markdown(f"""
                <div style="background:#2c3e50; color:white; padding:10px; border-radius:8px; margin-top:15px;">
                    <div style="display:flex; justify-content:space-between;">
                        <b>🚢 {nav_name or "Navigation"}</b>
                        <span>📍 {t_mil:.1f} NM | ⚡ {vitesse} kts moy.</span>
                    </div>
                    <div style="font-size:0.8em; color:#bdc3c7;">
                        📊 Ratio Voile: {ratio_v}% | Moteur: {t_mot:.1f}h | Voile: {t_voile:.1f}h
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            for idx, row in group.iterrows():
                with st.container():
                    st.markdown(f"""
                        <div style="background:white; border-left:4px solid #3498db; padding:8px 15px; margin-left:10px; border-bottom:1px solid #eee;">
                            <div style="display:flex; justify-content:space-between;">
                                <b>📅 {row['Date']}</b>
                                <span style="font-size:0.8em; color:red;">ID:{idx}</span>
                            </div>
                            <div style="font-size:0.9em; color:#2c3e50;">☁️ {row.get('Meteo','-')} | 📝 <small>{row.get('Notes','')}</small></div>
                            <div style="display:flex; justify-content:space-between; font-size:0.85em; margin-top:5px; color:#273c75;">
                                <span>⚙️ {row['TotalMot']:.1f}h mot.</span>
                                <span>⛵ {row['H_Voile']:.1f}h voile</span>
                                <b>{row['TotalMil']:.1f} NM</b>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    # --- 3. EXPORT CSV (IDÉE 2) ---
    if not df_log.empty:
        st.divider()
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Télécharger le Livre de Bord (Excel/CSV)", data=csv, file_name='livre_de_bord_vesta.csv', mime='text/csv', use_container_width=True)

    # --- 4. POSTE DE CONTRÔLE (BAS DE PAGE) ---
    # ... (Garder le code du poste de contrôle précédent ici) ...
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









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































