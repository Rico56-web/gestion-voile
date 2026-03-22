import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS AVEC COULEURS ---
st.markdown("""
    <style>
    /* Style des fiches */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-left: 12px solid #1e3a5f !important;
        background-color: #ffffff !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
        margin-bottom: 15px !important;
    }
    /* Bouton Nouvelle Mission */
    .stButton > button[kind="primary"] {
        background-color: #27ae60 !important;
        color: white !important;
        border-radius: 20px !important;
        font-weight: bold !important;
    }
    /* Bouton Modifier (Bleu) */
    div[data-testid="column"]:nth-of-type(1) button {
        border: 1px solid #3498db !important;
        color: #3498db !important;
    }
    /* Bouton Re-book (Vert) */
    div[data-testid="column"]:nth-of-type(2) button {
        border: 1px solid #2ecc71 !important;
        color: #2ecc71 !important;
    }
    /* Bouton Supprimer (Rouge) */
    div[data-testid="column"]:nth-of-type(3) button {
        border: 1px solid #e74c3c !important;
        color: #e74c3c !important;
    }
    .status-badge { padding: 4px 12px; border-radius: 15px; color: white; font-weight: bold; font-size: 11px; }
    .bg-ok { background-color: #2ecc71; }
    .bg-wait { background-color: #f1c40f; }
    .bg-done { background-color: #34495e; }
    .bg-pay-ok { background-color: #2ecc71; }
    .bg-pay-no { background-color: #e74c3c; }
    </style>
""", unsafe_allow_html=True)

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

st.title("⚓ Vesta Skipper 2026")

# --- BOUTON NOUVELLE MISSION ---
if not st.session_state.show_new:
    if st.button("➕ NOUVELLE MISSION", type="primary", use_container_width=True):
        st.session_state.show_new = True
        st.rerun()

if st.session_state.show_new:
    with st.container(border=True):
        st.subheader("🆕 Ajouter une mission")
        with st.form("new_form"):
            c1, c2 = st.columns(2)
            n_pre = c1.text_input("Prénom")
            n_nom = c2.text_input("Nom")
            n_tel = c1.text_input("Téléphone")
            n_dna = c2.text_input("Date Nav (JJ/MM/AAAA)")
            n_jou = c1.text_input("Nbre de jours", "1")
            n_sta = c2.selectbox("Statut", ["En attente", "OK"])
            if st.form_submit_button("💾 CRÉER LA MISSION", use_container_width=True):
                new_data = pd.DataFrame([{"Prénom": n_pre, "Nom": n_nom, "Téléphone": n_tel, "DateNav": n_dna, "NbreJours": n_jou, "Statut": n_sta, "Paiement": "Pas payé"}])
                df = pd.concat([df, new_data], ignore_index=True)
                sauver_data(df)
                st.session_state.show_new = False
                st.rerun()
        if st.button("❌ Annuler"):
            st.session_state.show_new = False
            st.rerun()

# --- MODIFICATION ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.container(border=True):
        st.subheader(f"✏️ Modification")
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", val['Prénom'])
            u_nom = c2.text_input("Nom", val['Nom'])
            u_tel = c1.text_input("Téléphone", val['Téléphone'])
            u_dna = c1.text_input("Date Nav", val['DateNav'])
            u_sta = c2.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
            u_pay = c2.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if val['Paiement']=="Payé" else 0)
            if st.form_submit_button("✅ SAUVEGARDER"):
                df.loc[idx, ['Prénom','Nom','Téléphone','DateNav','Statut','Paiement']] = [u_pre, u_nom, u_tel, u_dna, u_sta, u_pay]
                sauver_data(df)
                st.session_state.edit_idx = None
                st.rerun()
        if st.button("Annuler"):
            st.session_state.edit_idx = None
            st.rerun()

# --- AFFICHAGE ---
tab_encours, tab_archives = st.tabs(["🚀 EN COURS", "📁 ARCHIVÉES"])

def liste_missions(df_filtre):
    for idx, r in df_filtre.iterrows():
        with st.container(border=True):
            st.markdown(f"### {r['Prénom']} {str(r['Nom']).upper()}")
            st.write(f"📅 **{r['DateNav']}** | 📞 {r['Téléphone']}")
            
            s_cl = "bg-ok" if r['Statut'] == "OK" else "bg-done" if r['Statut'] in ["Terminé", "Refusé"] else "bg-wait"
            p_cl = "bg-pay-ok" if r['Paiement'] == "Payé" else "bg-pay-no"
            
            st.markdown(f'<span class="status-badge {s_cl}">{r['Statut']}</span> <span class="status-badge {p_cl}">{r['Paiement']}</span>', unsafe_allow_html=True)
            
            st.write("")
            b1, b2, b3 = st.columns(3)
            if b1.button("✏️ Edit", key=f"e_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.rerun()
            if b2.button("🔄 Book", key=f"b_{idx}", use_container_width=True):
                new_copy = r.copy()
                new_copy['DateNav'] = "À définir"; new_copy['Statut'] = "En attente"; new_copy['Paiement'] = "Pas payé"
                df_all = pd.concat([df, pd.DataFrame([new_copy])], ignore_index=True)
                sauver_data(df_all); st.rerun()
            
            if st.session_state.del_idx == idx:
                if b3.button("⚠️ OK ?", key=f"c_{idx}", type="primary", use_container_width=True):
                    df_all = df.drop(idx).reset_index(drop=True)
                    sauver_data(df_all); st.session_state.del_idx = None; st.rerun()
            else:
                if b3.button("🗑️ Del", key=f"d_{idx}", use_container_width=True):
                    st.session_state.del_idx = idx
                    st.rerun()

with tab_encours:
    liste_missions(df[~df['Statut'].isin(["Terminé", "Refusé"])])
with tab_archives:
    liste_missions(df[df['Statut'].isin(["Terminé", "Refusé"])])



































































































































































































































































































































































































































































