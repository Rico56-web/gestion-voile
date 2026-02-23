import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

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
    # Chargement
    contacts = charger_donnees('contacts.json')
    sorties = charger_donnees('sorties.json')

    # --- MENU ---
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
        
        # Formulaire d'ajout ou de modification
        if "edit_index" not in st.session_state:
            st.session_state.edit_index = -1

        titre_form = "➕ Ajouter un équipier" if st.session_state.edit_index == -1 else "✏️ Modifier l'équipier"
        with st.expander(titre_form, expanded=(st.session_state.edit_index != -1)):
            default_nom = "" if st.session_state.edit_index == -1 else contacts[st.session_state.edit_index]['Nom']
            default_tel = "" if st.session_state.edit_index == -1 else contacts[st.session_state.edit_index]['Tél']
            default_urg = "" if st.session_state.edit_index == -1 else contacts[st.session_state.edit_index]['Urgence']
            
            new_nom = st.text_input("Nom et Prénom", value=default_nom)
            new_tel = st.text_input("Téléphone", value=default_tel)
            new_urg = st.text_input("Contact d'urgence", value=default_urg)
            
            c1, c2 = st.columns(2)
            if c1.button("Enregistrer"):
                new_data = {"Nom": new_nom, "Tél": new_tel, "Urgence": new_urg}
                
                # --- SÉCURITÉ ANTI-DOUBLON ---
                # On vérifie si le nom existe déjà (seulement pour un nouvel ajout)
                noms_existants = [c['Nom'].lower().strip() for c in contacts]
                
                if st.session_state.edit_index == -1: # Si c'est un nouvel ajout
                    if new_nom.lower().strip() in noms_existants:
                        st.error("⚠️ Ce marin est déjà dans la liste !")
                    elif new_nom.strip() == "":
                        st.error("⚠️ Le nom ne peut pas être vide.")
                    else:
                        contacts.append(new_data)
                        sauvegarder_donnees('contacts.json', contacts)
                        st.rerun()
                else: # Si c'est une modification
                    contacts[st.session_state.edit_index] = new_data
                    st.session_state.edit_index = -1
                    sauvegarder_donnees('contacts.json', contacts)
                    st.rerun()
            
            if st.session_state.edit_index != -1:
                if c2.button("Annuler"):
                    st.session_state.edit_index = -1
                    st.rerun()

        st.divider()
        if contacts:
            for i, c in enumerate(contacts):
                col_n, col_m, col_s = st.columns([3, 1, 1])
                col_n.write(f"**{c['Nom']}** ({c['Tél']})")
                if col_m.button("✏️", key=f"edit_{i}"):
                    st.session_state.edit_index = i
                    st.rerun()
                if col_s.button("🗑️", key=f"del_{i}"):
                    contacts.pop(i)
                    sauvegarder_donnees('contacts.json', contacts)
                    st.rerun()

    elif menu == "Planifier une sortie":
        st.title("⛵ Nouvelle sortie")
        n_sortie = st.text_input("Nom de la navigation")
        d_sortie = st.date_input("Date", datetime.now())
        sel = st.multiselect("Qui est à bord ?", [c['Nom'] for c in contacts])
        if st.button("Valider la sortie"):
            sorties.append({"Date": str(d_sortie), "Nom": n_sortie, "Equipage": sel})
            sauvegarder_donnees('sorties.json', sorties)
            st.success("Sortie enregistrée !")

    elif menu == "Historique":
        st.title("📜 Historique")
        if sorties:
            for i, s in enumerate(reversed(sorties)):
                idx = len(sorties) - 1 - i
                col_h, col_del = st.columns([4, 1])
                col_h.write(f"**{s['Date']}** - {s['Nom']} ({', '.join(s['Equipage'])})")
                if col_del.button("🗑️", key=f"del_s_{idx}"):
                    sorties.pop(idx)
                    sauvegarder_donnees('sorties.json', sorties)
                    st.rerun()
                st.divider()
        else:
            st.write("Aucune sortie enregistrée.")

