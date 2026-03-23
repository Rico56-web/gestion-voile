import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- CHARGEMENT SÉCURISÉ DES DONNÉES ---
def charger_data():
    file = "contacts.json"
    # Liste complète des colonnes indispensables
    cols = ['Prénom', 'Nom', 'Société', 'DateResa', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Notes']
    
    if os.path.exists(file):
        df = pd.read_json(file)
        # On force la présence des colonnes si elles manquent
        for c in cols:
            if c not in df.columns:
                df[c] = ""
        return df[cols].fillna("")
    return pd.DataFrame(columns=cols)

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- ÉTATS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "show_new" not in st.session_state: st.session_state.show_new = False

st.title("⚓ Mes Missions & Contacts")

# --- FORMULAIRE D'ÉDITION / CRÉATION ---
if st.session_state.show_new or st.session_state.edit_idx is not None:
    is_edit = st.session_state.edit_idx is not None
    idx = st.session_state.edit_idx
    val = df.iloc[idx] if is_edit else None
    
    with st.container(border=True):
        st.subheader("📝 " + ("Modifier la fiche" if is_edit else "Nouvelle mission"))
        with st.form("mission_form"):
            c1, c2, c3 = st.columns(3)
            f_pre = c1.text_input("Prénom", val['Prénom'] if is_edit else "")
            f_nom = c2.text_input("Nom", val['Nom'] if is_edit else "")
            f_soc = c3.text_input("Société (ex: CMN)", val['Société'] if is_edit else "")
            
            c4, c5, c6 = st.columns(3)
            f_tel = c4.text_input("Téléphone", val['Téléphone'] if is_edit else "")
            f_mai = c5.text_input("Email", val['Email'] if is_edit else "")
            f_jou = c6.text_input("Nombre de jours", val['NbreJours'] if is_edit else "1")
            
            c7, c8 = st.columns(2)
            f_dna = c7.text_input("Date Navigation", val['DateNav'] if is_edit else "")
            f_dre = c8.text_input("Date Réservation", val['DateResa'] if is_edit else "")
            
            f_not = st.text_area("Notes particulières", val['Notes'] if is_edit else "")
            
            c9, c10 = st.columns(2)
            f_sta = c9.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                 index=0 if not is_edit else ["En attente", "OK", "Terminé", "Refusé"].index(val['Statut']))
            f_pay = c10.selectbox("Paiement", ["Pas payé", "Payé"], 
                                  index=0 if not is_edit else (1 if val['Paiement'] == "Payé" else 0))
            
            if st.form_submit_button("✅ ENREGISTRER"):
                # Mise à jour du DataFrame
                new_data = [f_pre, f_nom, f_soc, f_dre, f_dna, f_jou, f_tel, f_mai, f_sta, f_pay, f_not]
                if is_edit:
                    df.loc[idx] = new_data
                else:
                    df.loc[len(df)] = new_data
                sauver_data(df)
                st.session_state.show_new = False
                st.session_state.edit_idx = None
                st.rerun()
        
        if st.button("❌ ANNULER"):
            st.session_state.show_new = False
            st.session_state.edit_idx = None
            st.rerun()

# --- BOUTON CRÉER ---
if not st.session_state.show_new and st.session_state.edit_idx is None:
    if st.button("➕ NOUVELLE MISSION", type="primary", use_container_width=True):
        st.session_state.show_new = True
        st.rerun()

# --- AFFICHAGE DES FICHES ---
t1, t2 = st.tabs(["🚀 EN COURS", "📁 ARCHIVES"])

def afficher_fiches(df_filtre):
    for idx, r in df_filtre.iterrows():
        # Couleur bordure
        b_color = "#2ecc71" if r['Statut'] == "OK" else "#3498db"
        if r['Statut'] in ["Terminé", "Refusé"]: b_color = "#95a5a6"

        # Conversion WhatsApp
        t_wa = str(r['Téléphone']).replace(" ", "").replace("+", "")

        # LA FICHE VISUELLE (HTML)
        st.markdown(f"""
            <div style="border-left: 15px solid {b_color}; background: white; padding: 15px; border-radius: 12px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); margin-bottom: 15px; color: #2c3e50;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 22px; font-weight: bold;">{r['Prénom']} {str(r['Nom']).upper()}</span>
                    <span style="font-size: 16px; font-weight: bold; color: #1e3a5f;">📅 {r['DateNav']}</span>
                </div>
                
                <div style="margin: 5px 0; font-size: 14px;">
                    🏛️ Société : <b>{r['Société'] if r['Société'] else 'PARTICULIER'}</b> | ⏱️ Durée : <b>{r['NbreJours']} Jours</b>
                </div>

                <div style="margin: 10px 0; padding: 10px; background: #ebf5fb; border-radius: 8px; display: flex; justify-content: space-around;">
                    <a href="tel:{r['Téléphone']}" style="text-decoration:none; color:#2980b9; font-weight:bold;">📞 APPEL</a>
                    <a href="https://wa.me/{t_wa}" target="_blank" style="text-decoration:none; color:#27ae60; font-weight:bold;">💬 WHATSAPP</a>
                    <a href="mailto:{r['Email']}" style="text-decoration:none; color:#e67e22; font-weight:bold;">✉️ EMAIL</a>
                </div>

                <div style="font-size: 13px; color: #566573; border-top: 1px solid #eee; padding-top: 5px;">
                    📝 <b>Notes :</b> {r['Notes'] if r['Notes'] else '---'}
                </div>

                <div style="margin-top: 10px;">
                    <span style="background: {b_color}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Statut']}</span>
                    <span style="background: {'#2ecc71' if r['Paiement'] == 'Payé' else '#e74c3c'}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Paiement']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # BOUTONS STREAMLIT
        c1, c2, c3 = st.columns(3)
        if c1.button("✏️ Modif", key=f"e_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()
        if c2.button("🔄 Book", key=f"b_{idx}", use_container_width=True):
            new_r = r.copy()
            new_r['DateNav'] = "À définir"; new_r['Statut'] = "En attente"; new_r['Paiement'] = "Pas payé"
            df_new = pd.concat([df, pd.DataFrame([new_r])], ignore_index=True)
            sauver_data(df_new); st.rerun()
        if c3.button("🗑️ Suppr", key=f"d_{idx}", use_container_width=True):
            df_new = df.drop(idx).reset_index(drop=True)
            sauver_data(df_new); st.rerun()

with t1:
    afficher_fiches(df[~df['Statut'].isin(["Terminé", "Refusé"])])
with t2:
    afficher_fiches(df[df['Statut'].isin(["Terminé", "Refusé"])])


































































































































































































































































































































































































































































