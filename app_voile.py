import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- STYLE POUR LES BADGES ET LES FICHES ---
st.markdown("""
    <style>
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-left: 10px solid #1e3a5f !important;
        background-color: #ffffff !important;
        border-radius: 10px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    .status-ok { background-color: #2ecc71; color: white; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }
    .status-wait { background-color: #f1c40f; color: white; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }
    .pay-ok { background-color: #2ecc71; color: white; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }
    .pay-no { background-color: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }
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

st.title("⚓ Mes Missions")

# --- FENÊTRE DE MODIFICATION ---
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
            u_sta = c1.selectbox("Statut", ["OK", "En attente", "Terminé"], index=0)
            u_pay = c2.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
            
            col_btn1, col_btn2 = st.columns(2)
            submit = col_btn1.form_submit_button("✅ ENREGISTRER", use_container_width=True)
            
            if submit:
                df.loc[idx] = [u_pre, u_nom, val['Société'], val['DateResa'], u_dna, u_jou, u_tel, u_mai, u_sta, u_pay]
                sauver_data(df)
                st.session_state.edit_idx = None
                st.rerun()
        
        # BOUTON ANNULER (Hors du formulaire pour être réactif)
        if st.button("❌ ANNULER / FERMER", use_container_width=True):
            st.session_state.edit_idx = None
            st.rerun()

# --- LISTE DES FICHES ---
for idx, r in df.iterrows():
    with st.container(border=True):
        # En-tête
        c_titre, c_date = st.columns([2, 1])
        c_titre.markdown(f"### {r['Prénom']} {str(r['Nom']).upper()}")
        c_date.markdown(f"📅 **{r['DateNav']}**")
        
        # Infos de contact (Toujours visibles)
        st.write(f"📞 {r['Téléphone'] if r['Téléphone'] else 'Non renseigné'}")
        st.write(f"✉️ {r['Email'] if r['Email'] else 'Non renseigné'}")
        
        # Statuts (Badges colorés via HTML simple)
        s_class = "status-ok" if r['Statut'] == "OK" else "status-wait"
        p_class = "pay-ok" if r['Paiement'] == "Payé" else "pay-no"
        
        st.markdown(f"""
            <span class="{s_class}">{r['Statut']}</span> 
            <span class="{p_class}">{r['Paiement']}</span>
            <span style="margin-left:15px; font-size:12px; color:gray;">⏱️ {r['NbreJours']} jour(s)</span>
        """, unsafe_allow_html=True)
        
        st.write("") # Espace
        
        # Boutons d'action
        b1, b2, b3 = st.columns(3)
        
        if b1.button("✏️ Edit", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()
            
        if b2.button("🔄 Book", key=f"rb_{idx}", use_container_width=True):
            new_r = r.copy()
            new_r['DateNav'] = "À définir"
            df = pd.concat([df, pd.DataFrame([new_r])], ignore_index=True)
            sauver_data(df)
            st.rerun()
            
        # Sécurité supprimer
        if st.session_state.del_idx == idx:
            if b3.button("⚠️ OK ?", key=f"conf_{idx}", type="primary", use_container_width=True):
                df = df.drop(idx).reset_index(drop=True)
                sauver_data(df)
                st.session_state.del_idx = None
                st.rerun()
            if st.button("X", key=f"ann_del_{idx}"):
                st.session_state.del_idx = None
                st.rerun()
        else:
            if b3.button("🗑️ Del", key=f"del_{idx}", use_container_width=True):
                st.session_state.del_idx = idx
                st.rerun()






































































































































































































































































































































































































































































