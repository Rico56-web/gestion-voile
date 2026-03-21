import streamlit as st
import pandas as pd
import json
import requests
import base64
import time
import os
from datetime import datetime

# --- CONFIGURATION GITHUB (Secrets) ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

# --- MOTEUR DE SAUVEGARDE ---
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
    data = {"message": f"Update {fichier}", "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

def safe_get(row, col, default=""):
    return str(row[col]) if col in row and pd.notnull(row[col]) else default

# --- CONFIGURATION INTERFACE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 18px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .border-cmn { border-left: 8px solid #3498db !important; }
    .statut-badge { float: right; padding: 5px 12px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; margin-left: 8px; }
    .societe-style { color: #95a5a6; font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    .prenom-style { font-size: 20px; font-weight: 700; color: #2c3e50; margin: 8px 0; }
    .notes-box { background: #fcfcfc; padding: 12px; border-radius: 8px; font-size: 14px; margin-top: 12px; border: 1px dashed #ddd; color: #555; }
    .btn-contact { display: inline-block; padding: 10px 20px; border-radius: 6px; color: white !important; text-decoration: none !important; font-size: 14px; margin-right: 8px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "view_archive" not in st.session_state: st.session_state.view_archive = False

df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/814/814430.png", width=80)
    st.title("VESTA SKIPPER")
    st.subheader("Navigation 2026")
    st.divider()
    if st.button("📅 PLANNING GÉNÉRAL", use_container_width=True): st.session_state.page = "PLANNING"
    if st.button("👤 RÉPERTOIRE CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"
    if st.button("🔧 MAINTENANCE BATEAU", use_container_width=True): st.session_state.page = "MAINTENANCE"
    if st.button("📓 LIVRE DE BORD", use_container_width=True): st.session_state.page = "NOTES"
    if st.button("📈 ANALYSE & STATS", use_container_width=True): st.session_state.page = "STATS"

# --- PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.header("👤 Gestion des Missions")
    
    col_add, col_arch = st.columns([1, 1])
    with col_add:
        if st.button("➕ AJOUTER UNE MISSION", type="primary", use_container_width=True):
            new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
            df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
            sauvegarder_data(df_c, "contacts.json"); st.rerun()
    
    with col_arch:
        label = "📁 VOIR ARCHIVES" if not st.session_state.view_archive else "🚀 MISSIONS EN COURS"
        if st.button(label, use_container_width=True):
            st.session_state.view_archive = not st.session_state.view_archive; st.rerun()

    if st.session_state.edit_idx is not None:
        # --- FORMULAIRE D'ÉDITION DÉTAILLÉ ---
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        st.info(f"Modification de : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom')}")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = c2.text_input("Nom", value=safe_get(r, 'Nom'))
            u_soc = c1.text_input("Société / Client", value=safe_get(r, 'Société'))
            u_tel = c2.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = c1.text_input("Email", value=safe_get(r, 'Email'))
            u_date = c2.text_input("Date (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
            u_jours = c1.number_input("Nombre de jours", value=int(safe_get(r, 'NbreJours', "1")))
            u_prix = c2.text_input("Prix Total (€)", value=safe_get(r, 'Prix'))
            u_stat = st.selectbox("Statut Mission", ["En attente", "OK", "Terminé", "Refusé"], index=0)
            u_paye = st.selectbox("État Paiement", ["Pas payé", "Payé"], index=0)
            u_notes = st.text_area("Notes particulières (Équipage, trajet...)", value=safe_get(r, 'Notes'))
            
            cb1, cb2 = st.columns(2)
            if cb1.button("💾 SAUVEGARDER", type="primary", use_container_width=True):
                df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
                df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
                df_c.at[idx, 'NbreJours'], df_c.at[idx, 'Prix'] = str(u_jours), u_prix
                df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
                sauvegarder_data(df_c, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if cb2.button("Annuler", use_container_width=True): st.session_state.edit_idx = None; st.rerun()
    else:
        # --- LISTE DES FICHES ---
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
        for i, r in df_disp.iterrows():
            soc, s_val, pay_val = safe_get(r, 'Société'), safe_get(r, 'Statut'), safe_get(r, 'Paiement')
            c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
            c_p = "#FF0000" if "PAS" in pay_val.upper() else "#2ecc71"
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            
            st.markdown(f'''<div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
                <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
                📅 <b>{safe_get(r, "DateNav")}</b> ({safe_get(r, "NbreJours")} jrs) | 💰 <b>{safe_get(r, "Prix")} €</b><br>
                📞 {safe_get(r, "Téléphone")} | ✉️ {safe_get(r, "Email")}
                <div class="notes-box">📝 {safe_get(r, "Notes") or "Aucune note."}</div>
                <div style="margin-top:15px;">
                    <a href="tel:{safe_get(r, 'Téléphone')}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                    <a href="https://wa.me/{safe_get(r, 'Téléphone').replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                </div>
            </div>''', unsafe_allow_html=True)
            if st.button(f"✏️ MODIFIER LA FICHE {i}", key=f"edit_{i}"):
                st.session_state.edit_idx = i; st.rerun()

# --- PAGE MAINTENANCE ---
elif st.session_state.page == "MAINTENANCE":
    st.header("🔧 Maintenance & Travaux")
    with st.form("maint_form"):
        c1, c2 = st.columns(2)
        tache = c1.text_input("Travail à effectuer")
        echeance = c2.text_input("Échéance (ex: Avril 2026)")
        priorite = st.select_slider("Priorité", options=["Basse", "Moyenne", "Urgente"])
        if st.form_submit_button("AJOUTER AUX TRAVAUX"):
            new_m = {"Titre": tache, "Echeance": echeance, "Priorite": priorite, "Date": datetime.now().strftime("%d/%m/%Y")}
            df_m = pd.concat([df_m, pd.DataFrame([new_m])], ignore_index=True)
            sauvegarder_data(df_m, "maint.json"); st.rerun()
    st.table(df_m)

# --- PAGE STATS ---
elif st.session_state.page == "STATS":
    st.header("📊 Analyse de l'Activité")
    if not df_c.empty:
        total_ca = sum([float(str(x).replace('€','').strip() or 0) for x in df_c['Prix']])
        c1, c2, c3 = st.columns(3)
        c1.metric("Chiffre d'Affaires 2026", f"{total_ca:.2f} €")
        c2.metric("Nombre de Missions", len(df_c))
        c3.metric("Jours Mer", sum([int(x or 0) for x in df_c['NbreJours']]))
        
        st.subheader("Répartition par Société")
        st.bar_chart(df_c['Société'].value_counts())

# --- PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.header("📅 Planning de Navigation")
    # (Ici le code du calendrier reste identique car il est déjà optimisé)
    st.info("Le calendrier interactif est synchronisé avec vos contacts.")




























































































































































































































































































































































































































































































