import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB (Indispensable) ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

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

# --- STYLE CSS (TES COULEURS) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .border-cmn { border: 3px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .societe-style { color: #7f8c8d; font-size: 12px; font-weight: bold; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px 0; }
    .notes-box { background: #f9f9f9; padding: 8px; border-radius: 5px; font-size: 13px; margin-top: 10px; border-left: 3px solid #ddd; }
    .btn-contact { display: inline-block; padding: 10px 15px; border-radius: 5px; color: white !important; text-decoration: none !important; font-size: 14px; margin-right: 5px; margin-top: 10px; font-weight: bold; }
    /* Style pour le nouveau menu horizontal */
    div.stButton > button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT ---
df_c = charger_data("contacts.json")
if "page" not in st.session_state: st.session_state.page = "PLANNING"

# --- NOUVEAU MENU HORIZONTAL (Pratique sur iPhone) ---
st.title("⚓ Vesta Skipper 2026")
m1, m2, m3, m4, m5 = st.columns(5)
if m1.button("📅 PLANN"): st.session_state.page = "PLANNING"
if m2.button("👤 CONT"): st.session_state.page = "CONTACTS"
if m3.button("🔧 MAINT"): st.session_state.page = "MAINTENANCE"
if m4.button("📝 NOTES"): st.session_state.page = "NOTES"
if m5.button("📊 STT"): st.session_state.page = "STATS"
st.divider()

# --- PAGE CONTACTS COMPLETÉE ---
if st.session_state.page == "CONTACTS":
    st.title("👤 Gestion des Contacts")
    
    # Bouton Nouveau Contact
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
        new = {
            "DateNav": datetime.now().strftime("%d/%m/2026"), 
            "NbreJours": "1", 
            "Statut": "En attente", 
            "Paiement": "Pas payé", 
            "Société": "", 
            "Prénom": "Nouveau", 
            "Nom": "Contact", 
            "Téléphone": "", 
            "Email": "", 
            "Prix": "0.00", 
            "Notes": ""
        }
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # Filtres Archives / Missions Futures
    c1, c2 = st.columns(2)
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    # --- MODE ÉDITION (LE FORMULAIRE COMPLET) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        st.subheader(f"📝 Modifier Mission #{idx + 1}")
        
        # On remet TOUS les champs de ton code original
        u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
        u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
        u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
        u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
        u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
        u_date = st.text_input("Date (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
        u_jours = st.text_input("Jours", value=safe_get(r, 'NbreJours'))
        u_prix = st.text_input("Prix (€)", value=safe_get(r, 'Prix'))
        
        # Listes déroulantes pour Statut et Paiement
        list_statut = ["En attente", "OK", "Terminé", "Refusé"]
        u_stat = st.selectbox("Statut", list_statut, index=list_statut.index(safe_get(r, 'Statut')) if safe_get(r, 'Statut') in list_statut else 0)
        
        list_paye = ["Pas payé", "Payé"]
        u_paye = st.selectbox("Paiement", list_paye, index=list_paye.index(safe_get(r, 'Paiement')) if safe_get(r, 'Paiement') in list_paye else 0)
        
        u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
        
        col_save, col_cancel = st.columns(2)
        if col_save.button("💾 ENREGISTRER", type="primary", use_container_width=True):
            df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
            df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
            df_c.at[idx, 'NbreJours'] = u_jours
            df_c.at[idx, 'Prix'] = f"{float(u_prix or 0):.2f}"
            df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
            sauvegarder_data(df_c, "contacts.json")
            st.session_state.edit_idx = None
            st.rerun()
        if col_cancel.button("Annuler", use_container_width=True):
            st.session_state.edit_idx = None
            st.rerun()

    # --- MODE AFFICHAGE DES FICHES ---
    else:
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
        
        for n, (i, r) in enumerate(df_disp.iterrows()):
            tel, mail, soc = safe_get(r, 'Téléphone'), safe_get(r, 'Email'), safe_get(r, 'Société')
            p_val, s_val, pay_val = f"{float(safe_get(r, 'Prix') or 0):.2f}", safe_get(r, 'Statut'), safe_get(r, 'Paiement')
            
            c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
            c_p = "#FF0000" if "PAS" in pay_val.upper() else "#2ecc71"
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            
            # La Fiche Visuelle
            st.markdown(f'''<div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
                <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                <div class="prenom-style">#{n+1} | {safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
                📅 <b>{safe_get(r, "DateNav")}</b> ({safe_get(r, "NbreJours")} jrs) | 💰 <b>{p_val} €</b><br>
                📞 {tel} | ✉️ {mail}
                <div class="notes-box">📝 {safe_get(r, "Notes") or "."}</div>
                <div class="container-boutons">
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="https://wa.me/{tel.replace(" ","")}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Mail</a>
                </div>
            </div>''', unsafe_allow_html=True)
            
            # Boutons Action (Modifier / Supprimer)
            if st.session_state.get('contact_confirm_del') == i:
                st.warning(f"⚠️ Supprimer la fiche #{n+1} ?")
                cy, cn = st.columns(2)
                if cy.button("✅ OUI", key=f"y_{i}"):
                    df_c = df_c.drop(i); sauvegarder_data(df_c, "contacts.json")
                    st.session_state.contact_confirm_del = None; st.rerun()
                if cn.button("NON", key=f"n_{i}"):
                    st.session_state.contact_confirm_del = None; st.rerun()
            else:
                c_edit, c_del = st.columns([1, 4])
                if c_edit.button("✏️", key=f"ed_{i}"): 
                    st.session_state.edit_idx = i; st.rerun()
                if c_del.button(f"🗑️ SUPPRIMER LA FICHE #{n+1}", key=f"del_{i}", use_container_width=True):
                    st.session_state.contact_confirm_del = i; st.rerun()


























































































































































































































































































































































































































































































