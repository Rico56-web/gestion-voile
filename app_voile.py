import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE CSS ---
st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-left: 10px solid #1e3a5f !important;
        background-color: #ffffff !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
        margin-bottom: 10px !important;
    }
    .status-badge { padding: 2px 10px; border-radius: 12px; color: white; font-weight: bold; font-size: 11px; display: inline-block; }
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
            for c in cols:
                if c not in df.columns: df[c] = ""
            return df[cols]
        except: pass
    return pd.DataFrame(columns=cols)

def sauver_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

df = charger_data()

# --- ÉTATS ---
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "del_idx" not in st.session_state: st.session_state.del_idx = None

st.title("⚓ Vesta Skipper 2026")

# --- NAVIGATION SOUS-MENUS ---
tab_encours, tab_archives = st.tabs(["🚀 EN COURS", "📁 ARCHIVÉES"])

# --- FENÊTRE DE MODIFICATION (S'affiche si on clique sur Edit) ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.container(border=True):
        st.subheader(f"📝 Modifier : {val['Prénom']} {val['Nom']}")
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", val['Prénom'])
            u_nom = c2.text_input("Nom", val['Nom'])
            u_tel = c1.text_input("Téléphone", val['Téléphone'])
            u_mai = c2.text_input("Email", val['Email'])
            u_dna = c1.text_input("Date Nav", val['DateNav'])
            u_jou = c2.text_input("Jours", str(val['NbreJours']))
            u_sta = c1.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                 index=["En attente", "OK", "Terminé", "Refusé"].index(val['Statut']) if val['Statut'] in ["En attente", "OK", "Terminé", "Refusé"] else 0)
            u_pay = c2.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if val['Paiement']=="Payé" else 0)
            
            if st.form_submit_button("✅ ENREGISTRER", use_container_width=True):
                df.loc[idx] = [u_pre, u_nom, val['Société'], val['DateResa'], u_dna, u_jou, u_tel, u_mai, u_sta, u_pay]
                sauver_data(df)
                st.session_state.edit_idx = None
                st.rerun()
        if st.button("❌ ANNULER / FERMER", use_container_width=True):
            st.session_state.edit_idx = None
            st.rerun()

# --- FONCTION D'AFFICHAGE DES FICHES ---
def afficher_fiches(dataframe_filtre):
    if dataframe_filtre.empty:
        st.write("Aucune mission dans cette catégorie.")
        return

    for idx, r in dataframe_filtre.iterrows():
        with st.container(border=True):
            col_titre, col_date = st.columns([2, 1])
            col_titre.markdown(f"### {r['Prénom']} {str(r['Nom']).upper()}")
            col_date.markdown(f"📅 **{r['DateNav']}**")
            
            st.write(f"📞 {r['Téléphone'] if r['Téléphone'] else 'Non renseigné'}")
            st.write(f"✉️ {r['Email'] if r['Email'] else 'Non renseigné'}")
            
            # Badges Statuts
            s_class = "bg-ok" if r['Statut'] == "OK" else "bg-done" if r['Statut'] in ["Terminé", "Refusé"] else "bg-wait"
            p_class = "bg-pay-ok" if r['Paiement'] == "Payé" else "bg-pay-no"
            
            st.markdown(f"""
                <span class="status-badge {s_class}">{r['Statut']}</span> 
                <span class="status-badge {p_class}">{r['Paiement']}</span>
                <span style="margin-left:10px; font-size:12px; color:gray;">⏱️ {r['NbreJours']} jour(s)</span>
            """, unsafe_allow_html=True)
            
            st.write("") 
            
            # Boutons
            b1, b2, b3 = st.columns(3)
            if b1.button("✏️ Edit", key=f"ed_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.rerun()
            if b2.button("🔄 Book", key=f"rb_{idx}", use_container_width=True):
                new_r = r.copy()
                new_r['DateNav'] = "À définir"; new_r['Statut'] = "En attente"; new_r['Paiement'] = "Pas payé"
                df_global = charger_data() # On recharge pour être sûr
                df_global = pd.concat([df_global, pd.DataFrame([new_r])], ignore_index=True)
                sauver_data(df_global)
                st.rerun()
                
            if st.session_state.del_idx == idx:
                if b3.button("⚠️ OK ?", key=f"conf_{idx}", type="primary", use_container_width=True):
                    df_global = charger_data()
                    df_global = df_global.drop(idx).reset_index(drop=True)
                    sauver_data(df_global)
                    st.session_state.del_idx = None
                    st.rerun()
                if st.button("X", key=f"ann_del_{idx}"):
                    st.session_state.del_idx = None; st.rerun()
            else:
                if b3.button("🗑️ Del", key=f"del_{idx}", use_container_width=True):
                    st.session_state.del_idx = idx; st.rerun()

# --- LOGIQUE DES ONGLETS ---
with tab_encours:
    df_encours = df[~df['Statut'].isin(["Terminé", "Refusé"])]
    afficher_fiches(df_encours)

with tab_archives:
    df_archives = df[df['Statut'].isin(["Terminé", "Refusé"])]
    afficher_fiches(df_archives)





































































































































































































































































































































































































































































