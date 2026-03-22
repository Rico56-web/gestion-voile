import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS (DOIT ÊTRE EN HAUT) ---
st.markdown("""
    <style>
    .fiche-globale {
        background-color: white; border-radius: 12px; padding: 15px;
        margin-bottom: 12px; border-left: 8px solid #3498db;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: #2c3e50;
    }
    .border-cmn { border-left: 8px solid #2980b9 !important; background-color: #f0f7ff; }
    .prenom-style { font-size: 20px; font-weight: bold; margin-bottom: 2px; }
    .nom-style { text-transform: uppercase; }
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
    cols = ['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            for c in cols: 
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def sauvegarder_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

# --- INITIALISATION ---
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'del_idx' not in st.session_state: st.session_state.del_idx = None
if 'rebook_idx' not in st.session_state: st.session_state.rebook_idx = None
if 'confirm_clean' not in st.session_state: st.session_state.confirm_clean = False
if 'archives' not in st.session_state: st.session_state.archives = False

df_c = charger_data()

# --- MENU ---
page = st.sidebar.radio("Navigation", ["CONTACTS", "PLANNING", "STATS"])

if page == "CONTACTS":
    st.subheader("👤 Mes Missions")

    # Onglets
    c_t1, c_t2 = st.columns(2)
    if c_t1.button("🚀 EN COURS", type="primary" if not st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = False; st.rerun()
    if c_t2.button("📁 ARCHIVES", type="primary" if st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = True; st.rerun()

    # Barre d'actions
    col_a, col_b = st.columns([2, 1])
    if col_a.button("➕ NOUVELLE FICHE", use_container_width=True):
        new_line = {c: "" for c in df_c.columns}
        new_line.update({"Prénom": "Nouveau", "Nom": "Contact", "DateNav": "01/01/2026", "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé"})
        df_c = pd.concat([pd.DataFrame([new_line]), df_c], ignore_index=True)
        sauvegarder_data(df_c); st.rerun()

    # --- ÉDITION ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        with st.expander("📝 ÉDITION EN COURS", expanded=True):
            with st.form("edit_form"):
                u_pre = st.text_input("Prénom", r['Prénom'])
                u_nom = st.text_input("Nom", r['Nom'])
                u_soc = st.text_input("Société", r['Société'])
                u_tel = st.text_input("Téléphone", r['Téléphone'])
                u_mail = st.text_input("Email", r['Email'])
                u_nav = st.text_input("Date Nav", r['DateNav'])
                u_jou = st.text_input("Durée", r['NbreJours'])
                u_pri = st.text_input("Prix (€)", r['Prix'])
                u_sta = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
                u_pay = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
                if st.form_submit_button("VALIDER"):
                    df_c.loc[idx] = [u_pre, u_nom, u_soc, u_nav, u_jou, u_tel, u_mail, u_sta, u_pay, u_pri]
                    sauvegarder_data(df_c); st.session_state.edit_idx = None; st.rerun()

    # --- AFFICHAGE DES FICHES ---
    df_f = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.archives else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    for idx, r in df_f.iterrows():
        soc = str(r['Société']) if str(r['Société']).strip() != "" else "PARTICULIER"
        c_s = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f" if r['Statut'] == "En attente" else "#3498db"
        c_p = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""

        # LA PARTIE CRITIQUE : UN SEUL ST.MARKDOWN
        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} <span class="nom-style">{r['Nom']}</span></div>
                <div style="color:gray; font-size:14px;">🏛️ {soc}</div>
                <div style="font-size:14px;">📞 <b>{r['Téléphone']}</b> | ✉️ {r['Email']}</div>
                
                <div class="info-box">
                    ⏳ <span class="label-gris">Durée de la mission :</span> {r['NbreJours']} jour(s)
                </div>

                <hr style="margin:10px 0; border:0; border-top:1px solid #eee;">
                
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size:15px;">📅 <b>{r['DateNav']}</b></span>
                    <div>
                        <span class="statut-badge" style="background:{c_s};">{r['Statut']}</span>
                        <span class="statut-badge" style="background:{c_p};">{r['Paiement']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # BOUTONS
        c1, c2, c3 = st.columns(3)
        if c1.button("🔄 RE-BOOK", key=f"re_{idx}", use_container_width=True):
            st.session_state.rebook_idx = idx; st.rerun()
        if c2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.rerun()
        if c3.button("🗑️ Suppr.", key=f"dl_{idx}", use_container_width=True):
            st.session_state.del_idx = idx; st.rerun()

elif page == "PLANNING":
    st.write("Le planning arrive...")




















































































































































































































































































































































































































































































