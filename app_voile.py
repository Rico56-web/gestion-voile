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
# --- PAGE STATS : COCKPIT VESTA SKIPPER PRO 2026 ---
# =================================================================
if st.session_state.page == "STATS":
    st.markdown('<h2 style="text-align:center;">🚀 Cockpit Vesta 2026</h2>', unsafe_allow_html=True)

    # 1. Chargement des données
    df_actif = charger_data_safe('contacts.json')
    df_arch = charger_data_safe('archives_planning.json')
    df_m = charger_data_safe('maintenance.json') 
    df_log = charger_data_safe('logbook.json')
    
    # Fusion actif + archives
    df_all = pd.concat([df_actif, df_arch], ignore_index=True) if not df_arch.empty else df_actif

    def to_f(val):
        if pd.isna(val) or val == "": return 0.0
        try: return float(str(val).replace('€','').replace(' ','').replace(',','.').strip())
        except: return 0.0

    if not df_all.empty:
        # --- A. FILTRES ---
        c_sel1, c_sel2 = st.columns(2)
        mode_bilan = c_sel1.radio("Période :", ["À ce jour", "Année Complète"], horizontal=True)
        sel_y = c_sel2.selectbox("Année :", [2025, 2026, 2027], index=1)

        # Filtrage Revenus
        df_all['dt_vrai'] = pd.to_datetime(df_all['DateNav'], dayfirst=True, errors='coerce')
        df_f = df_all[df_all['dt_vrai'].dt.year == sel_y].copy()
        if mode_bilan == "À ce jour" and not df_f.empty:
            df_f = df_f[df_f['dt_vrai'] <= pd.Timestamp.now().normalize()].copy()

        def est_comptabilise(row):
            soc = str(row.get('Société', '')).upper()
            paiement = str(row.get('Paiement', '')).upper()
            if "LISTE D'ATTENTE" in str(row.get('Statut', '')).upper(): return False
            return "CMN" in soc or paiement == "PAID"

        df_final = df_f[df_f.apply(est_comptabilise, axis=1)].copy() if not df_f.empty else pd.DataFrame()
        
        # Filtrage Maintenance & Logbook
        df_m_y = pd.DataFrame()
        if not df_m.empty:
            df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
            df_m_y = df_m[(df_m['dt_maint'].dt.year == sel_y) & (df_m['Statut'] == "Fait")].copy()
        
        df_log_y = pd.DataFrame()
        if not df_log.empty:
            df_log['dt_log'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
            df_log_y = df_log[df_log['dt_log'].dt.year == sel_y].copy()

        # --- B. TOUS LES CALCULS (FINANCES & PERFORMANCE) ---
        total_ca = sum(to_f(x) for x in df_final['Prix']) if not df_final.empty else 0.0
        nb_jours = len(df_final)
        ca_moyen_jour = total_ca / nb_jours if nb_jours > 0 else 0.0
        
        col_m_val = 'M_Num' if 'M_Num' in df_m_y.columns else ('Montant' if 'Montant' in df_m_y.columns else None)
        t_maint = sum(to_f(x) for x in df_m_y[col_m_val]) if col_m_val and not df_m_y.empty else 0.0
        t_gasoil_eur = df_log_y['Cout Gazoil'].sum() if 'Cout Gazoil' in df_log_y.columns else 0.0
        total_dep = t_maint + t_gasoil_eur
        
        # Performance
        t_milles = df_log_y['TotalMil'].sum() if not df_log_y.empty else 0
        t_mot_p = df_log_y['TotalMot'].sum() if not df_log_y.empty else 0
        t_voile = df_log_y['HVoile'].sum() if not df_log_y.empty else 0
        
        revenu_par_h_moteur = total_ca / t_mot_p if t_mot_p > 0 else 0
        ratio_maintenance = (total_dep / total_ca * 100) if total_ca > 0 else 0
        mille_par_sortie = t_milles / nb_jours if nb_jours > 0 else 0

        # Vidange Synchro (Basé sur tes 13.9h restantes)
        h_moteur_actuel = df_log_y['TotalMot'].max() if not df_log_y.empty else 0.0
        prochaine_vidange = h_moteur_actuel + 13.9
        h_restantes = prochaine_vidange - h_moteur_actuel

        # --- C. BILAN SANTÉ ---
        st.markdown("### 🩺 Bilan de Santé")
        b1, b2, b3 = st.columns(3)
        b1.metric("🎯 Rentabilité", f"{min(100, int((total_ca/6500)*100))}%", help="Seuil 6500€")
        indice_eco = (t_voile / (t_mot_p + t_voile) * 100) if (t_mot_p + t_voile) > 0 else 0
        b2.metric("🌿 Indice Éco", f"{indice_eco:.0f}%")
        b3.metric("⚙️ Vidange dans", f"{h_restantes:.1f}h", delta=f"Mot: {h_moteur_actuel:.0f}h")

        # --- D. ANALYSE DE PERFORMANCE ---
        st.write("---")
        st.markdown("### 📈 Performance Opérationnelle")
        p1, p2, p3 = st.columns(3)
        p1.metric("💎 Rendement/H", f"{revenu_par_h_moteur:.1f} €/h")
        p2.metric("📉 Poids Frais", f"{ratio_maintenance:.1f} %")
        p3.metric("📏 Moy. Sortie", f"{mille_par_sortie:.1f} NM")

        # --- E. INDICATEURS FINANCIERS ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 CA", f"{total_ca:,.0f} €")
        c2.metric("💸 Dépenses", f"{total_dep:,.0f} €")
        c3.metric("⚖️ Net", f"{(total_ca - total_dep):,.0f} €")

        # --- F. GRAPHES (ORDRE CHRONOLOGIQUE) ---
        st.subheader("📉 Évolution Mensuelle")
        ordre_mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
        nom_mois_map = {i+1: m for i, m in enumerate(ordre_mois)}
        df_evo = pd.DataFrame(index=range(1, 13))
        if not df_final.empty:
            df_final['Mois'] = df_final['dt_vrai'].dt.month
            df_evo['Recettes'] = df_final.groupby('Mois')['Prix'].apply(lambda x: sum(to_f(i) for i in x))
        if not df_m_y.empty and col_m_val:
            df_m_y['Mois'] = df_m_y['dt_maint'].dt.month
            df_evo['Dépenses'] = df_m_y.groupby('Mois')[col_m_val].apply(lambda x: sum(to_f(i) for i in x))
        
        df_evo = df_evo.fillna(0)
        df_evo.index = df_evo.index.map(nom_mois_map)
        df_evo.index = pd.Categorical(df_evo.index, categories=ordre_mois, ordered=True)
        st.bar_chart(df_evo.sort_index(), height=220)

        # --- G. RÉPARTITION (SOCIÉTÉS ET TYPES) ---
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
                df_rep_maint = df_m_y.groupby('Type')[col_m_val].apply(lambda x: sum(to_f(i) for i in x))
                st.bar_chart(df_rep_maint, horizontal=True, height=200)

        # --- H. TABLEAUX DÉTAILLÉS (TRI RÉCENT EN HAUT) ---
        st.write("---")
        t1, t2 = st.tabs(["💰 Détails CA", "🛠️ Détails Dépenses"])
        
        with t1:
            if not df_final.empty:
                df_final_clean = df_final.sort_values(by='dt_vrai', ascending=False)
                cols_r = [c for c in ['DateNav', 'Société', 'Prix'] if c in df_final_clean.columns]
                st.dataframe(df_final_clean[cols_r], use_container_width=True, hide_index=True)
                st.success(f"**TOTAL RECETTES : {total_ca:,.2f} €** (Moy : {ca_moyen_jour:,.0f}€/j)")
        
        with t2:
            if not df_m_y.empty:
                df_m_y_clean = df_m_y.sort_values(by='dt_maint', ascending=False)
                st.write("**🔧 Maintenance :**")
                col_nom_m = 'Objet' if 'Objet' in df_m_y_clean.columns else 'Titre'
                cols_m = [c for c in ['Date', col_nom_m, col_m_val] if c in df_m_y_clean.columns]
                st.dataframe(df_m_y_clean[cols_m], use_container_width=True, hide_index=True)
            
            if t_gasoil_eur > 0:
                df_log_y_clean = df_log_y[df_log_y['Cout Gazoil']>0].sort_values(by='dt_log', ascending=False)
                st.write("**⛽ Carburant :**")
                st.dataframe(df_log_y_clean[['Date', 'PortArr', 'Cout Gazoil']], use_container_width=True, hide_index=True)
            
            st.error(f"**TOTAL DÉPENSES : {total_dep:,.2f} €**")

# =================================================================
# --- 8. PAGE MAINTENANCE (CHRONOLOGIQUE & FILTRÉE) ---
# =================================================================
if st.session_state.page == "MAINT":
    import pandas as pd
    from datetime import datetime

    df_m = charger_data_safe('maintenance.json')
    df_log = charger_data_safe('logbook.json')

    # --- 1. CALCULS HEURES ---
    releve_h = pd.to_numeric(df_log['TotalMot'], errors='coerce').max() if not df_log.empty else 0
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
        nb_lignes = len(df_filtre)
        hauteur_calculee = (nb_lignes * 35) + 45 
        hauteur_finale = max(hauteur_calculee, 150)

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
            height=hauteur_finale,
            key="maint_editor_v7"
        )
        
        col_save, col_del = st.columns(2)

        with col_save:
            if st.button("💾 ENREGISTRER", use_container_width=True, type="primary"):
                df_non_affiches = df_m[~df_m.index.isin(df_filtre.index)].drop(columns=['dt_maint'], errors='ignore')
                df_final_save = pd.concat([df_non_affiches, edited_df], ignore_index=True)
                sauvegarder_data(df_final_save, 'maintenance.json')
                st.success("✅ Mis à jour !")
                st.rerun()

        with col_del:
            with st.expander("🗑️ ZONE DE SUPPRESSION"):
                st.error("⚠️ Attention : action définitive")
                unlock = st.checkbox("Déverrouiller le bouton")
                idx_to_remove = st.number_input("Index à supprimer :", min_value=0, max_value=df_m.index.max() if not df_m.empty else 0, step=1)
                
                if unlock:
                    if st.button(f"🔥 CONFIRMER SUPPRESSION {idx_to_remove}", type="primary", use_container_width=True):
                        df_m = df_m.drop(index=idx_to_remove).reset_index(drop=True)
                        sauvegarder_data(df_m, 'maintenance.json')
                        st.success("Ligne supprimée !")
                        st.rerun()

    # --- 5. FORMULAIRE D'AJOUT ---
    st.write("---")
    with st.expander("➕ Ajouter une opération"):
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
                    if f_recurrence:
                        for m in range(f_date_iso.month, 13):
                            date_fr = f_date_iso.replace(month=m).strftime("%d/%m/%Y")
                            nouvelles_lignes.append({"Date": date_fr, "Objet": f"{f_obj} (M{m})", "M_Num": f_montant, "Statut": f_statut, "Type": f_type})
                    else:
                        date_fr = f_date_iso.strftime("%d/%m/%Y")
                        nouvelles_lignes.append({"Date": date_fr, "Objet": f_obj, "M_Num": f_montant, "Statut": f_statut, "Type": f_type})
                    
                    df_m_current = charger_data_safe('maintenance.json')
                    df_final = pd.concat([df_m_current, pd.DataFrame(nouvelles_lignes)], ignore_index=True)
                    sauvegarder_data(df_final, 'maintenance.json')
                    st.success("✅ Opération(s) ajoutée(s) !")
                    st.rerun()

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
# --- 12. PAGE LIVRE DE BORD (LOG) - VERSION COMPLÈTE & STABLE ---
# =================================================================
if st.session_state.page == "LOG":
    st.title("📖 Livre de Bord")

    # 1. Chargement des données
    df_log = charger_data_safe('logbook.json')

    # 2. Récupération des compteurs pour initialisation
    last_h = 0.0
    last_m = 0.0
    if not df_log.empty:
        try:
            last_h = pd.to_numeric(df_log['TotalMot'], errors='coerce').max()
            last_m = pd.to_numeric(df_log['TotalMil'], errors='coerce').max()
        except: pass

    # 3. ENTÊTE : Navigation Globale
    st.subheader("🚀 Nouvelle Navigation")
    col_h1, col_h2, col_h3 = st.columns([2, 1, 2])
    f_date = col_h1.date_input("Date", datetime.now())
    f_jours = col_h2.number_input("Jours", min_value=1, value=1)
    f_titre = col_h3.text_input("Destination / Titre", placeholder="ex: Traversée vers Groix")
    
    st.write("---")
    st.info("⚓ **Détail des étapes** : Remplissez les compteurs pour chaque escale.")

    # 4. TABLEAU D'ÉTAPES (Heures et Milles Départ/Arrivée)
    if 'temp_log_df' not in st.session_state:
        st.session_state.temp_log_df = pd.DataFrame([{
            "Port": "", 
            "H_Dep": float(last_h), "H_Arr": float(last_h),
            "M_Dep": float(last_m), "M_Arr": float(last_m),
            "H_Voile": 0.0,
            "Notes": ""
        }])

    # Configuration des colonnes simplifiée pour éviter le TypeError
    config_log = {
        "Port": st.column_config.TextColumn("Port / Etape", width="medium"),
        "H_Dep": st.column_config.NumberColumn("Mot. Début", format="%.1f"),
        "H_Arr": st.column_config.NumberColumn("Mot. Fin", format="%.1f"),
        "M_Dep": st.column_config.NumberColumn("Mil. Début", format="%.0f"),
        "M_Arr": st.column_config.NumberColumn("Mil. Fin", format="%.0f"),
        "H_Voile": st.column_config.NumberColumn("H. Voile", format="%.1f"),
        "Notes": st.column_config.TextColumn("Notes / Météo", width="small")
    }

    edited_steps = st.data_editor(
        st.session_state.temp_log_df,
        column_config=config_log,
        num_rows="dynamic",
        use_container_width=True,
        key="log_editor_v2026_pro"
    )

    # 5. BOUTON D'ENREGISTREMENT
    if st.button("💾 ENREGISTRER LA NAVIGATION", use_container_width=True, type="primary"):
        if not edited_steps.empty and edited_steps.iloc[0]["Port"] != "":
            nouvelles_entrees = []
            
            for _, row in edited_steps.iterrows():
                if row["Port"]:
                    # Calculs automatiques par ligne
                    milles_étape = float(row["M_Arr"]) - float(row["M_Dep"])
                    
                    nouvelles_entrees.append({
                        "Date": f_date.strftime("%d/%m/%Y"),
                        "Jours": int(f_jours),
                        "Navigation": f_titre,
                        "PortArr": row["Port"],
                        "MotDep": float(row["H_Dep"]),
                        "TotalMot": float(row["H_Arr"]),
                        "MillesEtape": milles_étape,
                        "TotalMil": float(row["M_Arr"]),
                        "H_Voile": float(row["H_Voile"]),
                        "Notes": row["Notes"]
                    })
            
            if nouvelles_entrees:
                df_actuel = charger_data_safe('logbook.json')
                df_final = pd.concat([df_actuel, pd.DataFrame(nouvelles_entrees)], ignore_index=True)
                sauvegarder_data(df_final, 'logbook.json')
                
                if 'temp_log_df' in st.session_state:
                    del st.session_state.temp_log_df
                
                st.success("✅ Livre de bord mis à jour !")
                st.rerun()
        else:
            st.warning("⚠️ Précisez au moins un port d'escale.")

    # 6. HISTORIQUE & MODIFICATIONS
    if not df_log.empty:
        st.divider()
        with st.expander("📜 Historique et corrections rapides"):
            edited_hist = st.data_editor(
                df_log.sort_index(ascending=False),
                use_container_width=True,
                num_rows="dynamic",
                key="hist_editor_log"
            )
            
            c_s, c_d = st.columns(2)
            if c_s.button("💾 Sauver les modifs", use_container_width=True):
                sauvegarder_data(edited_hist.sort_index(), 'logbook.json')
                st.rerun()
            
            with c_d:
                idx_del = st.number_input("Supprimer Index", min_value=0, max_value=df_log.index.max(), step=1)
                if st.button(f"🔥 Supprimer {idx_del}", type="primary"):
                    df_log = df_log.drop(index=idx_del).reset_index(drop=True)
                    sauvegarder_data(df_log, 'logbook.json')
                    st.rerun()


# --- FIN DU FICHIER ---









































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































