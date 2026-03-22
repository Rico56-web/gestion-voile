import streamlit as st
import pandas as pd
import os

# --- 1. CONFIGURATION ET DESIGN ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# On applique un style global sur les blocs de Streamlit
st.markdown("""
    <style>
    /* Supprime les bordures par défaut et ajoute notre style "Vesta" */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff !important;
        border-radius: 15px !important;
        border-left: 10px solid #2980b9 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        padding: 20px !important;
        margin-bottom: 10px !important;
    }
    /* Style pour les titres */
    h3 { color: #2c3e50; margin-bottom: 0px !important; padding-bottom: 0px !important; }
    .stMarkdown p { font-size: 15px; margin-bottom: 5px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIQUE DATA ---
def charger_data():
    if os.path.exists("contacts.json"):
        return pd.read_json("contacts.json")
    return pd.DataFrame(columns=['Prénom', 'Nom', 'Société', 'DateNav', 'NbreJours', 'Téléphone', 'Email', 'Statut', 'Paiement'])

df = charger_data()

# --- 3. AFFICHAGE DES MISSIONS ---
st.title("⚓ Mes Navigations")

# Barre de recherche simple
search = st.text_input("🔍 Rechercher...", "").lower()

for idx, r in df.iterrows():
    if search and not any(search in str(r[c]).lower() for c in ['Nom', 'Prénom', 'Société']):
        continue

    # --- CRÉATION DE LA FICHE ---
    with st.container(border=True):
        # Ligne d'en-tête
        st.markdown(f"### {r['Prénom']} **{str(r['Nom']).upper()}**")
        st.write(f"🏛️ {r['Société'] if r['Société'] else 'PARTICULIER'}")
        
        # Section Contacts
        c1, c2 = st.columns(2)
        c1.write(f"📞 **{r['Téléphone']}**")
        c2.write(f"✉️ {r['Email']}")
        
        # Section Détails (Bloc bleu clair natif)
        st.info(f"⏳ Durée de la mission : **{r['NbreJours']} jour(s)**")
        
        st.divider() # Ligne de séparation élégante
        
        # Pied de fiche : Date et Badges
        col_date, col_badges = st.columns([1, 1])
        
        with col_date:
            st.markdown(f"#### 📅 {r['DateNav']}")
            
        with col_badges:
            # On utilise des colonnes imbriquées pour aligner les badges à droite
            b_c1, b_c2 = st.columns(2)
            # Badge Statut
            if r['Statut'] == "OK": b_c1.success(r['Statut'])
            elif r['Statut'] == "Terminé": b_c1.info(r['Statut'])
            else: b_c1.warning(r['Statut'])
            # Badge Paiement
            if r['Paiement'] == "Payé": b_c2.success("✔ PAYÉ")
            else: b_c2.error("✖ IMPAYÉ")

        # Boutons d'actions en bas de fiche
        act1, act2, act3 = st.columns(3)
        act1.button("🔄 RE-BOOK", key=f"rb_{idx}", use_container_width=True)
        act2.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True)
        act3.button("🗑️ Suppr.", key=f"del_{idx}", use_container_width=True)
















































































































































































































































































































































































































































































