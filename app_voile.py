import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- INITIALISATION DES ACTIONS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "del_idx" not in st.session_state: st.session_state.del_idx = None

st.title("⚓ Mes Navigations")

# --- ZONE D'ÉDITION (S'affiche uniquement si on clique sur Edit) ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.expander(f"📝 Modifier {val['Prénom']} {val['Nom']}", expanded=True):
        with st.form("form_edit"):
            col1, col2 = st.columns(2)
            new_pre = col1.text_input("Prénom", val['Prénom'])
            new_nom = col2.text_input("Nom", val['Nom'])
            new_date = col1.text_input("Date (JJ/MM/AAAA)", val['DateNav'])
            new_statut = col2.selectbox("Statut", ["OK", "En attente", "Terminé"], index=0)
            new_pay = st.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if val['Paiement']=="Payé" else 0)
            
            if st.form_submit_button("Enregistrer les modifications"):
                df.at[idx, 'Prénom'] = new_pre
                df.at[idx, 'Nom'] = new_nom
                df.at[idx, 'DateNav'] = new_date
                df.at[idx, 'Statut'] = new_statut
                df.at[idx, 'Paiement'] = new_pay
                sauver_data(df)
                st.session_state.edit_idx = None
                st.rerun()
        if st.button("Annuler l'édition"):
            st.session_state.edit_idx = None
            st.rerun()

# --- BOUCLE D'AFFICHAGE DES FICHES ---
for idx, r in df.iterrows():
    
    bg_s = "#27ae60" if r['Statut'] == "OK" else "#f39c12"
    bg_p = "#27ae60" if r['Paiement'] == "Payé" else "#e74c3c"

    html_fiche = f"""
    <div style="font-family: -apple-system, sans-serif; background: white; border-radius: 10px; padding: 10px; border-left: 6px solid #1e3a5f; box-shadow: 0 1px 4px rgba(0,0,0,0.1); color: #2c3e50; width: 98%; margin: auto;">
        <div style="display: flex; justify-content: space-between;">
            <div style="font-size: 16px; font-weight: bold;">{r['Prénom']} <span style="text-transform: uppercase;">{r['Nom']}</span></div>
            <div style="font-size: 13px; font-weight: bold;">📅 {r['DateNav']}</div>
        </div>
        <div style="font-size: 11px; color: #7f8c8d;">🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'} | ⏳ {r['NbreJours']} J</div>
        <div style="font-size: 12px; margin: 4px 0;"><b>{r['Téléphone']}</b></div>
        <div style="display: flex; gap: 5px;">
            <span style="background: {bg_s}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Statut']}</span>
            <span style="background: {bg_p}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">{r['Paiement']}</span>
        </div>
    </div>
    """
    components.html(html_fiche, height=105)
    
    col1, col2, col3 = st.columns(3)
    
    # Bouton Re-book
    if col1.button("🔄 Book", key=f"rb_{idx}", use_container_width=True):
        new_line = r.copy()
        new_line['DateNav'] = "01/01/2026"
        new_line['Statut'] = "En attente"
        new_line['Paiement'] = "Pas payé"
        df = pd.concat([df, pd.DataFrame([new_line])], ignore_index=True)
        sauver_data(df)
        st.success("Nouvelle mission créée !")
        st.rerun()
        
    # Bouton Edit
    if col2.button("✏️ Edit", key=f"ed_{idx}", use_container_width=True):
        st.session_state.edit_idx = idx
        st.rerun()
        
    # Bouton Delete (avec sécurité)
    if st.session_state.del_idx == idx:
        if col3.button("⚠️ CONFIRMER", key=f"del_conf_{idx}", type="primary", use_container_width=True):
            df = df.drop(idx).reset_index(drop=True)
            sauver_data(df)
            st.session_state.del_idx = None
            st.rerun()
        if st.button("X", key=f"del_ann_{idx}"):
            st.session_state.del_idx = None
            st.rerun()
    else:
        if col3.button("🗑️ Del", key=f"del_{idx}", use_container_width=True):
            st.session_state.del_idx = idx
            st.rerun()
    
    st.write("")










































































































































































































































































































































































































































































