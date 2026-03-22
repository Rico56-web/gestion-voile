import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# --- CSS POUR IPHONE ---
st.markdown("""
    <style>
    .fiche-globale {
        background: white; border-radius: 12px; padding: 15px;
        margin-bottom: 10px; border-left: 8px solid #3498db;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .border-cmn { border-left: 8px solid #2980b9 !important; background: #f0f7ff; }
    .prenom-style { font-size: 19px; font-weight: bold; color: #2c3e50; }
    .statut-badge {
        padding: 3px 8px; border-radius: 15px; color: white;
        font-size: 10px; font-weight: bold; margin-left: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS DATA ---
def charger_data():
    file = "contacts.json"
    cols = ['Prénom', 'Nom', 'Société', 'DateNav', 'Téléphone', 'Email', 'Statut', 'Paiement', 'Prix']
    if os.path.exists(file):
        try:
            df = pd.read_json(file)
            for c in cols: 
                if c not in df.columns: df[c] = ""
            return df
        except: pass
    return pd.DataFrame(columns=cols)

def sauvegarder_data(df):
    df.to_json("contacts.json", orient='records', indent=4)

# --- INITIALISATION ---
df_c = charger_data()
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'delete_confirm_idx' not in st.session_state: st.session_state.delete_confirm_idx = None
if 'voir_archives' not in st.session_state: st.session_state.voir_archives = False

# --- MENU LATÉRAL ---
st.sidebar.title("⚓ Vesta 2026")
page = st.sidebar.radio("Navigation", ["CONTACTS", "PLANNING", "STATS"])

if page == "CONTACTS":
    st.subheader("👤 Mes Fiches")
    
    # --- 1. SÉLECTION ACTIVES / ARCHIVÉES ---
    col_t1, col_t2 = st.columns(2)
    if col_t1.button("🚀 ACTIVES", type="primary" if not st.session_state.voir_archives else "secondary", use_container_width=True, key="btn_actives"):
        st.session_state.voir_archives = False
        st.rerun()
    if col_t2.button("📁 ARCHIVÉES", type="primary" if st.session_state.voir_archives else "secondary", use_container_width=True, key="btn_archives"):
        st.session_state.voir_archives = True
        st.rerun()

    # Bouton Nouveau
    if st.button("➕ NOUVEAU CONTACT", use_container_width=True):
        new_line = {c: "" for c in df_c.columns}
        new_line.update({"Prénom": "Nouveau", "Nom": "Contact", "DateNav": datetime.now().strftime("%d/%m/2026"), "Statut": "En attente", "Paiement": "Pas payé"})
        df_c = pd.concat([pd.DataFrame([new_line]), df_c], ignore_index=True)
        sauvegarder_data(df_c)
        st.rerun()

    # --- 2. ZONE D'ÉDITION ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        if idx in df_c.index:
            r = df_c.loc[idx]
            with st.expander(f"📝 Modification : {r['Prénom']} {r['Nom']}", expanded=True):
                with st.form("edit_form"):
                    u_pre = st.text_input("Prénom", value=r['Prénom'])
                    u_nom = st.text_input("Nom", value=r['Nom'])
                    u_soc = st.text_input("Société", value=r['Société'])
                    u_tel = st.text_input("Téléphone", value=r['Téléphone'])
                    u_mail = st.text_input("Email", value=r['Email'])
                    u_date = st.text_input("Date (JJ/MM/AAAA)", value=r['DateNav'])
                    u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                         index=["En attente", "OK", "Terminé", "Refusé"].index(r['Statut']) if r['Statut'] in ["En attente", "OK", "Terminé", "Refusé"] else 0)
                    u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if r['Paiement']=="Payé" else 0)
                    
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("💾 ENREGISTRER"):
                        df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'] = u_pre, u_nom
                        df_c.at[idx, 'Société'], df_c.at[idx, 'Téléphone'] = u_soc, u_tel
                        df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_mail, u_date
                        df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'] = u_stat, u_paye
                        sauvegarder_data(df_c)
                        st.session_state.edit_idx = None
                        st.rerun()
                    if c2.form_submit_button("Fermer"):
                        st.session_state.edit_idx = None
                        st.rerun()

    # --- 3. FILTRAGE ET RECHERCHE ---
    search = st.text_input("🔍 Rechercher...", "").lower()
    
    # On sépare Actives (En attente, OK) et Archivées (Terminé, Refusé)
    if st.session_state.voir_archives:
        df_affichage = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])]
    else:
        df_affichage = df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    # --- 4. BOUCLE D'AFFICHAGE ---
    for idx, r in df_affichage.iterrows():
        if search and search not in str(r['Nom']).lower() and search not in str(r['Prénom']).lower() and search not in str(r['Société']).lower():
            continue
            
        soc = str(r['Société']) if str(r['Société']) != "" else "PARTICULIER"
        color_p = "#2ecc71" if r['Paiement'] == "Payé" else "#e74c3c"
        color_s = "#2ecc71" if r['Statut'] == "OK" else "#f1c40f" if r['Statut'] == "En attente" else "#3498db"
        cl_b = "border-cmn" if "CMN" in soc.upper() else ""

        st.markdown(f"""
            <div class="fiche-globale {cl_b}">
                <div class="prenom-style">{r['Prénom']} {str(r['Nom']).upper()}</div>
                <div style="color:gray; font-size:14px;">🏛️ {soc}</div>
                <div style="margin:5px 0; font-size:14px;">
                    📞 <b>{r['Téléphone']}</b><br>
                    ✉️ {r['Email']}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                    <span style="font-size:14px;">📅 <b>{r['DateNav']}</b></span>
                    <div>
                        <span class="statut-badge" style="background:{color_s};">{r['Statut']}</span>
                        <span class="statut-badge" style="background:{color_p};">{r['Paiement']}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        col_ed, col_del = st.columns(2)
        if col_ed.button(f"✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()

        if st.session_state.delete_confirm_idx == idx:
            if col_del.button(f"✅ CONFIRMER ?", key=f"conf_{idx}", type="primary", use_container_width=True):
                df_c = df_c.drop(idx).reset_index(drop=True)
                sauvegarder_data(df_c)
                st.session_state.delete_confirm_idx = None
                st.rerun()
            if st.button("Annuler suppression", key=f"ann_{idx}", use_container_width=True):
                st.session_state.delete_confirm_idx = None
                st.rerun()
        else:
            if col_del.button(f"🗑️ Supprimer", key=f"del_{idx}", use_container_width=True):
                st.session_state.delete_confirm_idx = idx
                st.rerun()

elif page == "PLANNING":
    st.info("Le module Planning est prêt à être codé.")

elif page == "STATS":
    st.metric("Total fiches", len(df_c))

























































































































































































































































































































































































































































































