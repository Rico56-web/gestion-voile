import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import time

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS OPTIMISÉ IPHONE ---
st.markdown("""
    <style>
    .fiche-globale {
        background: #ffffff; border-radius: 15px; padding: 15px;
        margin-bottom: 20px; border-left: 8px solid #3498db;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .border-cmn { border-left: 8px solid #2980b9 !important; background: #f0f7ff; }
    .statut-badge {
        padding: 5px 12px; border-radius: 20px; color: white;
        font-size: 12px; font-weight: bold; margin-left: 5px;
        display: inline-block;
    }
    .prenom-style { font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 2px; }
    .info-label { color: #7f8c8d; font-size: 14px; margin-bottom: 5px; }
    .contact-link { text-decoration: none; color: #2980b9; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DATA ---
def charger_data(file):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                return pd.DataFrame(data)
        except:
            pass
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Statut', 'Paiement', 'Prix', 'Notes', 'Téléphone', 'Email'])

def sauvegarder_data(df, file):
    df.to_json(file, orient='records', indent=4)

def safe_get(row, col):
    if col in row and pd.notnull(row[col]):
        val = str(row[col]).strip()
        return val if val != "" else "Non renseigné"
    return "Non renseigné"

# --- INITIALISATION ET ETAT ---
df_c = charger_data("contacts.json")

if 'page' not in st.session_state: st.session_state.page = "CONTACTS"
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'view_archive' not in st.session_state: st.session_state.view_archive = False
if 'confirm_del' not in st.session_state: st.session_state.confirm_del = None

# --- MENU LATÉRAL ---
with st.sidebar:
    st.title("⚓ Vesta Skipper 2026")
    if st.button("👤 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.rerun()
    if st.button("📅 PLANNING", use_container_width=True): st.session_state.page = "PLANNING"; st.rerun()
    if st.button("📊 STATS", use_container_width=True): st.session_state.page = "STATS"; st.rerun()

# --- PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.subheader("👤 Mes Navigations & Contacts")

    # 1. RECHERCHE (Tout en haut)
    search = st.text_input("🔍 Rechercher (Nom, Société...)", "").lower()

    # 2. BOUTON AJOUT
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        new_row = {"Prénom": "Nouveau", "Nom": "Contact", "Société": "", "DateNav": datetime.now().strftime("%d/%m/2026"), 
                   "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Prix": "0.00", "Notes": "", "Téléphone": "", "Email": ""}
        df_c = pd.concat([pd.DataFrame([new_row]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # 3. FORMULAIRE D'ÉDITION (Si actif)
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx in df_c.index:
            r = df_c.loc[idx]
            with st.expander(f"📝 MODIFIER : {r['Prénom']} {r['Nom']}", expanded=True):
                c1, c2 = st.columns(2)
                u_pre = c1.text_input("Prénom", value=r['Prénom'])
                u_nom = c2.text_input("Nom", value=r['Nom'])
                u_soc = c1.text_input("Société", value=r['Société'])
                u_tel = c2.text_input("Téléphone", value=r['Téléphone'])
                u_mail = c1.text_input("Email", value=r['Email'])
                u_date = c2.text_input("Date (JJ/MM/2026)", value=r['DateNav'])
                u_prix = c1.text_input("Prix (€)", value=r['Prix'])
                u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                     index=["En attente", "OK", "Terminé", "Refusé"].index(r['Statut']) if r['Statut'] in ["En attente", "OK", "Terminé", "Refusé"] else 0)
                u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if r['Paiement']=="Payé" else 0)
                u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
                
                col_b1, col_b2 = st.columns(2)
                if col_b1.button("💾 ENREGISTRER", type="primary", use_container_width=True):
                    df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'] = u_pre, u_nom
                    df_c.at[idx, 'Société'], df_c.at[idx, 'Téléphone'] = u_soc, u_tel
                    df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_mail, u_date
                    df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'] = u_stat, u_paye
                    df_c.at[idx, 'Prix'], df_c.at[idx, 'Notes'] = u_prix, u_notes
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.edit_idx = None
                    st.rerun()
                if col_b2.button("Annuler", use_container_width=True):
                    st.session_state.edit_idx = None
                    st.rerun()

    # 4. TRI ET FILTRAGE
    df_filtered = df_c.copy()
    if not df_filtered.empty:
        df_filtered['date_tri'] = pd.to_datetime(df_filtered['DateNav'], format='%d/%m/%Y', errors='coerce')
        df_filtered = df_filtered.sort_values(by='date_tri', ascending=True)
        
        if search:
            df_filtered = df_filtered[df_filtered['Nom'].str.lower().str.contains(search, na=False) | 
                                    df_filtered['Prénom'].str.lower().str.contains(search, na=False) |
                                    df_filtered['Société'].str.lower().str.contains(search, na=False)]

    # 5. ONGLETS EN COURS / ARCHIVES
    t1, t2 = st.columns(2)
    if t1.button("🚀 EN COURS", type="primary" if not st.session_state.view_archive else "secondary", use_container_width=True, key="tab_active"):
        st.session_state.view_archive = False; st.rerun()
    if t2.button("📁 ARCHIVÉS", type="primary" if st.session_state.view_archive else "secondary", use_container_width=True, key="tab_arch"):
        st.session_state.view_archive = True; st.rerun()

    df_disp = df_filtered[df_filtered['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_filtered[~df_filtered['Statut'].isin(["Terminé", "Refusé"])]

    # 6. BOUCLE D'AFFICHAGE DES FICHES
    for idx, r in df_disp.iterrows():
        # Préparation des données propres
        soc = safe_get(r, 'Société')
        tel = safe_get(r, 'Téléphone')
        mail = safe_get(r, 'Email')
        
        # Couleurs badges
        color_paye = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        s_val = str(r['Statut']).upper()
        color_statut = "#2ecc71" if "OK" in s_val else "#f1c40f" if "ATTENT" in s_val else "#3498db"
        cl_b = "border-cmn" if "CMN" in str(soc).upper() else ""
        
        # --- STRUCTURE DE LA FICHE (ORDRE DEMANDÉ) ---
        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} {r['Nom'].upper()}</div>
                <div class="info-label">🏛️ {soc if soc != "Non renseigné" else "PARTICULIER"}</div>
                
                <div style="margin: 8px 0;">
                    📞 <b><a href="tel:{tel}" class="contact-link">{tel}</a></b><br>
                    ✉️ <i>{mail}</i>
                </div>
                
                <hr style="margin: 10px 0; border: 0; border-top: 1px solid #eee;">
                
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span>📅 <b>{r['DateNav']}</b></span>
                    <div>
                        <span class="statut-badge" style="background:{color_statut};">{r['Statut']}</span>
                        <span class="statut-badge" style="background:{color_paye};">{r['Paiement']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Boutons Actions
        c_ed, c_del = st.columns(2)
        if c_ed.button(f"✏️ MODIFIER", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.rerun()
            
        if st.session_state.get('confirm_del') == idx:
            st.warning("Confirmer suppression ?")
            cy, cn = st.columns(2)
            if cy.button("OUI ✅", key=f"conf_{idx}", use_container_width=True):
                df_c = df_c.drop(idx); sauvegarder_data(df_c, "contacts.json")
                st.session_state.confirm_del = None; st.rerun()
            if cn.button("NON", key=f"ann_{idx}", use_container_width=True):
                st.session_state.confirm_del = None; st.rerun()
        else:
            if c_del.button(f"🗑️ SUPPRIMER", key=f"del_{idx}", use_container_width=True):
                st.session_state.confirm_del = idx; st.rerun()

# --- AUTRES PAGES ---
if st.session_state.page == "PLANNING":
    st.subheader("📅 Planning 2026")
    st.info("Module Planning prêt pour injection.")

if st.session_state.page == "STATS":
    st.subheader("📊 Statistiques")
    st.metric("Total Navigations", len(df_c))


























































































































































































































































































































































































































































































