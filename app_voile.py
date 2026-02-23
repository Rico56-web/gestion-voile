import streamlit as st
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Manager", layout="wide", page_icon="⛵")

# CSS pour compacter l'interface sur iPhone
st.markdown("""
    <style>
    /* Boutons d'action compacts */
    .stButton > button {
        padding: 2px 8px !important;
        font-size: 14px !important;
        border-radius: 5px !important;
        height: auto !important;
        min-height: 30px !important;
    }
    /* Harmonisation des textes et blocs */
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; border-left: 5px solid #0077b6; }
    .status-ok { background-color: #d4edda; padding: 8px; border-radius: 5px; border-left: 5px solid #28a745; margin-bottom: 5px; font-size: 14px; }
    .status-refuse { background-color: #f8d7da; padding: 8px; border-radius: 5px; border-left: 5px solid #dc3545; margin-bottom: 5px; font-size: 14px; }
    .status-attente { background-color: #fff3cd; padding: 8px; border-radius: 5px; border-left: 5px solid #ffc107; margin-bottom: 5px; font-size: 14px; }
    .note-box { background-color: #e7f3fe; padding: 10px; border-radius: 8px; border-left: 5px solid #2196f3; margin-bottom: 5px; font-size: 14px; }
    /* Ajustement des espaces entre les lignes de contacts */
    .contact-row { margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

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
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = -1
if "edit_note_idx" not in st.session_state:
    st.session_state.edit_note_idx = -1

if not st.session_state["authentifie"]:
    st.title("🔐 Accès Vesta")
    mdp = st.text_input("Code d'accès", type="password")
    if st.button("Monter à bord"):
        if mdp == "SKIPPER2026":
            st.session_state["authentifie"] = True
            st.rerun()
else:
    contacts = charger_donnees('contacts.json')
    echanges = charger_donnees('echanges.json')
    demandes = charger_donnees('demandes.json')
    check_data = charger_donnees('checklists.json')
    if not check_data:
        check_data = {"Départ": ["Météo", "Gilets"], "Arrivée": ["Vannes", "Batteries"]}

    st.sidebar.title("⚓ Vesta Navigation")
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "🗂️ Contacts", "⛵ Demandes", "💬 Historique", "📋 Checklists"])

    # --- 📊 DASHBOARD ---
    if menu == "📊 Dashboard":
        st.title("📊 Dashboard")
        col1, col2, col3 = st.columns(3)
        col1.metric("👥 Marins", len(contacts))
        col2.metric("💬 Notes", len(echanges))
        col3.metric("⏳ Attente", len([d for d in demandes if d.get('Statut') == 'En attente']))

    # --- 🗂️ CONTACTS ---
    elif menu == "🗂️ Contacts":
        st.title("🗂️ Carnet")
        search = st.text_input("🔍 Rechercher un nom...")
        
        with st.expander("📝 Ajouter / Modifier", expanded=(st.session_state.edit_idx != -1)):
            c_edit = contacts[st.session_state.edit_idx] if st.session_state.edit_idx != -1 else {"Nom": "", "Tél": "", "Email": ""}
            n = st.text_input("Nom", value=c_edit.get('Nom', ''))
            t = st.text_input("Tél", value=c_edit.get('Tél', ''))
            e = st.text_input("Email", value=c_edit.get('Email', ''))
            if st.button("💾 Enregistrer le contact"):
                if n:
                    new_c = {"Nom": n, "Tél": t, "Email": e}
                    if st.session_state.edit_idx == -1: contacts.append(new_c)
                    else: contacts[st.session_state.edit_idx] = new_c
                    sauvegarder_donnees('contacts.json', contacts)
                    st.session_state.edit_idx = -1
                    st.rerun()

        st.divider()
        for i, c in enumerate(contacts):
            if search.lower() in c['Nom'].lower():
                col_c1, col_c2, col_c3 = st.columns([4, 0.8, 0.8])
                tel = c.get('Tél', '')
                mail = c.get('Email', '')
                link_tel = f"📞 [{tel}](tel:{tel.replace(' ', '')})" if tel else ""
                link_mail = f"✉️ [{mail}](mailto:{mail})" if mail else ""
                
                col_c1.markdown(f"**{c['Nom']}** {link_tel}")
                if mail: col_c1.caption(link_mail)
                
                if col_c2.button("✏️", key=f"ed_c_{i}"):
                    st.session_state.edit_idx = i
                    st.rerun()
                if col_c3.button("🗑️", key=f"del_c_{i}"):
                    contacts.pop(i); sauvegarder_donnees('contacts.json', contacts); st.rerun()

    # --- ⛵ DEMANDES ---
    elif menu == "⛵ Demandes":
        st.title("⛵ Sorties")
        with st.expander("🆕 Nouvelle demande"):
            qui = st.selectbox("Qui ?", [c['Nom'] for c in contacts])
            statut = st.selectbox("Statut", ["En attente", "OK", "Refusé"])
            if st.button("Valider la demande"):
                demandes.append({"Nom": qui, "Date": str(datetime.now().date()), "Statut": statut})
                sauvegarder_donnees('demandes.json', demandes); st.rerun()
        
        for i, d in enumerate(reversed(demandes)):
            idx = len(demandes) - 1 - i
            css = "status-ok" if d['Statut'] == "OK" else "status-refuse" if d['Statut'] == "Refusé" else "status-attente"
            col_d1, col_d2 = st.columns([5, 1.2])
            col_d1.markdown(f'<div class="{css}">{d["Nom"]} - {d["Statut"]} ({d["Date"]})</div>', unsafe_allow_html=True)
            if col_d2.button("🗑️", key=f"del_d_{idx}"):
                demandes.pop(idx); sauvegarder_donnees('demandes.json', demandes); st.rerun()

    # --- 💬 HISTORIQUE ---
    elif menu == "💬 Historique":
        st.title("💬 Notes de bord")
        with st.expander("✍️ Écrire une note", expanded=(st.session_state.edit_note_idx != -1)):
            n_edit = echanges[st.session_state.edit_note_idx] if st.session_state.edit_note_idx != -1 else {"Nom": "", "Note": "", "Type": "📞 Téléphone"}
            with st.form("f_note", clear_on_submit=True):
                q = st.selectbox("Marin", [c['Nom'] for c in contacts], index=[c['Nom'] for c in contacts].index(n_edit['Nom']) if n_edit['Nom'] in [c['Nom'] for c in contacts] else 0)
                m = st.text_area("Texte de la note", value=n_edit['Note'])
                if st.form_submit_button("💾 Enregistrer"):
                    if m:
                        new_n = {"Nom": q, "Date": datetime.now().strftime("%d/%m %H:%M"), "Note": m}
                        if st.session_state.edit_note_idx == -1: echanges.append(new_n)
                        else: echanges[st.session_state.edit_note_idx] = new_n
                        sauvegarder_donnees('echanges.json', echanges)
                        st.session_state.edit_note_idx = -1
                        st.rerun()

        for i, e in enumerate(reversed(echanges)):
            idx = len(echanges) - 1 - i
            col_h1, col_h2, col_h3 = st.columns([4, 0.8, 0.8])
            col_h1.markdown(f'<div class="note-box"><strong>{e["Nom"]} ({e["Date"]})</strong><br>{e["Note"]}</div>', unsafe_allow_html=True)
            if col_h2.button("✏️", key=f"ed_h_{idx}"):
                st.session_state.edit_note_idx = idx
                st.rerun()
            if col_h3.button("🗑️", key=f"del_h_{idx}"):
                echanges.pop(idx); sauvegarder_donnees('echanges.json', echanges); st.rerun()

    # --- 📋 CHECKLISTS ---
    elif menu == "📋 Checklists":
        st.title("📋 Checklists")
        with st.expander("🛠️ Gérer les points de contrôle"):
            col_p1, col_p2 = st.columns([3, 1])
            new_p = col_p1.text_input("Nouveau point")
            c_p = col_p2.selectbox("Liste", ["Départ", "Arrivée"])
            if st.button("➕ Ajouter au protocole"):
                if new_p:
                    check_data[c_p].append(new_p)
                    sauvegarder_donnees('checklists.json', check_data); st.rerun()
            st.write("---")
            for cat in ["Départ", "Arrivée"]:
                st.write(f"**{cat} :**")
                for i, p in enumerate(check_data[cat]):
                    if st.button(f"🗑️ {p}", key=f"del_p_{cat}_{i}"):
                        check_data[cat].pop(i); sauvegarder_donnees('checklists.json', check_data); st.rerun()
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("⛵ Départ")
            for p in check_data["Départ"]: st.checkbox(p, key=f"ck_d_{p}")
        with c2:
            st.subheader("⚓ Arrivée")
            for p in check_data["Arrivée"]: st.checkbox(p, key=f"ck_a_{p}")
