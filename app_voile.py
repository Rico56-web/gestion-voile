import requests, base64, json, time, os, html, io
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import calendar

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
# --- NAVIGATION ---
# =================================================================
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "LOG"]
icones = {"CONTACTS": "👤", "PLANNING": "🗓️", "STATS": "📊", "MAINT": "🛠️", "LOG": "📖"}

cols_nav = st.columns(len(menu))
for i, name in enumerate(menu):
    if cols_nav[i].button(icones[name], key=f"nav_{name}", use_container_width=True, 
                          type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()

# =================================================================
# --- 5. BLOC CONTACTS (V96 - PROTECTION TOTALE ANTI-NAN) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.markdown('<h2 style="text-align:center;">⚓ Gestion des Clients Vesta</h2>', unsafe_allow_html=True)

    # 1. Chargement et Nettoyage de sécurité
    df_raw = charger_data('contacts.json')
    df_c = df_raw.copy() if not df_raw.empty else pd.DataFrame()

    if not df_c.empty:
        # --- LE BOUCLIER ANTI-NAN ---
        # On remplace TOUS les types de vides par une chaîne vide pour l'affichage
        df_c = df_c.fillna("")
        for col in df_c.columns:
            df_c[col] = df_c[col].astype(str).replace(['nan', 'NaN', 'None', 'NaT'], '')
        
        df_c['orig_idx'] = df_c.index
        # dt_sort sert uniquement au tri, on ne l'affiche jamais
        df_c['dt_sort'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
        
        if 'Relancer' not in df_c.columns: df_c['Relancer'] = "Non"
        
        c_search, c_yr = st.columns([2, 1])
        search = c_search.text_input("🔍 Rechercher...", "").upper()
        annee_sel = c_yr.selectbox("Saison", [2026, 2027, 2028], index=0)
        
        mask = (df_c['dt_sort'].dt.year == annee_sel) | (df_c['dt_sort'].isna()) | (df_c['DateNav'] == "")
        df_c = df_c[mask].copy()
        if search:
            mask_s = df_c['Nom'].str.upper().contains(search) | df_c['Prénom'].str.upper().contains(search)
            df_c = df_c[mask_s]
        df_c = df_c.sort_values(by='dt_sort', ascending=False)

    # 2. Onglets
    n1, n2, n3, n4 = st.columns(4)
    if n1.button("🟢 EN COURS", use_container_width=True, type="primary" if st.session_state.vue_contact == "En cours" else "secondary"): 
        st.session_state.vue_contact = "En cours"; st.rerun()
    if n2.button("⌛ ATTENTE", use_container_width=True, type="primary" if st.session_state.vue_contact == "Attente" else "secondary"): 
        st.session_state.vue_contact = "Attente"; st.rerun()
    if n3.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.vue_contact == "Archives" else "secondary"): 
        st.session_state.vue_contact = "Archives"; st.rerun()
    if n4.button("➕ NOUVEAU", use_container_width=True):
        new_r = {"Prénom":"PRÉNOM","Nom":"NOM","Statut":"En attente","Paiement":"Unpaid","Relancer":"Non","DateNav":f"01/06/{annee_sel}","Société":"PERSO","Jours":1,"Pers":1,"Notes":"","Téléphone":"","Email":"","Prix":0,"Acompte":0}
        df_new = pd.concat([pd.DataFrame([new_r]), df_raw], ignore_index=True)
        sauvegarder_data(df_new, 'contacts.json'); st.rerun()

    st.divider()

    # 3. Filtrage Robuste
    if not df_c.empty:
        # On ignore les accents et majuscules pour le filtrage
        statut_clean = df_c['Statut'].str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        relance_clean = df_c['Relancer'].str.upper()

        if st.session_state.vue_contact == "Archives":
            mask_aff = (statut_clean.str.contains("termine|annule|refuse")) & (relance_clean != "OUI")
        elif st.session_state.vue_contact == "Attente":
            mask_att = statut_clean.str.contains("liste|attente")
            mask_rel = (statut_clean.str.contains("termine")) & (relance_clean == "OUI")
            mask_aff = mask_att | mask_rel
        else:
            mask_aff = ~statut_clean.str.contains("termine|annule|refuse|liste|attente")

        df_aff = df_c[mask_aff].copy()

        # 4. Affichage des fiches
        for _, row in df_aff.iterrows():
            idx = row['orig_idx']
            
            # Données propres pour l'affichage
            pre = clean_text(row.get('Prénom', '')).upper()
            nom = clean_text(row.get('Nom', '')).upper()
            sta_clean = str(row.get('Statut', 'EN ATTENTE')).upper()
            soc = clean_text(row.get('Société', 'PERSO')).upper()
            tel = clean_text(row.get('Téléphone', ''))
            note = clean_text(row.get('Notes', ''))
            date_aff = str(row.get('DateNav', '')).strip()
            if not date_aff or date_aff.lower() == "nan": date_aff = "---"
            
            prix = clean_num(row.get('Prix', 0))
            aco = clean_num(row.get('Acompte', 0))
            reste = prix - aco
            val_paye = str(row.get('Paiement', 'UNPAID')).strip().upper()

            # --- CORRECTION PAIEMENT ---
            if val_paye == "PAID":
                p_label, p_color = "PAYÉ", "green"
            elif prix > 0 and reste <= 0:
                p_label, p_color = "PAYÉ", "green"
            else:
                p_label, p_color = "NON PAYÉ", "#E74C3C"

            # Couleurs Background
            rel_val = str(row.get('Relancer', 'NON')).upper()
            if rel_val == "OUI" or "LISTE" in sta_clean: bg = "#F5EEF8" 
            elif soc == "CMN": bg = "#D6EAF8"
            elif "ATTENTE" in sta_clean: bg = "#FCF3CF"
            else: bg = "#D5F5E3"

            etoile = " ⭐ <small>TOP CLIENT</small>" if rel_val == "OUI" else ""
            t_url = tel.replace(' ', '').replace('+', '')

            card_html = f"""
            <div style="background-color:{bg}; padding:15px; border-radius:12px; border:1px solid #ccc; margin-bottom:10px; color:#2C3E50;">
                <div style="display:flex; justify-content:space-between; font-weight:bold; border-bottom:1px solid rgba(0,0,0,0.1); padding-bottom:5px;">
                    <span>#{idx} | {pre} {nom} {etoile}</span>
                    <span style="background:white; padding:0 8px; border-radius:5px; font-size:0.75rem; border:1px solid #ddd;">{soc}</span>
                </div>
                <div style="display:grid; grid-template-columns: 1fr 1fr; font-size:0.85rem; margin-top:10px; gap:5px;">
                    <div>📅 Date: <b>{date_aff}</b></div>
                    <div>📊 Statut: <b>{sta_clean}</b></div>
                    <div>💰 Prix: <b>{prix} €</b></div>
                    <div style="color:{p_color}; font-weight:bold;">🏷️ {p_label} ({reste}€)</div>
                </div>
                <div style="margin-top:10px; padding:8px; background:rgba(255,255,255,0.4); border-radius:5px; font-size:0.8rem;">
                    📞 Tel: <b>{tel}</b> | ✉️ {row.get('Email','')}
                </div>
                {f'<div style="font-size:0.8rem; margin-top:8px; border-left:3px solid #666; padding-left:8px; color:#555;"><i>{note}</i></div>' if note and note != '---' else ''}
                <div style="margin-top:12px; display:flex; gap:10px;">
                    <a href="tel:{t_url}" style="flex:1; background:#5DADE2; color:white !important; text-align:center; padding:8px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:0.75rem;">📞 APPEL</a>
                    <a href="https://wa.me/{t_url}" style="flex:1; background:#52BE80; color:white !important; text-align:center; padding:8px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:0.75rem;">💬 WHATSAPP</a>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            if c1.button(f"ÉDITER #{idx}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.session_state.page = "MODIFIER_CONTACT"; st.rerun()
            if c2.button(f"SUPPRIMER #{idx}", key=f"del_{idx}", use_container_width=True):
                df_db = charger_data('contacts.json').drop(idx)
                sauvegarder_data(df_db, 'contacts.json'); st.rerun()
    else:
        st.info("Aucun contact à afficher.")
# =================================================================
# --- 6. PAGE MODIFIER CONTACT (V95 - AVEC RELANCE & FIX PAIEMENT) ---
# =================================================================
if st.session_state.page == "MODIFIER_CONTACT":
    st.markdown('<h3 style="text-align:center;">✏️ Modifier le Contact</h3>', unsafe_allow_html=True)
    
    idx_to_edit = st.session_state.get('edit_idx')
    df_m = charger_data('contacts.json')

    if idx_to_edit is not None and not df_m.empty and idx_to_edit in df_m.index:
        row = df_m.loc[idx_to_edit]
        
        with st.form("form_edit_v95"):
            # Ligne 1 : Identité
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=str(row.get('Prénom', '')))
            new_nom = c2.text_input("Nom", value=str(row.get('Nom', '')))
            
            # Ligne 2 : Date et Société
            c3, c4 = st.columns(2)
            new_date = c3.text_input("Date (JJ/MM/AAAA)", value=str(row.get('DateNav', '')))
            new_soc = c4.text_input("Société", value=str(row.get('Société', 'PERSO')))
            
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
            
            # Ligne 6 : Statuts & Options (FIX PAIEMENT & RELANCE)
            s1, s2 = st.columns(2)
            s_list = ["En attente", "Confirmé", "Terminé", "Annulé", "Refusé", "Liste d'attente"]
            curr_s = str(row.get('Statut', 'En attente')).capitalize()
            if "liste" in curr_s.lower(): curr_s = "Liste d'attente"
            s_idx = s_list.index(curr_s) if curr_s in s_list else 0
            new_statut = s1.selectbox("Statut Mission", s_list, index=s_idx)
            
            # Sous-colonnes pour Paiement et Relance
            sub1, sub2 = s2.columns(2)
            
            # Fix Paiement
            val_p = str(row.get('Paiement', 'Unpaid')).strip().upper()
            new_pay = sub1.radio("Paiement", ["Unpaid", "Paid"], index=1 if "PAID" in val_p else 0, horizontal=True)
            
            # Option Relance (Nouveauté)
            val_r = str(row.get('Relancer', 'Non')).strip().capitalize()
            new_relance = sub2.radio("À recontacter ?", ["Non", "Oui"], index=1 if val_r == "Oui" else 0, horizontal=True)
            
            new_notes = st.text_area("Notes", value=str(row.get('Notes', '')).replace('nan',''))

            # BOUTON DE VALIDATION
            submitted = st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True)
            
            if submitted:
                maj = {
                    'Prénom': new_pre.upper(),
                    'Nom': new_nom.upper(),
                    'DateNav': new_date,
                    'Société': new_soc.upper(),
                    'Téléphone': new_tel.strip(),
                    'Email': new_mail.strip(),
                    'Jours': int(new_jours),
                    'Pers': int(new_pers),
                    'Prix': int(new_prix),
                    'Acompte': int(new_aco),
                    'Statut': new_statut,
                    'Paiement': new_pay,
                    'Relancer': new_relance, # Sauvegarde de l'option relance
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
# ===============================================================
# --- 6. PAGE PLANNING (V18.4 - RÉSILIENCE TOTALE) ---
# =================================================================
if st.session_state.page == "PLANNING":
    from datetime import datetime, date, timedelta
    import calendar
    import pandas as pd

    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING</h1></div>', unsafe_allow_html=True)
    
    # Bouton Archives
    if st.button("📂 ACCÉDER AUX ARCHIVES", key="k_arch_p", use_container_width=True):
        st.session_state.last_page = "PLANNING"; st.session_state.page = "ARCHIVES"; st.rerun()

    st.divider()

    # Initialisation temporelle
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    # RESET DES VARIABLES
    jours_occ = {}
    total_mois = 0
    missions_list = []

    if 'curr_month_idx' not in st.session_state: st.session_state.curr_month_idx = aujourdhui.month - 1
    if 'curr_year' not in st.session_state: st.session_state.curr_year = aujourdhui.year

    # Menu de sélection
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

    # CHARGEMENT DES DONNÉES
    df_p = charger_data('contacts.json')

    if not df_p.empty:
        # Prétraitement pour éviter les erreurs de type sur tout le dataframe
        df_p = df_p.fillna("")

        for idx, r in df_p.iterrows():
            try:
                # 1. Nettoyage Nom
                nom_client = str(r.get('Nom', '')).strip().upper()
                if nom_client in ["", "CONTACT", "NAN"]: continue
                
                # 2. PARSEUR DE DATE AMÉLIORÉ
                d_brute = str(r.get('DateNav', '')).strip().split(' ')[0]
                
                # Sécurité anti-vide/nan
                if d_brute.lower() in ["nan", "---", "", "none"]: 
                    continue

                dt_start = None
                # Test des formats (ISO, Français, etc.)
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
                    try:
                        dt_start = datetime.strptime(d_brute, fmt).date()
                        break
                    except: continue
                
                if not dt_start: continue 

                # 3. Infos Mission
                # Utilisation de clean_num pour éviter les erreurs de texte dans les nombres
                n_j = int(float(str(r.get('Jours', 1) or 1))) 
                statut = str(r.get('Statut', 'En attente')).lower()
                soc = str(r.get('Société', 'PERSO')).upper()
                dt_end = dt_start + timedelta(days=max(0, n_j-1))
                prix_val = float(str(r.get('Prix', '0')).replace('€','').replace(' ','').strip() or 0)

                # 4. Couleur (CMN en bleu comme demandé)
                if "CMN" in soc: color = "#3498db"
                elif any(x in statut for x in ["annul", "refus"]): color = "#bdc3c7"
                elif dt_start < aujourdhui: color = "#34495e" # Passé
                else: color = "#27ae60" # Futur

                # 5. Remplissage Calendrier
                for i in range(n_j):
                    curr = dt_start + timedelta(days=i)
                    if curr.month == sel_m and curr.year == sel_y:
                        jours_occ[curr.day] = {"c": color}

                # 6. Liste des missions
                if (dt_start.year == sel_y and dt_start.month == sel_m) or (dt_end.year == sel_y and dt_end.month == sel_m):
                    missions_list.append({
                        'r': r, 'idx': idx, 'start': dt_start, 'end': dt_end, 
                        'n_j': n_j, 'color': color, 'prix': prix_val, 'statut': statut
                    })
                    if dt_start.month == sel_m and not any(x in statut for x in ["annul", "refus"]):
                        total_mois += prix_val
            except:
                continue

    # AFFICHAGE CALENDRIER HTML
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

    # DÉTAILS
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
    else:
        st.info("Aucune mission ce mois-ci.")

    # TOTAL
    st.success(f"**💰 Total prévisionnel {sel_m_nom} : {total_mois:,.0f} €**".replace(",", " "))

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

    # --- A. FONCTIONS INTERNES ---
    def charger_params():
        if os.path.exists('params_maint.json'):
            with open('params_maint.json', 'r') as f:
                return json.load(f)
        return {"cible_vidange": 2450.0}

    def sauver_params(data):
        with open('params_maint.json', 'w') as f:
            json.dump(data, f)

    # --- B. NETTOYAGE AUTOMATIQUE DES CONTACTS ---
    # Cette fonction est maintenant bien alignée à l'intérieur du bloc IF
    def maintenance_donnees():
        df = charger_data('contacts.json')
        if not df.empty:
            # 1. Redressement des dates : format ISO pour le stockage
            df['DateNav'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
            # 2. Remplissage des valeurs numériques
            df['Prix'] = pd.to_numeric(df['Prix'], errors='coerce').fillna(0).astype(int)
            df['Acompte'] = pd.to_numeric(df['Acompte'], errors='coerce').fillna(0).astype(int)
            # 3. Standardisation textes
            df['Nom'] = df['Nom'].astype(str).str.upper().str.strip()
            df['Prénom'] = df['Prénom'].astype(str).str.upper().str.strip()
            df['Société'] = df['Société'].astype(str).str.upper().str.strip().replace('NAN', 'PERSO')
            sauvegarder_data(df, 'contacts.json')

    # On lance le nettoyage immédiatement à l'ouverture de la page
    maintenance_donnees()

    # --- C. RÉCUPÉRATION DES DONNÉES ---
    params = charger_params()
    df_log = charger_data('logbook.json')
    df_m = charger_data('maintenance.json')
    
    releve_h = 0
    if not df_log.empty:
        df_log['MotArr'] = pd.to_numeric(df_log['MotArr'], errors='coerce').fillna(0)
        releve_h = df_log['MotArr'].max()

    # --- D. INTERFACE ---
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
    heures_restantes = PROCHAINE_VIDANGE - releve_h
    percent_prog = max(0.0, min(1.0, (100.0 - heures_restantes) / 100.0))

    # --- E. BANDEAU D'ALERTE ---
    color_v = "#2e7d32" if heures_restantes > 15 else ("#ef6c00" if heures_restantes > 0 else "#c62828")
    bg_v = "#e8f5e9" if heures_restantes > 15 else ("#fff3e0" if heures_restantes > 0 else "#ffebee")

    html_cycle = f"""
    <div style="background-color: {bg_v}; border: 2px solid {color_v}; padding: 12px; border-radius: 12px; text-align: center; margin-top: 10px;">
        <div style="color: {color_v}; font-weight: bold; font-size: 0.75rem;">&#128712; ÉTAT DU CYCLE</div>
        <div style="font-size: 1.6rem; font-weight: 900; color: {color_v};">{heures_restantes:.1f} h restantes</div>
        <div style="font-size: 0.75rem; color: #555;">Compteur : <b>{releve_h:.1f} h</b></div>
    </div>
    """
    st.markdown(html_cycle, unsafe_allow_html=True)
    st.progress(percent_prog)

    if st.button("🔧 ENREGISTRER LA VIDANGE", use_container_width=True, type="primary"):
        new_v = {
            "Date": datetime.now().strftime("%d/%m/%Y"),
            "Objet": f"VIDANGE MOTEUR ({releve_h}h)",
            "M_Num": 0.0, "Statut": "Fait", "Type": "Maintenance"
        }
        df_m = pd.concat([df_m, pd.DataFrame([new_v])], ignore_index=True)
        sauvegarder_data(df_m, 'maintenance.json')
        params['cible_vidange'] = releve_h + 100.0
        sauver_params(params)
        st.success("Vidange archivée !")
        st.rerun()

    st.divider()
    st.subheader("📋 Historique")
    # ... (Suite de ton code d'affichage d'historique)
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


































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































