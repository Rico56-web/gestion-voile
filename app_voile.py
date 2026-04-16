import requests, base64, json, time, os, html, io
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
from datetime import datetime, date, timedelta
import calendar

# --- INITIALISATION DU SESSION STATE (Ménage de début de script) ---
if 'log_edit_idx' not in st.session_state:
    st.session_state.log_edit_idx = None

# Vous pouvez faire de même pour les autres modes d'édition si vous en avez
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
# =================================================================
# --- 1. FONCTIONS DE SÉCURITÉ UNIVERSELLES ---
# =================================================================

def clean_num(val, default=0):
    """Nettoie les prix et nombres (gère €, espaces et nan)"""
    try:
        if pd.isna(val) or str(val).lower() in ["nan", "", "none"]: 
            return default
        # Nettoyage des caractères parasites
        clean_val = str(val).replace('€','').replace(' ','').replace(',','.').strip()
        return int(float(clean_val))
    except:
        return default

def clean_text(val):
    """Nettoie les textes et évite les injections HTML dans les notes"""
    if val is None or pd.isna(val): return ""
    v = str(val).replace('nan', '').replace('None', '').strip()
    if "<div" in v or "<a " in v: 
        return "Note à corriger (HTML détecté)"
    return v if v else "---"

def preparer_log_safe(df):
    """Garantit que le DataFrame des logs possède les colonnes minimales pour éviter les crashs"""
    cols_requises = ['Date', 'PortDep', 'PortArr', 'Bateau', 'Skipper', 'Action', 'Details']
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=cols_requises)
    for col in cols_requises:
        if col not in df.columns: 
            df[col] = ""
    return df

def format_tel_lien(tel):
    """Prépare le numéro pour les liens cliquables tel:"""
    if not tel: return ""
    return "".join(filter(str.isdigit, str(tel)))

def formater_date_affichage(date_val):
    """Convertit les dates ISO en format français JJ/MM/AAAA"""
    if pd.isna(date_val) or str(date_val).strip() in ["", "None", "nan"]: 
        return "---"
    try: 
        return datetime.strptime(str(date_val)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except: 
        return str(date_val)

# =================================================================
# --- 2. GESTION GITHUB (BASE DE DONNÉES) ---
# =================================================================

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: 
        return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        
        # Nettoyage du DataFrame avant export JSON
        df_export = df.copy()
        content = base64.b64encode(df_export.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
        
        requests.put(url, headers={"Authorization": f"token {token}"}, 
                     json={"message": f"Update {file}", "content": content, "sha": sha})
    except Exception as e: 
        st.error(f"Erreur sauvegarde {file} : {e}")
        
    # --- 3. SÉCURISATION (La nouvelle fonction) ---
def charger_data_safe(fichier):
    try:
        data = charger_data(fichier)
        if data is None or (isinstance(data, list) and len(data) == 0):
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Erreur sur {fichier}: {e}")
        return pd.DataFrame()
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
# --- SESSION & SÉCURITÉ ---
# =================================================================
keys_to_init = {
    'authenticated': False, 'page': "CONTACTS", 'edit_idx': None, 
    'vue_contact': "En cours"
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
# --- NAVIGATION (VERSION CORRIGÉE) ---
# =================================================================
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

# 1. Mise à jour de la liste (Ajout de FACTURES)
# J'ai raccourci "FACTURES" en "FACT" pour que ça tienne bien sur mobile
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "LOG", "FACT"]

# 2. Mise à jour des icônes
icones = {
    "CONTACTS": "👤", 
    "PLANNING": "🗓️", 
    "STATS": "📊", 
    "MAINT": "🛠️", 
    "LOG": "📖",
    "FACT": "📑"   # Nouvelle icône pour la facturation
}

# 3. Génération des colonnes de navigation
cols_nav = st.columns(len(menu))

for i, name in enumerate(menu):
    # Mapping du nom court (FACT) vers le nom de page utilisé dans votre code (FACTURES)
    page_target = "FACTURES" if name == "FACT" else name
    
    # Détermination du style (Bleu "Primary" si on est sur la page)
    is_active = st.session_state.page == page_target
    
    if cols_nav[i].button(
        f"{icones[name]}\n{name}", # Affiche l'icône ET le nom en dessous
        key=f"nav_{name}", 
        use_container_width=True, 
        type="primary" if is_active else "secondary"
    ):
        st.session_state.page = page_target
        st.rerun()

st.divider()


# =================================================================
# --- 5. BLOC CONTACTS (V98 - RESTAURATION COMPLÈTE + AUTO-EDIT) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.markdown('<h2 style="text-align:center;">⚓ Gestion des Clients Vesta</h2>', unsafe_allow_html=True)

    # 1. Chargement
    df_raw = charger_data('contacts.json')
    
    # Boutons de navigation (Placés en haut pour être toujours visibles)
    n1, n2, n3, n4 = st.columns(4)
    
    if n4.button("➕ NOUVEAU", use_container_width=True):
        new_r = {
            "Prénom": "NOUVEAU", "Nom": "CLIENT", "Statut": "Ok", 
            "Paiement": "Unpaid", "Relancer": "Non", "DateNav": "01/06/2026", 
            "Société": "PERSO", "Jours": 1, "Prix": 0, "Acompte": 0,
            "Notes": "", "Téléphone": "", "Email": "", "Pers": 1
        }
        df_actuel = charger_data('contacts.json')
        df_new = pd.concat([pd.DataFrame([new_r]), df_actuel], ignore_index=True)
        sauvegarder_data(df_new, 'contacts.json')
        
        # Redirection immédiate vers l'édition de la fiche 0 (la nouvelle)
        st.session_state.edit_idx = 0 
        st.session_state.page = "MODIFIER_CONTACT"
        st.rerun()

    # 2. Nettoyage et Filtrage
    if not df_raw.empty:
        df_c = df_raw.copy()
        df_c = df_c.fillna("")
        
        df_c['DateNav'] = df_c['DateNav'].apply(lambda x: "" if str(x).lower() in ['nan', 'none', 'nat'] else str(x))
        df_c['orig_idx'] = df_c.index
        df_c['dt_sort'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
        
        if 'Relancer' not in df_c.columns: df_c['Relancer'] = "Non"
        
        c_search, c_yr = st.columns([2, 1])
        search = c_search.text_input("🔍 Rechercher...", "").upper()
        annee_sel = c_yr.selectbox("Saison", [2026, 2027, 2028], index=0)
        
        mask = (df_c['dt_sort'].dt.year == annee_sel) | (df_c['dt_sort'].isna()) | (df_c['DateNav'] == "")
        df_c = df_c[mask].copy()
        
        if search:
            mask_s = df_c['Nom'].astype(str).str.upper().str.contains(search) | df_c['Prénom'].astype(str).str.upper().str.contains(search)
            df_c = df_c[mask_s]
        
        # TRI CHRONOLOGIQUE INVERSE (Le plus récent/futur en haut)
        # On utilise 'ascending=False' pour que 2027 soit avant 2026, 
        # et que Décembre soit avant Janvier.
        df_c = df_c.sort_values(by='dt_sort', ascending=True)
        

        # Onglets
        if n1.button("🟢 EN COURS", use_container_width=True, type="primary" if st.session_state.vue_contact == "En cours" else "secondary"): 
            st.session_state.vue_contact = "En cours"; st.rerun()
        if n2.button("⌛ ATTENTE", use_container_width=True, type="primary" if st.session_state.vue_contact == "Attente" else "secondary"): 
            st.session_state.vue_contact = "Attente"; st.rerun()
        if n3.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Archives" else "secondary"): 
            st.session_state.vue_contact = "Archives"; st.rerun()

        st.divider()
        
       # --- NOUVELLE LOGIQUE DE TRI DES ONGLETS ---
        statut_clean = df_c['Statut'].fillna("").str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        relance_clean = df_c['Relancer'].fillna("Non").str.upper()
        
        if st.session_state.vue_contact == "Archives":
            # ARCHIVES : Terminé, Annulé, Refusé (et pas de relance OUI)
            mask_aff = (statut_clean.str.contains("termine|annule|refuse")) & (relance_clean != "OUI")
            tri_ordre = False 

        elif st.session_state.vue_contact == "Attente":
            # ATTENTE : Uniquement "Liste d'attente" OU (Terminé + Relance Oui)
            # On exclut le "En attente" simple ici
            mask_aff = (statut_clean == "liste d'attente") | ((statut_clean.str.contains("termine")) & (relance_clean == "OUI"))
            tri_ordre = True  

        else:
            # EN COURS : Tout le reste, incluant désormais "En attente"
            # On retire les archives et la liste d'attente
            mask_aff = ~(statut_clean.str.contains("termine|annule|refuse")) & (statut_clean != "liste d'attente")
            tri_ordre = True

        # On applique le filtre
        df_aff = df_c[mask_aff].copy()

        # --- LE FIX : ON TRIE ICI POUR QUE ÇA MARCHE DANS TOUS LES ONGLETS ---
        if not df_aff.empty:
            df_aff = df_aff.sort_values(by='dt_sort', ascending=tri_ordre)

        # 4. BOUCLE D'AFFICHAGE
        for _, row in df_aff.iterrows():
            # ... (Gardez ici tout votre code card_html identique à avant) ...
    
            idx = row['orig_idx']
            pre = str(row.get('Prénom', '')).upper()
            nom = str(row.get('Nom', '')).upper()
            sta_clean = str(row.get('Statut', 'OK')).upper()
            soc = str(row.get('Société', 'PERSO')).upper()
            tel = str(row.get('Téléphone', ''))
            note = str(row.get('Notes', ''))
            date_aff = str(row.get('DateNav', '---'))
            
            # Calcul financier rapide
            prix = float(str(row.get('Prix', 0)).replace('€','').replace(' ','') or 0)
            aco = float(str(row.get('Acompte', 0)).replace('€','').replace(' ','') or 0)
            reste = prix - aco
            # --- FIX AFFICHAGE : On écoute uniquement le statut enregistré ---
            val_paye = str(row.get('Paiement', 'UNPAID')).upper()
            p_color = "green" if val_paye == "PAID" else "#E74C3C"
            p_label = "PAYÉ" if val_paye == "PAID" else "NON PAYÉ"

            # Background selon société ou statut
            bg = "#D6EAF8" if soc == "CMN" else "#D5F5E3"
            if "ATTENTE" in sta_clean: bg = "#FCF3CF"
            
            t_url = tel.replace(' ', '').replace('+', '')

            card_html = f"""
            <div style="background-color:{bg}; padding:15px; border-radius:12px; border:1px solid #ccc; margin-bottom:10px; color:#2C3E50;">
                <div style="display:flex; justify-content:space-between; font-weight:bold; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:5px;">
                    <span>#{idx} | {pre} {nom}</span>
                    <span style="background:white; padding:0 8px; border-radius:5px; font-size:0.75rem;">{soc}</span>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; font-size:0.85rem; margin-top:10px; gap:5px;">
                    <div>📅 Date: <b>{date_aff}</b></div>
                    <div>📊 Statut: <b>{sta_clean}</b></div>
                    <div>💰 Prix: <b>{prix:.0f} €</b></div>
                    <div style="color:{p_color}; font-weight:bold;">🏷️ {p_label}</div>
                </div>
                <div style="margin-top:12px; display:flex; gap:10px;">
                    <a href="tel:{t_url}" style="flex:1; background:#5DADE2; color:white !important; text-align:center; padding:8px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:0.75rem;">📞 APPEL</a>
                    <a href="https://wa.me/{t_url}" style="flex:1; background:#52BE80; color:white !important; text-align:center; padding:8px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:0.75rem;">💬 WA</a>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button(f"ÉDITER #{idx}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.session_state.page = "MODIFIER_CONTACT"
                st.rerun()
            if c2.button(f"SUPPRIMER #{idx}", key=f"del_{idx}", use_container_width=True):
                df_db = charger_data('contacts.json').drop(idx).reset_index(drop=True)
                sauvegarder_data(df_db, 'contacts.json')
                st.rerun()
    else:
        st.info("La base de données est vide.")
# =================================================================
# --- 6. PAGE MODIFIER CONTACT (V96 - FIX SOCIÉTÉ & PAIEMENT) ---
# =================================================================
if st.session_state.page == "MODIFIER_CONTACT":
    st.markdown('<h3 style="text-align:center;">✏️ Modifier le Contact</h3>', unsafe_allow_html=True)
    
    idx_to_edit = st.session_state.get('edit_idx')
    df_m = charger_data('contacts.json')

    if idx_to_edit is not None and not df_m.empty and idx_to_edit in df_m.index:
        row = df_m.loc[idx_to_edit]
        
        with st.form("form_edit_v96"):
            # Ligne 1 : Identité
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=str(row.get('Prénom', '')))
            new_nom = c2.text_input("Nom", value=str(row.get('Nom', '')))
            
            # Ligne 2 : Date et Société (MODIFIÉ : Menu Déroulant)
            c3, c4 = st.columns(2)
            new_date = c3.text_input("Date (JJ/MM/AAAA)", value=str(row.get('DateNav', '')))
            
            # --- LOGIQUE SOCIÉTÉ ---
            liste_soc = ["PERSO", "CLICK", "CMN", "VOG"]
            curr_soc = str(row.get('Société', 'PERSO')).upper().strip()
            # Si la société en base n'est pas dans la liste, on l'ajoute temporairement pour ne pas perdre l'info
            if curr_soc not in liste_soc and curr_soc != "":
                liste_soc.append(curr_soc)
            soc_idx = liste_soc.index(curr_soc) if curr_soc in liste_soc else 0
            new_soc = c4.selectbox("Société", liste_soc, index=soc_idx)
            
            # Ligne 3 : Contacts
            c5, c6 = st.columns(2)
            new_tel = c5.text_input("Téléphone", value=str(row.get('Téléphone', '')))
            new_mail = c6.text_input("Email", value=str(row.get('Email', '')))
            
            # Ligne 4 : Logistique
            cl1, cl2 = st.columns(2)
            new_jours = cl1.number_input("Nombre de jours", value=clean_num(row.get('Jours', 0)), min_value=0)
            new_pers = cl2.number_input("Nombre de personnes", value=clean_num(row.get('Pers', 0)), min_value=0)
            
            # Ligne 5 : Finances
            f1, f2 = st.columns(2)
            new_prix = f1.number_input("Prix Total (€)", value=clean_num(row.get('Prix', 0)))
            new_aco = f2.number_input("Acompte (€)", value=clean_num(row.get('Acompte', 0)))
            
            # Ligne 6 : Statuts & Options
            s1, s2 = st.columns(2)
            s_list = ["En attente", "Confirmé", "Terminé", "Annulé", "Refusé", "Liste d'attente"]
            curr_s = str(row.get('Statut', 'En attente')).capitalize()
            if "liste" in curr_s.lower(): curr_s = "Liste d'attente"
            s_idx = s_list.index(curr_s) if curr_s in s_list else 0
            new_statut = s1.selectbox("Statut Mission", s_list, index=s_idx)
            
            # Sous-colonnes pour Paiement et Relance
            sub1, sub2 = s2.columns(2)
            
            # --- FIX PAIEMENT DANS LE FORMULAIRE ---
            val_p_brute = str(row.get('Paiement', 'Unpaid')).strip()
            p_list = ["Unpaid", "Paid"]

            # On force l'index 1 uniquement si c'est écrit "Paid" exactement
            p_idx = 1 if val_p_brute.upper() == "PAID" else 0
            new_pay = sub1.selectbox("Paiement", p_list, index=p_idx)
            
            # Option Relance
            val_r = str(row.get('Relancer', 'Non')).strip().capitalize()
            new_relance = sub2.selectbox("À recontacter ?", ["Non", "Oui"], index=1 if val_r == "Oui" else 0)
            
            new_notes = st.text_area("Notes", value=str(row.get('Notes', '')).replace('nan',''))

            submitted = st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True)
            
            if submitted:
                maj = {
                    'Prénom': new_pre.upper(),
                    'Nom': new_nom.upper(),
                    'DateNav': new_date,
                    'Société': new_soc.upper(), # Sauvegarde la sélection du menu
                    'Téléphone': new_tel.strip(),
                    'Email': new_mail.strip(),
                    'Jours': int(new_jours),
                    'Pers': int(new_pers),
                    'Prix': int(new_prix),
                    'Acompte': int(new_aco),
                    'Statut': new_statut,
                    'Paiement': new_pay,
                    'Relancer': new_relance,
                    'Notes': str(new_notes).strip()
                }
                
                df_m.loc[idx_to_edit, maj.keys()] = list(maj.values())
                sauvegarder_data(df_m, 'contacts.json')
                st.success("Fiche mise à jour !")
                st.session_state.page = "CONTACTS"
                st.rerun()

    if st.button("⬅️ RETOUR"):
        st.session_state.page = "CONTACTS"
        st.rerun()
# =================================================================
# --- 6. PAGE PLANNING (V18.5 - FIX ORDRE CHARGEMENT) ---
# =================================================================
if st.session_state.page == "PLANNING":
    from datetime import datetime, date, timedelta
    import calendar
    import pandas as pd

    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING</h1></div>', unsafe_allow_html=True)
    
    if st.button("📂 ACCÉDER AUX ARCHIVES", key="k_arch_p", use_container_width=True):
        st.session_state.last_page = "PLANNING"; st.session_state.page = "ARCHIVES"; st.rerun()

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
    sel_y = c_y.selectbox("Année", [2026, 2027, 2028], index=[2026, 2027, 2028].index(st.session_state.curr_year))
    st.session_state.curr_year = sel_y

    if c_n.button("📍 ICI", use_container_width=True):
        st.session_state.curr_month_idx = aujourdhui.month - 1
        st.session_state.curr_year = aujourdhui.year
        st.rerun()

    # --- ÉTAPE 1 : CHARGEMENT ---
    df_p = charger_data('contacts.json')

    # --- ÉTAPE 2 : TRAITEMENT ---
    if df_p is not None and not df_p.empty:
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
                prix_val = float(str(r.get('Prix', '0')).replace('€','').replace(' ','').strip() or 0)

                # Couleurs
                if "CMN" in soc: color = "#3498db"
                elif any(x in statut for x in ["annul", "refus"]): color = "#bdc3c7"
                elif dt_start < aujourdhui: color = "#34495e"
                else: color = "#27ae60"

                # Remplissage calendrier
                for i in range(n_j):
                    curr = dt_start + timedelta(days=i)
                    if curr.month == sel_m and curr.year == sel_y:
                        jours_occ[curr.day] = {"c": color}

                # Ajout à la liste
                if (dt_start.year == sel_y and dt_start.month == sel_m) or (dt_end.year == sel_y and dt_end.month == sel_m):
                    missions_list.append({
                        'r': r, 'idx': idx, 'start': dt_start, 'end': dt_end, 
                        'n_j': n_j, 'color': color, 'prix': prix_val, 'statut': statut
                    })
                    if dt_start.month == sel_m and not any(x in statut for x in ["annul", "refus"]):
                        total_mois += prix_val
            except: continue

    # --- ÉTAPE 3 : AFFICHAGE CALENDRIER ---
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
                    st.session_state.page = "MODIFIER_CONTACT"; st.rerun()
        st.success(f"**💰 Total prévisionnel {sel_m_nom} : {total_mois:,.0f} €**".replace(",", " "))
    else:
        st.info("Aucune mission ce mois-ci.")
        
# =================================================================
# --- 7. PAGE STATS (SYNCHRO FINANCES & MAINTENANCE) ---
# =================================================================
if st.session_state.page == "STATS":
    st.markdown('<h2 style="text-align:center;">📊 Vesta Skipper 2026</h2>', unsafe_allow_html=True)

    # 1. Chargement des sources
    df_actif = charger_data_safe('contacts.json')
    df_arch = charger_data_safe('archives_planning.json')
    df_m = charger_data_safe('maintenance.json') 
    
    # Fusion des revenus
    df_all = pd.concat([df_actif, df_arch], ignore_index=True) if not df_arch.empty else df_actif

    if not df_all.empty:
        # --- A. CONFIGURATION ---
        col_sel1, col_sel2 = st.columns(2)
        mode_bilan = col_sel1.radio("Période :", ["À ce jour", "Année Complète"], horizontal=True)
        sel_y = col_sel2.selectbox("Année :", [2025, 2026, 2027], index=1)

        # --- B. RADAR DE DATE ---
        def radar_date(row):
            val = str(row.get('DateNav', '')).replace('\\/', '/').strip().split(' ')[0]
            if val and val.lower() not in ["nan", "", "none"]:
                dt = pd.to_datetime(val, dayfirst=True, errors='coerce')
                if pd.isnull(dt): dt = pd.to_datetime(val, errors='coerce')
                return dt
            return pd.NaT

        df_all['dt_vrai'] = df_all.apply(radar_date, axis=1)
        df_filtre = df_all[df_all['dt_vrai'].dt.year == sel_y].copy()

        # --- C. FILTRAGE REVENUS ---
        def est_comptabilise(row):
            soc = str(row.get('Société', '')).strip().upper()
            paiement = str(row.get('Paiement', '')).strip().upper()
            statut = str(row.get('Statut', '')).strip().upper()
            if "LISTE D'ATTENTE" in statut: return False
            if "CMN" in soc: return True
            return paiement == "PAID"

        df_final = df_filtre[df_filtre.apply(est_comptabilise, axis=1)].copy() if not df_filtre.empty else pd.DataFrame()
        
        if mode_bilan == "À ce jour" and not df_final.empty:
            today = pd.Timestamp.now().normalize()
            df_final = df_final[df_final['dt_vrai'] <= today].copy()

        # --- D. CALCUL DES DÉPENSES ---
        total_dep = 0.0
        df_dep_final = pd.DataFrame()

        if not df_m.empty:
            df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
            mask_dep = (df_m['dt_maint'].dt.year == sel_y) & (df_m['Statut'] == "Fait")
            
            if mode_bilan == "À ce jour":
                today = pd.Timestamp.now().normalize()
                mask_dep = mask_dep & (df_m['dt_maint'] <= today)
            
            df_dep_final = df_m[mask_dep].copy()
            
            def force_float_m(val):
                s = str(val).replace('€', '').replace(' ', '').replace('\xa0', '').replace(',', '.')
                try: return float(s)
                except: return 0.0

            total_dep = df_dep_final['M_Num'].apply(force_float_m).sum()
            
            # --- E. AFFICHAGE FINAL (AVEC TOTAUX SOUS TABLEAUX) ---
        st.divider()
        
        # Calculs CA et Net (déjà faits plus haut, on les réutilise)
        total_ca = df_final['Prix'].apply(force_float_m).sum() if not df_final.empty else 0.0
        net = total_ca - total_dep

        # KPI principaux
        c1, c2 = st.columns(2)
        c1.metric("💰 CA Brut", f"{total_ca:,.0f} €".replace(',', ' '))
        c2.metric("⚖️ Revenu Net", f"{net:,.0f} €".replace(',', ' '))

        # --- TABLEAU REVENUS ---
        st.write("---")
        if not df_final.empty:
            st.subheader("📄 Détail des Revenus")
            df_final['D'] = df_final['dt_vrai'].dt.strftime('%d/%m')
            st.dataframe(df_final[['D', 'Société', 'Prix']], hide_index=True, use_container_width=True)
            # Affichage du total juste en dessous
            st.markdown(f"<div style='text-align:right; font-weight:bold; color:#2e7d32;'>Total Revenus : {total_ca:,.2f} €</div>", unsafe_allow_html=True)

        # --- TABLEAU DÉPENSES ---
        if not df_dep_final.empty:
            st.write("")
            st.subheader("💸 Détail des Dépenses")
            df_dep_final['D'] = df_dep_final['dt_maint'].dt.strftime('%d/%m')
            st.dataframe(df_dep_final[['D', 'Objet', 'M_Num']], hide_index=True, use_container_width=True)
            # Affichage du total juste en dessous
            st.markdown(f"<div style='text-align:right; font-weight:bold; color:#c62828;'>Total Dépenses : {total_dep:,.2f} €</div>", unsafe_allow_html=True)


# =================================================================
# --- 8. PAGE MAINTENANCE (CHRONOLOGIQUE & FILTRÉE) ---
# =================================================================
if st.session_state.page == "MAINT":
    import pandas as pd
    from datetime import datetime

    df_m = charger_data_safe('maintenance.json')
    df_log = charger_data_safe('logbook.json')

    # --- 1. CALCULS HEURES ---
    releve_h = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if not df_log.empty else 0
    params = charger_params() if 'charger_params' in globals() else {"cible_vidange": 2450.0}

    st.title("🛠️ MAINTENANCE")

    # --- 2. FILTRES ---
    col_sel1, col_sel2 = st.columns(2)
    mode_maint = col_sel1.radio("Période :", ["À ce jour", "Année Complète"], horizontal=True)
    sel_y = col_sel2.selectbox("Année :", [2025, 2026, 2027], index=1)

    # --- 3. VIDANGE ---
    heures_restantes = params['cible_vidange'] - releve_h
    color_v = "#2e7d32" if heures_restantes > 15 else "#c62828"
    st.markdown(f"""<div style="background-color: {color_v}15; border: 1px solid {color_v}; padding: 10px; border-radius: 10px; text-align: center;">
        <span style="color: {color_v}; font-weight: bold;">{heures_restantes:.1f} h restantes</span> | Compteur : {releve_h:.1f} h
    </div>""", unsafe_allow_html=True)

    st.divider()

# --- 4. GESTION DU TABLEAU (MODIFICATION & SUPPRESSION SÉCURISÉE) ---
    if not df_m.empty:
        df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_filtre = df_m[df_m['dt_maint'].dt.year == sel_y].copy()
        
        if mode_maint == "À ce jour":
            today = pd.Timestamp.now().normalize()
            df_filtre = df_filtre[df_filtre['dt_maint'] <= today].copy()

        df_filtre = df_filtre.sort_values('dt_maint', ascending=False)

        st.subheader(f"📋 Suivi {sel_y}")
        
        # --- CALCUL DE LA HAUTEUR DYNAMIQUE ---
        # 35 pixels par ligne + environ 40 pixels pour l'en-tête
        nb_lignes = len(df_filtre)
        hauteur_calculee = (nb_lignes * 35) + 45 
        
        # On limite la hauteur minimale pour que ce ne soit pas trop écrasé
        hauteur_finale = max(hauteur_calculee, 150)

        # L'éditeur SANS ascenseur
        edited_df = st.data_editor(
            df_filtre.drop(columns=['dt_maint']),
            column_config={
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Objet": st.column_config.TextColumn("Désignation"),
                "M_Num": st.column_config.NumberColumn("€", format="%.2f"),
                "Statut": st.column_config.SelectboxColumn("Etat", options=["À prévoir", "Fait"], required=True),
                "Type": st.column_config.SelectboxColumn("Cat", options=["Port", "Assurances", "Maintenance", "Sécurité", "Autres"])
            },
            hide_index=False,
            use_container_width=True,
            num_rows="dynamic",
            height=hauteur_finale, # <--- LA CLÉ EST ICI
            key="maint_editor_v7"
        )
        
  

        # Grille de boutons pour iPhone
        col_save, col_del = st.columns(2)

        with col_save:
            if st.button("💾 ENREGISTRER", use_container_width=True, type="primary"):
                df_non_affiches = df_m[~df_m.index.isin(df_filtre.index)].drop(columns=['dt_maint'], errors='ignore')
                df_final_save = pd.concat([df_non_affiches, edited_df], ignore_index=True)
                sauvegarder_data(df_final_save, 'maintenance.json')
                st.success("✅ Mis à jour !")
                st.rerun()
        with col_del:
            # SYSTÈME DE SÉCURITÉ À DOUBLE ÉTAPE
            with st.expander("🗑️ ZONE DE SUPPRESSION"):
                st.error("⚠️ Attention : action définitive")
                
                # Étape 1 : Le Verrou
                unlock = st.checkbox("Déverrouiller le bouton")
                
                # Étape 2 : L'Index
                idx_to_remove = st.number_input(
                    "Index à supprimer (chiffre à gauche) :", 
                    min_value=0, 
                    max_value=df_m.index.max() if not df_m.empty else 0, 
                    step=1
                )
                
                # Étape 3 : Le bouton ne s'affiche QUE si déverrouillé
                if unlock:
                    if st.button(f"🔥 CONFIRMER SUPPRESSION {idx_to_remove}", type="primary", use_container_width=True):
                        # Action de suppression
                        df_m = df_m.drop(index=idx_to_remove).reset_index(drop=True)
                        sauvegarder_data(df_m, 'maintenance.json')
                        st.success("Ligne supprimée !")
                        st.rerun()
                else:
                    st.info("Cochez la case pour confirmer.")

      

    # --- 5. FORMULAIRE D'AJOUT (SÉCURISÉ CONTRE LES DOUBLONS) ---
    st.write("---")
    with st.expander("➕ Ajouter une opération"):
        # On utilise une clé unique basée sur le temps pour éviter les doubles clics
        with st.form("form_maint_v2", clear_on_submit=True):
            f_obj = st.text_input("Désignation")
            c_a, c_b = st.columns(2)
            f_date_iso = c_a.date_input("Date", datetime.now())
            f_montant = c_b.number_input("Montant (€)", min_value=0.0, format="%.2f")
            
            c_c, c_d = st.columns(2)
            f_type = c_c.selectbox("Catégorie", ["Port", "Assurances", "Maintenance", "Sécurité", "Autres"])
            f_statut = c_d.selectbox("Statut", ["À prévoir", "Fait"], index=1 if f_date_iso <= datetime.now().date() else 0)
            
            f_recurrence = st.checkbox("Répéter mensuellement")
            
            if st.form_submit_button("💾 Enregistrer l'opération", use_container_width=True):
                if f_obj:
                    nouvelles_lignes = []
                    # FORMATAGE DE LA DATE EN JJ/MM/AAAA AVANT SAUVEGARDE
                    if f_recurrence:
                        for m in range(f_date_iso.month, 13):
                            # On force le format français ici
                            date_fr = f_date_iso.replace(month=m).strftime("%d/%m/%Y")
                            nouvelles_lignes.append({
                                "Date": date_fr, 
                                "Objet": f"{f_obj} (M{m})", 
                                "M_Num": f_montant, 
                                "Statut": f_statut, 
                                "Type": f_type
                            })
                    else:
                        date_fr = f_date_iso.strftime("%d/%m/%Y")
                        nouvelles_lignes.append({
                            "Date": date_fr, 
                            "Objet": f_obj, 
                            "M_Num": f_montant, 
                            "Statut": f_statut, 
                            "Type": f_type
                        })
                    
                    # Chargement frais pour concaténation propre
                    df_m_current = charger_data_safe('maintenance.json')
                    df_final = pd.concat([df_m_current, pd.DataFrame(nouvelles_lignes)], ignore_index=True)
                    sauvegarder_data(df_final, 'maintenance.json')
                    
                    st.success("✅ Opération(s) ajoutée(s) au format FR !")
                    st.rerun()

# =================================================================
# --- PAGE : FACTURATION & SUIVI PAIEMENTS ---
# =================================================================
if st.session_state.page == "FACTURES":
    st.title("📑 Facturation & Suivi")

    # 1. Chargement sécurisé des données
    df_f = charger_data_safe('contacts.json')

    if df_f.empty:
        st.warning("Aucune donnée de facturation trouvée.")
    else:
        # --- 2. NETTOYAGE & HARMONISATION DES NOMBRES ---
        # On s'assure que les calculs ne plantent pas à cause des virgules
        for col in ['Prix', 'Acompte', 'Jours', 'Pers']:
            if col in df_f.columns:
                df_f[col] = pd.to_numeric(df_f[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # --- 3. FILTRES DE VUE ---
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtre_paye = st.selectbox("Filtrer par paiement", ["Tous", "Paid", "Unpaid"])
        with col_f2:
            search_nom = st.text_input("Rechercher un client", "").lower()

        # Application des filtres
        df_visu = df_f.copy()
        if filtre_paye != "Tous":
            df_visu = df_visu[df_visu['Paiement'] == filtre_paye]
        if search_nom:
            df_visu = df_visu[df_visu['Nom'].str.lower().contains(search_nom) | df_visu['Prénom'].str.lower().contains(search_nom)]

        # Tri par date (on crée une colonne de tri temporaire)
        df_visu['dt_tri'] = pd.to_datetime(df_visu['DateNav'], dayfirst=True, errors='coerce')
        df_visu = df_visu.sort_values('dt_tri', ascending=False)

        # --- 4. RÉCAPITULATIF FINANCIER ---
        total_du = df_visu['Prix'].sum()
        total_recu = df_visu['Acompte'].sum()
        reste_a_percevoir = total_du - total_recu

        c1, c2, c3 = st.columns(3)
        c1.metric("CA Total (Sélection)", f"{total_du:,.2f} €".replace(',', ' '))
        c2.metric("Total Encaissé", f"{total_recu:,.2f} €".replace(',', ' '), delta=None)
        c3.metric("Reste à percevoir", f"{reste_a_percevoir:,.2f} €".replace(',', ' '), delta_color="inverse")

        st.divider()

        # --- 5. AFFICHAGE DES LIGNES DE FACTURATION ---
        for idx, r in df_visu.iterrows():
            solde = r['Prix'] - r['Acompte']
            is_paid = r['Paiement'] == "Paid"
            
            # Design de la ligne
            color_border = "#2e7d32" if is_paid else "#d32f2f"
            bg_label = "rgba(46, 125, 50, 0.1)" if is_paid else "rgba(211, 47, 47, 0.1)"
            status_text = "✅ PAYÉ" if is_paid else "⏳ EN ATTENTE"

            html_facture = f"""
            <div style="border: 1px solid #ddd; padding: 12px; border-radius: 10px; 
                        margin-bottom: 8px; border-left: 10px solid {color_border}; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <b style="font-size: 1.1em;">{r['Nom']} {r['Prénom']}</b><br>
                        <small>📅 Date : {r['DateNav']} | 🏢 Société : {r.get('Société', 'PERSO')}</small>
                    </div>
                    <div style="text-align: right;">
                        <span style="background: {bg_label}; color: {color_border}; padding: 4px 8px; 
                                     border-radius: 5px; font-weight: bold; font-size: 0.9em;">{status_text}</span><br>
                        <b style="font-size: 1.2em;">{solde:,.2f} €</b><br>
                        <small>sur un total de {r['Prix']}€</small>
                    </div>
                </div>
            </div>
            """
            st.markdown(html_facture, unsafe_allow_html=True)

            # Actions rapides
            col_a, col_b, col_c = st.columns([2, 2, 6])
            if not is_paid:
                if col_a.button("💰 Marquer PAYÉ", key=f"pay_{idx}"):
                    # On met à jour le DataFrame original
                    df_f.at[idx, 'Paiement'] = "Paid"
                    df_f.at[idx, 'Acompte'] = df_f.at[idx, 'Prix'] # On considère tout payé
                    sauvegarder_data(df_f, 'contacts.json')
                    st.rerun()
            
            if col_b.button("✏️ Modifier", key=f"edit_f_{idx}"):
                st.session_state.contact_edit_idx = idx
                st.session_state.page = "CONTACTS" # Redirige vers le formulaire
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
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
# --- PAGE : LIVRE DE BORD (LOGBOOK) ---
# =================================================================
if st.session_state.page == "LOG":
    st.title("📖 Livre de Bord")

    # --- 1. CHARGEMENT INITIAL DES DONNÉES ---
    # On le met ici pour qu'il soit accessible par le formulaire ET par les onglets
    df_log = charger_data_safe('logbook.json')

    # --- 2. GESTION DU FORMULAIRE DE SAISIE ---
    # S'affiche si on édite ou si on clique sur Nouveau
    if st.session_state.get('log_edit_idx') is not None or st.session_state.get('nouveau_log', False):
        st.markdown("### 📝 Saisie de Navigation")
        
        idx = st.session_state.get('log_edit_idx')
        is_edit = idx is not None
        # Vérification de sécurité pour l'index
        row = df_log.loc[idx] if is_edit and idx in df_log.index else {}

        with st.form("form_logbook", clear_on_submit=False):
            # Ligne 1 : L'essentiel
            c1, c2, c3 = st.columns([2, 3, 3])
            date_n = c1.text_input("📅 Date", value=row.get('Date', datetime.now().strftime("%d/%m/%Y")))
            p_dep = c2.text_input("⚓ Départ", value=row.get('PortDep', ''), placeholder="Ex: Lorient")
            p_arr = c3.text_input("🏁 Arrivée", value=row.get('PortArr', ''), placeholder="Ex: Groix")

            # Ligne 2 : Les chiffres (Technique)
            c4, c5, c6, c7 = st.columns(4)
            milles = c4.number_input("📏 Milles (NM)", value=float(row.get('Milles', 0)), step=0.5)
            h_mot = c5.number_input("⚙️ Heures Moteur", value=float(row.get('HMot', 0)), step=0.1)
            gasoil = c6.number_input("⛽ Gasoil (L)", value=float(row.get('Gasoil', 0)), step=1.0)
            h_voile = c7.number_input("⛵ Heures Voile", value=float(row.get('HVoile', 0)), step=0.1)

            # Ligne 3 : Observations
            notes = st.text_area("🗒️ Observations", value=row.get('Notes', ''))

            # Ligne 4 : Boutons
            col_save, col_cancel = st.columns([1, 1])
            with col_save:
                submit = st.form_submit_button("💾 ENREGISTRER", use_container_width=True)
            with col_cancel:
                if st.form_submit_button("❌ ANNULER", use_container_width=True):
                    st.session_state.log_edit_idx = None
                    st.session_state.nouveau_log = False
                    st.rerun()

            if submit:
                new_data = {
                    "Date": date_n, "PortDep": p_dep, "PortArr": p_arr,
                    "Milles": milles, "HMot": h_mot, "Gasoil": gasoil,
                    "HVoile": h_voile, "Notes": notes
                }
                if is_edit:
                    df_log.loc[idx] = new_data
                else:
                    df_log = pd.concat([pd.DataFrame([new_data]), df_log], ignore_index=True)
                
                sauvegarder_data(df_log, 'logbook.json')
                st.session_state.log_edit_idx = None
                st.session_state.nouveau_log = False
                st.success("C'est noté dans le journal !")
                st.rerun()
        
        st.divider() # Séparateur entre le formulaire et la liste

    # --- 3. AFFICHAGE PAR ONGLETS ---
    tab1, tab2 = st.tabs(["⛵ Saison Actuelle", "📚 Archives Historiques"])

    # ONGLET 1 : SAISON EN COURS
    with tab1:
        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.subheader("Navigations 2026")
        with col_t2:
            if st.button("➕ Nouveau", key="btn_new_log", use_container_width=True):
                st.session_state.nouveau_log = True
                st.session_state.log_edit_idx = None
                st.rerun()

        if df_log.empty:
            st.info("Aucune navigation enregistrée.")
        else:
            # On trie pour l'affichage (plus récent en haut)
            df_log['dt_tri'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
            df_visu = df_log.sort_values('dt_tri', ascending=False)

            for idx, r in df_visu.iterrows():
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 12px; border-radius: 10px; 
                            background: white; margin-bottom: 5px; border-left: 8px solid #01579b;">
                    <b>📅 {r.get('Date')}</b> | 📍 {r.get('PortDep')} ➔ {r.get('PortArr')} | 📏 {r.get('Milles')} NM
                </div>
                """, unsafe_allow_html=True)
                
                c_ed, c_de, c_sp = st.columns([1, 1, 8])
                if c_ed.button("✏️", key=f"ed_{idx}"):
                    st.session_state.log_edit_idx = idx
                    st.rerun()
                if c_de.button("🗑️", key=f"de_{idx}"):
                    df_log = df_log.drop(idx)
                    sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                    st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

    # ONGLET 2 : ARCHIVES
    with tab2:
        st.subheader("Consulter les années passées")
        df_arch = charger_data_safe('archives_logbook.json')
        
        if df_arch.empty:
            st.write("Le coffre à souvenirs est vide.")
        else:
            df_arch['Année'] = pd.to_datetime(df_arch['Date'], dayfirst=True, errors='coerce').dt.year
            annees_dispo = sorted(df_arch['Année'].dropna().unique().astype(int).tolist(), reverse=True)
            sel_arch_y = st.selectbox("Choisir une année", annees_dispo)
            
            df_year_arch = df_arch[df_arch['Année'] == sel_arch_y]
            for idx, r in df_year_arch.iterrows():
                st.markdown(f"""
                <div style="border: 1px solid #ccc; padding: 10px; border-radius: 8px; margin-bottom: 5px; background: #f9f9f9;">
                    <b>{r.get('Date')}</b> : {r.get('PortDep')} ➔ {r.get('PortArr')} ({r.get('Milles', 0)} NM)
                </div>
                """, unsafe_allow_html=True)
 
# --- FIN DU FICHIER ---


































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































