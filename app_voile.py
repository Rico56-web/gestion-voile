import streamlit as st
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- DATA (Avec nouveaux champs 'Notes' et 'NbreJours') ---
def charger_data():
    file = "contacts.json"
    cols = ['Prénom', 'Nom', 'Société', 'DateResa', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Notes']
    if os.path.exists(file):
        df = pd.read_json(file)
        # S'assurer que les colonnes existent (pour les anciens fichiers)
        for c in cols:
            if c not in df.columns: df[c] = ""
        return df[cols].fillna("")
    return pd.DataFrame(columns=cols)

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- ÉTATS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "show_new" not in st.session_state: st.session_state.show_new = False

st.title("⚓ Missions & Clients")

# --- 1. BOUTON NOUVELLE MISSION ---
if not st.session_state.show_new and st.session_state.edit_idx is None:
    if st.button("➕ NOUVELLE MISSION", type="primary", use_container_width=True):
        st.session_state.show_new = True
        st.rerun()

# --- 2. FORMULAIRE (NOUVEAU / ÉDITION) ---
if st.session_state.show_new or st.session_state.edit_idx is not None:
    is_edit = st.session_state.edit_idx is not None
    idx = st.session_state.edit_idx
    val = df.iloc[idx] if is_edit else None
    
    with st.container(border=True):
        st.subheader("📝 " + ("Modifier la mission" if is_edit else "Nouvelle mission"))
        with st.form("mission_form"):
            c1, c2, c3 = st.columns(3)
            f_pre = c1.text_input("Prénom", val['Prénom'] if is_edit else "")
            f_nom = c2.text_input("Nom", val['Nom'] if is_edit else "")
            f_soc = c3.text_input("Société (CMN...)", val['Société'] if is_edit else "")
            
            c4, c5, c6 = st.columns(3)
            f_tel = c4.text_input("Téléphone", val['Téléphone'] if is_edit else "")
            f_mai = c5.text_input("Email", val['Email'] if is_edit else "")
            f_jou = c6.number_input("Nombre de jours", value=int(val['NbreJours']) if is_edit and str(val['NbreJours']).isdigit() else 1)
            
            c7, c8 = st.columns(2)
            f_dna = c7.text_input("Date Navigation", val['DateNav'] if is_edit else "")
            f_dre = c8.text_input("Date Réservation", val['DateResa'] if is_edit else "")
            
            f_not = st.text_area("Notes (Détails, trajet, spécifique...)", val['Notes'] if is_edit else "")
            
            c9, c10 = st.columns(2)
            f_sta = c9.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                 index=["En attente", "OK", "Terminé", "Refusé"].index(val['Statut']) if is_edit else 0)
            f_pay = c10.selectbox("Paiement", ["Pas payé", "Payé"], 
                                  index=1 if is_edit and val['Paiement'] == "Payé" else 0)
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = [f_pre, f_nom, f_soc, f_dre, f_dna, f_jou, f_tel, f_mai, f_sta, f_pay, f_not]
                if is_edit:
                    df.loc[idx] = new_row
                else:
                    df.loc[len(df)] = new_row
                sauver_data(df)
                st.session_state.show_new = False
                st.session_state.edit_idx = None
                st.rerun()
        
        if st.button("❌ ANNULER"):
            st.session_state.show_new = False
            st.session_state.edit_idx = None
            st.rerun()

# --- 3. AFFICHAGE DES FICHES ---
t1, t2 = st.tabs(["🚀 EN COURS", "📁 ARCHIVES"])

def afficher_liste(df_filtre):
    for idx, r in df_filtre.iterrows():
        # Préparation WhatsApp
        tel_clean = str(r['Téléphone']).replace(" ", "").replace("+", "")
        wa_link = f"https://wa.me/{tel_clean}"
        
        # Couleur bordure
        border_col = "#2ecc71" if r['Statut'] == "OK" else "#3498db"
        if r['Statut'] in ["Terminé", "Refusé"]: border_col = "#95a5a6"

        st.markdown(f"""
            <div style="border-left: 15px solid {border_col}; background: white; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size: 20px; font-weight: bold; color: #1e3a5f;">{r['Prénom']} {str(r['Nom']).upper()}</span>
                    <span style="font-size: 14px; font-weight: bold;">📅 {r['DateNav']}</span>
                </div>
                <div style="font-size: 13px; color: #7f8c8d; margin-bottom: 5px;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'} | ⏱️ {r['NbreJours']} jour(s)</div>
                
                <div style="margin: 10px 0; display: flex; gap: 15px;">
                    <a href="tel:{r['Téléphone']}" style="text-decoration:none; color:#2980b9; font-weight:bold;">📞 {r['Téléphone']}</a>
                    <a href="{wa_link}" target="_blank" style="text-decoration:none; color:#27ae60; font-weight:bold;">💬 WhatsApp</a>
                    <a href="mailto:{r['Email']}" style="text-decoration:none; color:#e67e22; font-weight:bold;">✉️ Email</a>
                </div>
                
                <div style="background: #f8f9fa; padding: 8px; border-radius: 5px; font-size: 12px; font-style: italic; color: #34495e; margin-bottom: 10px;">
                    <b>Note :</b> {r['Notes'] if r['Notes'] else 'Aucune note.'}
                </div>

                <div>
                    <span style="background: {border_col}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Statut']}</span>
                    <span style="background: {'#2ecc71' if r['Paiement'] == 'Payé' else '#e74c3c'}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Paiement']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Boutons d'action
        c1, c2, c3 = st.columns(3)
        if c1.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()
        if c2.button("🔄 Re-book", key=f"rb_{idx}", use_container_width=True):
            # Logique de duplication simplifiée
            new_r = r.copy()
            new_r['DateNav'] = "À définir"; new_r['Statut'] = "En attente"; new_r['Paiement'] = "Pas payé"
            df_all = charger_data()
            df_all.loc[len(df_all)] = new_r
            sauver_data(df_all)
            st.rerun()
        if c3.button("🗑️ Supprimer", key=f"del_{idx}", use_container_width=True):
            df_all = charger_data()
            df_all = df_all.drop(idx).reset_index(drop=True)
            sauver_data(df_all)
            st.rerun()

with t1:
    afficher_liste(df[~df['Statut'].isin(["Terminé", "Refusé"])])
with t2:
    afficher_liste(df[df['Statut'].isin(["Terminé", "Refusé"])])


































































































































































































































































































































































































































































