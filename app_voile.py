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
# --- 2. MENU MÉMOS (VERSION CORRIGÉE AVEC MODIFICATION ACTIVE) ---
# =================================================================
if st.session_state.page == "MEMOS":
    st.markdown("### 📝 Mémos & Notes de Bord")
    df_memos = charger_data_safe('memos.json')

    # Initialisation des états
    if 'memo_edit_id' not in st.session_state: st.session_state.memo_edit_id = None
    
    # --- A. FORMULAIRE DE MODIFICATION (S'AFFICHE SI ON CLIQUE SUR MODIFIER) ---
    if st.session_state.memo_edit_id is not None:
        idx_e = st.session_state.memo_edit_id
        row_e = df_memos.iloc[idx_e]
        
        st.warning(f"🔧 Modification du Mémo #{idx_e}")
        with st.form("form_edit_memo_global"):
            e_desc = st.text_area("Description", value=row_e['Description'])
            c1, c2 = st.columns(2)
            e_pay = c1.selectbox("Paiement", ["N/A", "À Payer", "Payé"], 
                                 index=["N/A", "À Payer", "Payé"].index(row_e.get('Paiement', 'N/A')))
            e_stat = c2.selectbox("Urgence", ["Normal", "Urgent", "Fait"], 
                                  index=["Normal", "Urgent", "Fait"].index(row_e.get('Statut', 'Normal')))
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.form_submit_button("✅ ENREGISTRER"):
                df_memos.at[idx_e, 'Description'] = e_desc
                df_memos.at[idx_e, 'Paiement'] = e_pay
                df_memos.at[idx_e, 'Statut'] = e_stat
                sauvegarder_data(df_memos, 'memos.json')
                st.session_state.memo_edit_id = None
                st.rerun()
            if col_b2.form_submit_button("❌ ANNULER"):
                st.session_state.memo_edit_id = None
                st.rerun()
        st.divider()

    # --- B. AJOUT D'UN NOUVEAU MÉMO ---
    with st.expander("➕ AJOUTER UN MÉMO OU UNE FACTURE", expanded=False):
        with st.form("new_memo_form_final", clear_on_submit=True):
            col1, col2 = st.columns(2)
            m_date = col1.text_input("Date", value=datetime.now().strftime("%d/%m/%Y"))
            m_pay = col2.selectbox("Statut Paiement", ["N/A", "À Payer", "Payé"])
            m_desc = st.text_area("Description")
            m_statut = st.selectbox("Urgence", ["Normal", "Urgent", "Fait"])
            if st.form_submit_button("💾 Enregistrer"):
                new_m = pd.DataFrame([{"Date": m_date, "Description": m_desc, "Statut": m_statut, "Paiement": m_pay, "Archive": "Non Archivé"}])
                df_memos = pd.concat([df_memos, new_m], ignore_index=True)
                sauvegarder_data(df_memos, 'memos.json')
                st.rerun()
    # --- C. LISTE DES MÉMOS (CORRECTION KEYERROR) ---
    # Sécurité : on s'assure que la colonne Archive existe avant de filtrer
    if 'Archive' not in df_memos.columns:
        df_memos['Archive'] = "Non Archivé"

    # Filtrage correct pour Pandas
    df_actifs = df_memos[df_memos['Archive'] == "Non Archivé"]
    
    if not df_actifs.empty:
        # Tri : les plus récents en haut
        for idx, row in df_actifs.sort_index(ascending=False).iterrows():
            est_fait = (row.get('Statut') == "Fait")
            bg = "#D5F5E3" if est_fait else ("#FADBD8" if row.get('Statut') == "Urgent" else "#FEF9E7")
            
            with st.container():
                c_check, c_text = st.columns([0.1, 0.9])
                
                # Case à cocher simplifiée
                val_check = c_check.checkbox("", value=est_fait, key=f"chk_v3_{idx}")
                
                # Si on clique sur la case, on met à jour le statut
                if val_check != est_fait:
                    df_memos.at[idx, 'Statut'] = "Fait" if val_check else "Normal"
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()

                with c_text:
                    p_label = f" | **{row.get('Paiement', 'N/A')}**" if row.get('Paiement') != "N/A" else ""
                    st.markdown(f"""
                    <div style="background:{bg}; padding:10px; border-radius:8px; border-left:5px solid #34495E; color:black;">
                        <small>{row.get('Date', '')} — <b>{str(row.get('Statut', '')).upper()}</b>{p_label}</small><br>
                        {row.get('Description', '')}
                    </div>
                    """, unsafe_allow_html=True)

                # Boutons d'action
                b1, b2, b3 = st.columns([1, 1, 1])
                if b1.button("✏️ Modifier", key=f"btn_ed_v3_{idx}"):
                    st.session_state.memo_edit_id = idx
                    st.rerun()
                
                if b2.button("📦 Archiver", key=f"btn_ar_v3_{idx}"):
                    df_memos.at[idx, 'Archive'] = "Archivé"
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()

                # Suppression avec sécurité
                conf_k = f"del_c_v3_{idx}"
                if st.session_state.get(conf_k):
                    if b3.button("⚠️ CONFIRMER ?", key=f"real_d_v3_{idx}", type="primary"):
                        df_memos = df_memos.drop(idx).reset_index(drop=True)
                        sauvegarder_data(df_memos, 'memos.json')
                        st.session_state[conf_k] = False
                        st.rerun()
                    if st.button("Annuler", key=f"ann_d_v3_{idx}"):
                        st.session_state[conf_k] = False
                        st.rerun()
                else:
                    if b3.button("🗑️ Supprimer", key=f"pre_d_v3_{idx}"):
                        st.session_state[conf_k] = True
                        st.rerun()
            st.divider()


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
# --- 12. PAGE LIVRE DE BORD (LOG) - SYNCHRONISÉE AVEC VOS DONNÉES ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>📖 Livre de Bord</h1></div>', unsafe_allow_html=True)

    df_log = charger_data_safe('logbook.json')
    
    # --- HARMONISATION DES COLONNES (Basé sur tes données réelles) ---
    # On s'assure que les colonnes de ton JSON sont bien reconnues par l'interface
    mapping = {
        'MotDep': 'MotDep', 'MotArr': 'MotArr', 'TotalMot': 'TotalMot',
        'MilDep': 'MilDep', 'MilArr': 'MilArr', 'TotalMil': 'TotalMil',
        'H_Voile': 'H_Voile', 'Coéquipiers': 'Coéquipiers', 'Navigation': 'Navigation'
    }
    
    for col in mapping.values():
        if col not in df_log.columns:
            df_log[col] = 0.0 if "Mot" in col or "Mil" in col or "H_" in col else ""

    # Conversion numérique pour les calculs de maintenance
    for col in ['TotalMot', 'TotalMil', 'MotDep', 'MotArr', 'MilDep', 'MilArr', 'H_Voile']:
        df_log[col] = pd.to_numeric(df_log[col], errors='coerce').fillna(0.0)

    if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
    if 'edit_id' not in st.session_state: st.session_state.edit_id = None

    # --- 1. FORMULAIRE DE SAISIE AVEC CLÉ DYNAMIQUE (ANTI-DOUBLON) ---
    if not st.session_state.edit_mode:
        # On crée une clé qui change à chaque seconde pour forcer le reset total après sauvegarde
        if 'form_key' not in st.session_state:
            st.session_state.form_key = str(int(time.time()))

        with st.expander("🚀 Enregistrer une Navigation", expanded=False):
            # La clé dynamique change après chaque st.rerun()
            with st.form(key=f"form_nav_{st.session_state.form_key}", clear_on_submit=True):
                c1, c2, c3 = st.columns([1, 1, 2])
                f_date = c1.date_input("Date départ", datetime.now())
                f_jours = c2.number_input("Nombre de jours", min_value=1, value=1)
                f_nav = c3.text_input("Nom du Voyage")
                f_coep = st.text_input("Coéquipiers")
                
                last_mot = df_log['MotArr'].max() if not df_log.empty else 0.0
                last_mil = df_log['MilArr'].max() if not df_log.empty else 0.0

                lignes = []
                for i in range(int(f_jours)):
                    lignes.append({
                        "Date": (f_date + timedelta(days=i)).strftime("%d/%m/%Y"),
                        "Dép": "", "Arr": "",
                        "Moteur Dép": last_mot if i == 0 else 0.0, "Moteur Arr": 0.0,
                        "Mille Dép": last_mil if i == 0 else 0.0, "Mille Arr": 0.0,
                        "Heures Voile": 0.0
                    })
                
                # On utilise aussi la clé dynamique ici pour l'éditeur
                edited_df = st.data_editor(pd.DataFrame(lignes), use_container_width=True, key=f"editor_{st.session_state.form_key}")

                submit_button = st.form_submit_button("💾 VALIDER ET FERMER LE FORMULAIRE", use_container_width=True, type="primary")

                if submit_button:
                    # Sécurité supplémentaire : on vérifie si l'utilisateur a rempli au moins une arrivée
                    nouvelles = []
                    for _, r in edited_df.iterrows():
                        if r['Arr'] and str(r['Arr']).strip() != "":
                            m_d, m_a = float(r['Moteur Dép']), float(r['Moteur Arr'])
                            mi_d, mi_a = float(r['Mille Dép']), float(r['Mille Arr'])
                            
                            nouvelles.append({
                                "Date": r['Date'], "Navigation": f_nav, "PortDep": r['Dép'], "PortArr": r['Arr'],
                                "Coéquipiers": f_coep, "MotDep": m_d, "MotArr": m_a, "TotalMot": round(m_a - m_d, 2),
                                "MilDep": mi_d, "MilArr": mi_a, "TotalMil": round(mi_a - mi_d, 2),
                                "H_Voile": float(r['Heures Voile']), "Group_ID": ""
                            })
                    
                    if nouvelles:
                        df_log = pd.concat([df_log, pd.DataFrame(nouvelles)], ignore_index=True)
                        sauvegarder_data(df_log, 'logbook.json')
                        
                        # ON CHANGE LA CLÉ pour forcer la destruction du formulaire au prochain passage
                        st.session_state.form_key = str(int(time.time()))
                        
                        st.success("✅ Enregistré !")
                        time.sleep(0.5)
                        st.rerun() # Ferme l'expander et réinitialise tout
                    else:
                        st.warning("⚠️ Veuillez saisir au moins un Port d'Arrivée.")

    # --- 2. AFFICHAGE DE L'HISTORIQUE ---
    if not df_log.empty:
        st.divider()
        df_v = df_log.copy()
        df_v['dt'] = pd.to_datetime(df_v['Date'], dayfirst=True, errors='coerce')
        df_v = df_v.sort_values(by='dt')

        # Logique de groupement par Coéquipiers
        blocs = []; current_bloc = []
        for i in range(len(df_v)):
            row = df_v.iloc[i]
            if not current_bloc: current_bloc.append(row)
            else:
                prev_row = current_bloc[-1]
                date_suivante = (row['dt'] - prev_row['dt']).days == 1
                meme_coep = str(row['Coéquipiers']).strip().lower() == str(prev_row['Coéquipiers']).strip().lower()
                if date_suivante and meme_coep and str(row['Coéquipiers']) != "": current_bloc.append(row)
                else:
                    blocs.append(current_bloc); current_bloc = [row]
        if current_bloc: blocs.append(current_bloc)

        for bloc in reversed(blocs):
            df_b = pd.DataFrame(bloc)
            if len(bloc) > 1:
                t_mil = df_b['TotalMil'].sum()
                t_mot = df_b['TotalMot'].sum()
                st.markdown(f"""
                    <div style="background:#eef2f7; color:#2c3e50; padding:12px; border-radius:10px; margin-bottom:10px; border-left: 8px solid #3498db;">
                        <div style="display:flex; justify-content:space-between; font-size:0.8rem; font-weight:bold;">
                            <span>🚢 {str(bloc[0]['Navigation']).upper() or "VOYAGE"}</span>
                            <span>⚙️ {t_mot:.1f}h Moteur | ⛵ {df_b['H_Voile'].sum():.1f}h Voile</span>
                        </div>
                        <div style="margin-top:5px;">
                            <b>Du {bloc[0]['Date']} au {bloc[-1]['Date']}</b><br>
                            <span style="font-size:0.9rem;">📍 {bloc[0]['PortDep']} → {bloc[-1]['PortArr']}</span>
                        </div>
                        <div style="text-align:right; margin-top:-15px;"><b style="font-size:1.3rem; color:#2980b9;">{t_mil:.1f} NM</b></div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                row = bloc[0]
                st.markdown(f"""
                    <div style="background:white; border:1px solid #dee2e6; padding:10px; border-radius:5px; margin-bottom:5px; display:flex; justify-content:space-between;">
                        <span><b>{row['Date']}</b> : {row['PortDep']} → {row['PortArr']} <br>
                        <small>⚙️ {row['TotalMot']}h mot. | ⛵ {row['H_Voile']}h voile | 👥 {row['Coéquipiers']}</small></span>
                        <b style="color:#27ae60;">{row['TotalMil']} NM</b>
                    </div>
                """, unsafe_allow_html=True)
    # --- 3. ADMINISTRATION (MODIFIER / SUPPRIMER AVEC SÉCURITÉ) ---
    with st.expander("🛠️ Gérer et Modifier les données", expanded=st.session_state.edit_mode):
        if not df_log.empty:
            df_adm = df_log.copy()
            
            # --- FIX NAMEERROR: Définition explicite des colonnes à afficher ---
            cols_adm = ['Date', 'Navigation', 'Coéquipiers', 'TotalMot', 'TotalMil']
            
            # On vérifie que ces colonnes existent bien dans le fichier avant d'afficher
            cols_existantes = [c for c in cols_adm if c in df_adm.columns]
            st.dataframe(df_adm[cols_existantes], use_container_width=True)
            
            c_sel, c_mod, c_sup = st.columns([1, 1, 1])
            sel_idx = c_sel.number_input("Sélectionner l'ID ligne", min_value=0, max_value=len(df_log)-1, step=1)
            
            # --- BOUTON MODIFIER ---
            if c_mod.button("✏️ MODIFIER", use_container_width=True):
                st.session_state.edit_mode = True
                st.session_state.edit_id = sel_idx
                st.rerun()

            # --- SYSTÈME DE SUPPRESSION AVEC CONFIRMATION ---
            confirm_key = f"confirm_del_{sel_idx}"
            if confirm_key not in st.session_state:
                st.session_state[confirm_key] = False

            if not st.session_state[confirm_key]:
                if c_sup.button("🗑️ SUPPRIMER", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()
            else:
                c_conf, c_annul = st.columns(2)
                if c_conf.button("⚠️ CONFIRMER ?", use_container_width=True, type="primary"):
                    df_log = df_log.drop(index=sel_idx).reset_index(drop=True)
                    sauvegarder_data(df_log, 'logbook.json')
                    st.session_state[confirm_key] = False
                    st.success(f"Ligne {sel_idx} supprimée.")
                    time.sleep(0.5)
                    st.rerun()
                if c_annul.button("❌ Annuler"):
                    st.session_state[confirm_key] = False
                    st.rerun()
    # --- FORMULAIRE DE MODIFICATION (VERSION FIABLE SANS TABLEAU) ---
        if st.session_state.edit_mode:
            st.divider()
            st.markdown(f"### ✏️ Modification de la ligne ID: {st.session_state.edit_id}")
            row_e = df_log.iloc[st.session_state.edit_id]
            
            with st.form("form_edit_log_simple"):
                # 1. Infos Générales
                c1, c2, c3 = st.columns(3)
                m_date = c1.text_input("Date (JJ/MM/AAAA)", value=str(row_e.get('Date', '')))
                m_nav = c2.text_input("Nom de la Croisière", value=str(row_e.get('Navigation', '')))
                m_coep = c3.text_input("Coéquipiers", value=str(row_e.get('Coéquipiers', '')))
                
                # 2. Trajet
                ct1, ct2 = st.columns(2)
                m_pdep = ct1.text_input("Port de Départ", value=str(row_e.get('PortDep', '')))
                m_parr = ct2.text_input("Port d'Arrivée", value=str(row_e.get('PortArr', '')))
                
                # 3. Compteurs (Moteur et Milles)
                st.markdown("**📊 Relevés Compteurs**")
                cm1, cm2, cm3 = st.columns(3)
                m_mot_d = cm1.number_input("Moteur Départ", value=float(row_e.get('MotDep', 0.0)), format="%.1f")
                m_mot_a = cm2.number_input("Moteur Arrivée", value=float(row_e.get('MotArr', 0.0)), format="%.1f")
                m_h_voile = cm3.number_input("Heures Voile", value=float(row_e.get('H_Voile', 0.0)), format="%.1f")
                
                ck1, ck2 = st.columns(2)
                m_mil_d = ck1.number_input("Milles Départ", value=float(row_e.get('MilDep', 0.0)), format="%.1f")
                m_mil_a = ck2.number_input("Milles Arrivée", value=float(row_e.get('MilArr', 0.0)), format="%.1f")
                
                st.divider()
                c_val, c_ann = st.columns(2)
                
                if c_val.form_submit_button("✅ ENREGISTRER LES MODIFICATIONS", use_container_width=True, type="primary"):
                    idx = st.session_state.edit_id
                    
                    # Mise à jour directe (plus de risque de conflit avec le data_editor)
                    df_log.at[idx, 'Date'] = m_date
                    df_log.at[idx, 'Navigation'] = m_nav
                    df_log.at[idx, 'Coéquipiers'] = m_coep
                    df_log.at[idx, 'PortDep'] = m_pdep
                    df_log.at[idx, 'PortArr'] = m_parr
                    
                    df_log.at[idx, 'MotDep'] = m_mot_d
                    df_log.at[idx, 'MotArr'] = m_mot_a
                    df_log.at[idx, 'TotalMot'] = round(m_mot_a - m_mot_d, 2)
                    
                    df_log.at[idx, 'MilDep'] = m_mil_d
                    df_log.at[idx, 'MilArr'] = m_mil_a
                    df_log.at[idx, 'TotalMil'] = round(m_mil_a - m_mil_d, 2)
                    
                    df_log.at[idx, 'H_Voile'] = m_h_voile
                    
                    sauvegarder_data(df_log, 'logbook.json')
                    st.session_state.edit_mode = False
                    st.success("✅ Modification enregistrée !")
                    time.sleep(0.5)
                    st.rerun()

                if c_ann.form_submit_button("❌ ANNULER", use_container_width=True):
                    st.session_state.edit_mode = False
                    st.rerun()
        else:
            st.info("Aucune donnée à gérer.")

 

# --- FIN DU FICHIER ---









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































