import requests, base64, json, time, os, html, io, shutil
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
from datetime import datetime, date, timedelta
import calendar
import streamlit.components.v1 as components

# =================================================================
# --- CONFIGURATION & STYLE REGROUPÉS ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- INITIALISATION DU SESSION STATE ---
if 'log_edit_idx' not in st.session_state: st.session_state.log_edit_idx = None
if 'edit_mode' not in st.session_state: st.session_state.edit_mode = False
if 'page' not in st.session_state: st.session_state.page = "PLANNING"
if 'vue_contact' not in st.session_state: st.session_state.vue_contact = "En cours"
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'memo_edit_id' not in st.session_state: st.session_state.memo_edit_id = None

# =================================================================
# --- FONCTIONS UTILITAIRES GLOBALES & IMPRESSION ---
# =================================================================
def bouton_imprimer_fiche(date_fiche, contenu, statut):
    html_content = f"""
    <html>
    <head><title>Impression Note - Vesta Skipper</title></head>
    <body style='font-family: sans-serif;'>
        <h1>Note du {date_fiche}</h1>
        <p><b>Statut :</b> {statut}</p>
        <hr>
        <pre style='font-size: 1.2rem;'>{contenu}</pre>
    </body>
    </html>
    """
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

def to_f(val):
    """Nettoie et convertit une chaîne financière/numérique en float propre"""
    if pd.isna(val) or val == "": return 0.0
    try: return float(str(val).replace('€','').replace(' ','').replace(',','.').strip())
    except: return 0.0

def bouton_export_excel(df, nom_fichier):
    if df.empty: return st.warning(f"Aucune donnée à exporter pour {nom_fichier}")
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

def charger_data_safe(fichier):
    df = charger_data(fichier)
    return df if not df.empty else pd.DataFrame()

def charger_params():
    if 'params_vesta' in st.session_state:
        return st.session_state.params_vesta
    df = charger_data('params.json')
    if not df.empty:
        st.session_state.params_vesta = df.iloc[0].to_dict()
    else:
        st.session_state.params_vesta = {
            "prochaine_vidange": 2450.0, 
            "cible_vidange": 250.0,
            "frais_fixes": {"Port Arzon": 3800, "Assurance": 1200, "Entretien": 1500, "Divers": 500}
        }
    return st.session_state.params_vesta
    
def sauvegarder_params(dict_params):
    st.session_state.params_vesta = dict_params
    df_params = pd.DataFrame([dict_params])
    generer_data = sauvegarder_data(df_params, 'params.json')

def executer_backup_auto():
    fichiers_a_sauver = ['contacts.json', 'maintenance.json', 'logbook.json', 'params.json', 'memos.json']
    if not os.path.exists('backups'): os.makedirs('backups')
    for fichier in fichiers_a_sauver:
        if os.path.exists(fichier):
            shutil.copy2(fichier, f"backups/{fichier}.bak")

executer_backup_auto()

# --- FONCTION UNIQUE DE CHANGEMENT DE PAGE (ÉVITE LES CONFLITS) ---
def changer_page(nom_page):
    st.session_state.page = nom_page
    st.session_state.maint_edit_id = None
    st.session_state.show_form_classique = False
    st.session_state.show_form_vidange = False
    st.session_state.edit_idx = None
    st.session_state.saisie_ouverte = False
    st.session_state.memo_edit_id = None
    st.rerun()

# =================================================================
# --- BANDEAU TEMPOREL & ÉCRAN DE CONNEXION ---
# =================================================================
now = datetime.now()
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
date_bandeau = f"&#128197; {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"

st.markdown("""<style>
    .main-header { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }
    .date-header { text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }
</style>""", unsafe_allow_html=True)

if not st.session_state.authenticated:
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

# =================================================================
# --- SYSTEME DE NAVIGATION HARMONISÉ (HAUT ET SIDEBAR) ---
# =================================================================
menu = ["PLANNING", "CONTACTS", "STATS", "MAINT", "LOG", "MEMOS", "FACT"]
icones = {"PLANNING": "📅", "CONTACTS": "👤", "STATS": "📊", "MAINT": "🛠️", "LOG": "📖", "MEMOS": "📝", "FACT": "📑"}

# 1. Barre de navigation horizontale (Haut)
cols_nav = st.columns(len(menu))
for i, name in enumerate(menu):
    is_active = st.session_state.page == name
    if cols_nav[i].button(f"{icones[name]}\n{name}", key=f"nav_{name}", use_container_width=True, type="primary" if is_active else "secondary"):
        changer_page(name)

# 2. Barre de navigation latérale (Sidebar)
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 10px; background-color: #2c3e50; border-radius: 8px; margin-bottom: 20px;">
            <h2 style="color: white; margin: 0; font-size: 1.3rem;">🚢 Vesta Skipper</h2>
            <small style="color: #bdc3c7;">Gestion de Bord v2026</small>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 🗺️ Navigation rapide")
    for name in menu:
        if st.button(f"{icones[name]} {name}", key=f"side_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
            changer_page(name)
            
    st.divider()
    st.markdown("### ⚙️ Paramètres")
    if st.button("📂 Archives & Coffre-Fort", use_container_width=True, type="primary" if st.session_state.page == "ARCHIVES" else "secondary"):
        changer_page("ARCHIVES")

    st.markdown("---")
    st.caption("⚓ Enregistré sur GitHub : Rico56-web")

st.divider()

# =================================================================
# --- 6. AIGUILLAGE DE L'AFFICHAGE CENTRAL ---
# =================================================================
if st.session_state.page == "PLANNING":
    st.subheader("📅 Planning & Engagements")
    pass # Votre code existant (avec couleur Bleue pour CMN !)

elif st.session_state.page == "CONTACTS":
    st.subheader("👤 Fiches Contacts")
    df_raw = charger_data_safe('contacts.json')
    pass # Votre suite du code contacts ici...

elif st.session_state.page == "MODIFIER_CONTACT":
    st.subheader("✏️ Modifier le contact")
    pass 

elif st.session_state.page == "FACT":
    st.subheader("📑 Suivi Facturation")
    pass 

elif st.session_state.page == "MAINT":
    st.subheader("🛠️ Maintenance & Moteur")
    pass 

elif st.session_state.page == "LOG":
    st.subheader("📖 Livre de Bord (Log)")
    pass 

elif st.session_state.page == "STATS":
    st.subheader("📊 Statistiques Saison")
    pass 

elif st.session_state.page == "ARCHIVES":
    st.subheader("📂 Archives & Clôtures")
    pass

# --- BLOC MEMOS INTEGRÉ DANS L'AIGUILLAGE GLOBAL ---
elif st.session_state.page == "MEMOS":
    st.markdown("<h2 style='text-align: center; color: #34495E;'>⚓ Mémos & Check-lists de Bord</h2>", unsafe_allow_html=True)
    df_memos = charger_data_safe('memos.json')

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

    if not df_memos.empty:
        if 'Archive' not in df_memos.columns: df_memos['Archive'] = "Non Archivé"
        df_show = df_memos[df_memos['Archive'] != "Archivé"]
        
        for idx, row in df_show.sort_index(ascending=False).iterrows():
            stat_val = str(row.get('Statut', 'Normal'))
            pay_val = str(row.get('Paiement', 'N/A'))

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
            else:
                if stat_val == "Urgent": h_c, bg_c = "#E74C3C", "#FDEDEC" 
                elif stat_val == "Fait": h_c, bg_c = "#27AE60", "#EAFAF1"
                else: h_c, bg_c = "#2980B9", "#EBF5FB"

                st.markdown(f"""
                    <div style="background-color:{bg_c}; border-left: 10px solid {h_c}; padding: 15px; border-radius: 10px;">
                        <span style="font-weight: bold; color: black;">📅 {row['Date']} | 💰 {pay_val}</span>
                    </div>
                """, unsafe_allow_html=True)

                lignes = str(row.get('Description', '')).split('\n')
                data_tasks = [{"Fait": l.startswith("✅ | "), "Tâche": l.replace("✅ | ", "").replace("❌ | ", "")} for l in lignes if l.strip()]
                
                if data_tasks:
                    edited_df = st.data_editor(pd.DataFrame(data_tasks), key=f"ed_{idx}", hide_index=True, use_container_width=True)
                    if not edited_df.equals(pd.DataFrame(data_tasks)):
                        new_desc = "\n".join([f"{'✅ | ' if r['Fait'] else ''}{r['Tâche']}" for _, r in edited_df.iterrows()])
                        df_memos.at[idx, 'Description'] = new_desc
                        sauvegarder_data(df_memos, 'memos.json')
                        st.rerun()

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
                if cols[3].button("🗑️ Suppr", key=f"btn_del_{idx}"):
                    df_memos = df_memos.drop(idx).reset_index(drop=True)
                    sauvegarder_data(df_memos, 'memos.json')
                    st.rerun()
                st.divider()
# =================================================================
# --- 5. BLOC CONTACTS (LOGIQUE FINANCIÈRE SECURISEE & SANS CONFLIT) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    # 🔄 NETTOYAGE FORCÉ DU CACHE POUR LIRE LES DONNÉES FRAÎCHES DE GITHUB
    st.cache_data.clear()

    if "vue_contact" not in st.session_state:
        st.session_state.vue_contact = "En cours"

    # Chargement brut
    df_raw = charger_data_safe('contacts.json')
    
    # 🚨 SÉCURITÉ ABSOLUE : Initialisation et contrôle des colonnes
    colonnes_requises = ['Prénom', 'Nom', 'Statut', 'Paiement', 'Relancer', 'DateNav', 'Société', 'Jours', 'Prix', 'Acompte', 'Notes', 'Téléphone', 'Email', 'Pers']
    if df_raw is None or not hasattr(df_raw, "empty") or df_raw.empty:
        df_raw = pd.DataFrame(columns=colonnes_requises)
    else:
        for col in colonnes_requises:
            if col not in df_raw.columns:
                df_raw[col] = ""
    
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

    df_c = df_raw.copy().fillna("")
    df_c['orig_idx'] = df_c.index  # CONSERVATION STRICTE DE L'INDEX ORIGINAL
    
    # 🎯 SÉCURISATION DU TRI ET DE L'ANNÉE : On extrait proprement les 4 derniers chiffres textuels de la date
    df_c['dt_sort'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
    df_c['Annee_Texte'] = df_c['DateNav'].astype(str).str.extract(r'(\d{{4}})')
    df_c['Annee_Texte'] = pd.to_numeric(df_c['Annee_Texte'], errors='coerce')
    
    c_search, c_yr, c_new = st.columns([2, 1, 1])
    search = c_search.text_input("🔍 Rechercher...", "", key="search_bar_contacts").upper()
    annee_sel = c_yr.selectbox("Saison", [2025, 2026, 2027], index=1)
    
    # --- DASHBOARD FINANCIER HARMONISÉ ---
    # Filtrage par année ultra tolérant (détection textuelle ou par objet date)
    mask_ca = ((df_c['Annee_Texte'] == annee_sel) | (df_c['dt_sort'].dt.year == annee_sel)) & (~df_c['Statut'].str.lower().str.contains("annule|refuse", na=False))
    df_ca = df_c[mask_ca].copy()

    def get_reel_encaisse(row):
        p = to_f(row.get('Prix', 0))
        a = to_f(row.get('Acompte', 0))
        return p if str(row.get('Paiement', '')).strip().upper() == "PAID" else a

    if not df_ca.empty:
        total_prevu = df_ca['Prix'].apply(to_f).sum()
        total_encaisse = df_ca.apply(get_reel_encaisse, axis=1).sum()
        reste_percevoir = max(0, total_prevu - total_encaisse)
    else:
        total_prevu = total_encaisse = reste_percevoir = 0

    col_f1, col_f2, col_f3 = st.columns(3)
    col_f1.metric(f"CA Prévu {annee_sel}", f"{int(total_prevu)} €")
    col_f2.metric("Encaissé (Réel)", f"{int(total_encaisse)} €")
    col_f3.metric("Reste à percevoir", f"{int(reste_percevoir)} €")
    st.divider()

    if c_new.button("➕ NOUVEAU CLIENT", use_container_width=True):
        new_r = {"Prénom": "NOUVEAU", "Nom": "CLIENT", "Statut": "En attente", "Paiement": "Unpaid", "Relancer": "Non", "DateNav": f"01/06/{annee_sel}", "Société": "PERSO", "Jours": 1, "Prix": 0, "Acompte": 0, "Notes": "", "Téléphone": "", "Email": "", "Pers": 1}
        df_new = pd.concat([pd.DataFrame([new_r]), df_raw], ignore_index=True)
        sauvegarder_data(df_new, 'contacts.json')
        st.session_state.edit_idx = 0  # Placé au sommet de la pile
        st.session_state.page = "MODIFIER_CONTACT"
        st.rerun()

    # Nettoyage et préparation des filtres de catégories
    statut_clean = df_c['Statut'].astype(str).str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    rel_clean = df_c['Relancer'].fillna("Non").astype(str).str.upper()
    
    if st.session_state.vue_contact == "Archives": 
        mask_aff = (statut_clean.str.contains("termine|annule|refuse")) & (rel_clean != "OUI")
    elif st.session_state.vue_contact == "Relances": 
        mask_aff = (rel_clean == "OUI")
    elif st.session_state.vue_contact == "Attente": 
        mask_aff = (statut_clean == "liste d'attente")
    else: 
        mask_aff = ~(statut_clean.str.contains("termine|annule|refuse")) & (statut_clean != "liste d'attente")

    # Application du filtre final d'affichage (Catégorie + Année sécurisée)
    mask_annee = (df_c['Annee_Texte'] == annee_sel) | (df_c['dt_sort'].dt.year == annee_sel) | (df_c['Annee_Texte'].isna() & df_c['dt_sort'].isna())
    df_aff = df_c[mask_aff & mask_annee].copy()
    
    if search: 
        df_aff = df_aff[df_aff['Nom'].astype(str).str.contains(search) | df_aff['Prénom'].astype(str).str.contains(search) | df_aff['Société'].astype(str).str.contains(search)]
    
    # Tri d'affichage chronologique
    if not df_aff.empty:
        df_aff = df_aff.sort_values(by='dt_sort', ascending=True)

        for _, row in df_aff.iterrows():
            idx = row['orig_idx']  
            p_tot = to_f(row.get('Prix', 0))
            p_enc = p_tot if str(row.get('Paiement', '')).strip().upper() == "PAID" else to_f(row.get('Acompte', 0))
            
            soc = str(row.get('Société', 'PERSO')).upper()
            colors = {"CMN": ("#2980B9", "#EBF5FB"), "CLICK": ("#27AE60", "#EAFAF1"), "VOG": ("#8E44AD", "#F5EEF8"), "PERSO": ("#F1C40F", "#FEF9E7")}
            border_col, bg_card = colors.get(soc, ("#7F8C8D", "#FDFEFE"))
            badge_vip = "⭐ " if str(row.get('Relancer', 'Non')).upper() == "OUI" else ""

            st.markdown(f"""
            <div style="background:{bg_card}; padding:15px; border-radius:12px; border-left:10px solid {border_col}; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); margin-bottom:10px; color: black;">
                <div style="display:flex; justify-content:space-between;">
                    <b>{badge_vip}{row['Prénom']} {row['Nom']}</b>
                    <span style="font-size:0.8rem; font-weight:bold; color:{border_col};">{soc}</span>
                </div>
                <div style="margin-top:5px; font-size:0.9rem;">
                    📅 {row['DateNav'] if row['DateNav'] else 'Date à définir'} | 👥 {int(to_f(row.get('Pers', 1)))} pers. | ⏱️ {row.get('Jours', 1)} j.<br>
                    💰 <b>Total: {int(p_tot)}€</b> | 💳 Reçu: {int(p_enc)}€ | 📉 <b>Reste: {int(max(0, p_tot-p_enc))}€</b>
                </div>
                <div style="font-style:italic; font-size:0.8rem; color:gray; margin-top:5px;">Statut: {row['Statut']} | Paiement: {row['Paiement']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            if c1.button("✏️ ÉDITER", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx  
                st.session_state.page = "MODIFIER_CONTACT"
                st.rerun()

            if st.session_state.vue_contact == "Relances":
                if c2.button("🔄 RE-RÉSERVER", key=f"dup_{idx}", use_container_width=True):
                    df_db = charger_data('contacts.json')
                    new_e = row.to_dict()
                    new_e.update({"DateNav": datetime.now().strftime("%d/%m/%Y"), "Statut": "En attente", "Paiement": "Unpaid", "Prix": 0, "Acompte": 0})
                    for k in ['orig_idx', 'dt_sort', 'Annee_Texte']: new_e.pop(k, None)
                    df_db = pd.concat([pd.DataFrame([new_e]), df_db], ignore_index=True)
                    sauvegarder_data(df_db, 'contacts.json')
                    st.session_state.edit_idx = 0
                    st.session_state.page = "MODIFIER_CONTACT"
                    st.rerun()
            else:
                if f"confirm_del_{idx}" not in st.session_state:
                    if c2.button("🗑️ SUPPRIMER", key=f"del_{idx}", use_container_width=True):
                        st.session_state[f"confirm_del_{idx}"] = True
                        st.rerun()
                else:
                    st.warning("Confirmer la suppression ?")
                    cx, cy = st.columns(2)
                    if cx.button("✅ OUI", key=f"y_{idx}", use_container_width=True):
                        df_db = charger_data('contacts.json').drop(idx).reset_index(drop=True)
                        sauvegarder_data(df_db, 'contacts.json')
                        del st.session_state[f"confirm_del_{idx}"]
                        st.rerun()
                    if cy.button("❌ NON", key=f"n_{idx}", use_container_width=True):
                        del st.session_state[f"confirm_del_{idx}"]
                        st.rerun()

            if st.session_state.vue_contact == "En cours" and c3.button("🏁 FINIR", key=f"fin_{idx}", use_container_width=True):
                df_all = charger_data('contacts.json')
                df_all.loc[idx, ['Statut', 'Paiement']] = ["Terminé", "Paid"]
                sauvegarder_data(df_all, 'contacts.json')
                st.rerun()
    else:
        st.info("💡 Aucun contact enregistré pour cette catégorie ou cette saison. Utilisez le bouton '➕ NOUVEAU CLIENT' ci-dessus pour commencer.")

# =================================================================
# --- 6. PAGE MODIFIER CONTACT : VERSION SÉCURISÉE (V110) ---
# =================================================================
elif st.session_state.page == "MODIFIER_CONTACT":
    st.markdown('<h3 style="text-align:center;">✏️ Modifier le Contact</h3>', unsafe_allow_html=True)
    
    idx_to_edit = st.session_state.get('edit_idx')
    df_m = charger_data_safe('contacts.json')

    if idx_to_edit is not None and not df_m.empty and idx_to_edit in df_m.index:
        row = df_m.loc[idx_to_edit]
        
        with st.form("form_edit_v2026"):
            # --- Ligne 1 : Identité ---
            c1, c2 = st.columns(2)
            new_pre = c1.text_input("Prénom", value=str(row.get('Prénom', '')))
            new_nom = c2.text_input("Nom", value=str(row.get('Nom', '')))
            
            # --- Ligne 2 : Logistique ---
            c3, c4, c5, c6 = st.columns([2, 1, 1, 1])
            new_date = c3.text_input("Date (JJ/MM/AAAA)", value=str(row.get('DateNav', '')))
            
            val_jours = to_f(row.get('Jours', 1.0))
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
            val_prix = int(to_f(row.get('Prix', 0)))
            val_acompte = int(to_f(row.get('Acompte', 0)))
                
            new_prix = f1.number_input("Prix Total (€)", value=val_prix)
            new_acompte = f2.number_input("Acompte encaissé (€)", value=val_acompte)
            f3.markdown(f"<br><b style='color:gray;'>Reste : {new_prix - new_acompte} €</b>", unsafe_allow_html=True)

            # --- Ligne 5 : Contact & Notes ---
            new_tel = st.text_input("Téléphone", value=str(row.get('Téléphone', '')))
            new_mail = st.text_input("Email", value=str(row.get('Email', '')))
            new_notes = st.text_area("Notes", value=str(row.get('Notes', '')))

            # --- Validation Sécurisée ---
            if st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS", use_container_width=True):
                df_m.at[idx_to_edit, 'Prénom'] = str(new_pre).upper().strip()
                df_m.at[idx_to_edit, 'Nom'] = str(new_nom).upper().strip()
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
        st.error("Erreur de chargement ou contact introuvable.")

    if st.button("⬅️ ANNULER ET RETOUR", key="back_mod_contact"):
        st.session_state.page = "CONTACTS"
        st.rerun()


# =================================================================
# --- 7. PAGE PLANNING (V19.2 - CALIBRÉ SÉCURITÉ) ---
# =================================================================
if st.session_state.page == "PLANNING":
    st.markdown("## ⚓ Tableau de Bord - Port Crouesty")

    # Widget Météo Windy
    st.markdown("""
        <iframe width="100%" height="350" src="https://www.windy.com/embed2.html?lat=47.545&lon=-2.894&zoom=10&level=surface&overlay=wind&product=ecmwf&metricWind=kt&metricTemp=%C2%B0C" frameborder="0"></iframe>
    """, unsafe_allow_html=True)
    
    col_v1, col_v2, col_v3 = st.columns(3)
    
    # --- A. ALERTE MAINTENANCE (HARMONISÉE ABSOLUE) ---
    df_log = charger_data_safe('logbook.json')
    derniere_heure = 0.0
    if not df_log.empty:
        df_valid = df_log[df_log['MotArr'] > 0]
        derniere_heure = to_f(df_valid['MotArr'].max()) if not df_valid.empty else to_f(df_log['MotArr'].max())
    
    params = charger_params()
    seuil_v = params.get('prochaine_vidange', 2500.0)
    heures_restantes = seuil_v - derniere_heure
    
    if heures_restantes < 15:
        col_v1.error(f"🛠️ Vidange : Proche ({heures_restantes:.1f}h restantes) !")
    else:
        col_v1.success(f"⚙️ Moteur : {derniere_heure:.1f}h (Reste {heures_restantes:.1f}h)")

    # --- B. FACTURATION EN ATTENTE ---
    df_f = charger_data_safe('contacts.json')
    nb_unpaid = len(df_f[df_f['Paiement'] == "Unpaid"]) if not df_f.empty else 0
    col_v2.metric("Factures Unpaid", f"{nb_unpaid}", delta=f"{nb_unpaid}" if nb_unpaid > 0 else "OK", delta_color="inverse")

    # --- C. MARÉES ---
    col_v3.link_button("🌊 Marées Crouesty", "https://maree.info/104", use_container_width=True)
    st.divider()

    # --- CALENDRIER & SORTIES ---
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>🗓️ PLANNING DES SORTIES</h1></div>', unsafe_allow_html=True)
    st.divider()

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

    jours_occ = {}
    total_mois = 0
    missions_list = []

    if not df_f.empty:
        df_p = df_f.fillna("")
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

                # REGLE COULEUR SPECIFIQUE : CMN EN BLEU
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
## =================================================================
# --- 8. PAGE STATS : SOURCE DE VÉRITÉ UNIQUE HARMONISÉE ---
# =================================================================
if st.session_state.page == "STATS":
    st.markdown('<h2 style="text-align:center;">📊 Dashboard Intégral Vesta</h2>', unsafe_allow_html=True)
    
# 1. CHARGEMENT SÉCURISÉ DES DONNÉES
    df_actif = charger_data_safe('contacts.json')
    df_m = charger_data_safe('maintenance.json') 
    df_log = charger_data_safe('logbook.json')
    
    params = charger_params()
    frais_defaut = {"Port Arzon": 3800, "Assurance": 1200, "Entretien": 1500, "Divers": 500}
    
    # --- SÉCURISATION CRUCIALE : On vérifie que c'est bien un dictionnaire ---
    if 'frais_fixes' not in params or not isinstance(params['frais_fixes'], dict) or not params['frais_fixes']:
        params['frais_fixes'] = frais_defaut
    
    frais_params = params['frais_fixes']
    
    # Calcul sécurisé de la somme
    total_frais_fixes = 0.0
    for v in frais_params.values():
        try:
            clean_v = str(v).replace('€', '').replace(' ', '').replace(',', '.').strip()
            total_frais_fixes += float(clean_v)
        except (ValueError, TypeError):
            continue
    # ----------------------------
    
    # FILTRES DE LA PAGE
    c_sel1, c_sel2 = st.columns([3, 1])
    mode_bilan = c_sel1.radio("Mode de calcul :", ["Réel (Encaissé)", "Prévisionnel (Saison)"], horizontal=True)
    sel_y = c_sel2.selectbox("Saison :", [2025, 2026, 2027], index=1)

    # 2. NETTOYAGE ET CONVERSION SÉCURISÉE EN AMONT
    if not df_actif.empty:
        df_actif['dt_vrai'] = pd.to_datetime(df_actif['DateNav'], dayfirst=True, errors='coerce')
        df_actif['Prix'] = pd.to_numeric(df_actif['Prix'], errors='coerce').fillna(0.0)
        df_actif['Acompte'] = pd.to_numeric(df_actif['Acompte'], errors='coerce').fillna(0.0)
        
        mask_f = (df_actif['dt_vrai'].dt.year == sel_y) & (~df_actif['Statut'].str.lower().str.contains("annule|refuse", na=False))
        df_f = df_actif[mask_f].copy()
        
        # EXCLUSION STRUCTURELLE DES UNPAID DANS LE MODE REEL
        df_f['Montant_Encaisse'] = df_f.apply(
            lambda x: x['Prix'] if str(x.get('Paiement', '')).strip().upper() == "PAID" else x['Acompte'], 
            axis=1
        )
        total_ca_saison = df_f['Prix'].sum()
        total_encaisse_reel = df_f['Montant_Encaisse'].sum()
        reste_a_percevoir = total_ca_saison - total_encaisse_reel
    else:
        df_f = pd.DataFrame(columns=['dt_vrai', 'Prix', 'Acompte', 'Montant_Encaisse', 'Société', 'Statut'])
        total_ca_saison = total_encaisse_reel = reste_a_percevoir = 0.0

    total_ca_display = total_encaisse_reel if mode_bilan == "Réel (Encaissé)" else total_ca_saison
    df_rec_f = df_f[df_f['Montant_Encaisse'] > 0].copy() if mode_bilan == "Réel (Encaissé)" else df_f.copy()

    # 3. TRAITEMENT AUTOMATISÉ DU JOURNAL DE MAINTENANCE
    if not df_m.empty:
        df_m['dt_maint'] = pd.to_datetime(df_m['Date'], dayfirst=True, errors='coerce')
        df_m['M_Num'] = pd.to_numeric(df_m['M_Num'], errors='coerce').fillna(0.0)
        
        if mode_bilan == "Réel (Encaissé)":
            mask_maint_mode = (df_m['dt_maint'].dt.year == sel_y) & (df_m['Statut'] == "Fait")
            titre_tableaux = "Réelles Encaissées / Faites"
        else:
            mask_maint_mode = (df_m['dt_maint'].dt.year == sel_y) & (df_m['Statut'].isin(["Fait", "À prévoir"]))
            titre_tableaux = "Cumulées (Fait + À prévoir)"
            
        df_m_y = df_m[mask_maint_mode].copy()
    else:
        df_m_y = pd.DataFrame(columns=['dt_maint', 'M_Num', 'Type', 'Objet'])
        titre_tableaux = "Aucune donnée"

    total_dep = df_m_y['M_Num'].sum()

    if not df_m_y.empty:
        mask_frais_fixes = df_m_y['Type'].fillna('').str.lower().str.contains('port|assur', na=False)
        total_pure_maint = df_m_y[~mask_frais_fixes]['M_Num'].sum()
        total_reels_fixes = df_m_y[mask_frais_fixes]['M_Num'].sum()
    else:
        total_pure_maint = 0.0
        total_reels_fixes = 0.0

    # 4. TRAITEMENT DU LOGBOOK
    if not df_log.empty:
        df_log['dt_log'] = pd.to_datetime(df_log['Date'], dayfirst=True, errors='coerce')
        df_log_y = df_log[df_log['dt_log'].dt.year == sel_y].copy()
        
        total_h_moteur = pd.to_numeric(df_log_y['TotalMot'], errors='coerce').sum() if 'TotalMot' in df_log_y.columns else 0.0
        total_gazole = pd.to_numeric(df_log_y['VolumeGazole'], errors='coerce').sum() if 'VolumeGazole' in df_log_y.columns else 0.0
        h_moteur_abs = pd.to_numeric(df_log['MotArr'], errors='coerce').max()
        
        total_milles = pd.to_numeric(df_log_y['TotalMil'], errors='coerce').sum() if 'TotalMil' in df_log_y.columns else 0.0
        total_h_voile = pd.to_numeric(df_log_y['H_Voile'], errors='coerce').sum() if 'H_Voile' in df_log_y.columns else 0.0
        total_heures_mer = total_h_moteur + total_h_voile
        ratio_voile = (total_h_voile / total_heures_mer * 100) if total_heures_mer > 0 else 0.0
    else:
        total_h_moteur = total_gazole = h_moteur_abs = total_milles = total_h_voile = ratio_voile = 0.0

    # CALCULS DES COMPLÉMENTS FINANCIERS
    total_sommes_percues = total_encaisse_reel
    solde_net_calculé = total_ca_display - total_dep

    # =================================================================
    # --- AFFICHAGE : BLOC COMPACT DES INDICATEURS VISUELS (METRICS) ---
    # =================================================================
    st.divider()
    
    # LIGNE 1 : ACTIVITÉ & TECHNIQUE
    st.markdown("##### ⚓ Activité & Navigation")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("⛵ Sorties", f"{len(df_f[df_f['Prix'] > 0]) if not df_f.empty else 0}")
    t2.metric("⚙️ Heures Mot.", f"{total_h_moteur:.1f} h")
    t3.metric("⛽ Gazole", f"{total_gazole:,.0f} L")
    conso_h = total_gazole / total_h_moteur if total_h_moteur > 0 else 0
    t4.metric("📉 Conso Moyenne", f"{conso_h:.1f} L/h")

    st.write("") 

    # LIGNE 2 : RECETTES DE LA SAISON
    st.markdown("##### 💰 Recettes de la Saison")
    f1, f2, f3 = st.columns(3)
    f1.metric("🎯 CA Prévu", f"{total_ca_saison:,.0f} €")
    f2.metric("📥 Sommes Perçues", f"{total_sommes_percues:,.0f} €")
    f3.metric("📩 Reste à percevoir", f"{reste_a_percevoir:,.0f} €")

    st.write("")

    # LIGNE 3 : SOMMES DÉPENSÉES
    st.markdown(f"##### 💸 Sommes Dépensées ({mode_bilan})")
    d1, d2, d3 = st.columns(3)
    d1.metric("🔧 Dépenses Maint.", f"{total_pure_maint:,.0f} €")
    d2.metric("📋 Charges Fixes Réelles", f"{total_reels_fixes:,.0f} €")
    d3.metric("📊 Total Sorties", f"{total_dep:,.0f} €")

    st.write("")

    # LIGNE 4 : SYNTHÈSE GLOBALE & VIDANGE
    st.markdown("##### 📈 Bilan Net & Maintenance")
    m_col1, m_col2 = st.columns([1, 3])
    m_col1.metric("📊 Solde Net", f"{solde_net_calculé:,.0f} €")
    
    h_rest = params.get('prochaine_vidange', 2500.0) - h_moteur_abs
    
    with m_col2:
        st.write(f"**🔧 Vidange dans : {max(0, h_rest):.1f} h**")
        if h_rest <= 0:
            st.error(f"🚨 Échéance de vidange dépassée de {abs(h_rest):.1f} heures ! Penser à planifier l'entretien du moteur.")
        elif h_rest <= 20:
            st.warning(f"⚠️ Échéance de vidange proche ({h_rest:.1f} h restantes).")
        else:
            st.caption(f"Compteur absolu : {h_moteur_abs:.1f} h. Échéance configurée à : {params.get('prochaine_vidange', 2500.0):.1f} h.")

    # =================================================================
    # --- LES TABLEAUX ET ANALYSES ---
    # =================================================================

    # --- 1. TABLEAU REPARTITION TOP CLIENTS / SOCIÉTÉS ---
    st.divider()
    st.markdown("### 🏢 Répartition par Client / Entreprise")
    if not df_rec_f.empty:
        df_rec_f['Soc_Clean'] = df_rec_f['Société'].fillna('PERSO').str.upper().str.strip()
        val_somme = 'Montant_Encaisse' if mode_bilan == "Réel (Encaissé)" else 'Prix'
        stats_soc = df_rec_f.groupby('Soc_Clean')[val_somme].sum().reset_index()
        stats_soc = stats_soc.sort_values(by=val_somme, ascending=False)
        stats_soc.columns = ['Société / Client', 'Volume Affaires (€)']
        st.dataframe(
            stats_soc.style.format({'Volume Affaires (€)': '{:,.2f} €'}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Aucune donnée d'entreprise à afficher pour les filtres sélectionnés.")

    # --- 2. TABLEAU COMPLÉMENT NAVIGATION VESTA ---
    st.divider()
    st.markdown("### ⚓ Complément de Navigation Vesta")
    col_n1, col_n2, col_n3 = st.columns(3)
    col_n1.metric(label="🌊 Distance Totale Saison", value=f"{total_milles:.1f} NM")
    col_n2.metric(label="⛵ Heures sous Voile", value=f"{total_h_voile:.1f} h")
    col_n3.metric(label="📊 Part de la Voile (Ratio)", value=f"{ratio_voile:.1f} %")
    
    if not df_log.empty and not df_log_y.empty:
        st.markdown("#### 🗺️ Synthèse des milles et moteur par Voyage")
        df_log_y['TotalMil_Num'] = pd.to_numeric(df_log_y['TotalMil'], errors='coerce').fillna(0.0)
        df_log_y['TotalMot_Num'] = pd.to_numeric(df_log_y['TotalMot'], errors='coerce').fillna(0.0)
        
        stats_voyages = df_log_y.groupby('Navigation').agg({
            'Date': 'count',
            'TotalMil_Num': 'sum',
            'TotalMot_Num': 'sum'
        }).reset_index()
        
        stats_voyages.columns = ['Nom de la Croisière', 'Nombre d\'Étapes', 'Milles parcourus (NM)', 'Heures Moteur']
        stats_voyages = stats_voyages.sort_values(by='Milles parcourus (NM)', ascending=False)
        
        st.dataframe(
            stats_voyages.style.format({
                'Milles parcourus (NM)': '{:.1f} NM',
                'Heures Moteur': '{:.1f} h'
            }),
            use_container_width=True, hide_index=True
        )

    # --- 3. GRAPHIQUE CHRONOLOGIQUE ET SUIVI DE RENTABILITÉ DYNAMIQUE ---
    st.divider()
    st.markdown(f"### 📈 Chronologie des Recettes ({mode_bilan}) & Seuil de Rentabilité")
    
    ordre_mois = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    df_graph = pd.DataFrame({'Mois': range(1, 13), 'NomMois': ordre_mois})
    
    # Choix dynamique de la colonne à cumuler selon le mode de calcul sélectionné
    val_col_graph = 'Montant_Encaisse' if mode_bilan == "Réel (Encaissé)" else 'Prix'
    
    if not df_f.empty:
        r_m = df_f.groupby(df_f['dt_vrai'].dt.month)[val_col_graph].sum()
        df_graph = df_graph.merge(r_m.rename('Recettes'), left_on='Mois', right_index=True, how='left')
        act_m = df_f.groupby(df_f['dt_vrai'].dt.month).size()
        df_graph = df_graph.merge(act_m.rename('Sorties'), left_on='Mois', right_index=True, how='left')
    if not df_m_y.empty:
        d_m = df_m_y.groupby(df_m_y['dt_maint'].dt.month)['M_Num'].sum()
        df_graph = df_graph.merge(d_m.rename('Dépenses'), left_on='Mois', right_index=True, how='left')
    
    df_graph = df_graph.fillna(0)
    
    # Calcul du cumulatif dynamique
    df_graph['Recettes_Cumulees'] = df_graph['Recettes'].cumsum()

    # AMÉLIORATION CLÉ : Tronquer la ligne pour ne pas étirer la courbe sur les mois futurs sans données
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if sel_y == current_year:
        # On ne garde les étiquettes de texte et la courbe que jusqu'au mois en cours
        df_graph['Recettes_Cumulees_Visuel'] = df_graph.apply(lambda x: x['Recettes_Cumulees'] if x['Mois'] <= current_month else None, axis=1)
    else:
        df_graph['Recettes_Cumulees_Visuel'] = df_graph['Recettes_Cumulees']

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Histogrammes mensuels (Dépenses & Recettes du mois)
    fig.add_trace(go.Bar(x=df_graph['NomMois'], y=df_graph['Recettes'], name='Recettes du Mois (€)', marker_color='#a3e4d7', opacity=0.5), secondary_y=False)
    fig.add_trace(go.Bar(x=df_graph['NomMois'], y=df_graph['Dépenses'], name='Dépenses du Mois (€)', marker_color='#f5b7b1', opacity=0.5), secondary_y=False)
    
    # Courbe d'évolution cumulée réactive et tronquée
    fig.add_trace(go.Scatter(
        x=df_graph['NomMois'], 
        y=df_graph['Recettes_Cumulees_Visuel'], 
        name='Cumul de la Saison (€)', 
        line=dict(color='#2ecc71', width=4, shape='spline'),
        mode='lines+markers+text',
        text=[f"{v:,.0f}€" if (not pd.isna(v) and v > 0) else "" for v in df_graph['Recettes_Cumulees_Visuel']],
        textposition="top center"
    ), secondary_y=False)
    
    # Ligne de Seuil de Rentabilité
    fig.add_trace(go.Scatter(
        x=df_graph['NomMois'], 
        y=[total_frais_fixes] * 12, 
        name='Seuil de Rentabilité', 
        line=dict(color='#e74c3c', width=2, dash='dash'),
        mode='lines'
    ), secondary_y=False)
    
    # Courbe secondaire : Nombre de sorties
    fig.add_trace(go.Scatter(x=df_graph['NomMois'], y=df_graph['Sorties'], name='Nb Sorties', line=dict(color='#3498db', width=2, dash='dot')), secondary_y=True)
    
    fig.update_layout(
        height=400, 
        barmode='group', 
        margin=dict(l=0, r=0, t=20, b=0), 
        legend=dict(orientation="h", y=1.2, x=0),
        yaxis=dict(title="Montants (€)", gridcolor="#eee"),
        yaxis2=dict(title="Nombre de Sorties", showgrid=False)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. TABLEAUX SÉPARÉS : MAINTENANCE TECHNIQUE VS FRAIS FIXES RÉELS ---
    st.divider()
    
    if not df_m_y.empty:
        df_pure_maint = df_m_y[~mask_frais_fixes].copy()
        df_reels_fixes = df_m_y[mask_frais_fixes].copy()
    else:
        df_pure_maint = pd.DataFrame()
        df_reels_fixes = pd.DataFrame()

    colonnes_souhaitees = ['Date', 'Type', 'Objet', 'M_Num']
    mapping_renom = {'Type': 'Catégorie', 'Objet': 'Désignation', 'M_Num': 'Montant (€)'}

    # TABLEAU A : MAINTENANCE TECHNIQUE UNIQUEMENT
    st.markdown(f"### 🔧 Détail des Dépenses de Maintenance Pure ({titre_tableaux})")
    if not df_pure_maint.empty:
        df_pm_trié = df_pure_maint.sort_values('dt_maint', ascending=True)
        col_val_pm = [c for c in colonnes_souhaitees if c in df_pm_trié.columns]
        st.dataframe(df_pm_trié[col_val_pm].rename(columns=mapping_renom), use_container_width=True, hide_index=True)
        st.markdown(f"<div style='text-align:right; background:#e8f4fd; padding:10px; border-radius:5px; color:#1d6fa5; font-weight:bold; margin-top:5px; margin-bottom:25px;'>TOTAL MAINTENANCE TECHNIQUE : {total_pure_maint:,.2f} €</div>", unsafe_allow_html=True)
    else:
        st.info("Aucune dépense de maintenance technique enregistrée sur cette sélection.")

    # TABLEAU B : SUIVI DES FRAIS FIXES RÉELS DU JOURNAL
    st.markdown(f"### 📋 Suivi Réel des Frais Fixes du Journal ({titre_tableaux})")
    if not df_reels_fixes.empty:
        df_rf_trié = df_reels_fixes.sort_values('dt_maint', ascending=True)
        col_val_rf = [c for c in colonnes_souhaitees if c in df_rf_trié.columns]
        st.dataframe(df_rf_trié[col_val_rf].rename(columns=mapping_renom), use_container_width=True, hide_index=True)
        st.markdown(f"<div style='text-align:right; background:#fef5d1; padding:10px; border-radius:5px; color:#856404; font-weight:bold; margin-top:5px;'>TOTAL FRAIS FIXES RÉELS RELEVÉS : {total_reels_fixes:,.2f} €</div>", unsafe_allow_html=True)
    else:
        st.info("Aucun paiement de type Port ou Assurance relevé sur cette sélection.")

    # --- 5. TABLEAU DES SOMMES PERÇUES ---
    st.divider()
    st.markdown("### 📥 Détail des sommes perçues")
    if not df_f.empty:
        df_percues = df_f[df_f['Montant_Encaisse'] > 0.01].sort_values('dt_vrai').copy()
        if not df_percues.empty:
            df_percues_display = df_percues[['DateNav', 'Nom', 'Prénom', 'Prix', 'Acompte', 'Paiement', 'Montant_Encaisse']].copy()
            df_percues_display.columns = ['Date Nav.', 'Nom', 'Prénom', 'Prix Contrat', 'Acompte', 'Statut Paiement', 'Somme Perçue (€)']
            st.dataframe(
                df_percues_display.style.format({
                    'Prix Contrat': '{:,.2f} €',
                    'Acompte': '{:,.2f} €',
                    'Somme Perçue (€)': '{:,.2f} €'
                }),
                use_container_width=True, hide_index=True
            )
            st.markdown(f"<div style='text-align:right; background:#d4edda; padding:10px; border-radius:5px; color:#155724; font-weight:bold;'>TOTAL ENCAISSÉ : {total_encaisse_reel:,.2f} €</div>", unsafe_allow_html=True)
        else:
            st.info("Aucun encaissement enregistré pour cette sélection.")
    else:
        st.info("Aucune donnée disponible.")

    # --- 6. TABLEAU DES SOMMES RESTANT À PERCEVOIR ---
    st.divider()
    st.markdown("### 🔍 Détail des sommes restant à percevoir")
    if not df_f.empty:
        df_reste = df_f.copy()
        df_reste['Reste'] = df_reste['Prix'] - df_reste['Montant_Encaisse']
        df_a_percevoir = df_reste[df_reste['Reste'] > 0.01].sort_values('dt_vrai')
        if not df_a_percevoir.empty:
            df_a_percevoir_display = df_a_percevoir[['DateNav', 'Nom', 'Prénom', 'Prix', 'Montant_Encaisse', 'Reste']].copy()
            df_a_percevoir_display.columns = ['Date Nav.', 'Nom', 'Prénom', 'Prix Contrat', 'Déjà Encaissé', 'Reste à Percevoir (€)']
            st.dataframe(
                df_a_percevoir_display.style.format({
                    'Prix Contrat': '{:,.2f} €',
                    'Déjà Encaissé': '{:,.2f} €',
                    'Reste à Percevoir (€)': '{:,.2f} €'
                }),
                use_container_width=True, hide_index=True
            )
            st.markdown(f"<div style='text-align:right; background:#f8d7da; padding:10px; border-radius:5px; color:#721c24; font-weight:bold;'>TOTAL À RÉCUPÉRER : {reste_a_percevoir:,.2f} €</div>", unsafe_allow_html=True)
        else:
            st.success("✅ Aucune somme en attente.")

    # --- 7. SEUIL DE RENTABILITÉ CALIBRÉ ---
    st.divider()
    st.markdown("### ⚓ Seuil de Rentabilité (Point Mort Annuel)")
    
    ca_actuel = total_encaisse_reel 
    progression = min(1.0, ca_actuel / total_frais_fixes) if total_frais_fixes > 0 else 0
    manque_a_gagner = max(0.0, total_frais_fixes - ca_actuel)

    c_pm1, c_pm2 = st.columns([2, 1])
    with c_pm1:
        st.write(f"**Objectif : Couvrir les charges prévisionnelles de l'année ({int(total_frais_fixes):,} €)**")
        st.progress(progression)
        if progression >= 1:
            st.success(f"🎉 **Seuil de rentabilité atteint !** Le prévisionnel des charges annuelles est couvert pour {sel_y}.")
        else:
            st.info(f"Il manque encore **{int(manque_a_gagner):,} €** pour équilibrer le budget annuel théorique.")

    with c_pm2:
        with st.expander("Détail des charges de référence"):
            for poste, montant in frais_params.items():
                st.write(f"{poste} : {int(montant):,} €")
            st.write(f"---")
            st.write(f"**TOTAL : {int(total_frais_fixes):,} €**")

    # --- 8. CONFIGURATION ET MODIFICATION DES CHARGES ---
    st.divider()
    with st.expander("⚙️ Modifier les charges fixes annuelles"):
        st.info("Modifiez les montants ci-dessous et cliquez sur 'Enregistrer'.")
        frais_actuels = params['frais_fixes']
        
        with st.form("form_frais_fixes"):
            new_frais = {}
            cols_f = st.columns(2)
            for i, (poste, montant) in enumerate(frais_actuels.items()):
                with cols_f[i % 2]:
                    new_frais[poste] = st.number_input(f"{poste} (€)", value=float(montant), step=50.0)
            
            if st.form_submit_button("💾 ENREGISTRER LES CHARGES"):
                params['frais_fixes'] = new_frais
                sauvegarder_params(params)
                st.success("Configuration sauvegardée à distance !")
                st.rerun()

# =================================================================
# --- 8. PAGE MAINTENANCE : GESTION SÉCURISÉE (V2026) ---
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
            <meta charset="utf-8">
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

    # --- 2. CHARGEMENT DES DONNÉES SÉCURISÉES ---
    df_m = charger_data_safe('maintenance.json')
    df_log = charger_data_safe('logbook.json')
    releve_h = pd.to_numeric(df_log['MotArr'], errors='coerce').max() if not df_log.empty else 0.0
    
    params = charger_params()
    if 'prochaine_vidange' not in params:
        params['prochaine_vidange'] = 2500.0
        sauvegarder_params(params)

    if 'maint_edit_id' not in st.session_state:
        st.session_state.maint_edit_id = None

    st.markdown('<h2 style="text-align:center;">🛠️ Maintenance & Vidange</h2>', unsafe_allow_html=True)

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
    
    # --- 4. DASHBOARD CARBURANT ---
    st.markdown("### ⛽ Suivi Carburant")
    df_carb = charger_data_safe('carburant.json')
    
    col_c1, col_c2, col_c3 = st.columns(3)
    if not df_carb.empty:
        total_l = to_f(df_carb['Litres'].sum())
        total_e = to_f(df_carb['Prix'].sum())
        dernier_pu = to_f(df_carb['PU'].iloc[-1]) if 'PU' in df_carb.columns else 0.0
        
        col_c1.metric("Total Litres", f"{total_l:.0f} L")
        col_c2.metric("Total Dépensé", f"{total_e:.2f} €")
        col_c3.metric("Dernier Prix/L", f"{dernier_pu:.3f} €")

    with st.expander("➕ Enregistrer un plein / Voir l'historique", expanded=False):
        with st.form("form_fuel_v2026"):
            c1, c2, c3 = st.columns(3)
            d_f = c1.date_input("Date du plein")
            l_f = c2.number_input("Litres", min_value=0.0, step=10.0)
            p_f = c3.number_input("Total TTC (€)", min_value=0.0, step=10.0)
        
            if st.form_submit_button("Enregistrer le plein", use_container_width=True):
                if l_f > 0:
                    new_f = {"Date": d_f.strftime("%d/%m/%Y"), "Litres": l_f, "Prix": p_f, "PU": round(p_f / l_f, 3)}
                    df_carb = pd.concat([df_carb, pd.DataFrame([new_f])], ignore_index=True)
                    sauvegarder_data(df_carb, 'carburant.json')
                    st.success("Plein enregistré !")
                    st.rerun()
                else:
                    st.error("Le nombre de litres doit être supérieur à 0.")

        if not df_carb.empty:
            st.dataframe(df_carb.tail(5), use_container_width=True, hide_index=True)
            
    # --- INITIALISATION DES ÉTATS ---
    if 'show_form_classique' not in st.session_state: st.session_state.show_form_classique = False
    if 'show_form_vidange' not in st.session_state: st.session_state.show_form_vidange = False

    # --- 5. BOUTONS D'APPEL ---
    col_btn1, col_btn2 = st.columns(2)
    if col_btn1.button("🔧 NOUVELLE INTERVENTION", use_container_width=True):
        st.session_state.show_form_classique = True
        st.session_state.show_form_vidange = False
        st.rerun()
    
    if col_btn2.button("🛢️ RÉVISION MOTEUR", use_container_width=True):
        st.session_state.show_form_vidange = True
        st.session_state.show_form_classique = False
        st.rerun()

    # --- 6. FORMULAIRE CLASSIQUE ---
    if st.session_state.show_form_classique:
        with st.form("form_new_maint"):
            st.subheader("🔧 Nouvelle Intervention")
            f_obj = st.text_input("Désignation")
            c1, c2, c3 = st.columns(3)
            f_d = c1.date_input("Date", datetime.now())
            f_m = c2.number_input("Montant (€)", min_value=0.0, step=10.0)
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
                st.session_state.show_form_classique = False
                st.rerun()

    # --- 7. FORMULAIRE VIDANGE ---
    if st.session_state.show_form_vidange:
        with st.form("form_vidange_moteur"):
            st.subheader("🛢️ Révision Moteur")
            c_v1, c_v2 = st.columns(2)
            v_date = c_v1.date_input("Date", datetime.now())
            v_heures = c_v2.number_input("Heures moteur actualisées", value=float(releve_h))
            
            st.markdown("**Check-list révision :**")
            col_c1, col_c2, col_c3 = st.columns(3)
            chk_huile = col_c1.checkbox("Vidange Huile")
            chk_f_huile = col_c1.checkbox("Filtre Huile")
            chk_f_gasoil = col_c2.checkbox("Filtre Gasoil")
            chk_f_pre = col_c2.checkbox("Pré-filtre")
            chk_courroie = col_c3.checkbox("Courroies")
            chk_impeller = col_c3.checkbox("Impeller")
            
            v_cout = st.number_input("Coût fournitures (€)", min_value=0.0, step=5.0)
            v_notes = st.text_area("Observations additionnelles")
            inc_h = st.selectbox("Échéance prochaine vidange (+h)", [50, 100, 150, 200], index=1)
            
            bv_col1, bv_col2 = st.columns(2)
            if bv_col1.form_submit_button("✅ VALIDER LA RÉVISION", use_container_width=True, type="primary"):
                travaux = [t for t, c in zip(["Huile", "F-Huile", "F-Gasoil", "Pré-filtre", "Courroies", "Impeller"], 
                                             [chk_huile, chk_f_huile, chk_f_gasoil, chk_f_pre, chk_courroie, chk_impeller]) if c]
                details = f"Révision à {v_heures}h. Travaux validés : {', '.join(travaux)}. Obs : {v_notes}"
                
                new_row = {"Date": v_date.strftime("%d/%m/%Y"), "Objet": f"RÉVISION MOTEUR ({v_heures}h)", "M_Num": v_cout, "Statut": "Fait", "Type": "Maintenance", "Notes": details}
                
                params['prochaine_vidange'] = round(v_heures + inc_h, 1)
                sauvegarder_params(params)
                
                df_m = pd.concat([df_m, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df_m, 'maintenance.json')
                st.session_state.show_form_vidange = False
                st.rerun()

            if bv_col2.form_submit_button("❌ FERMER", use_container_width=True):
                st.session_state.show_form_vidange = False
                st.rerun()

    # --- 8. FILTRES & AFFICHAGE LOGS ---
    st.divider()
    col_menu1, col_menu2, col_menu3 = st.columns([2, 1.2, 1.2])
    filter_statut = col_menu1.radio("Filtre statut :", ["Tout", "⏳ À faire", "✅ Fait"], horizontal=True)
    mode_m = col_menu2.radio("Fenêtre :", ["À ce jour", "Année complète"], horizontal=True)
    sel_y = col_menu3.selectbox("Sélection année :", [2025, 2026, 2027], index=1)

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
            st.info("Aucune fiche de maintenance ne correspond aux critères.")
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
                        e_mon = c2.number_input("Montant (€)", value=float(to_f(row['M_Num'])))
                        e_not = st.text_area("Notes", value=row.get('Notes', ''))
                        e_sta = st.selectbox("Statut", ["À prévoir", "Fait"], index=1 if est_fait else 0)
                        
                        cb1, cb2 = st.columns(2)
                        if cb1.form_submit_button("✅ SAUVER"):
                            df_m.at[idx, 'Objet'] = e_obj
                            df_m.at[idx, 'Date'] = e_dat
                            df_m.at[idx, 'M_Num'] = e_mon
                            df_m.at[idx, 'Notes'] = e_not
                            df_m.at[idx, 'Statut'] = e_sta
                            
                            df_sauve = df_m.drop(columns=['dt_maint'], errors='ignore')
                            sauvegarder_data(df_sauve, 'maintenance.json')
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
                                <small>Catégorie : <b>{row.get('Type', 'Maintenance')}</b></small>
                                <small>Coût : <b>{row['M_Num']} €</b></small>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    if row.get('Notes'): st.caption(f"📝 {row['Notes']}")

                    bc1, bc2, bc3, bc4 = st.columns(4)
                    if bc1.button("✏️ Modif", key=f"ed_m_{idx}"):
                        st.session_state.maint_edit_id = idx
                        st.session_state.show_form_classique = False
                        st.session_state.show_form_vidange = False
                        st.rerun()
                        
                    with bc2:
                        bouton_imprimer_fiche_maint(row['Objet'], row['Date'], row.get('Notes', 'N/A'), row['Statut'])
                    
                    label_toggle = "⏳ À prévoir" if est_fait else "✅ Marquer FAIT"
                    if bc3.button(label_toggle, key=f"st_m_{idx}"):
                        df_m.at[idx, 'Statut'] = "À prévoir" if est_fait else "Fait"
                        df_sauve = df_m.drop(columns=['dt_maint'], errors='ignore')
                        sauvegarder_data(df_sauve, 'maintenance.json')
                        st.rerun()

                    if bc4.button("🗑️ Suppr", key=f"pre_m_{idx}"):
                        df_m = df_m.drop(idx)
                        df_sauve = df_m.drop(columns=['dt_maint'], errors='ignore')
                        sauvegarder_data(df_sauve, 'maintenance.json')
                        st.rerun()
                        
    # --- 9. EXPORT EXCEL SÉCURISÉ ---
    if not df_m.empty:
        st.divider()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_m.drop(columns=['dt_maint'], errors='ignore').to_excel(writer, index=False)
        st.download_button("📥 Télécharger Historique Complet (Excel)", data=buffer.getvalue(), 
                           file_name=f"Maintenance_Vesta_Skipper.xlsx", use_container_width=True)

# facturation
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =================================================================
# --- FONCTION COMPLÉMENTAIRE D'ENVOI DE MAIL ---
# =================================================================
def envoyer_email_facturation_cmn(corps_texte, mois_annee, destinataire=None):
    """Gère l'envoi de l'email via le protocole sécurisé TLS."""
    try:
        # Récupération sécurisée des accès dans les secrets Streamlit
        cfg = st.secrets["email"]
        
        # Si aucun destinataire n'est spécifié, on prend l'officiel des secrets
        if destinataire is None:
            destinataire = cfg["email_destinataire"]
        
        msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]
        msg['To'] = destinataire
        msg['Subject'] = f"🧾 Facturation Vesta Skipper - Prestations CMN ({mois_annee})"
        
        msg.attach(MIMEText(corps_texte, 'html'))
        
        # Connexion sécurisée au serveur
        server = smtplib.SMTP(cfg["smtp_server"], int(cfg["smtp_port"]))
        server.starttls()  # Chiffrement de la connexion
        server.login(cfg["smtp_user"], cfg["smtp_password"])
        server.sendmail(cfg["smtp_user"], destinataire, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur d'envoi de l'email : {e}")
        return False


# =================================================================
# --- 7. PAGE FACTURATION (FACT) ---
# =================================================================
if st.session_state.page == "FACT":
    st.markdown("<h2 style='text-align: center;'>📑 Suivi de Facturation</h2>", unsafe_allow_html=True)
    
    # Chargement des données fraîches
    df_fact = charger_data_safe('contacts.json')

    if df_fact.empty:
        st.info("Aucune donnée de facturation disponible.")
    else:
        # --- CALCULS SÉCURISÉS ---
        total_ca = sum(df_fact['Prix'].apply(to_f))
        total_enc = sum(df_fact['Acompte'].apply(to_f))
        reste_a_percevoir = max(0.0, total_ca - total_enc)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total CA", f"{total_ca:,.2f} €".replace(",", " "))
        m2.metric("Encaissé", f"{total_enc:,.2f} €".replace(",", " "))
        m3.metric("Reste à percevoir", f"{reste_a_percevoir:,.2f} €".replace(",", " "), 
                  delta=f"-{reste_a_percevoir:,.2f} €" if reste_a_percevoir > 0 else None, 
                  delta_color="inverse")

        st.divider()

        # --- MODULE D'ENVOI CONFIGURABLE CMN ---
        st.subheader("📬 Envoi groupé CMN (Vérification & Signature)")
        
        # Initialisation des états de révision dans la session Streamlit
        if 'preparer_mail_cmn' not in st.session_state: st.session_state.preparer_mail_cmn = False

        df_fact['dt_temp'] = pd.to_datetime(df_fact['DateNav'], dayfirst=True, errors='coerce')
        df_cmn_attente = df_fact[(df_fact['Société'].str.upper().str.contains('CMN', na=False)) & (df_fact['Paiement'] == "Unpaid")].copy()
        
        if not df_cmn_attente.empty:
            mois_actuel = pd.Timestamp.now().strftime("%B %Y")
            st.info(f"Il y a **{len(df_cmn_attente)}** prestation(s) CMN en attente de règlement.")
            
            # Bouton d'ouverture de l'espace de révision
            if not st.session_state.preparer_mail_cmn:
                if st.button("📝 Préparer et réviser le relevé mensuel CMN", use_container_width=True):
                    st.session_state.preparer_mail_cmn = True
                    st.rerun()
            
            # --- ESPACE DE RÉVISION ACTIF ---
            if st.session_state.preparer_mail_cmn:
                with st.expander("🔍 CONFIGURATION DE L'EMAIL AVANT ENVOI", expanded=True):
                    
                    st.markdown("### 1. Sélectionner les prestations à inclure")
                    prestations_choisies = {}
                    for idx, row in df_cmn_attente.iterrows():
                        label_presta = f"📅 {row.get('DateNav','')} - {row.get('Nom','')} {row.get('Prénom','')} ({to_f(row.get('Prix',0)):.2f} €)"
                        prestations_choisies[idx] = st.checkbox(label_presta, value=True, key=f"chk_mail_{idx}")
                    
                    # Filtrage des lignes retenues par l'utilisateur
                    indices_retenus = [k for k, v in prestations_choisies.items() if v]
                    df_cmn_filtre = df_cmn_attente.loc[indices_retenus]
                    
                    st.markdown("### 2. Destinataire et Message d'accompagnement")
                    # Récupération de l'adresse par défaut depuis les secrets
                    email_defaut_cmn = st.secrets["email"].get("email_destinataire", "compta.cmn@exemple.com")
                    
                    # Champ modifiable pour faire des essais (ex: eric.clavreul@gmail.com)
                    email_destinataire_actif = st.text_input(
                        "Adresse email du destinataire", 
                        value=email_defaut_cmn,
                        help="Par défaut celle des secrets. Modifie-la pour faire un test (ex: eric.clavreul@gmail.com)"
                    )
                    
                    texte_defaut = f"Bonjour,\n\nVeuillez trouver ci-dessous le récapitulatif des prestations maritimes effectuées sur le voilier VESTA pour le compte de CMN au titre du mois de {mois_actuel}.\n Bonne reception"
                    corps_texte_user = st.text_area("Message d'introduction", value=texte_defaut, height=120)
                    
                    st.markdown("### 3. Signature électronique & Certification")
                    col_sig1, col_sig2 = st.columns([6, 4])
                    with col_sig1:
                        signataire = st.text_input("Nom du signataire", value="Le propiétaire de Vesta: Eric CLAVREUL")
                        certif_signature = st.checkbox("✍️ Certifier l'exactitude des prestations et apposer ma signature numérique", value=False)
                    with col_sig2:
                        # Génération visuelle d'un bloc de signature électronique
                        date_signature = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
                        if certif_signature:
                            st.markdown(f"""
                            <div style="border: 2px dashed #27ae60; background-color: #f2f9f4; padding: 10px; border-radius: 5px; text-align: center; color: #27ae60;">
                                <small style="text-transform: uppercase; font-weight: bold; letter-spacing: 1px;">Signé Électriquement</small><br>
                                <b>{signataire}</b><br>
                                <small>Horodatage : {date_signature}</small><br>
                                <small style="font-size: 0.6rem; color: #7f8c8d;">ID: SECURE-LOG-{pd.Timestamp.now().strftime('%Y%m%d')}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("""
                            <div style="border: 2px dashed #bdc3c7; background-color: #f9f9f9; padding: 10px; border-radius: 5px; text-align: center; color: #7f8c8d; height: 85px; display: flex; align-items: center; justify-content: center;">
                                <small>En attente de signature...</small>
                            </div>
                            """, unsafe_allow_html=True)

                    st.divider()
                    
                    # --- ACTION D'ENVOI ET CONFIRMATION DÉFINITIVE ---
                    c_btn1, c_btn2 = st.columns(2)
                    
                    if c_btn1.button("❌ Annuler / Masquer la préparation", use_container_width=True):
                        st.session_state.preparer_mail_cmn = False
                        st.rerun()
                        
                    if c_btn2.button("🚀 CONFIRMER ET ENVOYER LE MAIL", type="primary", use_container_width=True, disabled=not certif_signature):
                        if df_cmn_filtre.empty:
                            st.warning("Veuillez sélectionner au moins une prestation à inclure dans le tableau.")
                        else:
                            # Construction dynamique du tableau HTML des prestations validées
                            lignes_tableau = ""
                            total_cmn = 0.0
                            for _, row in df_cmn_filtre.iterrows():
                                valeur = to_f(row.get('Prix', 0))
                                total_cmn += valeur
                                lignes_tableau += f"""
                                <tr>
                                    <td style='padding:8px; border:1px solid #ddd;'>{row.get('DateNav','')}</td>
                                    <td style='padding:8px; border:1px solid #ddd;'>{row.get('Nom','')} {row.get('Prénom','')}</td>
                                    <td style='padding:8px; border:1px solid #ddd; text-align:right;'>{valeur:.2f} €</td>
                                </tr>
                                """
                            
                            # Corps de l'email HTML final avec mise en forme de la signature
                            corps_html_final = f"""
                            <html>
                            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
                                <p>{corps_texte_user.replace('\n', '<br>')}</p>
                                
                                <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
                                    <thead>
                                        <tr style="background-color: #3498db; color: white;">
                                            <th style="padding:10px; border:1px solid #ddd; text-align:left;">Date</th>
                                            <th style="padding:10px; border:1px solid #ddd; text-align:left;">Skipper / Contact</th>
                                            <th style="padding:10px; border:1px solid #ddd; text-align:right;">Montant</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {lignes_tableau}
                                        <tr style="font-weight: bold; background-color: #f9f9f9;">
                                            <td colspan="2" style="padding:10px; border:1px solid #ddd; text-align:right;">Total à régler :</td>
                                            <td style="padding:10px; border:1px solid #ddd; text-align:right; color:#2c3e50;">{total_cmn:.2f} €</td>
                                        </tr>
                                    </tbody>
                                </table>
                                
                                <br>
                                <div style="border-top: 1px solid #eee; padding-top: 15px; margin-top: 30px;">
                                    <p style="margin: 0; font-size: 0.9rem; color: #7f8c8d;"><i>Message certifié et signé numériquement par l'expéditeur :</i></p>
                                    <p style="margin: 5px 0 0 0; font-weight: bold; color: #27ae60; font-size: 1.1rem;">✍️ {signataire}</p>
                                    <p style="margin: 0; font-size: 0.8rem; color: #95a5a6;">Horodatage de certification : {date_signature}</p>
                                    <p style="margin: 0; font-size: 0.7rem; color: #bdc3c7;">ID Traçabilité Vesta : SECURE-LOG-{pd.Timestamp.now().strftime('%Y%m%d')}</p>
                                </div>
                            </body>
                            </html>
                            """
                            
                            with st.spinner(f"Envoi sécurisé du relevé à {email_destinataire_actif}..."):
                                succes = envoyer_email_facturation_cmn(corps_html_final, mois_actuel, destinataire=email_destinataire_actif)
                                if succes:
                                    st.success(f"Le relevé de facturation révisé et signé a été envoyé à {email_destinataire_actif} !")
                                    st.session_state.preparer_mail_cmn = False
                                    st.balloons()
                                    st.rerun()
        else:
            st.write("✨ Aucune facture CMN en attente d'envoi ce mois-ci.")
            
        st.divider()

        # --- FILTRAGE ET TRI CHRONOLOGIQUE DES ONGLETS ---
        df_fact = df_fact.sort_values(by='dt_temp', ascending=True)
        df_fact = df_fact.drop(columns=['dt_temp'], errors='ignore')

        t1, t2 = st.tabs(["⏳ À ENCAISSER", "✅ PAYÉ"])

        def afficher_onglet(status_filtre):
            df_vue = df_fact[df_fact['Paiement'] == status_filtre]
            
            if df_vue.empty:
                st.info(f"Aucune fiche dans la catégorie '{status_filtre}'.")
            else:
                aujourdhui = pd.Timestamp.now().normalize()

                for idx, row in df_vue.iterrows():
                    soc = str(row.get('Société', 'PERSO')).upper()
                    is_cmn = "CMN" in soc
                    
                    date_nav = pd.to_datetime(row.get('DateNav',''), dayfirst=True, errors='coerce')
                    retard = (status_filtre == "Unpaid") and (pd.notna(date_nav) and date_nav < aujourdhui)
                    
                    label_retard = "<span style='color:#E74C3C; font-weight:bold; font-size:0.8rem;'>⚠️ RETARD</span>" if retard else ""
                    card_bg = "#E3F2FD" if is_cmn else "#F9F9F9"
                    border_color = "#E74C3C" if retard else ("#3498db" if is_cmn else "#7F8C8D")
                    
                    st.markdown(f"""
                        <div style="background:{card_bg}; border: 1px solid #ddd; border-left:10px solid {border_color}; padding:15px; border-radius:8px; margin-bottom:10px; color:black;">
                            <div style="display:flex; justify-content:space-between;">
                                <b>{row.get('Nom','')} {row.get('Prénom','')}</b>
                                <span style="font-size:1.1rem; font-weight:bold;">{to_f(row.get('Prix',0)):.2f} €</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <small>📅 {row.get('DateNav','')} | 🏢 {soc}</small>
                                {label_retard}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    c1, c2, _ = st.columns([2.5, 2.5, 5])
                    
                    if status_filtre == "Unpaid":
                        if c1.button(f"💰 Encaisser", key=f"pay_btn_{idx}"):
                            df_fact.at[idx, 'Paiement'] = "Paid"
                            df_fact.at[idx, 'Acompte'] = df_fact.at[idx, 'Prix']
                            sauvegarder_data(df_fact, 'contacts.json')
                            st.toast("Paiement enregistré !", icon="💰")
                            st.rerun()
                    else:
                        if c1.button(f"↩️ Annuler", key=f"unpay_btn_{idx}"):
                            df_fact.at[idx, 'Paiement'] = "Unpaid"
                            df_fact.at[idx, 'Acompte'] = 0.0
                            sauvegarder_data(df_fact, 'contacts.json')
                            st.toast("Paiement annulé et remis en attente", icon="↩️")
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
# --- 11. PAGE ARCHIVES & SÉCURITÉ (VERSION UNIFIÉE & FIXÉE) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    st.markdown("<h2 style='text-align: center;'>📂 Archives & Clôture de Saison</h2>", unsafe_allow_html=True)
    
    if st.button("⬅️ Retour au Planning", use_container_width=True):
        st.session_state.page = "PLANNING"
        st.rerun()

    # --- SECTION 1 : CONSULTATION DES HISTORIQUES ---
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
        st.subheader("Archives Contacts (Saisons passées - Statut Inclus)")
        st.dataframe(charger_data_safe('archives_contacts_2026.json'), use_container_width=True)

    st.divider()

    # --- SECTION 2 : COFFRE-FORT (SAUVEGARDE MANUELLE) ---
    st.markdown("### 🛡️ Coffre-fort de sauvegarde")
    with st.expander("💾 Exporter les données actives (.CSV)", expanded=False):
        st.write("Téléchargez vos fichiers de données actuels pour les sauvegarder localement.")
        
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
                csv_data = df_bak.to_csv(index=False).encode('utf-8-sig')
                date_str = pd.Timestamp.now().strftime("%d_%m_%Y")
                file_final = f"VESTA_{nom_fichier.replace('.json', '')}_{date_str}.csv"
                
                cols[i].download_button(
                    label=f"📥 {nom_affichage}",
                    data=csv_data,
                    file_name=file_final,
                    mime='text/csv',
                    use_container_width=True
                )
            else:
                cols[i].caption(f"⚠️ {nom_affichage} vide.")

    st.divider()

    # --- SECTION 3 : OUTILS DE FIN DE SAISON ---
    st.markdown("### 🏁 Clôture de Saison 2026")
    with st.expander("🚨 ZONE DE DANGER : Archiver les dossiers réglés", expanded=False):
        st.warning("""
            **Action irréversible :** Cela va basculer définitivement toutes les fiches marquées comme **'Paid'** 
            vers le fichier d'archive. Les dossiers restés en 'Unpaid' resteront dans le tableau de bord actif.
        """)
        
        if st.button("🔒 EXÉCUTER L'ARCHIVAGE DES CONTACTS RÉGLÉS", use_container_width=True, type="primary"):
            df_f = charger_data_safe('contacts.json')
            
            if not df_f.empty:
                if 'Paiement' not in df_f.columns:
                    df_f['Paiement'] = "Unpaid"
                
                df_paid = df_f[df_f['Paiement'] == "Paid"].copy()
                df_unpaid = df_f[df_f['Paiement'] != "Paid"].copy()
                
                if not df_paid.empty:
                    # Rétention stricte du statut Paid dans les archives
                    df_hist = charger_data_safe('archives_contacts_2026.json')
                    df_new_hist = pd.concat([df_hist, df_paid], ignore_index=True)
                    sauvegarder_data(df_new_hist, 'archives_contacts_2026.json')
                    
                    # Nettoyage du fichier actif
                    sauvegarder_data(df_unpaid, 'contacts.json')
                    st.success(f"✅ {len(df_paid)} fiches traitées et sécurisées dans 'archives_contacts_2026.json'.")
                    st.rerun()
                else:
                    st.info("Aucun contact marqué 'Paid' à archiver pour le moment.")
            else:
                st.error("Le fichier de contacts actif est vide.")

# =================================================================
# --- 12. PAGE LIVRE DE BORD (LOG) ---
# =================================================================
if st.session_state.page == "LOG":
    st.markdown('<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;"><h1>📖 Livre de Bord & Statistiques</h1></div>', unsafe_allow_html=True)

    df_log = charger_data_safe('logbook.json')
    
    if 'saisie_ouverte' not in st.session_state: st.session_state.saisie_ouverte = False
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None

    # --- A. SUPPRESSION SECURISEE ---
    def supprimer_entree(idx_to_remove):
        df_now = charger_data_safe('logbook.json')
        df_now = df_now.drop(idx_to_remove).reset_index(drop=True)
        sauvegarder_data(df_now, 'logbook.json')
        st.toast("Entrée supprimée", icon="🗑️")
        st.rerun()

    # --- B. FORMULAIRE UNIQUE ---
    def formulaire_fiche(mode="creation", index=None):
        title = "➕ NOUVELLE ÉTAPE QUOTIDIENNE" if mode == "creation" else "📝 MODIFIER L'ÉTAPE"
        
        if mode == "edition" and index is not None:
            r = df_log.iloc[index]
            val_date = r['Date']
            val_nav = r['Navigation']
            val_equi = r.get('Coéquipiers', '')
            val_meteo = r.get('Meteo', '')
            val_notes = r.get('Notes', '')
            val_mot_dep = float(r.get('MotDep', 0.0))
            val_mot_arr = float(r.get('MotArr', 0.0))
            val_mil_dep = float(r.get('MilDep', 0.0))
            val_mil_arr = float(r.get('MilArr', 0.0))
            val_voile = float(r.get('H_Voile', 0.0))
        else:
            last_mot = df_log['MotArr'].max() if not df_log.empty else 0.0
            last_mil = df_log['MilArr'].max() if not df_log.empty else 0.0
            val_date = pd.Timestamp.now().to_pydatetime()
            
            # --- Suggestion automatique du nom selon la date ---
            val_nav = ""
            if not df_log.empty:
                try:
                    # Copie pour isoler le calcul de la date la plus récente
                    df_calc = df_log.copy()
                    df_calc['dt_temp'] = pd.to_datetime(df_calc['Date'], dayfirst=True, errors='coerce')
                    df_calc = df_calc.dropna(subset=['dt_temp'])
                    
                    if not df_calc.empty:
                        # On récupère la ligne de l'étape la plus récente chronologiquement
                        derniere_etape = df_calc.loc[df_calc['dt_temp'].idxmax()]
                        date_derniere = derniere_etape['dt_temp']
                        date_actuelle = pd.Timestamp.now().normalize()
                        
                        # Si l'écart est strictement inférieur à 5 jours, on conserve le nom
                        if (date_actuelle - date_derniere).days < 5:
                            val_nav = derniere_etape.get('Navigation', '')
                except:
                    val_nav = "" # Sécurité en cas d'erreur de parsing des dates
            
            val_equi = ""
            val_meteo = ""
            val_notes = ""
            val_mot_dep = last_mot
            val_mot_arr = last_mot
            val_mil_dep = last_mil
            val_mil_arr = last_mil
            val_voile = 0.0

        with st.expander(title, expanded=True):
            with st.form(key=f"form_log_{mode}"):
                c1, c2 = st.columns(2)
                f_date = c1.date_input("Date", val_date) if mode=="creation" else c2.text_input("Date", value=val_date)
                f_but = c2.text_input("Nom du Voyage / Croisière", value=val_nav, placeholder="ex: Gijón 2026")
                
                f_equipage = st.text_area("Équipage / Rôle", value=val_equi, height=60)
                
                cm1, cm2 = st.columns(2)
                f_meteo = cm1.text_input("Météo (Vent/Mer)", value=val_meteo)
                f_notes = cm2.text_area("Observations / Escale", value=val_notes, height=60)
                
                st.divider()
                col1, col2, col3 = st.columns(3)
                m_dep = col1.number_input("Moteur Départ (h)", value=val_mot_dep, format="%.1f", step=0.5)
                m_arr = col2.number_input("Moteur Arrivée (h)", value=val_mot_arr, format="%.1f", step=0.5)
                h_voile = col3.number_input("Heures Voile (h)", value=val_voile, format="%.1f", step=0.5)
                
                ck1, ck2 = st.columns(2)
                k_dep = ck1.number_input("Milles Départ (Log)", value=val_mil_dep, format="%.1f", step=1.0)
                k_arr = ck2.number_input("Milles Arrivée (Log)", value=val_mil_arr, format="%.1f", step=1.0)

                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 ENREGISTRER L'ÉTAPE", use_container_width=True, type="primary"):
                    new_entry = {
                        "Date": f_date.strftime("%d/%m/%Y") if mode=="creation" else f_date,
                        "Navigation": f_but,
                        "Coéquipiers": f_equipage,
                        "Meteo": f_meteo, "Notes": f_notes,
                        "MotDep": m_dep, "MotArr": m_arr, "TotalMot": round(max(0.0, m_arr - m_dep), 2),
                        "MilDep": k_dep, "MilArr": k_arr, "TotalMil": round(max(0.0, k_arr - k_dep), 2),
                        "H_Voile": h_voile
                    }
                    
                    if mode == "creation":
                        df_updated = pd.concat([df_log, pd.DataFrame([new_entry])], ignore_index=True)
                    else:
                        for k, v in new_entry.items(): df_log.at[index, k] = v
                        df_updated = df_log
                        st.session_state.edit_idx = None
                    
                    sauvegarder_data(df_updated, 'logbook.json')
                    st.session_state.saisie_ouverte = False
                    st.rerun()

                if b2.form_submit_button("❌ ANNULER", use_container_width=True):
                    st.session_state.saisie_ouverte = False
                    st.session_state.edit_idx = None
                    st.rerun()

    if st.session_state.edit_idx is not None:
        formulaire_fiche(mode="edition", index=st.session_state.edit_idx)
    elif st.session_state.saisie_ouverte:
        formulaire_fiche(mode="creation")
    else:
        st.button("➕ NOUVELLE ÉTAPE QUOTIDIENNE", on_click=lambda: st.session_state.update({"saisie_ouverte": True}), use_container_width=True)

    # --- C. VUE EN LISTE CHRONOLOGIQUE PAR CRUISE ---
    if not df_log.empty:
        st.divider()
        df_v = df_log.copy()
        df_v['dt'] = pd.to_datetime(df_v['Date'], dayfirst=True, errors='coerce')
        df_v['original_index'] = df_v.index
        df_v = df_v.sort_values(by=['dt', 'Navigation'], ascending=[False, False])

        for nav_name, group in df_v.groupby('Navigation', sort=False):
            t_mil = group['TotalMil'].sum()
            st.markdown(f"""
                <div style="background:#2c3e50; color:white; padding:10px; border-radius:8px; margin-top:15px; border-left: 5px solid #3498db;">
                    <b>🚢 {nav_name or "Navigation Hors-Croisière"}</b> | Distance Totale Voyage : {t_mil:.1f} NM
                </div>
            """, unsafe_allow_html=True)
            
            for idx, row in group.iterrows():
                idx_orig = int(row['original_index'])
                with st.container():
                    c_txt, c_btn = st.columns([0.7, 0.3])
                    with c_txt:
                        st.markdown(f"""
                            <div style="background:white; border-left:4px solid #bdc3c7; padding:8px 15px; border-bottom:1px solid #eee; color: black;">
                                <b>📅 {row['Date']}</b> | ⚙️ {row['TotalMot']:.1f}h Mot. | ⛵ {row['H_Voile']:.1f}h Voile | <b>{row['TotalMil']:.1f} NM</b><br>
                                <small style="color:#34495e;">📍 Cond. Météo : {row.get('Meteo','-')} | {row.get('Notes','')}</small>
                            </div>
                        """, unsafe_allow_html=True)
                    with c_btn:
                        ce, cd, cc = st.columns([1, 1, 2])
                        
                        if ce.button("✏️", key=f"e_{idx_orig}"):
                            st.session_state.edit_idx = idx_orig
                            st.rerun()
                        
                        confirm_key = f"confirm_del_{idx_orig}"
                        if not st.session_state.get(confirm_key, False):
                            if cd.button("🗑️", key=f"d_{idx_orig}"):
                                st.session_state[confirm_key] = True
                                st.rerun()
                        else:
                            if cc.button("✅ OUI", key=f"ok_{idx_orig}", type="primary"):
                                st.session_state[confirm_key] = False
                                supprimer_entree(idx_orig)
                            if cc.button("❌", key=f"no_{idx_orig}"):
                                st.session_state[confirm_key] = False
                                st.rerun()

    # --- D. EXPORT EXCEL/CSV ---
    if not df_log.empty:
        st.divider()
        csv = df_log.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Télécharger le Livre de Bord complet (.CSV)", data=csv, file_name='livre_de_bord_vesta.csv', mime='text/csv', use_container_width=True)







































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































