import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

# --- FONCTIONS UTILES ---
def safe_get(row, key, default=""):
    return row[key] if key in row and pd.notnull(row[key]) else default

def charger_data(fichier):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
        res = requests.get(url, headers={"Authorization": f"token {TOKEN}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, fichier):
    url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    sha = res.json()['sha'] if res.status_code == 200 else None
    content = json.dumps(df.to_dict(orient="records"), indent=4, ensure_ascii=False)
    data = {"message": f"Maj {fichier}", "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

# --- CONFIGURATION PAGE & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .border-cmn { border-left: 8px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; }
    .btn-contact { display: inline-block; padding: 12px; border-radius: 8px; color: white !important; text-decoration: none; font-size: 14px; font-weight: bold; text-align: center; width: 30%; }
    /* Optimisation iPhone : gros boutons */
    div.stButton > button { height: 3.5em; border-radius: 10px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "view_archive" not in st.session_state: st.session_state.view_archive = False

df_c = charger_data("contacts.json")

# --- MENU PRINCIPAL (Adapté Mobile) ---
st.title("⚓ Vesta Skipper 2026")
cols = st.columns(5)
menu = ["PLANNING", "CONTACTS", "MAINTENANCE", "NOTES", "STATS"]
labels = ["📅 Plann", "👤 Cont", "🔧 Maint", "📝 Notes", "📊 Stat"]
for i, m in enumerate(menu):
    if cols[i].button(labels[i]): st.session_state.page = m

st.divider()

# --- MODULE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Gestion des Contacts & Clients")
    
    # 🔍 RECHERCHE
    search = st.text_input("🔍 Rechercher un nom, prénom ou société...", "").lower()
    
    # Bouton Ajout
    if st.button("➕ NOUVEAU CONTACT / NAVIGATION", use_container_width=True):
        new_row = {"Prénom": "Nouveau", "Nom": "Contact", "Société": "", "DateNav": datetime.now().strftime("%d/%m/2026"), 
                   "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Prix": "0.00", "Notes": "", "Téléphone": "", "Email": ""}
        df_c = pd.concat([pd.DataFrame([new_row]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # --- LOGIQUE D'ÉDITION (FORMULAIRE) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        st.markdown("### 📝 Modification & Historique")
        
        with st.expander("Modifier les informations", expanded=True):
            col1, col2 = st.columns(2)
            u_pre = col1.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = col2.text_input("Nom", value=safe_get(r, 'Nom'))
            u_soc = col1.text_input("Société (Mettre CMN pour le bleu)", value=safe_get(r, 'Société'))
            u_tel = col2.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = col1.text_input("Email", value=safe_get(r, 'Email'))
            u_date = col2.text_input("Date (JJ/MM/2026)", value=safe_get(r, 'DateNav'))
            u_jours = col1.text_input("Nombre de jours", value=safe_get(r, 'NbreJours'))
            u_prix = col2.text_input("Prix total (€)", value=safe_get(r, 'Prix'))
            
            u_stat = st.selectbox("Statut Mission", ["En attente", "OK", "Terminé", "Refusé"], 
                                 index=["En attente", "OK", "Terminé", "Refusé"].index(r['Statut']) if r['Statut'] in ["En attente", "OK", "Terminé", "Refusé"] else 0)
            u_paye = st.selectbox("Statut Paiement", ["Pas payé", "Payé"], 
                                 index=0 if r['Paiement'] == "Pas payé" else 1)
            u_notes = st.text_area("Notes / Commentaires", value=safe_get(r, 'Notes'))

            c_save, c_annul = st.columns(2)
            if c_save.button("💾 ENREGISTRER LES MODIFICATIONS", type="primary", use_container_width=True):
                df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
                df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
                df_c.at[idx, 'NbreJours'], df_c.at[idx, 'Prix'] = u_jours, u_prix
                df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.edit_idx = None
                st.success("Modification enregistrée !")
                time.sleep(1)
                st.rerun()
            
            if c_annul.button("Annuler", use_container_width=True):
                st.session_state.edit_idx = None
                st.rerun()

        # --- AFFICHAGE HISTORIQUE (Navigations liées au même nom) ---
        st.markdown("#### 📜 Historique des navigations de ce client")
        hist = df_c[(df_c['Nom'] == r['Nom']) & (df_c['Prénom'] == r['Prénom'])]
        st.table(hist[['DateNav', 'NbreJours', 'Statut', 'Prix', 'Paiement']])
        st.divider()

    # --- AFFICHAGE DE LA LISTE ---
    t1, t2 = st.columns(2)
    if t1.button("🚀 EN COURS", type="primary" if not st.session_state.view_archive else "secondary", use_container_width=True):
        st.session_state.view_archive = False; st.rerun()
    if t2.button("📁 ARCHIVÉS", type="primary" if st.session_state.view_archive else "secondary", use_container_width=True):
        st.session_state.view_archive = True; st.rerun()

    df_filtered = df_c.copy()
    if search:
        df_filtered = df_filtered[
            df_filtered['Nom'].str.lower().str.contains(search, na=False) | 
            df_filtered['Prénom'].str.lower().str.contains(search, na=False) | 
            df_filtered['Société'].str.lower().str.contains(search, na=False)
        ]
    
    if st.session_state.view_archive:
        df_disp = df_filtered[df_filtered['Statut'].isin(["Terminé", "Refusé"])]
    else:
        df_disp = df_filtered[~df_filtered['Statut'].isin(["Terminé", "Refusé"])]

 # --- BLOC BOUTONS ACTIONS (MODIFIER & SUPPRIMER) ---
        c_ed, c_del = st.columns([1, 1])
        
        # Bouton Modifier
        if c_ed.button(f"✏️ MODIFIER / HISTORIQUE", key=f"btn_ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()
            
        # Bouton Supprimer avec Confirmation
        if st.session_state.get('confirm_del') == idx:
            st.warning(f"⚠️ Supprimer définitivement #{idx} ?")
            col_y, col_n = st.columns(2)
            if col_y.button("✅ OUI", key=f"conf_y_{idx}", use_container_width=True):
                df_c = df_c.drop(idx)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.confirm_del = None
                st.success("Fiche supprimée")
                time.sleep(1)
                st.rerun()
            if col_n.button("NON", key=f"conf_n_{idx}", use_container_width=True):
                st.session_state.confirm_del = None
                st.rerun()
        else:
            if c_del.button(f"🗑️ SUPPRIMER", key=f"btn_del_{idx}", use_container_width=True):
                st.session_state.confirm_del = idx
                st.rerun()
        
        # Fidélité
        nb_nav = len(df_c[(df_c['Nom'] == r['Nom']) & (df_c['Prénom'] == r['Prénom'])])
        badge_fid = f"<span style='color:#f39c12; font-weight:bold;'>⭐ Fidèle ({nb_nav} nav.)</span>" if nb_nav > 1 else ""

        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{color_paye};">{r['Paiement']}</span>
                <span class="statut-badge" style="background:{color_statut};">{r['Statut']}</span>
                <div style="font-size:12px; color:gray;">{soc if soc else "PARTICULIER"} {badge_fid}</div>
                <div class="prenom-style">{r['Prénom']} {r['Nom'].upper()}</div>
                📞 <b>{r['Téléphone']}</b> | ✉️ <i>{r['Email']}</i><br>
                📅 <b>{r['DateNav']}</b> ({r['NbreJours']}j) | 💰 <b>{r['Prix']}€</b>
                <div style="margin-top:10px; display: flex; justify-content: space-between;">
                    <a href="tel:{r['Téléphone']}" class="btn-contact" style="background:#3498db;">Appel</a>
                    <a href="https://wa.me/{str(r['Téléphone']).replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                    <a href="mailto:{r['Email']}" class="btn-contact" style="background:#e67e22;">Mail</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"✏️ MODIFIER / HISTORIQUE #{idx}", key=f"btn_ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()

# --- MODULE STATS (Calculs automatiques) ---
if st.session_state.page == "STATS":
    st.subheader("📊 Bilan Financier Mensuel")
    df_c['Prix'] = pd.to_numeric(df_c['Prix'], errors='coerce').fillna(0)
    
    # Logique de calcul
    recettes = df_c[(df_c['Statut'] == "OK") & (df_c['Paiement'] == "Payé")]['Prix'].sum()
    previsions = df_c[(df_c['Paiement'] == "Pas payé")]['Prix'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Recettes (Encaissé)", f"{recettes:.2f} €")
    c2.metric("Prévisionnel (À recevoir)", f"{previsions:.2f} €")
    c3.metric("Bilan Total", f"{(recettes + previsions):.2f} €", delta_color="normal")

    st.info("Les données de Maintenance seront déduites ici une fois le module complété.")


























































































































































































































































































































































































































































































