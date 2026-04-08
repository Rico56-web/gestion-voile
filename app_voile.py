
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import json
import html
import streamlit.components.v1 as components
from datetime import datetime, date
import plotly.express as px

def preparer_log_safe(df):
    cols = ["Date", "Meteo", "PortDep", "PortArr", "MotDep", "MotArr", "MilDep", "MilArr", 
            "TotalMot", "TotalMil", "Observations", "Vent", "Mouillage", "Equipage", 
            "Plein", "Litre Gazoil", "Cout Gazoil"]
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=cols)
    # Nettoyage des numériques
    for c in ["TotalMot", "TotalMil", "MotDep", "MotArr", "MilDep", "MilArr", "Litre Gazoil", "Cout Gazoil"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
    if 'Date' in df.columns:
        df['dt_tri'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    return df

# ... vos autres fonctions (charger_data, sauvegarder_data) ...
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        # L'ajout de params={"v": time.time()} force la mise à jour
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except:
        return pd.DataFrame()
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

# --- INITIALISATION DES VARIABLES DE SESSION (Haut du script) ---
# Pour le Planning / Contacts
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None

# Pour le LOGBOOK (Livre de bord)
if 'log_edit_idx' not in st.session_state: st.session_state.log_edit_idx = None
if 'log_confirm_del' not in st.session_state: st.session_state.log_confirm_del = None

# Pour la Maintenance
if 'm_edit_idx' not in st.session_state: st.session_state.m_edit_idx = None
if 'maint_confirm_del' not in st.session_state: st.session_state.maint_confirm_del = None
 
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

st.sidebar.divider()
st.sidebar.subheader("💾 Sauvegarde de Sécurité")

# Fonction pour préparer le téléchargement
def preparer_download(file_path):
    with open(file_path, 'r') as f:
        return f.read()

if st.sidebar.expander("Exporter les données"):
    for file in ['logbook.json', 'maintenance.json', 'params_maint.json']:
        if os.path.exists(file):
            st.sidebar.download_button(
                label=f"📥 Télécharger {file}",
                data=preparer_download(file),
                file_name=file,
                mime="application/json",
                use_container_width=True
            )
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
# --- 6. PAGE PLANNING (AVEC BOUTON ARCHIVES VISIBLE) ---
# =================================================================
if st.session_state.page == "PLANNING":
    from datetime import datetime, date, timedelta
    import calendar

    # --- EN-TÊTE & NAVIGATION HAUT ---
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING 2026</h1></div>', unsafe_allow_html=True)
    
    # Bouton Archives mis en évidence
    col_arch, col_vide = st.columns([1, 1])
    with col_arch:
        if st.button("📂 ACCÉDER AUX ARCHIVES", key="k_arch_p", use_container_width=True, type="primary"):
            st.session_state.last_page = "PLANNING" # Pour le bouton retour des archives
            st.session_state.page = "ARCHIVES"
            st.rerun()

    st.divider()

    # --- LOGIQUE CALENDRIER ---
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)

    # Initialisation session_state
    if 'curr_month_idx' not in st.session_state:
        st.session_state.curr_month_idx = aujourdhui.month - 1
    if 'curr_year' not in st.session_state:
        st.session_state.curr_year = aujourdhui.year
    if 'nav_key' not in st.session_state:
        st.session_state.nav_key = 0

    # Sélecteurs de date
    col_m, col_y, col_now = st.columns([1.5, 1, 0.8])
    with col_m:
        sel_m_nom = st.selectbox("Mois", m_noms, index=st.session_state.curr_month_idx, key=f"m_{st.session_state.nav_key}")
        sel_m = m_noms.index(sel_m_nom) + 1
        st.session_state.curr_month_idx = sel_m - 1
    with col_y:
        annees_dispo = [2026, 2027, 2028]
        idx_y = annees_dispo.index(st.session_state.curr_year) if st.session_state.curr_year in annees_dispo else 0
        sel_y = st.selectbox("Année", annees_dispo, index=idx_y, key=f"y_{st.session_state.nav_key}")
        st.session_state.curr_year = sel_y
    with col_now:
        if st.button("📍 ICI", use_container_width=True):
            st.session_state.curr_month_idx = aujourdhui.month - 1
            st.session_state.curr_year = aujourdhui.year
            st.session_state.nav_key += 1
            st.rerun()

    # --- CALCULS OCCUPATION ---
    jours_occ = {}
    total_mois = 0
    missions_list = []

    if df_c is not None and not df_c.empty:
        for idx, r in df_c.iterrows():
            try:
                d_val = r.get('DateNav', '')
                if pd.isna(d_val) or str(d_val).strip() == "": continue
                d_str = str(d_val).strip().split(' ')[0]
                # Formatage date
                if '/' in d_str:
                    parts = d_str.split('/')
                    dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
                    if yv < 100: yv += 2000
                    date_debut = date(yv, mv, dv)
                else: continue
                
                n_j = int(float(safe_val(r.get('Nbre de jours'), 1)))
                soc_v = str(r.get('Société','')).upper()
                
                for i in range(n_j):
                    date_courante = date_debut + timedelta(days=i)
                    if date_courante.month == sel_m and date_courante.year == sel_y:
                        p_val = str(r.get('Paiement', '')).upper()
                        s_val = str(r.get('Statut', '')).lower()
                        is_paye = "PAY" in p_val and "NON" not in p_val
                        
                        # Couleur CMN Prioritaire
                        color = "transparent"
                        if "CMN" in soc_v: color = "#0047AB"
                        elif date_courante < aujourdhui: color = "#34495e" if is_paye else "#e74c3c"
                        elif "ok" in s_val: color = "#27ae60"
                        elif "attente" in s_val: color = "#f39c12"
                        
                        jours_occ[date_courante.day] = {"c": color}

                # Ajout à la liste pour affichage sous calendrier
                date_fin = date_debut + timedelta(days=n_j-1)
                if (date_debut.year == sel_y and date_debut.month == sel_m) or (date_fin.year == sel_y and date_fin.month == sel_m):
                    missions_list.append({'data': r, 'idx': idx, 'start': date_debut, 'end': date_fin, 'n_j': n_j})
                    if date_debut.month == sel_m:
                        val_prix = str(r.get('Prix', 0)).replace(',','.').replace('€','').strip()
                        total_mois += float(val_prix) if val_prix else 0
            except: continue

    # --- RENDU CALENDRIER HTML ---
    st.markdown("""<style>.full-width-cal { width: 100%; border-collapse: collapse; table-layout: fixed; } .full-width-cal td { border: 0.5px solid #eee; padding: 5px 0; }</style>""", unsafe_allow_html=True)
    
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

    # --- LISTE DES MISSIONS & TOTAL ---
    st.markdown(f"#### 📋 Détails {sel_m_nom}")
    if missions_list:
        missions_list.sort(key=lambda x: x['start'])
        for m in missions_list:
            r = m['data']
            soc = str(r.get('Société','')).upper()
            c_line = "#0047AB" if "CMN" in soc else "#27ae60"
            txt_d = f"{m['start'].day:02d}/{m['start'].month:02d}"
            if m['n_j'] > 1: txt_d += f" ➔ {m['end'].day:02d}/{m['end'].month:02d}"
            icon = "💰" if "PAY" in str(r.get('Paiement','')).upper() and "NON" not in str(r.get('Paiement','')).upper() else "⚠️"
            
            st.markdown(f"""<div style="display: flex; padding: 10px; border-bottom: 1px solid #eee; background: white; align-items: center;"><div style="background: {c_line}; color: white; border-radius: 5px; padding: 4px; min-width: 85px; text-align: center; font-weight: bold; margin-right: 10px; line-height:1.2;"><span style="font-size: 0.75rem;">{txt_d}</span><br><span style="font-size: 0.5rem;">{"JOURS" if m['n_j'] > 1 else "JOUR"}</span></div><div style="flex-grow: 1;"><b>{icon} {str(r.get('Nom','')).upper()}</b><br><small>{soc} | {r.get('Prix','0')}€</small></div></div>""", unsafe_allow_html=True)
            if st.button(f"🔍 FICHE : {str(r.get('Nom',''))}", key=f"p_btn_{m['idx']}", use_container_width=True):
                st.session_state.edit_idx = m['idx']
                st.session_state.mode_saisie = True
                st.session_state.page = "CONTACTS"
                st.rerun()

    # Bloc CA (Couleur Or/Sombre)
    st.markdown(f"""
    <div style="background:#2c3e50; color:#f1c40f; padding:15px; border-radius:10px; text-align:center; margin-top:15px; border: 2px solid #f1c40f;">
        <span style="font-size:0.8rem; color:white; text-transform:uppercase;">Estimation Chiffre d'Affaires</span><br>
        <b style="font-size:1.4rem;">TOTAL : {total_mois:,.0f} €</b>
    </div>
    """, unsafe_allow_html=True)
# =================================================================
# --- 9. PAGE STATS (VERSION FINALE OPTIMISÉE IPHONE 16) ---
# =================================================================
if st.session_state.page == "STATS":
    import plotly.express as px
    import pandas as pd
    import datetime

    # --- 1. INITIALISATION SÉCURISÉE ---
    df_recettes_view = pd.DataFrame()
    df_charges_view = pd.DataFrame()
    df_log_yr = pd.DataFrame()
    total_recettes, total_charges, total_h_moteur = 0, 0, 0
    total_milles, total_cout_gasoil, total_litres = 0, 0, 0

    # --- 2. NAVIGATION & FILTRES ---
    col_t1, col_t2 = st.columns([2, 1])
    col_t1.title("📊 Bilan Vesta")
    
    # Indicateur de fraîcheur pour vérifier le rafraîchissement sur iPhone 16
    col_t1.caption(f"🕒 Données actualisées à : {datetime.datetime.now().strftime('%H:%M:%S')}")
    
    ANNEES_STATS = [2025, 2026, 2027, 2028]
    sel_y_stats = col_t2.selectbox(
        "Saison", ANNEES_STATS, index=1, 
        label_visibility="collapsed", key="stats_year_select_final"
    )
    
    mode_previ = st.toggle(
        "🔮 Voir le Prévisionnel (Toute l'année)", 
        value=False, key="stats_previ_toggle_final"
    )
    
    if st.button("📂 ARCHIVES", use_container_width=True, key="stats_to_archives"):
        st.session_state.page = "ARCHIVES"; st.rerun()

    # --- 3. RÉCUPÉRATION DES DONNÉES ---
    df_m = charger_data('maintenance.json') 
    df_c = charger_data('contacts.json')    
    df_log = charger_data('logbook.json')   
    config_static = {'staticPlot': True, 'responsive': True}

    # --- 4. CALCULS (Navigation & Finances) ---
    if not df_log.empty:
        df_log['dt'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
        df_log_yr = df_log[df_log['dt'].dt.year == sel_y_stats].copy()
        total_h_moteur = pd.to_numeric(df_log_yr.get('TotalMot', 0), errors='coerce').sum()
        total_milles = pd.to_numeric(df_log_yr.get('TotalMil', 0), errors='coerce').sum()
        total_cout_gasoil = pd.to_numeric(df_log_yr.get('Cout Gazoil', 0), errors='coerce').sum()
        total_litres = pd.to_numeric(df_log_yr.get('Litre Gazoil', 0), errors='coerce').sum()

    if not df_m.empty:
        df_m['M_Num'] = pd.to_numeric(df_m['M_Num'], errors='coerce').fillna(0.0)
        df_m['dt'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        mask_m = (df_m['dt'].dt.year == sel_y_stats)
        df_charges_view = df_m[mask_m].copy() if mode_previ else df_m[mask_m & (df_m['Statut'] == "Fait")].copy()
        total_charges = df_charges_view['M_Num'].sum() + total_cout_gasoil

    if not df_c.empty:
        df_c['dt'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
        df_c_yr = df_c[df_c['dt'].dt.year == sel_y_stats].copy()
        df_c_yr['P_Num'] = pd.to_numeric(df_c_yr['Prix'].astype(str).str.replace('€','').str.replace(' ','').str.strip(), errors='coerce').fillna(0.0)
        def is_paye(v): return "PAY" in str(v).upper() and "NON" not in str(v).upper()
        df_recettes_view = df_c_yr if mode_previ else df_c_yr[df_c_yr['Paiement'].apply(is_paye)].copy()
        total_recettes = df_recettes_view['P_Num'].sum()

    # --- 5. TRÉSORERIE (AFFICHAGE VERTICAL POUR LÉGENDES IPHONE) ---
    st.subheader(f"💰 Finances {sel_y_stats}")
    
    # Graphique 1 : Revenus vs Frais
    st.caption("📈 Revenus vs Frais")
    fig1 = px.pie(names=['Frais', 'Revenus'], values=[total_charges, total_recettes],
                  color_discrete_map={'Frais': '#ef553b', 'Revenus': '#00cc96'}, hole=0.4)
    fig1.update_layout(
        margin=dict(t=10, b=60, l=10, r=10), height=300, showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig1, use_container_width=True, config=config_static)

    # Graphique 2 : Dépenses
    if not df_charges_view.empty and total_charges > 0:
        st.caption("🔍 Répartition des Dépenses")
        df_p = df_charges_view.groupby('Type')['M_Num'].sum().reset_index()
        if total_cout_gasoil > 0:
            df_p = pd.concat([df_p, pd.DataFrame([{'Type': 'Gasoil', 'M_Num': total_cout_gasoil}])], ignore_index=True)
        fig2 = px.pie(df_p, names='Type', values='M_Num', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
        fig2.update_layout(
            margin=dict(t=10, b=60, l=10, r=10), height=300, showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig2, use_container_width=True, config=config_static)

    # Solde en gros pavé
    solde = total_recettes - total_charges
    st.markdown(f"""
        <div style="text-align:center; border:2px solid #ddd; padding:15px; border-radius:15px; background:#fff; margin:15px 0;">
            <span style="color:#666; font-weight:bold;">SOLDE {"PRÉVISIONNEL" if mode_previ else "RÉEL"}</span><br>
            <b style="color:{'#28a745' if solde>=0 else '#dc3545'}; font-size:1.8rem;">{solde:,.0f} €</b>
        </div>
    """, unsafe_allow_html=True)

    # --- 6. ANALYSE PAR SOCIÉTÉ (GRAPHIQUES HORIZONTAUX OPTIMISÉS) ---
    st.divider()
    st.subheader("🏢 Analyse par Société")
    if not df_recettes_view.empty:
        df_soc = df_recettes_view.copy()
        df_soc['Société'] = df_soc['Société'].replace(['', 'nan', None], 'PARTICULIER').str.upper().str.strip()
        df_soc['Société'] = df_soc['Société'].replace({'CLICK': 'CLICK & BOAT', 'CLICK AND BOAT': 'CLICK & BOAT', 'CLICK&BOAT': 'CLICK & BOAT'})
        df_soc['Jours_Num'] = pd.to_numeric(df_soc['Nbre de jours'], errors='coerce').fillna(0.0)
        
        stats_soc = df_soc.groupby('Société').agg({'P_Num': 'sum', 'Jours_Num': 'sum'}).reset_index()
        stats_soc['Moy_Jour'] = stats_soc.apply(lambda x: round(x['P_Num']/x['Jours_Num'],0) if x['Jours_Num']>0 else 0, axis=1)
        stats_soc = stats_soc.sort_values(by='P_Num', ascending=False)

        st.caption("⛵ Jours de Navigation")
        f_vol = px.bar(stats_soc, y='Société', x='Jours_Num', orientation='h', text_auto=True, 
                       color='Société', color_discrete_sequence=px.colors.qualitative.Pastel)
        f_vol.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=180, showlegend=False, xaxis_visible=False, yaxis_title=None)
        st.plotly_chart(f_vol, use_container_width=True, config=config_static)

        st.caption("💰 Revenu / Jour (€)")
        f_yield = px.bar(stats_soc, y='Société', x='Moy_Jour', orientation='h', text_auto='.0f', 
                         color='Société', color_discrete_sequence=px.colors.qualitative.Safe)
        f_yield.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=180, showlegend=False, xaxis_visible=False, yaxis_title=None)
        st.plotly_chart(f_yield, use_container_width=True, config=config_static)
        
        st.table(stats_soc[['Société','P_Num','Jours_Num','Moy_Jour']].rename(columns={'P_Num':'CA €','Jours_Num':'Jours'}))
    else:
        st.info("Aucune donnée disponible.")

    # --- 7. NAVIGATION & SYNTHÈSE MENSUELLE ---
    st.divider()
    st.subheader("⚓ Détails Navigation")
    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Moteur", f"{total_h_moteur:.1f}h")
    n2.metric("Milles", f"{total_milles:.0f}mn")
    n3.metric("Gasoil", f"{total_cout_gasoil:.0f}€")
    conso = round(total_litres / total_h_moteur, 1) if total_h_moteur > 0 else 0
    n4.metric("Conso", f"{conso}L/h")

    mois_noms = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jui", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    syn = []
    for i in range(1, 13):
        r = df_recettes_view[df_recettes_view['dt'].dt.month == i]['P_Num'].sum() if not df_recettes_view.empty else 0
        c = df_charges_view[df_charges_view['dt'].dt.month == i]['M_Num'].sum() if not df_charges_view.empty else 0
        if r > 0 or c > 0:
            syn.append({"Mois": mois_noms[i-1], "CA": f"{r:.0f}€", "Frais": f"{c:.0f}€", "Net": f"{r-c:.0f}€"})
    
    if syn:
        st.table(pd.DataFrame(syn))
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

    st.markdown(f"""
        <div style="background-color: {bg_v}; border: 2px solid {color_v}; padding: 12px; border-radius: 12px; text-align: center; margin-top: 10px;">
            <div style="color: {color_v}; font-weight: bold; font-size: 0.75rem; text-transform: uppercase;">🛢️ État du Cycle</div>
            <div style="font-size: 1.6rem; font-weight: 900; color: {color_v}; margin: 5px 0;">
                {heures_restantes:.1f} h <span style="font-size:0.8rem; font-weight:normal;">restantes</span>
            </div>
            <div style="font-size: 0.75rem; color: #555;">Compteur actuel : <b>{releve_h:.1f} h</b></div>
        </div>
    """, unsafe_allow_html=True)
    st.progress(percent_prog)

    if st.button("🔧 ENREGISTRER LA VIDANGE COMME FAITE", use_container_width=True, type="primary"):
        # Ajout automatique dans maintenance.json
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
        # On projette la prochaine à +100h
        params['cible_vidange'] = releve_h + 100.0
        sauver_params(params)
        st.success("Vidange archivée ! Prochaine cible mise à jour.")
        st.rerun()

    st.divider()

    # --- E. FILTRES & RÉCAPITULATIF FINANCIER ---
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
    
    LISTE_TYPES = ["Assurances", "Port", "Maintenance, matériels", "Sécurité", "Autres frais"]
    ANNEES_VUES = ["2026", "2027", "2028"]
    
    c_y1, c_y2 = st.columns([1, 2])
    annee_choisie = c_y1.selectbox("📅", ANNEES_VUES, index=0, label_visibility="collapsed", key="maint_yr")
    vue = c_y2.radio("Vue", ["✅ Payé", "📅 Tout"], horizontal=True, label_visibility="collapsed", key="maint_vue")

    if not df_m.empty:
        df_m['M_Num'] = pd.to_numeric(df_m['M_Num'], errors='coerce').fillna(0.0)
        df_annee = df_m[df_m['Date'].str.contains(annee_choisie, na=False)].copy()
        df_view = df_annee[df_annee['Statut'] == "Fait"].copy() if "Payé" in vue else df_annee.copy()
        df_view['dt_t'] = pd.to_datetime(df_view['Date'], dayfirst=True, errors='coerce')
        df_view = df_view.sort_values('dt_t', ascending=False)
    else:
        df_view = pd.DataFrame()
        
    if not df_view.empty:
        total_gen = df_view['M_Num'].sum()
        def metric_card(label, value, color):
            st.markdown(f'<div style="background-color: {color}; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px;"><div style="font-size: 0.65rem; font-weight: bold; color: #555;">{label}</div><div style="font-size: 1rem; font-weight: bold;">{value:,.0f}€</div></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            metric_card("⚓ Port", df_view[df_view['Type'] == 'Port']['M_Num'].sum(), "#e3f2fd")
            metric_card("🛟 Sécurité", df_view[df_view['Type'] == 'Sécurité']['M_Num'].sum(), "#fff3e0")
        with col2:
            metric_card("🛡️ Assurances", df_view[df_view['Type'] == 'Assurances']['M_Num'].sum(), "#f3e5f5")
            metric_card("🛠️ Maintenance", df_view[df_view['Type'] == 'Maintenance, matériels']['M_Num'].sum(), "#e8f5e9")

        st.markdown(f'<div style="background-color: #01579b; padding: 12px; border-radius: 12px; text-align: center; color: white;"><b>TOTAL {annee_choisie} : {total_gen:,.0f}€</b></div>', unsafe_allow_html=True)

    # --- F. LISTE & ÉDITION ---
    for idx, row in df_view.iterrows():
        if st.session_state.edit_idx == idx:
            with st.container(border=True):
                new_mt = st.number_input("Prix €", value=float(row['M_Num']), key=f"m_mt_{idx}")
                new_st = st.selectbox("Statut", ["À prévoir", "Fait"], index=1 if row['Statut']=="Fait" else 0, key=f"m_st_{idx}")
                if st.button("💾", key=f"s_{idx}"):
                    df_m.at[idx, 'M_Num'] = new_mt; df_m.at[idx, 'Statut'] = new_st
                    sauvegarder_data(df_m, 'maintenance.json'); st.session_state.edit_idx = None; st.rerun()
        else:
            status_icon = "🟢" if row['Statut'] == "Fait" else "⏳"
            st.markdown(f'<div style="border-left: 8px solid #01579b; padding: 10px; border-radius: 10px; background-color: #e1f5fe; margin-bottom: 5px;"><b>{status_icon} {row["Date"][:5]}</b> | {row["Objet"][:25]} | <b>{row["M_Num"]:.0f}€</b></div>', unsafe_allow_html=True)
            if st.button(f"✏️ Modifier {idx}", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.rerun()

    # --- G. AJOUT & MODE HORS-LIGNE (SYNC) ---
    with st.expander("➕ AJOUTER / 📥 SYNCHRO HORS-LIGNE"):
        tab1, tab2 = st.tabs(["Dépense", "Sauvegarde iPhone"])
        with tab1:
            f_obj = st.text_input("Objet")
            f_mt = st.number_input("Montant €", min_value=0.0)
            if st.button("Enregistrer"):
                new_r = {"Date": datetime.now().strftime("%d/%m/%Y"), "Objet": f_obj, "M_Num": f_mt, "Statut": "À prévoir", "Type": "Autres frais"}
                df_m = pd.concat([df_m, pd.DataFrame([new_r])], ignore_index=True)
                sauvegarder_data(df_m, 'maintenance.json'); st.rerun()
        with tab2:
            st.write("Téléchargez vos données avant de partir en mer :")
            for f in ['logbook.json', 'maintenance.json', 'params_maint.json']:
                data = preparer_download(f)
                if data: st.download_button(f"📥 {f}", data, file_name=f, use_container_width=True)
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
# --- 11. PAGE ARCHIVES (NETTOYAGE, EXPORT & LOG) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    import pandas as pd
    import io

    # 1. BOUTON DE RETOUR (Dynamique selon la provenance)
    last = st.session_state.get('last_page', 'PLANNING')
    if st.button(f"⬅️ RETOUR VERS {last}", use_container_width=True):
        st.session_state.page = last
        st.rerun()

    st.title("📂 Centre d'Archivage Vesta")

    # --- 2. LE PANNEAU DE NETTOYAGE (Incluant le LOG) ---
    with st.expander("✂️ ARCHIVER UNE PÉRIODE (Nettoyage)", expanded=True):
        st.info("Sélectionnez une période pour basculer les données actives vers l'historique.")
        
        c1, c2 = st.columns(2)
        d_debut = c1.date_input("Du", datetime(2026, 1, 1), key="arch_d1")
        d_fin = c2.date_input("Au", datetime(2026, 12, 31), key="arch_d2")
        
        if st.button("🚀 LANCER L'ARCHIVAGE GLOBAL", use_container_width=True, type="primary"):
            # A. Maintenance
            df_m = charger_data('maintenance.json')
            nb_m = archiver_donnees(df_m, d_debut, d_fin, 'maintenance.json', 'archives_maintenance.json', 'Date')
            
            # B. Planning / Contacts
            df_c = charger_data('contacts.json')
            nb_p = archiver_donnees(df_c, d_debut, d_fin, 'contacts.json', 'archives_planning.json', 'DateNav')
            
            # C. Livre de Bord (Nouveau)
            df_l = charger_data('logbook.json')
            nb_l = archiver_donnees(df_l, d_debut, d_fin, 'logbook.json', 'archives_logbook.json', 'Date')
            
            st.success(f"Archivage réussi : {nb_m} frais, {nb_p} missions et {nb_l} navigations déplacés.")
            st.rerun()

    # --- 3. EXPORT EXCEL COMPLET ---
    with st.expander("📤 TRANSFÉRER VERS PC (Excel)", expanded=False):
        df_arch_m = charger_data('archives_maintenance.json')
        df_arch_p = charger_data('archives_planning.json')
        df_arch_l = charger_data('archives_logbook.json')
        
        if not df_arch_m.empty or not df_arch_p.empty or not df_arch_l.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                if not df_arch_p.empty: 
                    df_arch_p.to_excel(writer, sheet_name='Planning', index=False)
                if not df_arch_m.empty: 
                    df_arch_m.to_excel(writer, sheet_name='Frais', index=False)
                if not df_arch_l.empty: 
                    df_arch_l.to_excel(writer, sheet_name='Livre de Bord', index=False)
            
            st.download_button("📥 TÉLÉCHARGER L'EXCEL GLOBAL", buffer.getvalue(), 
                               file_name=f"Archives_Vesta_Total_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                               mime="application/vnd.ms-excel", use_container_width=True)

    st.divider()

    # --- 4. AFFICHAGE DES TABLEAUX ---
    st.subheader("📜 Historique actuel")
    t1, t2, t3 = st.tabs(["🛠️ Frais", "📅 Planning", "📖 Livre de Bord"])
    
    with t1:
        st.dataframe(charger_data('archives_maintenance.json'), use_container_width=True, hide_index=True)
    
    with t2:
        # Ici apparaissent les statuts Paid/Unpaid pour ton suivi
        st.dataframe(charger_data('archives_planning.json'), use_container_width=True, hide_index=True)
        
    with t3:
        # Affichage des navigations passées
        df_log_arch = charger_data('archives_logbook.json')
        if not df_log_arch.empty:
            st.dataframe(df_log_arch, use_container_width=True, hide_index=True)
        else:
            st.write("Aucune navigation dans l'historique.")
# =================================================================
# --- 10. PAGE LOG (LIVRE DE BORD) ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#01579b; color:white; padding:10px; border-radius:10px; margin-bottom:20px;"><h1>📖 LIVRE DE BORD</h1></div>', unsafe_allow_html=True)
    
    # --- BOUTON ARCHIVES (Même style que sur les autres pages) ---
    if st.button("📂 ACCÉDER AUX ARCHIVES", use_container_width=True):
        st.session_state.page = "ARCHIVES"
        st.rerun()
    
    # 1. Chargement et préparation sécurisée des données
    df_log = preparer_log_safe(charger_data('logbook.json'))
    
    # 2. Vérification de sécurité pour l'index d'édition
    is_editing = False
    if st.session_state.log_edit_idx is not None:
        if st.session_state.log_edit_idx in df_log.index:
            is_editing = True
        else:
            st.session_state.log_edit_idx = None

    titre_expander = "📝 MODIFIER LA NAVIGATION" if is_editing else "➕ NOUVELLE SORTIE"
    
    with st.expander(titre_expander, expanded=is_editing):
        # Récupération de la ligne en cours ou ligne vide
        row = df_log.loc[st.session_state.log_edit_idx] if is_editing else {}
        
        # --- DÉBUT DU FORMULAIRE ---
        with st.form("form_log_vesta", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 1, 1])
            
            # Date avec sécurité conversion
            try:
                d_val = datetime.strptime(row['Date'], "%d/%m/%Y") if is_editing else datetime.now()
            except: d_val = datetime.now()
            
            f_date = c1.date_input("Date", d_val)
            f_p_dep = c2.text_input("⚓ Départ", value=row.get('PortDep', ""))
            f_p_arr = c3.text_input("🏁 Arrivée", value=row.get('PortArr', ""))
            
            st.markdown("##### 🌊 Conditions & Escales")
            n1, n2, n3 = st.columns([1, 1, 1])
            
            list_mouillage = ["Port", "Ancre", "Bouée"]
            idx_m = list_mouillage.index(row['Mouillage']) if is_editing and row.get('Mouillage') in list_mouillage else 0
            f_mouillage = n1.selectbox("Type d'escale", list_mouillage, index=idx_m)
            
            # SÉCURITÉ SLIDER VENT (Évite ValueError)
            try:
                v_init = int(float(row.get('Vent', 2))) if is_editing and row.get('Vent') else 2
            except: v_init = 2
            f_vent = n2.select_slider("Vent (Beaufort)", options=list(range(11)), value=v_init)
            
            f_meteo = n3.text_input("🌤️ Météo", value=row.get('Meteo', ""))
            
            st.markdown("##### ⚙️ Compteurs")
            m1, m2, m3, m4 = st.columns(4)
            # Conversion forcée en float pour éviter les erreurs de calcul
            f_m_dep = m1.number_input("H. Mot. Dép", value=float(pd.to_numeric(row.get('MotDep', 0.0), errors='coerce')), step=0.1, format="%.1f")
            f_m_arr = m2.number_input("H. Mot. Arr", value=float(pd.to_numeric(row.get('MotArr', 0.0), errors='coerce')), step=0.1, format="%.1f")
            f_mi_dep = m3.number_input("Mi. Dép", value=float(pd.to_numeric(row.get('MilDep', 0.0), errors='coerce')), step=1.0)
            f_mi_arr = m4.number_input("Mi. Arr", value=float(pd.to_numeric(row.get('MilArr', 0.0), errors='coerce')), step=1.0)
            
            st.markdown("##### 👥 Équipage (Max 6)")
            e_cols = st.columns(3)
            e_vals = str(row.get('Equipage', "")).split(', ') if is_editing else [""]*6
            while len(e_vals) < 6: e_vals.append("")
            
            e1 = e_cols[0].text_input("P1", value=e_vals[0], placeholder="Skipper", label_visibility="collapsed")
            e2 = e_cols[1].text_input("P2", value=e_vals[1], placeholder="Équipier", label_visibility="collapsed")
            e3 = e_cols[2].text_input("P3", value=e_vals[2], placeholder="Équipier", label_visibility="collapsed")
            e4 = e_cols[0].text_input("P4", value=e_vals[3], placeholder="Équipier", label_visibility="collapsed")
            e5 = e_cols[1].text_input("P5", value=e_vals[4], placeholder="Équipier", label_visibility="collapsed")
            e6 = e_cols[2].text_input("P6", value=e_vals[5], placeholder="Équipier", label_visibility="collapsed")
            
            st.markdown("##### ⛽ Carburant")
            f_plein = st.checkbox("Plein effectué ?", value=(row.get('Plein') == "Oui"))
            g1, g2 = st.columns(2)
            f_litres = g1.number_input("Volume (L)", value=float(pd.to_numeric(row.get('Litre Gazoil', 0.0), errors='coerce')))
            f_cout = g2.number_input("Coût (€)", value=float(pd.to_numeric(row.get('Cout Gazoil', 0.0), errors='coerce')))
            
            f_obs = st.text_area("📝 Observations", value=row.get('Observations', ""))

            # BOUTONS DE SOUMISSION
            col_sub1, col_sub2 = st.columns(2)
            btn_save = col_sub1.form_submit_button("💾 ENREGISTRER", use_container_width=True)
            btn_cancel = col_sub2.form_submit_button("❌ ANNULER", use_container_width=True)

            if btn_cancel:
                st.session_state.log_edit_idx = None
                st.rerun()

            if btn_save:
                equipe_final = ", ".join(filter(None, [e1, e2, e3, e4, e5, e6]))
                new_entry = {
                    "Date": f_date.strftime("%d/%m/%Y"), 
                    "Meteo": f_meteo, 
                    "Vent": f_vent,
                    "PortDep": f_p_dep.upper(), 
                    "PortArr": f_p_arr.upper(), 
                    "Mouillage": f_mouillage,
                    "MotDep": f_m_dep, 
                    "MotArr": f_m_arr, 
                    "TotalMot": round(f_m_arr - f_m_dep, 1),
                    "MilDep": f_mi_dep, 
                    "MilArr": f_mi_arr, 
                    "TotalMil": round(f_mi_arr - f_mi_dep, 1),
                    "Equipage": equipe_final, 
                    "Plein": "Oui" if f_plein else "Non",
                    "Litre Gazoil": f_litres, 
                    "Cout Gazoil": f_cout, 
                    "Observations": f_obs
                }
                
                if is_editing:
                    for k, v in new_entry.items():
                        df_log.at[st.session_state.log_edit_idx, k] = v
                    st.session_state.log_edit_idx = None
                else:
                    df_log = pd.concat([df_log, pd.DataFrame([new_entry])], ignore_index=True)
                
                # Sauvegarde propre
                sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                st.success("C'est enregistré ! Bon vent !")
                st.rerun()

    # --- 3. AFFICHAGE DES FICHES ---
    st.divider()
    if not df_log.empty:
        # Tri temporaire pour l'affichage (plus récent en haut)
        df_log['dt_tri'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
        df_visu = df_log.sort_values('dt_tri', ascending=False)
        
        for idx, r in df_visu.iterrows():
            # Carte visuelle
            st.markdown(f"""
            <div style="border: 1px solid #ddd; padding: 12px; border-radius: 10px; background: #f1f8ff; margin-bottom: 5px; border-left: 8px solid #01579b;">
                <div style="display:flex; justify-content:space-between;">
                    <b style="color:#01579b;">📅 {r['Date']}</b> 
                    <span style="font-size:0.8rem; background:white; padding:2px 8px; border-radius:10px;">💨 F{r.get('Vent',0)} | {r.get('Mouillage','Port')}</span>
                </div>
                <div style="font-weight:bold; margin:5px 0;">⚓ {r['PortDep']} ➔ {r['PortArr']}</div>
                <div style="font-size:0.85rem; color:#444;">👥 {r.get('Equipage','-')}</div>
                <div style="margin-top:5px; font-size:0.85rem; border-top:1px solid #eee; padding-top:5px;">
                    ⚙️ <b>{r['TotalMot']}h</b> moteur | 📏 <b>{r['TotalMil']}mn</b> parcourus
                    {f" | ⛽ {r['Litre Gazoil']}L" if r.get('Plein')=="Oui" else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Boutons Actions
            c_a, c_b, c_c = st.columns([1, 1, 4])
            if c_a.button("✏️", key=f"edit_btn_{idx}"):
                st.session_state.log_edit_idx = idx
                st.rerun()
            
            if st.session_state.log_confirm_del == idx:
                if c_b.button("✅ OUI", key=f"conf_del_{idx}", type="primary"):
                    df_log = df_log.drop(idx)
                    sauvegarder_data(df_log.drop(columns=['dt_tri'], errors='ignore'), 'logbook.json')
                    st.session_state.log_confirm_del = None
                    st.rerun()
                if c_c.button("❌ NON", key=f"cancel_del_{idx}"):
                    st.session_state.log_confirm_del = None
                    st.rerun()
            else:
                if c_b.button("🗑️", key=f"ask_del_{idx}"):
                    st.session_state.log_confirm_del = idx
                    st.rerun()
# --- FIN DU FICHIER ---


































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































