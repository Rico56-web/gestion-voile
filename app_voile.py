import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS (OPTIMISÉ MOBILE) ---
st.markdown("""
    <style>
    .fiche-globale {
        background-color: white; border-radius: 12px; padding: 15px;
        margin-bottom: 12px; border-left: 8px solid #3498db;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: #2c3e50;
    }
    .border-cmn { border-left: 8px solid #2980b9 !important; background-color: #f0f7ff; }
    .prenom-style { font-size: 20px; font-weight: bold; margin-bottom: 2px; }
    .statut-badge {
        padding: 4px 10px; border-radius: 15px; color: white;
        font-size: 11px; font-weight: bold; margin-left: 5px; display: inline-block;
    }
    .label-gris { color: #7f8c8d; font-size: 13px; font-weight: 500; }
    .info-box { background-color:#f9f9f9; padding:8px; border-radius:8px; margin:8px 0; font-size:13px; border: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DATA ---
def charger_data():
    file = "contacts.json"
    cols = ['Prénom', 'Nom', 'Société', 'DateNav', 'DateResa', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            for c in cols: 
                if c not in df.columns: df[c] = ""
            return df
        except: pass
    return pd.DataFrame(columns=cols)

def sauvegarder_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

# --- INITIALISATION ---
df_c = charger_data()
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'del_idx' not in st.session_state: st.session_state.del_idx = None
if 'archives' not in st.session_state: st.session_state.archives = False

# --- BARRE LATÉRALE ---
st.sidebar.title("⚓ Vesta Skipper")
page = st.sidebar.radio("Navigation", ["CONTACTS", "PLANNING", "STATS"])

# --- PAGE CONTACTS ---
if page == "CONTACTS":
    st.subheader("👤 Gestion des Navigations")

    # Onglets Actives / Archives
    c_t1, c_t2 = st.columns(2)
    if c_t1.button("🚀 EN COURS", type="primary" if not st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = False; st.rerun()
    if c_t2.button("📁 ARCHIVES", type="primary" if st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = True; st.rerun()

    # Bouton Nouveau & Archivage Auto
    col_a, col_b = st.columns([2, 1])
    if col_a.button("➕ NOUVEAU CONTACT", use_container_width=True):
        new_line = {c: "" for c in df_c.columns}
        new_line.update({"Prénom": "Nouveau", "Nom": "Contact", "DateNav": datetime.now().strftime("%d/%m/2026"), "DateResa": datetime.now().strftime("%d/%m/%Y"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé"})
        df_c = pd.concat([pd.DataFrame([new_line]), df_c], ignore_index=True)
        sauvegarder_data(df_c); st.rerun()

    if not st.session_state.archives:
        if col_b.button("🧹 NETTOYER", help="Archive les dossiers payés et passés", use_container_width=True):
            auj = datetime.now()
            def check_archive(row):
                try:
                    d_nav = datetime.strptime(str(row['DateNav']), "%d/%m/%Y")
                    if d_nav < auj and row['Paiement'] == "Payé" and row['Statut'] == "OK":
                        return "Terminé"
                except: pass
                return row['Statut']
            df_c['Statut'] = df_c.apply(check_archive, axis=1)
            sauvegarder_data(df_c); st.toast("Ménage terminé !"); time.sleep(1); st.rerun()

    # Formulaire de modification
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx in df_c.index:
            r = df_c.loc[idx]
            with st.expander(f"📝 MODIFIER : {r['Prénom']} {r['Nom']}", expanded=True):
                with st.form("edit_form"):
                    c1, c2 = st.columns(2)
                    u_pre = c1.text_input("Prénom", r['Prénom'])
                    u_nom = c2.text_input("Nom", r['Nom'])
                    u_soc = c1.text_input("Société", r['Société'])
                    u_tel = c2.text_input("Téléphone", r['Téléphone'])
                    u_nav = c1.text_input("Date Navigation", r['DateNav'])
                    u_res = c2.text_input("Date Réservation", r['DateResa'])
                    u_jou = c1.text_input("Nb Jours", r['NbreJours'])
                    u_pri = c2.text_input("Prix (€)", r['Prix'])
                    u_sta = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
                    u_pay = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
                    if st.form_submit_button("ENREGISTRER LES MODIFICATIONS", use_container_width=True):
                        df_c.loc[idx] = [u_pre, u_nom, u_soc, u_nav, u_res, u_jou, u_tel, r['Email'], u_sta, u_pay, u_pri]
                        sauvegarder_data(df_c); st.session_state.edit_idx = None; st.rerun()

    # Filtrage
    search = st.text_input("🔍 Rechercher un nom ou une société...", "").lower()
    df_f = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.archives else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    # Boucle d'affichage
    for idx, r in df_f.iterrows():
        if search and search not in str(r['Nom']).lower() and search not in str(r['Prénom']).lower() and search not in str(r['Société']).lower():
            continue
            
        soc = str(r['Société']) if str(r['Société']).strip() != "" else "PARTICULIER"
        color_s = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f" if r['Statut'] == "En attente" else "#3498db"
        color_p = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""

        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} {str(r['Nom']).upper()}</div>
                <div style="color:gray; font-size:14px;">🏛️ {soc}</div>
                <div style="margin:5px 0; font-size:14px;">📞 <b>{r['Téléphone']}</b></div>
                <div class="info-box">
                    📝 <span class="label-gris">Réservé le :</span> {r['DateResa'] if r['DateResa'] else "N/A"}<br>
                    ⏳ <span class="label-gris">Durée :</span> {r['NbreJours']} jour(s)
                </div>
                <hr style="margin:10px 0; border:0; border-top:1px solid #eee;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:14px;">📅 <b>{r['DateNav']}</b></span>
                    <div>
                        <span class="statut-badge" style="background:{color_s};">{r['Statut']}</span>
                        <span class="statut-badge" style="background:{color_p};">{r['Paiement']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Actions
        c1, c2, c3 = st.columns(3)
        if c1.button("🔄 RE-BOOK", key=f"re_{idx}", help="Dupliquer pour une nouvelle nav", use_container_width=True):
            new_nav = r.copy()
            new_nav.update({"DateNav": datetime.now().strftime("%d/%m/2026"), "Statut": "En attente", "Paiement": "Pas payé"})
            df_c = pd.concat([pd.DataFrame([new_nav]), df_c], ignore_index=True)
            sauvegarder_data(df_c); st.rerun()
        
        if c2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.rerun()

        if st.session_state.del_idx == idx:
            if c3.button("✅ OK ?", key=f"cf_{idx}", type="primary", use_container_width=True):
                df_c = df_c.drop(idx).reset_index(drop=True); sauvegarder_data(df_c)
                st.session_state.del_idx = None; st.rerun()
        elif c3.button("🗑️ Suppr.", key=f"dl_{idx}", use_container_width=True):
            st.session_state.del_idx = idx; st.rerun()

elif page == "PLANNING":
    st.subheader("📅 Calendrier des Navigations")
    st.write("Module prêt. Voulez-vous que j'ajoute le calendrier visuel ici ?")
























































































































































































































































































































































































































































































