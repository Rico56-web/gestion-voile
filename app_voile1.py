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
menu = ["PLANNING","CROISIERES","CONTACTS", "STATS", "MAINT", "LOG", "MEMOS", "FACT"]
icones = {"PLANNING": "📅", "CROISIERES": "⛵", "CONTACTS": "👤", "STATS": "📊", "MAINT": "🛠️", "LOG": "📖", "MEMOS": "📝", "FACT": "📑"}
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
                    
                    # FIX DE SÉCURITÉ : Vérification de la présence de la clé 'email' dans les secrets
                    if "email" in st.secrets and "email_destinataire" in st.secrets["email"]:
                        email_defaut_cmn = st.secrets["email"]["email_destinataire"]
                    else:
                        email_defaut_cmn = "compta.cmn@exemple.com"
                    
                    # Champ modifiable pour faire des essais
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
                    df_calc = df_log.copy()
                    df_calc['dt_temp'] = pd.to_datetime(df_calc['Date'], dayfirst=True, errors='coerce')
                    df_calc = df_calc.dropna(subset=['dt_temp'])
                    
                    if not df_calc.empty:
                        derniere_etape = df_calc.loc[df_calc['dt_temp'].idxmax()]
                        date_derniere = derniere_etape['dt_temp']
                        date_actuelle = pd.Timestamp.now().normalize()
                        
                        if (date_actuelle - date_derniere).days < 5:
                            val_nav = derniere_etape.get('Navigation', '')
                except:
                    val_nav = ""
            
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






































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































