import os
import requests, base64, json, time, html, io, shutil
import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse
from datetime import datetime, date, timedelta
import calendar
import streamlit.components.v1 as components
from page_contacts import afficher_page_contacts
from page_modifier_contact import afficher_page_modifier_contact
from page_planning import afficher_page_planning
from page_croisieres import afficher_page_croisieres
from page_modifier_croisiere import afficher_page_modifier_croisiere
from page_stats import afficher_page_stats
from page_fact import afficher_page_fact
from page_relances import afficher_page_relances
from page_maint import afficher_page_maint
from page_log import afficher_page_log
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
    repo = "rico56-web/gestion-voile"
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("Token GitHub manquant : configure-le dans .streamlit/secrets.toml (voir README).")
        return pd.DataFrame()
    try:
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content_b64 = res.json().get('content', '')
            content_str = base64.b64encode(b"[]").decode('utf-8') if not content_b64 else content_b64
            decoded_bytes = base64.b64decode(content_str)
            import io
            df = pd.read_json(io.BytesIO(decoded_bytes), orient="records")
            return df
        else:
            st.error(f"Erreur GitHub ({res.status_code}) en chargeant {file} : {res.json().get('message', res.text)}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur chargement {file} : {e}")
        return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo = "rico56-web/gestion-voile"
        token = st.secrets.get("github", {}).get("token")
        if not token:
            st.error("Token GitHub manquant : configure-le dans .streamlit/secrets.toml (voir README).")
            return
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        content_str = df.to_json(orient="records", indent=4)
        content_b64 = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
        res_put = requests.put(url, headers={"Authorization": f"token {token}"}, 
                     json={"message": f"Update {file}", "content": content_b64, "sha": sha})
        if res_put.status_code not in (200, 201):
            st.error(f"Échec de la sauvegarde de {file} (code {res_put.status_code}) : {res_put.json().get('message', res_put.text)}")
            return False
        return True
    except Exception as e: 
        st.error(f"Erreur sauvegarde {file} : {e}")

def charger_data_safe(fichier):
    df = charger_data(fichier)
    if df is not None and not df.empty:
        return df
    return pd.DataFrame()

def charger_params():
    if 'params_vesta' in st.session_state:
        return st.session_state.params_vesta
    df = charger_data('params.json')
    if df is not None and not df.empty:
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
    sauvegarder_data(df_params, 'params.json')

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
menu = ["PLANNING","CROISIERES","CONTACTS","RELANCES","STATS", "MAINT", "LOG", "MEMOS", "FACT"]
icones = {"PLANNING": "📅", "CROISIERES": "⛵", "RELANCES": "🔔", "CONTACTS": "👤", "STATS": "📊", "MAINT": "🛠️", "LOG": "📖", "MEMOS": "📝", "FACT": "📑"}
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

# --- BLOC MEMOS INTEGRÉ DANS L'AIGUILLAGE GLOBAL ---
if st.session_state.page == "MEMOS":
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
# --- 5. BLOC CONTACTS (NOUVEAU MODÈLE — contacts_v2 / croisieres_v2 / interets_v2) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    afficher_page_contacts(
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        charger_interets=lambda: charger_data_safe('interets_v2.json').to_dict('records'),
        sauvegarder_contacts=lambda c: sauvegarder_data(pd.DataFrame(c), 'contacts_v2.json'),
    )

elif st.session_state.page == "MODIFIER_CONTACT":
    afficher_page_modifier_contact(
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
        sauvegarder_contacts=lambda c: sauvegarder_data(pd.DataFrame(c), 'contacts_v2.json'),
    )
# =================================================================
# --- 7. PAGE PLANNING (NOUVEAU MODÈLE — croisieres_v2 / etapes_v2) ---
# =================================================================
if st.session_state.page == "PLANNING":
    afficher_page_planning(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
        charger_params=charger_params,
    )
elif st.session_state.page == "CROISIERES":
    afficher_page_croisieres(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        sauvegarder_croisieres=lambda c: sauvegarder_data(pd.DataFrame(c), 'croisieres_v2.json'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
    )

elif st.session_state.page == "MODIFIER_CROISIERE":
    afficher_page_modifier_croisiere(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        sauvegarder_croisieres=lambda c: sauvegarder_data(pd.DataFrame(c), 'croisieres_v2.json'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
        sauvegarder_contacts=lambda c: sauvegarder_data(pd.DataFrame(c), 'contacts_v2.json'),
    )
# =================================================================
# --- 8. PAGE STATS (NOUVEAU MODÈLE — croisieres_v2 / etapes_v2) ---
# =================================================================
if st.session_state.page == "STATS":
    afficher_page_stats(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        charger_maintenance=lambda: charger_data_safe('maintenance.json'),
        charger_params=charger_params,
    )
# =================================================================
# --- 9. PAGE MAINT (heures moteur depuis etapes_v2) ---
# =================================================================
if st.session_state.page == "MAINT":
    afficher_page_maint(
        charger_maintenance=lambda: charger_data_safe('maintenance.json'),
        sauvegarder_maintenance=lambda df: sauvegarder_data(df, 'maintenance.json'),
        charger_carburant=lambda: charger_data_safe('carburant.json'),
        sauvegarder_carburant=lambda df: sauvegarder_data(df, 'carburant.json'),
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        charger_params=charger_params,
        sauvegarder_params=sauvegarder_params,
    )


# facturation
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =================================================================
# RELANCES
# =================================================================
if st.session_state.page == "RELANCES":
    afficher_page_relances(
        charger_interets=lambda: charger_data_safe('interets_v2.json').to_dict('records'),
        sauvegarder_interets=lambda i: sauvegarder_data(pd.DataFrame(i), 'interets_v2.json'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
    )

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
# --- 10. PAGE FACT (NOUVEAU MODÈLE — croisieres_v2) ---
# =================================================================
if st.session_state.page == "FACT":
    afficher_page_fact(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        sauvegarder_croisieres=lambda c: sauvegarder_data(pd.DataFrame(c), 'croisieres_v2.json'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
        envoyer_email=envoyer_email_facturation_cmn,
    )
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
            **Action irréversible :** Cela va basculer définitivement toutes les fiches marquées comme **'Paid'** vers le fichier d'archive. Les dossiers restés en 'Unpaid' resteront dans le tableau de bord actif.
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
# --- 10. PAGE LOG (NOUVEAU MODÈLE — etapes_v2 / croisieres_v2) ---
# =================================================================
if st.session_state.page == "LOG":
    afficher_page_log(
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        sauvegarder_etapes=lambda e: sauvegarder_data(pd.DataFrame(e), 'etapes_v2.json'),
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
    )


    # --- D. EXPORT EXCEL/CSV ---
    if not df_log.empty:
        st.divider()
        csv = df_log.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 Télécharger le Livre de Bord complet (.CSV)", data=csv, file_name='livre_de_bord_vesta.csv', mime='text/csv', use_container_width=True)






































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































