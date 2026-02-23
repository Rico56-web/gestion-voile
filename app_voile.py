import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Skipper Manager", layout="wide", page_icon="⛵")

def charger_donnees(fichier):
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

# --- SÉCURITÉ ---
if "authentifie" not in st.session_state:
    st.session_state["authentifie"] = False

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Skipper Manager")
    mdp = st.text_input("Entrez le code d'accès au bord", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
        else:
            st.error("Code incorrect.")
else:
    # --- CHARGEMENT DES DONNÉES ---
    contacts = charger_donnees('contacts.json')
    sorties = charger_donnees('sorties.json')

    # --- BARRE LATÉRALE (MENU) ---
    st.sidebar.title("⚓ Navigation")
    menu = st.sidebar.radio("Aller à :", ["Tableau de bord", "Carnet d'adresses", "Planifier une sortie", "Historique"])

    if menu == "Tableau de bord":
        st.title("📊 Tableau de bord")
        col1, col2 = st.columns(2)
        col1.metric("Équipage inscrit", len(contacts))
        col2.metric("Sorties réalisées", len(sorties))
        st.info("Utilisez le menu à gauche pour naviguer.")

    elif menu == "Carnet d'adresses":
        st.title("🗂️ Carnet d'adresses")
        # Formulaire d'ajout
        with st.expander("➕ Ajouter un équipier"):
            nom = st.text_input("Nom et Prénom")
            tel = st.text_input("Téléphone")
            urgence = st.text_input("Contact d'urgence")
            if st.button("Enregistrer le marin"):
                contacts.append({"Nom": nom, "Tél": tel, "Urgence": urgence})
                sauvegarder_donnees('contacts.json', contacts)
                st.success("Ajouté !")
                st.rerun()
        
        st.divider()

        # Liste avec option de suppression
        if contacts:
            for i, c in enumerate(contacts):
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{c['Nom']}** - {c['Tél']}")
                # On crée un bouton supprimer unique pour chaque marin
                if col2.button("🗑️", key=f"del_{i}"):
                    contacts.pop(i) # Enlever le marin de la liste
                    sauvegarder_donnees('contacts.json', contacts)
                    st.rerun()
        else:
            st.info("Le carnet est vide.")
        
        if contacts:
            st.table(pd.DataFrame(contacts))

    elif menu == "Planifier une sortie":
        st.title("⛵ Nouvelle sortie")
        nom_sortie = st.text_input("Nom de la navigation")
        date_sortie = st.date_input("Date", datetime.now())
        selection = st.multiselect("Qui est à bord ?", [c['Nom'] for c in contacts])
        if st.button("Valider la sortie"):
            sorties.append({"Date": str(date_sortie), "Nom": nom_sortie, "Equipage": selection})
            sauvegarder_donnees('sorties.json', sorties)
            st.success("Sortie enregistrée !")

    elif menu == "Historique":
        st.title("📜 Historique des navigations")
        for s in reversed(sorties):
            st.write(f"**{s['Date']}** - {s['Nom']}")
            st.write(f"Équipage : {', '.join(s['Equipage'])}")
            st.divider()

