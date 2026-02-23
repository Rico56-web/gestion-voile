import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

# --- FONCTIONS DE DONNÉES ---
def charger_donnees(fichier):
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

# --- INITIALISATION ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Vesta Manager")
    mdp = st.text_input("Entrez le code d'accès", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
else:
    # Chargement des fichiers
    contacts = charger_donnees('contacts.json')
    echanges = charger_donnees('echanges.json')
    demandes = charger_donnees('demandes.json')
    # Initialisation des check-lists personnalisables
    check_data = charger_donnees('checklists.json')
    if not check_data:
        check_data = {"Départ": ["Météo", "Gilets"], "Arrivée": ["Vannes", "Batteries"]}

    st.sidebar.title("⚓ Navigation")
    menu = st.sidebar.radio("Aller à :", ["📊 Dashboard", "🗂️ Contacts", "⛵ Demandes", "💬 Historique", "📋 Checklists"])

    # ... (Les sections Dashboard, Contacts, Demandes et Historique restent identiques) ...
    # [Note : Gardez le code des sections précédentes ici]

elif menu == "📋 Checklists":
        st.title("📋 Checklists Personnalisables")
        
        # --- GESTION DES POINTS ---
        with st.expander("🛠️ Modifier les listes (Ajouter/Supprimer)"):
            col_add, col_cat = st.columns([3, 1])
            new_item = col_add.text_input("Nouveau point de contrôle")
            cat = col_cat.selectbox("Liste cible", ["Départ", "Arrivée"])
            
            if st.button("➕ Ajouter à la liste"):
                if new_item:
                    check_data[cat].append(new_item)
                    sauvegarder_donnees('checklists.json', check_data)
                    st.rerun()
            
            st.divider()
            st.write("🗑️ **Supprimer des points existants :**")
            for cat_name in ["Départ", "Arrivée"]:
                st.write(f"**Liste {cat_name} :**")
                for i, item in enumerate(check_data[cat_name]):
                    # Utilisation d'une clé unique avec l'index pour éviter le blocage
                    if st.button(f"❌ {item}", key=f"del_{cat_name}_{i}"):
                        check_data[cat_name].pop(i)
                        sauvegarder_donnees('checklists.json', check_data)
                        st.rerun()

        st.divider()

        # --- AFFICHAGE POUR UTILISATION ---
        col_dep, col_arr = st.columns(2)
        with col_dep:
            st.subheader("⛵ Départ")
            for item in check_data["Départ"]:
                st.checkbox(item, key=f"run_dep_{item}")
            
        with col_arr:
            st.subheader("⚓ Arrivée")
            for item in check_data["Arrivée"]:
                st.checkbox(item, key=f"run_arr_{item}")
        
        # --- AJOUT DE NOUVELLES LIGNES ---
        with st.expander("🛠️ Gérer les points de contrôle"):
            col_add, col_cat = st.columns([3, 1])
            new_item = col_add.text_input("Ajouter un point (ex: Vérifier le frigo)")
            cat = col_cat.selectbox("Liste", ["Départ", "Arrivée"])
            if st.button("➕ Ajouter à la liste"):
                if new_item:
                    check_data[cat].append(new_item)
                    sauvegarder_donnees('checklists.json', check_data)
                    st.rerun()
            
            st.divider()
            st.write("🗑️ **Supprimer un point :**")
            for cat_name in ["Départ", "Arrivée"]:
                for i, item in enumerate(check_data[cat_name]):
                    if st.button(f"Supprimer {item}", key=f"del_{cat_name}_{i}"):
                        check_data[cat_name].pop(i)
                        sauvegarder_donnees('checklists.json', check_data)
                        st.rerun()

        st.divider()

        # --- AFFICHAGE DES LISTES POUR COCHER ---
        col_dep, col_arr = st.columns(2)
        
        with col_dep:
            st.subheader("⛵ Départ")
            for item in check_data["Départ"]:
                st.checkbox(item, key=f"run_dep_{item}")
            
        with col_arr:
            st.subheader("⚓ Arrivée")
            for item in check_data["Arrivée"]:
                st.checkbox(item, key=f"run_arr_{item}")

