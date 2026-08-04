import requests, base64, io
import streamlit as st
import pandas as pd
from datetime import datetime
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
from page_archives import afficher_page_archives
# =================================================================
# --- CONFIGURATION & STYLE REGROUPÉS ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- INITIALISATION DU SESSION STATE ---
if 'page' not in st.session_state: st.session_state.page = "PLANNING"
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
            df = pd.read_json(io.BytesIO(decoded_bytes), orient="records", convert_dates=False)
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

# --- FONCTION UNIQUE DE CHANGEMENT DE PAGE (ÉVITE LES CONFLITS) ---
def changer_page(nom_page):
    st.session_state.page = nom_page
    st.session_state.maint_edit_id = None
    st.session_state.show_form_classique = False
    st.session_state.show_form_vidange = False
    st.session_state.log_edit_id = None
    st.session_state.log_saisie_ouverte = False
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
# 1. Barre de navigation horizontale (Haut) — menus déroulants, compacts sur mobile
THEMES = {
    "🧭 Navigation": ["PLANNING", "CROISIERES", "LOG"],
    "👥 Gestion": ["CONTACTS", "RELANCES", "FACT"],
    "🛠️ Bord": ["MAINT", "STATS", "MEMOS"],
}

theme_de_la_page_active = next((t for t, pages in THEMES.items() if st.session_state.page in pages), "🧭 Navigation")
if "theme_selectionne" not in st.session_state or st.session_state.page in sum(THEMES.values(), []):
    st.session_state.theme_selectionne = theme_de_la_page_active

col_theme, col_page = st.columns(2)
theme_choisi = col_theme.selectbox("Thème", list(THEMES.keys()),
                                    index=list(THEMES.keys()).index(st.session_state.theme_selectionne),
                                    key="select_theme", label_visibility="collapsed")
st.session_state.theme_selectionne = theme_choisi

pages_du_theme = THEMES[theme_choisi]
page_par_defaut = st.session_state.page if st.session_state.page in pages_du_theme else pages_du_theme[0]
page_choisie = col_page.selectbox(
    "Page", pages_du_theme,
    index=pages_du_theme.index(page_par_defaut),
    format_func=lambda name: f"{icones[name]} {name}",
    key="select_page", label_visibility="collapsed",
)
if page_choisie != st.session_state.page:
    changer_page(page_choisie)
    
THEME_COULEURS = {"🧭 Navigation": "#2980B9", "👥 Gestion": "#27AE60", "🛠️ Bord": "#E67E22"}
couleur_theme = THEME_COULEURS[theme_choisi]
st.markdown(
    f"""<div style="background:{couleur_theme}; color:white; padding:8px 16px; border-radius:8px;
    margin-top:6px; text-align:center; font-weight:bold;">
    {theme_choisi} &nbsp;→&nbsp; {icones[st.session_state.page]} {st.session_state.page}</div>""",
    unsafe_allow_html=True,
)
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
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
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
    """Gère l'envoi de l'email via le protocole sécurisé TLS, avec une copie automatique."""
    try:
        cfg = st.secrets["email"]
        
        if destinataire is None:
            destinataire = cfg["email_destinataire"]
        
        copie_auto = "eric.clavreul@gmail.com"
        
        msg = MIMEMultipart()
        msg['From'] = cfg["smtp_user"]
        msg['To'] = destinataire
        msg['Cc'] = copie_auto
        msg['Subject'] = f"🧾 Facturation Vesta Skipper - Prestations CMN ({mois_annee})"
        
        msg.attach(MIMEText(corps_texte, 'html'))
        
        server = smtplib.SMTP(cfg["smtp_server"], int(cfg["smtp_port"]))
        server.starttls()
        server.login(cfg["smtp_user"], cfg["smtp_password"])
        server.sendmail(cfg["smtp_user"], [destinataire, copie_auto], msg.as_string())
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
# --- 11. PAGE ARCHIVES (consultation par période, rien n'est déplacé) ---
# =================================================================
if st.session_state.page == "ARCHIVES":
    afficher_page_archives(
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        charger_maintenance=lambda: charger_data_safe('maintenance.json'),
        charger_contacts=lambda: charger_data_safe('contacts_v2.json').to_dict('records'),
    )
# =================================================================
# --- 10. PAGE LOG (NOUVEAU MODÈLE — etapes_v2 / croisieres_v2) ---
# =================================================================
if st.session_state.page == "LOG":
    afficher_page_log(
        charger_etapes=lambda: charger_data_safe('etapes_v2.json').to_dict('records'),
        sauvegarder_etapes=lambda e: sauvegarder_data(pd.DataFrame(e), 'etapes_v2.json'),
        charger_croisieres=lambda: charger_data_safe('croisieres_v2.json').to_dict('records'),
    )
