import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    .fiche-globale {
        background: white; border-radius: 15px; padding: 15px;
        margin-bottom: 20px; border-left: 8px solid #3498db;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .border-cmn { border-left: 8px solid #2980b9 !important; background: #f0f7ff; }
    .statut-badge {
        padding: 4px 10px; border-radius: 20px; color: white;
        font-size: 11px; font-weight: bold; margin-left: 5px;
    }
    .prenom-style { font-size: 20px; font-weight: bold; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DATA ---
def charger_data(file):
    cols_voulues = ['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Statut', 'Paiement', 'Prix', 'Notes', 'Téléphone', 'Email']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            # Sécurité : On ajoute les colonnes manquantes si elles n'existent pas
            for col in cols_voulues:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            pass
    return pd.DataFrame(columns=cols_voulues)

def sauvegarder_data(df, file):
    df.to_json(file, orient='records', indent=4)

# --- INITIALISATION ---
df_c = charger_data("contacts.json")

if 'page' not in st.session_state: st.session_state.page = "CONTACTS"
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'view_archive' not in st.session_state: st.session_state.view_archive = False
if 'confirm_del' not in st.session_state: st.session_state.confirm_del = None

# --- MENU LATÉRAL ---
with st.sidebar:
    st.title("⚓ Vesta Skipper")
    if st.button("👤 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.rerun()
    if st.button("📅 PLANNING", use_container_width=True): st.session_state.page = "PLANNING"; st.rerun()

# --- PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Mes Contacts")

    # Recherche
    search = st.text_input("🔍 Rechercher...", "").lower()

    # Bouton Ajout
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        new_row = {c: "" for c in df_c.columns}
        new_row.update({"Prénom": "Nouveau", "Nom": "Contact", "DateNav": datetime.now().strftime("%d/%m/2026"), "Statut": "En attente", "Paiement": "Pas payé"})
        df_c = pd.concat([pd.DataFrame([new_row]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # Logique Edition (Formulaire)
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx in df_c.index:
            r = df_c.loc[idx]
            with st.expander("📝 MODIFIER LES INFORMATIONS", expanded=True):
                u_pre = st.text_input("Prénom", value=r['Prénom'])
                u_nom = st.text_input("Nom", value=r['Nom'])
                u_soc = st.text_input("Société", value=r['Société'])
                u_tel = st.text_input("Téléphone", value=r['Téléphone'])
                u_mail = st.text_input("Email", value=r['Email'])
                u_date = st.text_input("Date Navigation", value=r['DateNav'])
                u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
                u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
                
                if st.button("💾 ENREGISTRER"):
                    df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'] = u_pre, u_nom
                    df_c.at[idx, 'Société'], df_c.at[idx, 'Téléphone'] = u_soc, u_tel
                    df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_mail, u_date
                    df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'] = u_stat, u_paye
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.edit_idx = None
                    st.rerun()

    # Tri et Filtrage
    df_filtered = df_c.copy()
    if search:
        df_filtered = df_filtered[df_filtered['Nom'].str.lower().str.contains(search, na=False) | 
                                 df_filtered['Prénom'].str.lower().str.contains(search, na=False)]

    # Affichage
    for idx, r in df_filtered.iterrows():
        # Sécurité affichage vide
        soc = r['Société'] if str(r['Société']).strip() != "" else "PARTICULIER"
        tel = r['Téléphone'] if str(r['Téléphone']).strip() != "" else "Non renseigné"
        mail = r['Email'] if str(r['Email']).strip() != "" else "Non renseigné"
        
        # Style
        color_paye = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        color_statut = "#2ecc71" if "OK" in str(r['Statut']).upper() else "#f1c40f"
        cl_b = "border-cmn" if "CMN" in str(soc).upper() else ""

        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} {str(r['Nom']).upper()}</div>
                <div style="color:gray; font-weight:bold;">🏛️ {soc}</div>
                <div style="margin:8px 0;">
                    📞 <b><a href="tel:{tel}" style="text-decoration:none; color:#2980b9;">{tel}</a></b><br>
                    ✉️ <i>{mail}</i>
                </div>
                <hr style="margin:10px 0; border:0; border-top:1px solid #eee;">
                <div style="display:flex; justify-content:space-between;">
                    <span>📅 <b>{r['DateNav']}</b></span>
                    <div>
                        <span class="statut-badge" style="background:{color_statut};">{r['Statut']}</span>
                        <span class="statut-badge" style="background:{color_paye};">{r['Paiement']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"✏️ MODIFIER", key=f"btn_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()


























































































































































































































































































































































































































































































