import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- CSS (Sécurisé) ---
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

# --- FONCTIONS ---
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

# --- PAGE CONTACTS ---
st.sidebar.title("⚓ Vesta 2026")
page = st.sidebar.radio("Navigation", ["CONTACTS", "PLANNING"])

if page == "CONTACTS":
    st.subheader("👤 Mes Fiches")
    
    # Boutons d'onglet
    c_t1, c_t2 = st.columns(2)
    if c_t1.button("🚀 ACTIVES", type="primary" if not st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = False; st.rerun()
    if c_t2.button("📁 ARCHIVES", type="primary" if st.session_state.archives else "secondary", use_container_width=True):
        st.session_state.archives = True; st.rerun()

    # Formulaire de modification
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        with st.expander("📝 MODIFIER LA FICHE", expanded=True):
            with st.form("edit_f"):
                u_pre = st.text_input("Prénom", r['Prénom'])
                u_nom = st.text_input("Nom", r['Nom'])
                u_soc = st.text_input("Société", r['Société'])
                u_tel = st.text_input("Téléphone", r['Téléphone'])
                u_mail = st.text_input("Email", r['Email'])
                u_nav = st.text_input("Date Nav", r['DateNav'])
                u_res = st.text_input("Date Résa", r['DateResa'])
                u_j = st.text_input("Nombre Jours", r['NbreJours'])
                u_st = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
                u_pa = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
                
                if st.form_submit_button("SAUVEGARDER"):
                    df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'] = u_pre, u_nom
                    df_c.at[idx, 'Société'], df_c.at[idx, 'Téléphone'] = u_soc, u_tel
                    df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_mail, u_nav
                    df_c.at[idx, 'DateResa'], df_c.at[idx, 'NbreJours'] = u_res, u_j
                    df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'] = u_st, u_pa
                    sauvegarder_data(df_c); st.session_state.edit_idx = None; st.rerun()

    # Liste des fiches
    df_f = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.archives else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    for idx, r in df_f.iterrows():
        color_s = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f" if r['Statut'] == "En attente" else "#3498db"
        color_p = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        cl_b = "border-cmn" if "CMN" in str(r['Société']).upper() else ""
        d_res = r['DateResa'] if str(r['DateResa']).strip() != "" else "Non précisée"

        # --- L'AFFICHAGE (CRITIQUE : unsafe_allow_html=True) ---
        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} {str(r['Nom']).upper()}</div>
                <div style="color:gray; font-size:14px;">🏛️ {r['Société'] if r['Société'] else "PARTICULIER"}</div>
                <div style="margin:5px 0; font-size:14px;">📞 {r['Téléphone']} | ✉️ {r['Email']}</div>
                <div class="info-box">
                    📝 <span class="label-gris">Réservé le :</span> {d_res}<br>
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
        
        c1, c2 = st.columns(2)
        if c1.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.rerun()
        
        if st.session_state.del_idx == idx:
            if c2.button("✅ CONFIRMER", key=f"conf_{idx}", type="primary", use_container_width=True):
                df_c = df_c.drop(idx).reset_index(drop=True); sauvegarder_data(df_c)
                st.session_state.del_idx = None; st.rerun()
        else:
            if c2.button("🗑️ Supprimer", key=f"del_{idx}", use_container_width=True):
                st.session_state.del_idx = idx; st.rerun()

elif page == "PLANNING":
    st.title("📅 Planning")
    st.write("Le calendrier sera ici.")
























































































































































































































































































































































































































































































