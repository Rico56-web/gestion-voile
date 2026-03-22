import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- DATA ---
def charger_data():
    file = "contacts.json"
    cols = ['Prénom', 'Nom', 'Société', 'DateResa', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            return df.reindex(columns=cols).fillna("")
        except: pass
    return pd.DataFrame(columns=cols)

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- ÉTATS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "del_idx" not in st.session_state: st.session_state.del_idx = None
if "show_new" not in st.session_state: st.session_state.show_new = False

# --- INTERFACE TITRE ---
st.title("⚓ Vesta Skipper 2026")

# --- BOUTON NOUVELLE MISSION (VERT) ---
col_new = st.columns([1, 2, 1])
if not st.session_state.show_new:
    if col_new[1].button("➕ CRÉER UNE NOUVELLE MISSION", type="primary", use_container_width=True):
        st.session_state.show_new = True
        st.rerun()

if st.session_state.show_new:
    with st.container(border=True):
        st.subheader("🆕 Nouveau Client")
        with st.form("new_form"):
            c1, c2 = st.columns(2)
            n_pre = c1.text_input("Prénom")
            n_nom = c2.text_input("Nom")
            n_tel = c1.text_input("Téléphone")
            n_dna = c2.text_input("Date Nav (JJ/MM/AAAA)")
            n_jou = c1.text_input("Nbre de jours", "1")
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = pd.DataFrame([{"Prénom": n_pre, "Nom": n_nom, "Téléphone": n_tel, "DateNav": n_dna, "NbreJours": n_jou, "Statut": "En attente", "Paiement": "Pas payé"}])
                df = pd.concat([df, new_row], ignore_index=True)
                sauver_data(df)
                st.session_state.show_new = False
                st.rerun()
        if st.button("❌ Annuler"):
            st.session_state.show_new = False; st.rerun()

# --- FORMULAIRE D'ÉDITION ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.container(border=True):
        st.subheader(f"✏️ Modifier {val['Prénom']}")
        with st.form("edit_form"):
            e_dna = st.text_input("Date Nav", val['DateNav'])
            e_sta = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
            e_pay = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
            if st.form_submit_button("✅ SAUVEGARDER"):
                df.loc[idx, ['DateNav', 'Statut', 'Paiement']] = [e_dna, e_sta, e_pay]
                sauver_data(df); st.session_state.edit_idx = None; st.rerun()
        if st.button("Fermer"): st.session_state.edit_idx = None; st.rerun()

# --- ONGLETS ---
t1, t2 = st.tabs(["🚀 MISSIONS EN COURS", "📁 ARCHIVES"])

def afficher_fiches_couleur(df_filtre):
    for idx, r in df_filtre.iterrows():
        # Déterminer la couleur de la bordure selon le statut
        border_color = "#3498db" # Bleu par défaut
        if r['Statut'] == "OK": border_color = "#2ecc71" # Vert
        if r['Statut'] == "Terminé": border_color = "#95a5a6" # Gris

        # Injection du design de la fiche
        st.markdown(f"""
            <div style="
                border-left: 15px solid {border_color};
                background-color: white;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 10px;
                color: #2c3e50;
            ">
                <div style="font-size: 20px; font-weight: bold;">{r['Prénom']} {str(r['Nom']).upper()}</div>
                <div style="font-size: 14px; margin: 5px 0;">📅 <b>{r['DateNav']}</b> | 📞 {r['Téléphone']}</div>
                <div style="margin-top: 10px;">
                    <span style="background: {border_color}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Statut']}</span>
                    <span style="background: {'#2ecc71' if r['Paiement'] == 'Payé' else '#e74c3c'}; color: white; padding: 3px 10px; border-radius: 10px; font-size: 11px; font-weight: bold;">{r['Paiement']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Boutons colorés
        c1, c2, c3 = st.columns(3)
        if c1.button(f"✏️ Modifier", key=f"e_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx; st.rerun()
        
        if c2.button(f"🔄 Re-book", key=f"b_{idx}", use_container_width=True):
            new_r = r.copy(); new_r['DateNav'] = "À définir"; new_r['Statut'] = "En attente"; new_r['Paiement'] = "Pas payé"
            df_new = pd.concat([df, pd.DataFrame([new_r])], ignore_index=True)
            sauver_data(df_new); st.rerun()

        if st.session_state.del_idx == idx:
            if c3.button("⚠️ CONFIRMER ?", key=f"c_{idx}", type="primary", use_container_width=True):
                df_new = df.drop(idx).reset_index(drop=True)
                sauver_data(df_new); st.session_state.del_idx = None; st.rerun()
        else:
            if c3.button(f"🗑️ Suppr.", key=f"d_{idx}", use_container_width=True):
                st.session_state.del_idx = idx; st.rerun()
        st.write("")

# Remplissage des onglets
with t1:
    afficher_fiches_couleur(df[~df['Statut'].isin(["Terminé", "Refusé"])])
with t2:
    afficher_fiches_couleur(df[df['Statut'].isin(["Terminé", "Refusé"])])


































































































































































































































































































































































































































































