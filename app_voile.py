
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Skipper Manager", layout="wide", page_icon="⛵")

# --- SÉCURITÉ : MOT DE PASSE ---
def verifier_mot_de_passe():
    if "authentifie" not in st.session_state:
        st.session_state["authentifie"] = False

    if not st.session_state["authentifie"]:
        st.title("🔐 Accès Skipper Manager")
        # Change 'SKIPPER2026' par le mot de passe de ton choix !
        mdp = st.text_input("Entrez le code d'accès au bord", type="password")
        if st.button("Monter à bord"):
            if mdp == "SKIPPER2026": 
                st.session_state["authentifie"] = True
                st.rerun()
            else:
                st.error("Code incorrect.")
        return False
    return True

# --- FONCTIONS DE GESTION DES DONNÉES ---
def charger_donnees(fichier):
    try:
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def sauvegarder_donnees(fichier, donnees):
    with open(fichier, 'w', encoding='utf-8') as f:
        json.dump(donnees, f, indent=4, ensure_ascii=False)

# Chargement initial
contacts = charger_donnees('contacts.json')
sorties = charger_donnees('sorties.json')

# --- INTERFACE PRINCIPALE ---
if verifier_mot_de_passe():
    # Fenêtre surgissante (Dialog)
    @st.dialog("Ajouter un nouveau coéquipier")
    def ajouter_marin_modal():
        st.write("Informations de sécurité")
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom et Prénom")
            statut = st.selectbox("Statut", ["Nouveau", "Ancien"])
        with col2:
            urgence = st.text_input("Urgence (Nom & Tél)")
        notes = st.text_area("Commentaires (Santé, niveau...)")
        
        if st.button("Valider"):
            if nom:
                contacts.append({"nom": nom, "statut": statut, "urgence": urgence, "notes": notes})
                sauvegarder_donnees('contacts.json', contacts)
                st.success("Enregistré !")
                st.rerun()

    # Menu
    st.sidebar.title("⚓ Menu Navigation")
    menu = st.sidebar.radio("Aller à :", ["Tableau de bord", "Carnet d'adresses", "Planifier une sortie", "Historique"])

    if menu == "Tableau de bord":
        st.title("Tableau de bord")
        c1, c2 = st.columns(2)
        c1.metric("Équipage", len(contacts))
        c2.metric("Sorties", len(sorties))

    elif menu == "Carnet d'adresses":
        st.title("🗂️ Carnet d'adresses")
        if st.button("➕ Nouveau Marin"): ajouter_marin_modal()
        if contacts:
            st.dataframe(pd.DataFrame(contacts), use_container_width=True)

    elif menu == "Planifier une sortie":
        st.title("⛵ Préparer une navigation")
        if st.button("➕ Nouveau Marin absent de la liste"): ajouter_marin_modal()
        st.divider()
        nom_s = st.text_input("Nom de la sortie")
        date_s = st.date_input("Date")
        selection = st.multiselect("Équipage", [c['nom'] for c in contacts])
        if st.button("Enregistrer la sortie"):
            sorties.append({"nom": nom_s, "date": str(date_s), "equipage": selection})
            sauvegarder_donnees('sorties.json', sorties)
            st.success("Sortie enregistrée !")

    elif menu == "Historique":
        st.title("📜 Historique")
        for s in reversed(sorties):
            with st.expander(f"{s['date']} - {s['nom']}"):

                st.write(f"Équipage : {', '.join(s['equipage'])}")
