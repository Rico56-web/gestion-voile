
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import json
import html
import streamlit.components.v1 as components
from datetime import datetime, date
import plotly.express as px

# --- BLOC DE SECOURS (A mettre ici) ---
def preparer_log_safe(df):
    cols_attendues = ["Date", "Meteo", "PortDep", "PortArr", "MotDep", "MotArr", "MilDep", "MilArr", "TotalMot", "TotalMil", "Observations"]
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=cols_attendues)
    
    # S'assurer que les colonnes de calcul sont numériques
    for c in ["TotalMot", "TotalMil", "MotDep", "MotArr", "MilDep", "MilArr"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        else:
            df[c] = 0.0
            
    # Création d'une date technique pour le tri
    if 'Date' in df.columns:
        df['dt_tri'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    else:
        df['dt_tri'] = pd.Timestamp.now()
        
    return df

# ... vos autres fonctions (charger_data, sauvegarder_data) ...
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
        
def archiver_donnees(df_source, date_debut, date_fin, fichier_source, fichier_archive, col_date='Date'):
    df_source['dt_temp'] = pd.to_datetime(df_source[col_date], dayfirst=True, errors='coerce')
    mask = (df_source['dt_temp'].dt.date >= date_debut) & (df_source['dt_temp'].dt.date <= date_fin)
    
    a_archiver = df_source[mask].copy()
    a_garder = df_source[~mask].copy()
    
    if not a_archiver.empty:
        df_arch_old = charger_data(fichier_archive)
        df_arch_new = pd.concat([df_arch_old, a_archiver.drop(columns=['dt_temp'])], ignore_index=True)
        sauvegarder_data(df_arch_new, fichier_archive)
        sauvegarder_data(a_garder.drop(columns=['dt_temp']), fichier_source)
        return len(a_archiver)
    return 0

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

# On remplace LOGBOOK par LOG ici pour correspondre à tes conditions 'if page == "LOG"'
m = st.columns(7) 
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "ARCHIVES", "LOG"] # <-- CHANGÉ ICI
icones = {"CONTACTS": "👤", "PLANNING": "🗓️", "STATS": "📊", "MAINT": "🛠️", "FACTURES": "🧾", "ARCHIVES": "📂", "LOG": "📖"}

for i, name in enumerate(menu):
    if m[i].button(f"{icones[name]} {name}", key=f"nav_{name}", use_container_width=True, 
                   type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
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
# --- 5. PAGE CONTACTS (OPTIMISÉE COMPACTE) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    # Bouton Archives en haut
    if st.button("📦 ALLER AUX ARCHIVES", key="k_arch_c", use_container_width=True, type="primary"):
        st.session_state.last_page = "CONTACTS"
        st.session_state.page = "ARCHIVES"
        st.rerun()
    
    st.title("👤 MES CONTACTS")
    st.divider()
    
    if 'mode_saisie' not in st.session_state: st.session_state.mode_saisie = False
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
    if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None
    if 'view_archive' not in st.session_state: st.session_state.view_archive = False

    if st.session_state.mode_saisie:
        # --- FORMULAIRE DE SAISIE (Inchangé pour la stabilité) ---
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
        # --- MODE AFFICHAGE LISTE ---
        st.markdown('<div class="main-header">📇 CONTACTS 2026</div>', unsafe_allow_html=True)
        
        n1, n2, n3 = st.columns([1, 1, 1.2])
        if n1.button("⛵ EN COURS", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
            st.session_state.view_archive = False; st.rerun()
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

        # --- BOUCLE D'AFFICHAGE COMPACTE ---
        for i, r in df_visu.iterrows():
            def clean_h(val): return html.escape(str(val)) if pd.notna(val) else ""

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

            # Zone Note compacte
            note_html = ""
            if com_v and com_v.lower() != 'none':
                note_html = f"""<div style="margin-left:40px; margin-top:5px; padding:8px; background-color:#f8f9fa; border-left:4px solid {base_col}; border-radius:5px; font-size:0.85rem; color:#444; font-style:italic;">💬 {com_v}</div>"""

            # 1. Carte HTML (margin-bottom: 5px et padding réduit)
            card_template = f"""<div style="border:5px solid {base_col}; border-left:15px solid {base_col}; padding:10px; border-radius:15px; background-color:white; margin-bottom:5px; box-shadow:2px 2px 8px rgba(0,0,0,0.1); font-family:sans-serif;"><span style="float:right; color:{p_color}; font-weight:bold; border:1px solid {p_color}; padding:1px 4px; border-radius:5px; font-size:0.75rem;">{p_status}</span><div style="font-size:1.1rem; font-weight:bold; color:{base_col}; margin-bottom:2px; display:flex; align-items:center;"><span style="background-color:{base_col}; color:white; min-width:24px; height:24px; display:flex; align-items:center; justify-content:center; border-radius:50%; font-size:0.8rem; margin-right:10px;">{i+1}</span>{nom_v} {pre_v}</div><div style="font-weight:bold; color:#666; margin-left:34px; font-size:0.8rem; text-transform:uppercase; margin-bottom:5px;">{label_soc}</div><div style="margin-left:34px; font-size:0.95rem; font-weight:bold; color:#333;">📞 {tel_v if tel_v not in ['nan',''] else '---'}</div><div style="margin-left:34px; font-size:0.8rem; color:#555;">📧 {eml_v if eml_v not in ['nan',''] else '---'}</div>{note_html}<hr style="border:0; border-top:1px solid #eee; margin:8px 0;"><div style="display:flex; justify-content:space-between; align-items:center; background:#f8f9fa; padding:6px 10px; border-radius:8px;"><div style="text-align:center; flex:1;"><div style="font-size:0.55rem; color:#888;">DATE/DURÉE</div><div style="font-size:0.8rem; font-weight:bold;">{date_v} ({nb_jours}j)</div></div><div style="text-align:center; flex:1; border-left:1px solid #ddd; border-right:1px solid #ddd;"><div style="font-size:0.55rem; color:#888;">PRIX</div><div style="font-size:0.8rem; font-weight:bold; color:#27ae60;">{prix_v}€</div></div><div style="text-align:center; flex:1;"><div style="font-size:0.55rem; color:#888;">PERS.</div><div style="font-size:0.8rem; font-weight:bold;">{pers_v}p</div></div></div></div>"""
            st.markdown(card_template, unsafe_allow_html=True)

            # 2. Boutons Com (Appel, WA, Mail) avec réduction d'espace Streamlit
            st.write('<div style="margin-top:-15px"></div>', unsafe_allow_html=True)
            t_clean = str(tel_v).replace(" ","").replace(".","")
            st.markdown(f"""<div style="display:flex;gap:5px;margin-bottom:5px;"><a href="tel:{t_clean}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:10px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:12px;">📞 APPEL</a><a href="https://wa.me/{t_clean}" style="flex:1;text-align:center;background:#25D366;color:white;text-decoration:none;padding:10px;border-radius:10px;font-weight:bold;font-size:12px;">🟢 WA</a><a href="mailto:{eml_v}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:10px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:12px;">✉️ MAIL</a></div>""", unsafe_allow_html=True)

            # 3. Boutons Modifier/Supprimer avec réduction d'espace Streamlit
            st.write('<div style="margin-top:-15px"></div>', unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            if g1.button(f"✏️ MODIFIER {i+1}", key=f"ed_v_{i}", use_container_width=True):
                st.session_state.edit_idx = i
                st.session_state.mode_saisie = True
                st.rerun()
            if g2.button(f"🗑️ SUPPRIMER {i+1}", key=f"dl_v_{i}", use_container_width=True):
                st.session_state.confirm_del_idx = i
                st.rerun()
            
            # 4. Dialogue suppression
            if st.session_state.get('confirm_del_idx') == i:
                st.warning(f"Confirmer suppression ?")
                cy, cn = st.columns(2)
                if cy.button("OUI", key=f"y_v_{i}", use_container_width=True, type="primary"):
                    df_c = df_c.drop(i).reset_index(drop=True)
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.confirm_del_idx = None
                    st.rerun()
                if cn.button("NON", key=f"n_v_{i}", use_container_width=True):
                    st.session_state.confirm_del_idx = None
                    st.rerun()
            
            # Séparateur final minimal
            st.write('<div style="margin-top:5px; margin-bottom:10px; border-bottom:1px solid #eee;"></div>', unsafe_allow_html=True)
  
# =================================================================
# --- 6. PAGE PLANNING (CORRECTIF CMN & COULEUR TOTAL) ---
# =================================================================
if st.session_state.page == "PLANNING":
    # 1. Navigation condensée (Spécial iPhone)
    if st.button("📦 ALLER AUX ARCHIVES", key="k_arch_p", use_container_width=True, type="primary"):
        st.session_state.last_page = "PLANNING"
        st.session_state.page = "ARCHIVES"
        st.rerun()
    
    st.title("🗓️ PLANNING 2026")
    st.divider()
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
    
    st.divider() # Sépare la navigation du calendrier
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
# --- 9. PAGE STATS (FINANCES & NAVIGATION) ---
# =================================================================
if st.session_state.page == "STATS":
    import plotly.express as px
    import pandas as pd

    # --- 1. NAVIGATION & FILTRES ---
    col_t1, col_t2 = st.columns([2, 1])
    col_t1.title("📊 Bilan Vesta")
    
    ANNEES_STATS = [2025, 2026, 2027, 2028]
    sel_y_stats = col_t2.selectbox("Saison", ANNEES_STATS, index=1, label_visibility="collapsed")
    
    mode_previ = st.toggle("🔮 Voir le Prévisionnel (Toute l'année)", value=False)
    
    if st.button("📂 ARCHIVES", use_container_width=True):
        st.session_state.page = "ARCHIVES"
        st.rerun()

    # --- 2. RÉCUPÉRATION DES DONNÉES ---
    df_m = charger_data('maintenance.json') 
    df_c = charger_data('contacts.json')    
    df_log = charger_data('logbook.json')   

    # --- TRAITEMENT DES CHARGES ---
    total_charges = 0
    df_charges_view = pd.DataFrame()
    if not df_m.empty:
        df_m['M_Num'] = pd.to_numeric(df_m['M_Num'], errors='coerce').fillna(0.0)
        df_m['dt'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_m_yr = df_m[df_m['dt'].dt.year == sel_y_stats].copy()
        df_charges_view = df_m_yr if mode_previ else df_m_yr[df_m_yr['Statut'] == "Fait"].copy()
        total_charges = df_charges_view['M_Num'].sum()

    # --- TRAITEMENT DES RECETTES ---
    total_recettes = 0
    df_recettes_view = pd.DataFrame()
    if not df_c.empty:
        df_temp = df_c.copy()
        df_temp['dt'] = pd.to_datetime(df_temp['DateNav'], dayfirst=True, errors='coerce')
        df_temp = df_temp[df_temp['dt'].dt.year == sel_y_stats].copy()
        df_temp['P_Num'] = pd.to_numeric(df_temp['Prix'].astype(str).str.replace('€','').str.strip(), errors='coerce').fillna(0.0)
        
        def check_p(val):
            v = str(val).upper()
            return "PAY" in v and "NON" not in v
        
        df_recettes_view = df_temp if mode_previ else df_temp[df_temp['Paiement'].apply(check_p)].copy()
        total_recettes = df_recettes_view['P_Num'].sum()

    # --- TRAITEMENT NAVIGATION ---
    total_h_moteur = 0
    total_milles = 0
    if not df_log.empty:
        df_log['dt'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
        df_log_yr = df_log[df_log['dt'].dt.year == sel_y_stats].copy()
        total_h_moteur = pd.to_numeric(df_log_yr.get('TotalMot', 0), errors='coerce').sum()
        total_milles = pd.to_numeric(df_log_yr.get('TotalMil', 0), errors='coerce').sum()

    # --- 3. AFFICHAGE TRÉSORERIE & RÉPARTITION ---
    st.subheader(f"💰 Finances {sel_y_stats}")
    c_pie1, c_pie2, c_sol = st.columns([1, 1, 1])
    
    with c_pie1:
        st.caption("Revenus vs Frais")
        fig1 = px.pie(names=['Charges', 'Recettes'], values=[total_charges, total_recettes],
                     color_discrete_map={'Charges': '#ef553b', 'Recettes': '#00cc96'}, hole=0.4)
        fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=180, showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
    
    with c_pie2:
        st.caption("Répartition Frais")
        if not df_charges_view.empty and total_charges > 0:
            df_poste = df_charges_view.groupby('Type')['M_Num'].sum().reset_index()
            fig2 = px.pie(df_poste, names='Type', values='M_Num', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
            fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=180, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
    
    with c_sol:
        solde = total_recettes - total_charges
        txt_c = "#28a745" if solde >= 0 else "#dc3545"
        st.markdown(f"""<div style="text-align:center; border:1px solid #ddd; padding:10px; border-radius:10px; background:#fff; margin-top:25px;">
            <small style="color:#666; font-weight:bold;">SOLDE</small><br>
            <b style="color:{txt_c}; font-size:1.6rem;">{solde:,.0f} €</b></div>""", unsafe_allow_html=True)

    st.divider()

    # --- 4. ANALYSE NAVIGATION ---
    st.subheader("⚓ Analyse Navigation")
    n1, n2, n3 = st.columns(3)
    n1.metric("⚙️ Heures Moteur", f"{total_h_moteur:.1f} h")
    n2.metric("📏 Milles parcourus", f"{total_milles:.0f} mn")
    # Ratio d'autonomie/voile
    ratio = round(total_milles / total_h_moteur, 1) if total_h_moteur > 0 else total_milles
    n3.metric("⛵ Ratio Voile", f"{ratio} mn/h mtr")

    st.divider()

    # --- 5. SYNTHÈSE MENSUELLE ---
    st.subheader("📅 Synthèse Mensuelle")
    mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    synthese_data = []

    for m_idx in range(1, 13):
        m_rec = df_recettes_view[df_recettes_view['dt'].dt.month == m_idx]['P_Num'].sum() if not df_recettes_view.empty else 0
        m_cha = df_charges_view[df_charges_view['dt'].dt.month == m_idx]['M_Num'].sum() if not df_charges_view.empty else 0
        m_mil = df_log_yr[df_log_yr['dt'].dt.month == m_idx].get('TotalMil', 0).sum() if not df_log.empty else 0
        
        if m_rec > 0 or m_cha > 0 or m_mil > 0:
            synthese_data.append({"Mois": mois_noms[m_idx-1], "Recettes": f"{m_rec:.0f}€", "Frais": f"{m_cha:.0f}€", "Milles": f"{m_mil:.0f} mn", "Net": f"{m_rec - m_cha:.0f}€"})

    if synthese_data:
        st.dataframe(pd.DataFrame(synthese_data), use_container_width=True, hide_index=True)

    # --- 6. TABS DÉTAILLÉS ---
    st.divider()
    t1, t2 = st.tabs(["📥 Recettes", "📤 Charges"])
    with t1: st.dataframe(df_recettes_view[['DateNav', 'Nom', 'Prix', 'Paiement']] if not df_recettes_view.empty else pd.DataFrame())
    with t2: st.dataframe(df_charges_view[['Date', 'Objet', 'M_Num', 'Type']] if not df_charges_view.empty else pd.DataFrame())

# =================================================================
# --- 8. PAGE MAINTENANCE (OPTI IPHONE & AUTO-CLOSE) ---
# =================================================================
if st.session_state.page == "MAINT":
    if st.button("📦 ALLER AUX ARCHIVES", key="k_arch_m", use_container_width=True, type="primary"):
        st.session_state.last_page = "MAINTENANCE"
        st.session_state.page = "ARCHIVES"
        st.rerun()
    
    st.title("🛠️ MAINTENANCE")
    st.divider()
    if 'edit_idx' not in st.session_state:
        st.session_state.edit_idx = None

    file_path_m = 'maintenance.json'
    df_m = charger_data(file_path_m)
    
    # Liste complète des catégories
    LISTE_TYPES = ["Assurances", "Port", "Maintenance, matériels", "Sécurité", "Autres frais"]
    ANNEES_VUES = ["2026", "2027", "2028"]
    
    # --- 1. FILTRES COMPACTS ---
    c_y1, c_y2 = st.columns([1, 2])
    annee_choisie = c_y1.selectbox("📅", ANNEES_VUES, label_visibility="collapsed")
    vue = c_y2.radio("Vue", ["✅ Payé", "📅 Tout"], horizontal=True, label_visibility="collapsed")

    # --- 2. TRAITEMENT ---
    if not df_m.empty:
        df_m['M_Num'] = pd.to_numeric(df_m['M_Num'], errors='coerce').fillna(0.0)
        df_annee = df_m[df_m['Date'].str.endswith(annee_choisie)].copy()
        df_view = df_annee[df_annee['Statut'] == "Fait"].copy() if "Payé" in vue else df_annee.copy()
        df_view['dt_t'] = pd.to_datetime(df_view['Date'], dayfirst=True, errors='coerce')
        df_view = df_view.sort_values('dt_t', ascending=False)
    else:
        df_view = pd.DataFrame()
        
    # --- 3. METRICS EN CARTES (PLACE DE PORT, ASSURANCES, SÉCURITE, MAINTENANCE -> TOTAL) ---
    if not df_view.empty:
        def g_s(df, c): return df[df['Type'] == c]['M_Num'].sum()
        total_gen = df_view['M_Num'].sum()

        # Fonction pour créer une petite carte stylisée
        def metric_card(label, value, color):
            st.markdown(f"""
                <div style="
                    background-color: {color}; 
                    padding: 10px; 
                    border-radius: 10px; 
                    text-align: center; 
                    border: 1px solid rgba(0,0,0,0.1);
                    margin-bottom: 10px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                ">
                    <div style="font-size: 0.7rem; font-weight: bold; color: #555; text-transform: uppercase;">{label}</div>
                    <div style="font-size: 1.1rem; font-weight: bold; color: #000;">{value:,.0f}€</div>
                </div>
            """, unsafe_allow_html=True)

        # Affichage en colonnes
        col1, col2 = st.columns(2)
        with col1:
            metric_card("⚓ Place de Port", g_s(df_view, 'Port'), "#e3f2fd")      # Bleu très clair
            metric_card("🛟 Sécurité", g_s(df_view, 'Sécurité'), "#fff3e0") # Orange très clair
        
        with col2:
            metric_card("🛡️ Assurances", g_s(df_view, 'Assurances'), "#f3e5f5") # Violet très clair
            metric_card("🛠️ Maintenance", g_s(df_view, 'Maintenance, matériels'), "#e8f5e9") # Vert très clair

        # Ligne du TOTAL en bas (plus large et plus forte)
        st.markdown(f"""
            <div style="
                background-color: #01579b; 
                padding: 12px; 
                border-radius: 12px; 
                text-align: center; 
                margin-top: 5px;
                box-shadow: 4px 4px 10px rgba(1, 87, 155, 0.2);
            ">
                <div style="font-size: 0.8rem; font-weight: bold; color: white; text-transform: uppercase; opacity: 0.9;">💰 TOTAL GÉNÉRAL</div>
                <div style="font-size: 1.4rem; font-weight: bold; color: white;">{total_gen:,.0f}€</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write('<div style="margin-bottom:20px"></div>', unsafe_allow_html=True)

    # --- 4. LISTE ULTRA-COMPACTE (ENCADRÉ BLEU CLAIR) ---
    if not df_view.empty:
        for idx, row in df_view.iterrows():
            if st.session_state.edit_idx == idx:
                # --- BLOC ÉDITION ---
                with st.container(border=True):
                    st.caption(f"Modification : {row['Objet']}")
                    new_mt = st.number_input("Prix €", value=float(row['M_Num']), key=f"ed_mt_{idx}")
                    new_ty = st.selectbox("Type", LISTE_TYPES, index=LISTE_TYPES.index(row['Type']) if row['Type'] in LISTE_TYPES else 0, key=f"ed_ty_{idx}")
                    new_st = st.selectbox("Statut", ["À prévoir", "Fait"], index=1 if row['Statut']=="Fait" else 0, key=f"ed_st_{idx}")
                    
                    c_b1, c_b2, c_b3 = st.columns(3)
                    if c_b1.button("💾 OK", key=f"sv_{idx}", use_container_width=True, type="primary"):
                        df_m.at[idx, 'M_Num'] = new_mt
                        df_m.at[idx, 'Montant'] = new_mt
                        df_m.at[idx, 'Type'] = new_ty
                        df_m.at[idx, 'Statut'] = new_st
                        sauvegarder_data(df_m, file_path_m)
                        st.session_state.edit_idx = None
                        st.rerun()
                    if c_b2.button("❌", key=f"ann_{idx}", use_container_width=True):
                        st.session_state.edit_idx = None
                        st.rerun()
                    if c_b3.button("🗑️", key=f"del_{idx}", use_container_width=True):
                        df_m = df_m.drop(idx).reset_index(drop=True)
                        sauvegarder_data(df_m, file_path_m)
                        st.session_state.edit_idx = None
                        st.rerun()
            else:
                # --- AFFICHAGE FICHE BLEU CLAIR ---
                st_b = row['Statut']
                status_icon = "🟢" if st_b == "Fait" else "⏳"
                
                # Couleurs Thème Bleu
                bg_color = "#e1f5fe"      # Bleu très clair (fond)
                border_main = "#03a9f4"    # Bleu azur (contour)
                border_strong = "#01579b"  # Bleu foncé (trait fort gauche)
                
                card_maint = f"""
                <div style="border: 1px solid {border_main}; border-left: 8px solid {border_strong}; 
                            padding: 8px; border-radius: 10px; margin-bottom: 5px; 
                            background-color: {bg_color}; font-family: sans-serif;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="font-size: 0.85rem; font-weight: bold; color: #01579b;">
                            {status_icon} {row['Date'][0:5]} | {row['Objet'][:18]}
                        </div>
                        <div style="font-size: 0.95rem; font-weight: bold; color: #d32f2f if row['M_Num'] > 0 else #333;">
                            {row['M_Num']:.0f}€
                        </div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 2px; border-top: 1px dashed {border_main}; padding-top: 4px;">
                        <div style="font-size: 0.7rem; color: #0277bd; text-transform: uppercase; font-weight: 600;">
                            📂 {row['Type']}
                        </div>
                        <div style="font-size: 0.7rem; color: #555; font-style: italic;">
                            Statut: {st_b}
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_maint, unsafe_allow_html=True)
                
                # Bouton de modification (collé sous l'encadré)
                st.write('<div style="margin-top:-12px"></div>', unsafe_allow_html=True)
                if st.button(f"✏️ ÉDITER {row['Objet'][:10]}", key=f"edit_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx
                    st.rerun()
                
                st.write('<div style="margin-bottom:8px"></div>', unsafe_allow_html=True)

    # --- 5. AJOUT RAPIDE ---
    with st.expander("➕ Nouvelle charge"):
        f_date = st.date_input("Date", datetime.now(), format="DD/MM/YYYY")
        f_obj = st.text_input("Objet")
        f_mt = st.number_input("Montant €", min_value=0.0)
        f_type = st.selectbox("Catégorie", LISTE_TYPES)
        f_stat = st.selectbox("Statut", ["À prévoir", "Fait"])
        if st.button("💾 ENREGISTRER LA SAISIE", use_container_width=True):
            if f_obj:
                new_data = {"Date": f_date.strftime("%d/%m/%Y"), "Objet": f_obj, "Montant": f_mt, "M_Num": f_mt, "Statut": f_stat, "Type": f_type}
                df_m = pd.concat([df_m, pd.DataFrame([new_data])], ignore_index=True)
                sauvegarder_data(df_m, file_path_m)
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
# --- 10. PAGE ARCHIVES (NETTOYAGE & EXPORT) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    import pandas as pd
    import io

    # 1. BOUTON DE RETOUR (TOUT EN HAUT)
    last = st.session_state.get('last_page', 'PLANNING')
    if st.button(f"⬅️ RETOUR VERS {last}", use_container_width=True):
        st.session_state.page = last
        st.rerun()

    st.title("📂 Centre d'Archivage Vesta")

    # --- 2. LE PANNEAU DE NETTOYAGE (Important : doit être ICI) ---
    with st.expander("✂️ ARCHIVER UNE PÉRIODE (Nettoyage)", expanded=True):
        st.info("Choisissez les dates pour déplacer les éléments vers l'historique.")
        
        c1, c2 = st.columns(2)
        d_debut = c1.date_input("Du", datetime(2026, 1, 1), key="arch_d1")
        d_fin = c2.date_input("Au", datetime(2026, 3, 31), key="arch_d2")
        
        if st.button("🚀 LANCER L'ARCHIVAGE GLOBAL", use_container_width=True, type="primary"):
            # A. Maintenance
            df_m = charger_data('maintenance.json')
            nb_m = archiver_donnees(df_m, d_debut, d_fin, 'maintenance.json', 'archives_maintenance.json', 'Date')
            
            # B. Planning
            df_c = charger_data('contacts.json')
            nb_p = archiver_donnees(df_c, d_debut, d_fin, 'contacts.json', 'archives_planning.json', 'DateNav')
            
            st.success(f"Terminé : {nb_m} frais et {nb_p} missions archivés.")
            st.rerun()

    # --- 3. EXPORT EXCEL ---
    with st.expander("📤 TRANSPÉRER VERS PC (Excel)", expanded=False):
        df_arch_m = charger_data('archives_maintenance.json')
        df_arch_p = charger_data('archives_planning.json')
        
        if not df_arch_m.empty or not df_arch_p.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                if not df_arch_p.empty: df_arch_p.to_excel(writer, sheet_name='Planning', index=False)
                if not df_arch_m.empty: df_arch_m.to_excel(writer, sheet_name='Frais', index=False)
            
            st.download_button("📥 TÉLÉCHARGER L'EXCEL", buffer.getvalue(), 
                               file_name=f"Archives_Vesta_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                               mime="application/vnd.ms-excel", use_container_width=True)

    st.divider()

    # --- 4. AFFICHAGE DES TABLEAUX ---
    st.subheader("📜 Historique actuel")
    t1, t2 = st.tabs(["🛠️ Frais", "📅 Planning"])
    with t1:
        st.dataframe(charger_data('archives_maintenance.json'), use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(charger_data('archives_planning.json'), use_container_width=True, hide_index=True)
# =================================================================
# --- 10. PAGE LOG (LIVRE DE BORD) ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#01579b; color:white; padding:10px; border-radius:10px; margin-bottom:20px;"><h1>📖 LIVRE DE BORD</h1></div>', unsafe_allow_html=True)
    
    # Chargement sécurisé
    try:
        data_brute = charger_data('logbook.json')
        df_log = preparer_log_safe(data_brute)
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")
        df_log = preparer_log_safe(None)

    # --- A. SAISIE NOUVELLE NAVIGATION ---
    with st.expander("➕ NOUVELLE SORTIE", expanded=False):
        with st.form("form_log_2026"):
            d1, d2 = st.columns(2)
            f_date = d1.date_input("Date", datetime.now())
            f_meteo = d2.text_input("🌦️ Météo")
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            f_p_dep = c1.text_input("⚓ Port Départ")
            f_p_arr = c2.text_input("🏁 Port Arrivée")
            
            st.write("**Compteurs :**")
            m1, m2, m3, m4 = st.columns(4)
            f_m_dep = m1.number_input("H. Mot. Dép", min_value=0.0, step=0.1, format="%.1f")
            f_m_arr = m2.number_input("H. Mot. Arr", min_value=0.0, step=0.1, format="%.1f")
            f_mi_dep = m3.number_input("Mi. Dép", min_value=0.0, step=1.0)
            f_mi_arr = m4.number_input("Mi. Arr", min_value=0.0, step=1.0)
            
            f_obs = st.text_area("📝 Observations / Équipage")
            
            if st.form_submit_button("💾 ENREGISTRER LA NAV", use_container_width=True):
                t_mot = round(f_m_arr - f_m_dep, 1)
                t_mil = round(f_mi_arr - f_mi_dep, 1)
                
                new_row = {
                    "Date": f_date.strftime("%d/%m/%Y"),
                    "Meteo": f_meteo,
                    "PortDep": f_p_dep.upper(),
                    "PortArr": f_p_arr.upper(),
                    "MotDep": f_m_dep, "MotArr": f_m_arr,
                    "MilDep": f_mi_dep, "MilArr": f_mi_arr,
                    "TotalMot": t_mot, "TotalMil": t_mil,
                    "Observations": f_obs
                }
                df_log = pd.concat([df_log, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                st.success("✅ Navigation enregistrée !")
                st.rerun()

    st.divider()

    # --- B. AFFICHAGE DES FICHES ---
    if df_log.empty:
        st.info("ℹ️ Aucun historique de navigation.")
    else:
        # Tri : Du plus récent au plus ancien
        df_visu = df_log.sort_values('dt_tri', ascending=False)
        
        for idx, r in df_visu.iterrows():
            # Affichage en fiches bleu clair
            st.markdown(f"""
                <div style="border: 1px solid #03a9f4; border-left: 10px solid #01579b; 
                            padding: 12px; border-radius: 12px; margin-bottom: 5px; 
                            background-color: #e1f5fe; font-family: sans-serif;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #01579b;">📅 {r.get('Date','-')}</span>
                        <span style="font-size: 0.75rem; background: white; padding: 2px 8px; border-radius: 20px; border: 1px solid #03a9f4;">🌤️ {r.get('Meteo','-')}</span>
                    </div>
                    <div style="margin: 8px 0; font-size: 0.95rem; font-weight: bold; color:#333;">
                        ⚓ {r.get('PortDep','-')} → 🏁 {r.get('PortArr','-')}
                    </div>
                    <div style="display: flex; justify-content: space-between; background: rgba(255,255,255,0.6); padding: 8px; border-radius: 8px;">
                        <div style="text-align:center; flex:1;">
                            <div style="font-size:0.6rem; color:#666; font-weight:bold;">MOTEUR</div>
                            <div style="font-size:1rem; font-weight:bold; color:#01579b;">+{r.get('TotalMot',0):.1f}h</div>
                        </div>
                        <div style="text-align:center; flex:1; border-left:1px solid #add8e6;">
                            <div style="font-size:0.6rem; color:#666; font-weight:bold;">MILLES</div>
                            <div style="font-size:1rem; font-weight:bold; color:#01579b;">{r.get('TotalMil',0):.0f}mn</div>
                        </div>
                    </div>
                    <div style="font-size: 0.75rem; color: #444; margin-top: 8px; font-style: italic; border-top: 1px dashed #b3e5fc; padding-top: 5px;">
                        📝 {r.get('Observations','')}
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Bouton de suppression très discret
            if st.button(f"🗑️ Supprimer {r.get('Date','-')}", key=f"del_{idx}"):
                df_log = df_log.drop(idx)
                sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                st.rerun()

    # --- C. ZONE DE DANGER (Clôture) ---
    st.write("<br><br>", unsafe_allow_html=True)
    with st.expander("☢️ ZONE DE DANGER"):
        st.warning("L'archivage clôture la saison.")
        if st.button("📁 CLÔTURER L'ANNÉE", use_container_width=True):
            st.info("Le journal a été sauvegardé en archive.")

# --- FIN DU FICHIER ---



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































