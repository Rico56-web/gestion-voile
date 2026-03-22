import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- DATA ---
def charger_data():
    file = "contacts.json"
    cols = ['Prénom', 'Nom', 'Société', 'DateResa', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- INITIALISATION ACTIONS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.title("⚓ Mes Missions Skipper")

# --- FORMULAIRE D'ÉDITION ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.expander("📝 MODIFIER LA FICHE", expanded=True):
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", val['Prénom'])
            u_nom = c2.text_input("Nom", val['Nom'])
            u_soc = c1.text_input("Société", val['Société'])
            u_tel = c2.text_input("Téléphone", val['Téléphone'])
            u_mai = c1.text_input("Email", val['Email'])
            u_dre = c2.text_input("Date Réservation", val['DateResa'])
            u_dna = c1.text_input("Date Navigation", val['DateNav'])
            u_jou = c2.text_input("Nombre de jours", str(val['NbreJours']))
            u_sta = c1.selectbox("Statut", ["OK", "En attente", "Terminé"], index=0)
            u_pay = c2.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
            
            if st.form_submit_button("VALIDER"):
                df.loc[idx] = [u_pre, u_nom, u_soc, u_dre, u_dna, u_jou, u_tel, u_mai, u_sta, u_pay]
                sauver_data(df)
                st.session_state.edit_idx = None
                st.rerun()
        if st.button("Annuler"):
            st.session_state.edit_idx = None
            st.rerun()

# --- BOUCLE D'AFFICHAGE ---
for idx, r in df.iterrows():
    # Préparation WhatsApp
    tel_clean = str(r['Téléphone']).replace(" ", "").replace("+", "")
    msg_wa = urllib.parse.quote(f"Bonjour {r['Prénom']}, c'est votre skipper...")
    link_wa = f"https://wa.me/{tel_clean}?text={msg_wa}"
    
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    # DESIGN DE LA FICHE RÉORDONNÉE
    html_fiche = f"""
    <div style="font-family: -apple-system, sans-serif; background: white; border-radius: 12px; padding: 12px; border-left: 8px solid #1e3a5f; box-shadow: 0 2px 5px rgba(0,0,0,0.1); color: #2c3e50; width: 96%; margin: auto;">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <div>
                <div style="font-size: 18px; font-weight: bold;">{r['Prénom']} <span style="text-transform: uppercase;">{r['Nom']}</span></div>
                <div style="font-size: 12px; color: #7f8c8d;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}</div>
            </div>
            <div style="text-align: right; font-size: 11px; color: #95a5a6;">
                Résa le : {r['DateResa']}<br>
                <b>{r['NbreJours']} Jours</b>
            </div>
        </div>

        <div style="margin: 8px 0; font-size: 16px; color: #1e3a5f; font-weight: bold;">
            📅 Navigation : {r['DateNav']}
        </div>

        <div style="display: flex; gap: 15px; margin-bottom: 8px;">
            <a href="tel:{r['Téléphone']}" style="text-decoration:none; color:#2980b9; font-size:13px;">📞 Appeler</a>
            <a href="{link_wa}" target="_blank" style="text-decoration:none; color:#27ae60; font-size:13px;">💬 WhatsApp</a>
            <a href="mailto:{r['Email']}" style="text-decoration:none; color:#e67e22; font-size:13px;">✉️ Email</a>
        </div>

        <div style="display: flex; gap: 6px;">
            <span style="background: {bg_s}; color: white; padding: 3px 10px; border-radius: 15px; font-size: 10px; font-weight: bold;">{r['Statut']}</span>
            <span style="background: {bg_p}; color: white; padding: 3px 10px; border-radius: 15px; font-size: 10px; font-weight: bold;">{r['Paiement']}</span>
        </div>
    </div>
    """
    components.html(html_fiche, height=155)
    
    # Boutons d'administration Streamlit
    col1, col2 = st.columns(2)
    if col1.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
        st.session_state.edit_idx = idx
        st.rerun()
    if col2.button("🔄 Re-book", key=f"rb_{idx}", use_container_width=True):
        # Logique re-book simplifiée
        new_row = r.copy()
        new_row['DateNav'] = "À définir"
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        sauver_data(df)
        st.rerun()
    
    st.write("---")








































































































































































































































































































































































































































































