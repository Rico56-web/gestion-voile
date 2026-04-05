
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import html
import streamlit.components.v1 as components
from datetime import datetime, date
# --- FONCTIONS DE SÉCURITÉ ---
def clean_text(text):
    """Nettoie le texte pour éviter de casser le JSON (supprime retours à la ligne et guillemets)"""
    if text is None or pd.isna(text): 
        return ""
    # Remplace les guillemets doubles par des simples et supprime les sauts de ligne
    return str(text).replace("\n", " ").replace('"', "'").strip()

def safe_val(val, default=0):
    """Convertit en entier sans planter"""
    try:
        if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan": return default
        clean = "".join(filter(str.isdigit, str(val).split('.')[0]))
        return int(clean) if clean else default
    except: return default 
# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

 # --- AJOUTER CE BLOC AU TOUT DÉBUT DE TON SCRIPT (HORS DU IF PAGE) ---
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None
 
# Date du jour en français
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
now = datetime.now()
date_bandeau = f"📅 {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"
 
st.markdown(f"""<style>
    .main-header {{ font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }}
    .date-header {{ text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }}
    button[data-testid="baseButton-primary"] {{ background-color: #ff4b4b !important; color: white !important; }}
    button[data-testid="baseButton-secondary"] {{ background-color: white !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; }}
    .fiche-globale {{ border-radius: 12px; background: white; margin-bottom: 15px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #ddd; }}
    .border-cmn {{ border: 4px solid #0056b3 !important; background-color: #f0f7ff !important; }}
    .prenom-style {{ font-size: 1.5rem; font-weight: bold; color: #1a2a6c; }}
    .societe-style {{ color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; }}
    .statut-badge {{ padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }}
    .container-boutons {{ display: flex; gap: 8px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 12px; }}
    .btn-contact {{ flex: 1; text-align: center; padding: 10px 5px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.85rem; font-weight: bold; }}
    .notes-box {{ background-color: #f8f9fa; border-left: 5px solid #1a2a6c; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 0.95rem; }}
    .calendar-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }}
    .calendar-table th {{ background-color: #1a2a6c; color: white; padding: 10px; border: 1px solid #ddd; }}
    .calendar-table td {{ height: 50px; border: 1px solid #ddd; text-align: center; font-weight: bold; }}
    .day-ok {{ background-color: #2ecc71 !important; color: white; }}
    .day-attente {{ background-color: #f1c40f !important; color: black; }}
</style>""", unsafe_allow_html=True)
 
# --- 2. SÉCURITÉ ACCÈS ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
 
if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("ACCÉDER"):
        if password == "Skipper2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Code incorrect.")
    st.stop()
 
# --- 3. FONCTIONS DONNÉES ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()
 
def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
 
def safe_get(r, key):
    val = r.get(key)
    return str(val).strip() if pd.notna(val) and val is not None else ""
 
# --- 4. NAVIGATION & ENTÊTE ---
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)
 
if "page" not in st.session_state:
    st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state:
    st.session_state.view_archive = False
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "m_edit_idx" not in st.session_state:
    st.session_state.m_edit_idx = None
if "maint_confirm_del" not in st.session_state:
    st.session_state.maint_confirm_del = None
 
# PASSAGE À 7 COLONNES ET AJOUT DE "LOG"
m = st.columns(7) 
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES", "LOG"]
 
for i, name in enumerate(menu):
    if m[i].button(name, key=f"nav_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.session_state.edit_idx = None
        st.session_state.m_edit_idx = None
        st.rerun()
        
# --- CHARGEMENT DES DONNÉES ---
df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")
 
# --- NETTOYAGE AUTOMATIQUE DES DONNÉES ---
def harmoniser_paiements(val):
    v = str(val).strip().lower()
    if not v or "un" in v or "non" in v or "pas" in v:
        return "Non payé"
    if "pay" in v:
        return "Payé"
    return "Non payé"
 
if 'Paiement' in df_c.columns:
    df_c['Paiement'] = df_c['Paiement'].apply(harmoniser_paiements)
 
# --- TRI CHRONOLOGIQUE ---
if not df_c.empty and 'DateNav' in df_c.columns:
    try:
        df_c['DateNav'] = df_c['DateNav'].astype(str).str.strip()
        df_c['temp_date'] = pd.to_datetime(df_c['DateNav'], format='%d/%m/%Y', errors='coerce')
        df_c = df_c.sort_values(by='temp_date', ascending=True, na_position='last')
        df_c = df_c.drop(columns=['temp_date'])
    except: pass
# =================================================================
# --- 5. PAGE CONTACTS (VERSION FINALE + NOTES VISIBLES) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    if 'mode_saisie' not in st.session_state: st.session_state.mode_saisie = False
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
    if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None
    if 'view_archive' not in st.session_state: st.session_state.view_archive = False

    if st.session_state.mode_saisie:
        st.markdown('<div class="main-header">📝 FICHE CONTACT</div>', unsafe_allow_html=True)
        idx = st.session_state.edit_idx
        is_edit = idx is not None and idx < len(df_c)
        c_ref = df_c.iloc[idx] if is_edit else {}

        with st.form("form_contact_2026"):
            c1, c2 = st.columns(2)
            f_pre = c1.text_input("👤 Prénom", value=str(c_ref.get('Prénom', '')))
            f_nom = c2.text_input("📛 NOM", value=str(c_ref.get('Nom', '')))
            f_tel = st.text_input("📞 Téléphone", value=str(c_ref.get('Téléphone', '')))
            f_eml = st.text_input("📧 Email", value=str(c_ref.get('Email', '')))
            f_soc = st.text_input("🏢 Société", value=str(c_ref.get('Société', 'PARTICULIER')))
            
            c3, col_paie = st.columns(2)
            l_statuts = ["En attente", "Ok", "Refusé", "Terminé"]
            curr_s = str(c_ref.get('Statut', 'En attente')).capitalize()
            s_idx = l_statuts.index(curr_s) if curr_s in l_statuts else 0
            f_statut = c3.selectbox("🚦 Statut Dossier", options=l_statuts, index=s_idx)
            
            p_val_f = str(c_ref.get('Paiement', '')).strip().upper()
            p_idx = 1 if ("PAY" in p_val_f and "NON" not in p_val_f) else 0
            f_paie = col_paie.selectbox("💰 État Paiement", options=["Non payé", "Payé"], index=p_idx)

            c5, c6, c7 = st.columns([1.5, 1, 1])
            f_dat = c5.text_input("📅 Date Nav", value=str(c_ref.get('DateNav', '')))
            f_jou = c6.number_input("⏳ Jours", min_value=1, value=int(safe_val(c_ref.get('Nbre de jours'), 1)))
            f_per = c7.number_input("👥 Pers", min_value=1, value=int(safe_val(c_ref.get('Nbre de personnes'), 1)))
            
            f_pri = st.number_input("💵 Prix Total (€)", min_value=0, value=int(safe_val(c_ref.get('Prix'), 0)))
            f_com = st.text_area("💬 Notes", value=str(c_ref.get('Commentaires', '')))

            bs1, bs2 = st.columns(2)
            if bs1.form_submit_button("💾 ENREGISTRER", use_container_width=True):
                new_d = {
                    "Prénom": f_pre, "Nom": f_nom.upper(), "Téléphone": f_tel, "Email": f_eml, 
                    "Société": f_soc.upper(), "Statut": f_statut, "DateNav": f_dat, 
                    "Nbre de jours": f_jou, "Nbre de personnes": f_per, "Prix": f_pri, 
                    "Paiement": str(f_paie), "Commentaires": clean_text(f_com)
                }
                if is_edit: df_c.iloc[idx] = new_d
                else: df_c = pd.concat([df_c, pd.DataFrame([new_d])], ignore_index=True)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.mode_saisie = False
                st.rerun()

            if bs2.form_submit_button("🔙 RETOUR", use_container_width=True):
                st.session_state.mode_saisie = False
                st.rerun()

    else:
        st.markdown('<div class="main-header">📇 CONTACTS 2026</div>', unsafe_allow_html=True)
        
        n1, n2, n3 = st.columns([1, 1, 1.2])
        if n1.button("⛵ EN COURS", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
            st.session_state.view_archive = False; st.rerun()
        if n2.button("📦 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
            st.session_state.view_archive = True; st.rerun()
        if n3.button("➕ NOUVEAU", use_container_width=True, type="primary"):
            st.session_state.mode_saisie = True; st.session_state.edit_idx = None; st.rerun()

        search_q = st.text_input("🔍 Rechercher...", "").strip().upper()

        st.divider()

        # Filtrage
        is_paye_mask = df_c['Paiement'].astype(str).str.upper().str.contains("PAY", na=False) & \
                  ~df_c['Paiement'].astype(str).str.upper().str.contains("NON", na=False)
        mask_arch = df_c['Statut'].astype(str).str.upper().str.contains("TERMINÉ|REFUSÉ", na=False) & is_paye_mask
        df_visu = df_c[mask_arch].copy() if st.session_state.view_archive else df_c[~mask_arch].copy()

        if search_q:
            m_s = (df_visu['Nom'].astype(str).str.upper().str.contains(search_q, na=False) | 
                  df_visu['Société'].astype(str).str.upper().str.contains(search_q, na=False))
            df_visu = df_visu[m_s]
            # --- BOUCLE D'AFFICHAGE SÉCURISÉE ---
        for i, r in df_visu.iterrows():
            # 1. Préparation et nettoyage strict des données
            import html
            def clean_h(val):
                """Nettoie la valeur pour l'affichage HTML"""
                return html.escape(str(val)) if pd.notna(val) else ""

            st_b = str(r.get('Statut','En attente')).capitalize()
            nom_v = clean_h(r.get('Nom','')).upper()
            pre_v = clean_h(r.get('Prénom','')).capitalize()
            soc_v = clean_h(r.get('Société','')).upper()
            tel_v = clean_h(r.get('Téléphone',''))
            eml_v = clean_h(r.get('Email',''))
            com_v = clean_h(r.get('Commentaires','')).strip()
            
            p_val_brut = str(r.get('Paiement', '')).strip().upper()
            is_paye = ("PAY" in p_val_brut and "NON" not in p_val_brut)
            p_status, p_color = ("✅ PAYÉ", "#0047AB") if is_paye else ("⚠️ NON PAYÉ", "#e74c3c")
            
            color_map = {"Ok": "#27ae60", "Refusé": "#e74c3c", "Terminé": "#34495e", "En attente": "#f39c12"}
            base_col = "#0047AB" if "CMN" in soc_v else color_map.get(st_b, "#f39c12")
            label_soc = f"🏢 {soc_v}" if soc_v != nom_v and soc_v != "" else "👤 PARTICULIER"
            
            nb_jours = clean_h(r.get('Nbre de jours', '1'))
            prix_v = clean_h(r.get('Prix', '0'))
            pers_v = clean_h(r.get('Nbre de personnes', '1'))
            date_v = clean_h(r.get('DateNav', '-'))

            # 2. Construction de la zone Note (uniquement si remplie)
            note_html = ""
            if com_v and com_v.lower() != 'none':
                note_html = f"""<div style="margin-left:40px; margin-top:10px; padding:10px; background-color:#f8f9fa; border-left:4px solid {base_col}; border-radius:5px; font-size:0.9rem; color:#444; font-style:italic;">💬 {com_v}</div>"""

            # 3. Assemblage de la carte (SANS ESPACES ENTRE LES BALISES pour éviter les bugs Markdown)
            card_template = f"""<div style="border:5px solid {base_col}; border-left:20px solid {base_col}; padding:15px; border-radius:15px; background-color:white; margin-bottom:12px; box-shadow:5px 5px 15px rgba(0,0,0,0.1); font-family:sans-serif;"><span style="float:right; color:{p_color}; font-weight:bold; border:2px solid {p_color}; padding:2px 5px; border-radius:5px; font-size:0.8rem;">{p_status}</span><div style="font-size:1.25rem; font-weight:bold; color:{base_col}; margin-bottom:2px; display:flex; align-items:center;"><span style="background-color:{base_col}; color:white; min-width:28px; height:28px; display:flex; align-items:center; justify-content:center; border-radius:50%; font-size:0.9rem; margin-right:12px;">{i+1}</span>{nom_v} {pre_v}</div><div style="font-weight:bold; color:#666; margin-left:40px; font-size:0.85rem; text-transform:uppercase; margin-bottom:8px;">{label_soc}</div><div style="margin-left:40px; font-size:1rem; font-weight:bold; color:#333;">📞 {tel_v if tel_v not in ['nan',''] else '---'}</div><div style="margin-left:40px; font-size:0.85rem; color:#555;">📧 {eml_v if eml_v not in ['nan',''] else '---'}</div>{note_html}<hr style="border:0; border-top:1px solid #eee; margin:12px 0;"><div style="display:flex; justify-content:space-between; align-items:center; background:#f8f9fa; padding:8px 12px; border-radius:8px;"><div style="text-align:center; flex:1;"><div style="font-size:0.6rem; color:#888;">DATE/DURÉE</div><div style="font-size:0.85rem; font-weight:bold;">{date_v} ({nb_jours}j)</div></div><div style="text-align:center; flex:1; border-left:1px solid #ddd; border-right:1px solid #ddd;"><div style="font-size:0.6rem; color:#888;">PRIX</div><div style="font-size:0.85rem; font-weight:bold; color:#27ae60;">{prix_v}€</div></div><div style="text-align:center; flex:1;"><div style="font-size:0.6rem; color:#888;">PERS.</div><div style="font-size:0.85rem; font-weight:bold;">{pers_v}p</div></div></div></div>"""
            
            st.markdown(card_template, unsafe_allow_html=True)

            # --- BOUTONS D'ACTION (Hors HTML pour plus de stabilité) ---
            t_clean = str(tel_v).replace(" ","").replace(".","")
            st.markdown(f"""<div style="display:flex;gap:8px;margin-bottom:15px;"><a href="tel:{t_clean}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:14px;">📞 APPEL</a><a href="https://wa.me/{t_clean}" style="flex:1;text-align:center;background:#25D366;color:white;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;font-size:14px;">🟢 WA</a><a href="mailto:{eml_v}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:14px;">✉️ MAIL</a></div>""", unsafe_allow_html=True)

            g1, g2 = st.columns(2)
            if g1.button(f"✏️ MODIFIER {i+1}", key=f"ed_v_{i}", use_container_width=True):
                st.session_state.edit_idx = i
                st.session_state.mode_saisie = True
                st.rerun()
            if g2.button(f"🗑️ SUPPRIMER {i+1}", key=f"dl_v_{i}", use_container_width=True):
                st.session_state.confirm_del_idx = i
                st.rerun()
            
            # Dialogue de suppression
            if st.session_state.get('confirm_del_idx') == i:
                st.warning(f"Confirmer la suppression de {nom_v} ?")
                cy, cn = st.columns(2)
                if cy.button("OUI, SUPPRIMER", key=f"y_v_{i}", use_container_width=True, type="primary"):
                    df_c = df_c.drop(i).reset_index(drop=True)
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.confirm_del_idx = None
                    st.rerun()
                if cn.button("ANNULER", key=f"n_v_{i}", use_container_width=True):
                    st.session_state.confirm_del_idx = None
                    st.rerun()
  
# =================================================================
# --- 6. PAGE PLANNING (CORRECTIF CMN & COULEUR TOTAL) ---
# =================================================================
elif st.session_state.page == "PLANNING":
    from datetime import datetime, date, timedelta
    import calendar

    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)

    # INITIALISATION SANS CONFLIT
    if 'curr_month_idx' not in st.session_state:
        st.session_state.curr_month_idx = aujourdhui.month - 1
    if 'curr_year' not in st.session_state:
        st.session_state.curr_year = aujourdhui.year

    # CSS
    st.markdown("""<style>.block-container { padding: 10px 5px !important; } .full-width-cal { width: 98% !important; margin: auto !important; border-collapse: collapse; table-layout: fixed; } .full-width-cal td { width: 14.28%; padding: 0 !important; border: 0.5px solid #eee; }</style>""", unsafe_allow_html=True)
    st.markdown('<div class="main-header">🗓️ PLANNING VESTA 2026</div>', unsafe_allow_html=True)

    # --- NAVIGATION (VERSION SYNCHRONISÉE) ---
    if 'nav_key' not in st.session_state:
        st.session_state.nav_key = 0

    col_m, col_y, col_now = st.columns([1.5, 1, 0.8])
    
    with col_m:
        sel_m_nom = st.selectbox(
            "Mois", 
            m_noms, 
            index=st.session_state.curr_month_idx,
            key=f"month_select_{st.session_state.nav_key}" 
        )
        sel_m = m_noms.index(sel_m_nom) + 1
        st.session_state.curr_month_idx = sel_m - 1
        
    with col_y:
        annees_dispo = [2026, 2027, 2028]
        idx_y = annees_dispo.index(st.session_state.curr_year) if st.session_state.curr_year in annees_dispo else 0
        sel_y = st.selectbox(
            "Année", 
            annees_dispo, 
            index=idx_y,
            key=f"year_select_{st.session_state.nav_key}"
        )
        st.session_state.curr_year = sel_y
        
    with col_now:
        if st.button("📍 ICI", use_container_width=True):
            st.session_state.curr_month_idx = aujourdhui.month - 1
            st.session_state.curr_year = aujourdhui.year
            st.session_state.nav_key += 1
            st.rerun()

    # --- CALCULS ---
    jours_occ = {}
    total_mois = 0
    missions_list = []

    if df_c is not None and not df_c.empty:
        for idx, r in df_c.iterrows():
            try:
                d_val = r.get('DateNav', '')
                if pd.isna(d_val) or str(d_val).strip() == "": continue
                d_str = str(d_val).strip().split(' ')[0]
                if '/' in d_str:
                    parts = d_str.split('/')
                    dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
                    if yv < 100: yv += 2000
                    date_debut = date(yv, mv, dv)
                else: continue
                
                n_j = int(float(safe_val(r.get('Nbre de jours'), 1)))
                soc_v = str(r.get('Société','')).upper() # Récupération société
                
                for i in range(n_j):
                    date_courante = date_debut + timedelta(days=i)
                    if date_courante.month == sel_m and date_courante.year == sel_y:
                        p_val = str(r.get('Paiement', '')).upper()
                        s_val = str(r.get('Statut', '')).lower()
                        is_paye = "PAY" in p_val and "NON" not in p_val
                        
                        # --- LOGIQUE COULEUR CALENDRIER (CMN PRIORITAIRE) ---
                        color = "transparent"
                        if "CMN" in soc_v:
                            color = "#0047AB" # Bleu CMN
                        elif date_courante < aujourdhui:
                            color = "#34495e" if is_paye else "#e74c3c"
                        elif "ok" in s_val:
                            color = "#27ae60"
                        elif "attente" in s_val:
                            color = "#f39c12"
                            
                        jours_occ[date_courante.day] = {"c": color}

                date_fin = date_debut + timedelta(days=n_j-1)
                if (date_debut.year == sel_y and date_debut.month == sel_m) or (date_fin.year == sel_y and date_fin.month == sel_m):
                    missions_list.append({'data': r, 'idx': idx, 'start': date_debut, 'end': date_fin, 'n_j': n_j})
                    if date_debut.month == sel_m:
                        val_prix = str(r.get('Prix', 0)).replace(',','.').replace('€','').strip()
                        total_mois += float(val_prix) if val_prix else 0
            except: continue

    # --- AFFICHAGE TABLEAU ---
    h_cal = '<table class="full-width-cal" style="text-align:center; background:white;">'
    h_cal += '<tr style="background:#f1f3f5; font-size:10px; font-weight:bold;"><td>Lu</td><td>Ma</td><td>Me</td><td>Je</td><td>Ve</td><td style="color:#d9534f;">Sa</td><td style="color:#d9534f;">Di</td></tr>'
    cal_mat = calendar.monthcalendar(sel_y, sel_m)
    for sem in cal_mat:
        h_cal += '<tr>'
        for i, jour in enumerate(sem):
            if jour == 0:
                h_cal += '<td style="height:48px; background:#fdfdfd;"></td>'
            else:
                occ = jours_occ.get(jour, {})
                bg_c = occ.get("c", "transparent")
                is_today = (jour == aujourdhui.day and sel_m == aujourdhui.month and sel_y == aujourdhui.year)
                cell_bg = "background:#D2B48C;" if is_today else ("background:#f9f9f9;" if i >= 5 else "")
                txt_c = "white" if bg_c != "transparent" else "black"
                circle = f'<div style="background:{bg_c}; color:{txt_c}; border-radius:50%; width:28px; height:28px; line-height:28px; margin:auto; font-weight:bold; font-size:12px;">{jour}</div>'
                h_cal += f'<td style="height:50px; {cell_bg}">{circle}</td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    st.markdown(h_cal, unsafe_allow_html=True)

    # LISTE DES MISSIONS
    st.markdown(f"#### 📋 {sel_m_nom} {sel_y}")
    if missions_list:
        missions_list.sort(key=lambda x: x['start'])
        for m in missions_list:
            r = m['data']
            soc = str(r.get('Société','')).upper()
            c_line = "#0047AB" if "CMN" in soc else "#27ae60"
            txt_d = f"{m['start'].day:02d}/{m['start'].month:02d}"
            if m['n_j'] > 1: txt_d += f" ➔ {m['end'].day:02d}/{m['end'].month:02d}"
            icon = "💰" if "PAY" in str(r.get('Paiement','')).upper() and "NON" not in str(r.get('Paiement','')).upper() else "⚠️"
            st.markdown(f"""<div style="display: flex; padding: 10px; border-bottom: 1px solid #eee; background: white; align-items: center;"><div style="background: {c_line}; color: white; border-radius: 5px; padding: 4px; min-width: 85px; text-align: center; font-weight: bold; margin-right: 10px; line-height:1.2;"><span style="font-size: 0.75rem;">{txt_d}</span><br><span style="font-size: 0.5rem;">{"JOURS" if m['n_j'] > 1 else "JOUR"}</span></div><div style="flex-grow: 1;"><b>{icon} {str(r.get('Nom','')).upper()}</b><br><small>{soc} | {r.get('Prix','0')}€ | {m['n_j']}j</small></div></div>""", unsafe_allow_html=True)
            if st.button(f"🔍 FICHE : {str(r.get('Nom',''))}", key=f"btn_{m['idx']}", use_container_width=True):
                st.session_state.edit_idx = m['idx']
                st.session_state.mode_saisie = True
                st.session_state.page = "CONTACTS"
                st.rerun()

    # --- NOUVEAU BLOC TOTAL (Couleur différente du bleu) ---
    st.markdown(f"""
    <div style="background:#2c3e50; color:#f1c40f; padding:15px; border-radius:10px; text-align:center; margin-top:10px; border: 2px solid #f1c40f;">
        <span style="font-size:0.8rem; color:white; text-transform:uppercase;">Estimation Chiffre d'Affaires</span><br>
        <b style="font-size:1.4rem;">TOTAL : {total_mois:,.0f} €</b>
    </div>
    """, unsafe_allow_html=True)
# =================================================================
# --- 7. PAGE STATS - VESTA SKIPPER 2026 (VERSION FINALE VALIDÉE) ---
# =================================================================
elif st.session_state.page == "STATS":
    st.title("⚓ Vesta Skipper 2026 - Pilotage Global")
    import plotly.express as px
    from datetime import datetime
    import pandas as pd

    # --- 1. PRÉPARATION ---
    df_st = df_c.copy()
    df_m = charger_data('maintenance.json')
    # On fixe la date au 5 Avril 2026 pour la cohérence des calculs
    maintenant = pd.Timestamp(2026, 4, 5) 

    def clean_val(v):
        if v is None or str(v).strip() in ["", "nan", "None", "null"]: return 0.0
        try: 
            # Nettoyage strict pour ne pas transformer des dates en euros
            s = str(v).replace('€','').replace(' ','').replace(',','.')
            return float(s)
        except: return 0.0

    # --- 2. CALCULS RECETTES ---
    recette_faite = 0.0      
    recette_a_recevoir = 0.0 
    recette_future = 0.0     

    if not df_st.empty:
        # On s'assure que les colonnes sont propres
        df_st.columns = [str(c).strip() for c in df_st.columns]
        
        # Conversion du Prix (colonne 'Prix')
        df_st['PrixNum'] = df_st['Prix'].apply(clean_val)
        
        # Conversion Date (colonne 'DateNav')
        df_st['Date_C'] = df_st['DateNav'].astype(str).str.replace('\\', '', regex=False)
        df_st['dt_obj'] = pd.to_datetime(df_st['Date_C'], dayfirst=True, errors='coerce')

        # Logique de paiement INFRAILLIBLE
        def check_paye(val):
            s = str(val).upper()
            if "NON" in s: return False # Bloque "Non payé"
            return "PAY" in s or s == "OK" # Autorise "Payé", "Paye", "Acompte", "OK"

        df_st['Is_Paid'] = df_st['Paiement'].apply(check_paye)

        # 1. ENCAISSÉ (Elisabeth + Pedro + Benoit = 619€)
        recette_faite = df_st[df_st['Is_Paid'] == True]['PrixNum'].sum()
        
        # 2. RETARD (Ex: CMN du 7 et 21 mars)
        mask_retard = (df_st['dt_obj'] <= maintenant) & (df_st['Is_Paid'] == False)
        recette_a_recevoir = df_st[mask_retard]['PrixNum'].sum()
        
        # 3. À VENIR (Tout le reste après le 5 avril)
        mask_futur = (df_st['dt_obj'] > maintenant) & (df_st['Is_Paid'] == False)
        recette_future = df_st[mask_futur]['PrixNum'].sum()

    # --- 3. CALCULS MAINTENANCE ---
    maint_faite = 0.0
    f_vesta, f_autres, f_obligatoires = 0.0, 0.0, 0.0
    if not df_m.empty:
        df_m['M_Calc'] = df_m['M_Num'] if 'M_Num' in df_m.columns else df_m['Montant'].apply(clean_val)
        for _, row in df_m.iterrows():
            mt, obj = row['M_Calc'], str(row.get('Objet', '')).upper()
            if "VESTA" in obj: f_vesta += mt
            elif any(x in obj for x in ["MAIF", "ASSUR", "PORT"]): f_obligatoires += mt
            else: f_autres += mt
            if str(row.get('Statut', '')).upper() in ["OK", "FAIT"]: maint_faite += mt

    # --- 4. AFFICHAGE ---
    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Encaissé Réel", f"{int(recette_faite)} €")
    k2.metric("⏳ Retards (Dû)", f"{int(recette_a_recevoir)} €")
    k3.metric("📅 Reste à venir", f"{int(recette_future)} €")

    with st.expander("🔍 Vérifier le détail des encaissements"):
        cols = ['DateNav', 'Prénom', 'Nom', 'Société', 'Prix', 'Paiement']
        existantes = [c for c in cols if c in df_st.columns]
        st.dataframe(df_st[df_st['Is_Paid'] == True][existantes], use_container_width=True)

    st.divider()

    # --- 5. GRAPHIQUES ---
    c1, c2 = st.columns(2)
    with c1:
        fig1 = px.pie(values=[maint_faite, recette_faite, recette_a_recevoir],
                     names=['Dépenses OK', 'Recettes OK', 'Retards'],
                     title="🎯 Trésorerie Net (Réalisé)", hole=0.5,
                     color_discrete_sequence=['#e74c3c', '#2ecc71', '#f1c40f'])
        st.plotly_chart(fig1, use_container_width=True)
    with c2:
        fig2 = px.pie(values=[f_vesta, f_obligatoires, f_autres],
                     names=['Vesta', 'Assur/Port', 'Autres'],
                     title="💸 Nature des Frais", hole=0.5,
                     color_discrete_sequence=['#3498db', '#34495e', '#9b59b6'])
        st.plotly_chart(fig2, use_container_width=True)
# =================================================================
# --- 8. PAGE MAINTENANCE (EDITION & SÉCURITÉ SUPPRESSION) ---
# =================================================================
elif st.session_state.page == "MAINT":
    st.title("🔧 Maintenance & Charges Vesta")
 
    file_path_m = 'maintenance.json'
    df_m = charger_data(file_path_m)
    
    if df_m.empty:
        df_m = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut", "Type"])
 
    # --- ZONE D'AJOUT ---
    with st.expander("➕ Ajouter une dépense ou une charge", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            f_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"), key="add_m_date")
            f_obj = st.text_input("Objet", key="add_m_obj")
        with col2:
            f_type = st.selectbox("Type", ["Frais Obligatoires", "Frais Maint Vesta", "Frais Autres"], key="add_m_type")
            f_statut = st.selectbox("Statut", ["À prévoir", "Fait"], key="add_m_statut")
            
        f_mt = st.number_input("Montant (€)", min_value=0.0, step=10.0, key="add_m_mt")
        is_recurring = st.checkbox("🔄 Répéter chaque mois jusqu'à fin 2026")
        
        if st.button("💾 ENREGISTRER L'ENTRÉE", type="primary", use_container_width=True):
            if f_obj and f_mt > 0:
                new_data = []
                if is_recurring:
                    j, m_start, a = map(int, f_date.split('/'))
                    for m_idx in range(m_start, 13):
                        new_data.append({"Date": f"{j:02d}/{m_idx:02d}/{a}", "Objet": f"{f_obj} (M{m_idx})", "Montant": float(f_mt), "Statut": f_statut, "Type": f_type})
                else:
                    new_data.append({"Date": f_date, "Objet": f_obj, "Montant": float(f_mt), "Statut": f_statut, "Type": f_type})
                
                df_m = pd.concat([df_m, pd.DataFrame(new_data)], ignore_index=True)
                sauvegarder_data(df_m, file_path_m)
                st.success("Enregistré !")
                st.rerun()

    st.divider()
 
    # --- LISTE DES DÉPENSES ---
    if not df_m.empty:
        df_m['M_Num'] = pd.to_numeric(df_m['Montant'], errors='coerce').fillna(0)
        st.metric("TOTAL CUMULÉ", f"{df_m['M_Num'].sum():.0f} €")
 
        # Tri par date décroissante
        df_m['dt_temp'] = pd.to_datetime(df_m['Date'], format='%d/%m/%Y', errors='coerce')
        df_m = df_m.sort_values('dt_temp', ascending=False).drop(columns=['dt_temp'])

        for index, item in df_m.iterrows():
            couleur = "🟢" if item['Statut'] == "Fait" else "⏳"
            with st.expander(f"{couleur} {item['Date']} - {item['Objet']} ({item['Montant']}€)"):
                
                # --- MODE ÉDITION ---
                edit_mode = st.toggle("📝 Modifier cette fiche", key=f"toggle_{index}")
                
                if edit_mode:
                    e_date = st.text_input("Date", item['Date'], key=f"ed_date_{index}")
                    e_obj = st.text_input("Objet", item['Objet'], key=f"ed_obj_{index}")
                    e_mt = st.number_input("Montant (€)", value=float(item['Montant']), key=f"ed_mt_{index}")
                    e_type = st.selectbox("Type", ["Frais Obligatoires", "Frais Maint Vesta", "Frais Autres"], 
                                         index=["Frais Obligatoires", "Frais Maint Vesta", "Frais Autres"].index(item.get('Type', 'Frais Autres')), key=f"ed_type_{index}")
                    e_statut = st.selectbox("Statut", ["À prévoir", "Fait"], 
                                           index=0 if item['Statut'] != "Fait" else 1, key=f"ed_stat_{index}")
                    
                    if st.button("✅ VALIDER LES MODIFICATIONS", key=f"save_{index}", use_container_width=True):
                        df_m.at[index, 'Date'] = e_date
                        df_m.at[index, 'Objet'] = e_obj
                        df_m.at[index, 'Montant'] = e_mt
                        df_m.at[index, 'Type'] = e_type
                        df_m.at[index, 'Statut'] = e_statut
                        sauvegarder_data(df_m, file_path_m)
                        st.rerun()
                else:
                    st.write(f"**Type :** {item.get('Type', 'N/A')}")
                    st.write(f"**Statut actuel :** {item['Statut']}")

                st.write("---")
                # --- SUPPRESSION AVEC CONFIRMATION ---
                if st.button(f"🗑️ Supprimer", key=f"pre_del_{index}", use_container_width=True, type="secondary"):
                    st.session_state[f"confirm_del_{index}"] = True
                
                if st.session_state.get(f"confirm_del_{index}", False):
                    st.warning("⚠️ Confirmer la suppression définitive ?")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("OUI", key=f"real_del_{index}", type="danger", use_container_width=True):
                            df_m = df_m.drop(index).reset_index(drop=True)
                            sauvegarder_data(df_m, file_path_m)
                            st.rerun()
                    with col_no:
                        if st.button("NON", key=f"cancel_del_{index}", use_container_width=True):
                            st.session_state[f"confirm_del_{index}"] = False
                            st.rerun()

    # --- ZONE DE DANGER ---
    st.write("---")
    with st.expander("🚨 Archives"):
        if st.button("🗄️ ARCHIVER TOUT", use_container_width=True):
            if not df_m.empty:
                df_arch = charger_data('archives_maintenance.json')
                sauvegarder_data(pd.concat([df_arch, df_m], ignore_index=True), 'archives_maintenance.json')
                sauvegarder_data(pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut", "Type"]), file_path_m)
                st.rerun()
# =================================================================
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
        # Conversion temporaire pour le filtrage
        df_fact = df_c.copy()
        df_fact['dt'] = pd.to_datetime(df_fact['DateNav'], format='%d/%m/%Y', errors='coerce')
        
        # Filtre : Société CMN + Mois + Année
        mask_cmn = (df_fact['Société'].astype(str).str.upper() == "CMN") & \
                   (df_fact['dt'].dt.month == index_mois) & \
                   (df_fact['dt'].dt.year == sel_annee)
        
        df_cmn_mois = df_fact[mask_cmn].copy()
        
        if not df_cmn_mois.empty:
            st.subheader(f"Missions CMN - {sel_mois} {sel_annee}")
            
            # Nettoyage des prix pour le calcul
            def clean_prix(x):
                try:
                    s = "".join(c for c in str(x) if c.isdigit() or c in ".,")
                    return float(s.replace(",", "."))
                except: return 0.0
 
            df_cmn_mois['PrixNum'] = df_cmn_mois['Prix'].apply(clean_prix)
            total_cmn = df_cmn_mois['PrixNum'].sum()
            
            # Affichage du tableau de contrôle sur l'iPhone
            st.table(df_cmn_mois[['DateNav', 'Nom', 'Prix']].set_index('DateNav'))
            st.metric("Total à facturer", f"{total_cmn:.2f} €")
            
            # --- 3. PRÉPARATION DU TEXTE ALIGNÉ (12 ET 3 ESPACES) ---
            st.divider()
            st.subheader("✉️ Rapport pour le Trésorier")
            
            lignes_missions = []
            esp12 = " " * 12
            esp3  = " " * 3
            
            for _, row in df_cmn_mois.iterrows():
                d_str = str(row['DateNav']).ljust(10)
                n_str = str(row['Nom'])
                p_str = f"{row['PrixNum']:.2f} €"
                # Assemblage de la ligne demandée
                lignes_missions.append(f"{d_str}{esp12}{n_str}{esp3}{p_str}")
            
            texte_missions = "\n".join(lignes_missions)
            
            destinataire = "tresorier@cmn-asso.fr, aurelienfaucheux@gmail.com"
            objet = f"Facturation Missions Vesta - {sel_mois} {sel_annee}"
            
            # Utilisation des TRIPLES GUILLEMETS pour éviter la SyntaxError
            corps_mail = f"""Bonjour,
 
J'espère que vous allez bien ! ⛵
 
Voici le récapitulatif des navigations de la CMN concernant le mois de {sel_mois} {sel_annee} :
 
{texte_missions}
 
Le montant total s'élève à {total_cmn:.2f} €.
 
Merci d'avance pour le règlement et à très vite sur l'eau !
 
Amicalement,
Eric (vesta)"""
 
            # --- 4. ZONE D'ENVOI ET COPIE ---
            st.text_area("Copier ce texte pour Gmail :", corps_mail, height=300)
            
            st.info(f"**Destinataire :** {destinataire}\n\n**Objet :** {objet}")
            
            import urllib.parse
            mail_link = f"mailto:{destinataire}?subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            
            st.link_button("🚀 TENTER L'ENVOI DIRECT (MAILTO)", mail_link, use_container_width=True)
            st.caption("Note : Si le bouton bloque, utilise le copier-coller du texte ci-dessus dans ton appli Gmail.")
            
        else:
            st.info(f"Aucune mission CMN trouvée pour {sel_mois} {sel_annee}.")
    else:
        st.warning("La base de données 'Contacts' est vide.")

# =================================================================
# --- 10. PAGE LOG (CONSULTATION DES ARCHIVES) ---
# =================================================================
elif st.session_state.page == "LOG":
    st.title("📂 Archives & Logs")
    
    annee_actuelle = datetime.now().year
    nom_archive = f"archives_{annee_actuelle}.json"
    
    df_arch = charger_data(nom_archive)
    
    if not df_arch.empty:
        st.write(f"### 📋 Missions Archivées {annee_actuelle}")
        st.dataframe(df_arch, use_container_width=True)
    else:
        st.info("Aucune archive trouvée pour cette saison.")
 
# --- FIN DU FICHIER ---



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































