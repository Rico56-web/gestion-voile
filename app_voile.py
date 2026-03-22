import streamlit as st
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

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
if "del_confirm_idx" not in st.session_state: st.session_state.del_confirm_idx = None

st.title("⚓ Mes Missions")

# --- FORMULAIRE D'ÉDITION ---
if st.session_state.edit_idx is not None:
    idx = st.session_state.edit_idx
    val = df.iloc[idx]
    with st.form("edit_form"):
        st.subheader(f"Modifier {val['Prénom']}")
        c1, c2 = st.columns(2)
        u_pre = c1.text_input("Prénom", val['Prénom'])
        u_nom = c2.text_input("Nom", val['Nom'])
        u_tel = c1.text_input("Téléphone", val['Téléphone'])
        u_mai = c2.text_input("Email", val['Email'])
        u_dna = c1.text_input("Date Nav", val['DateNav'])
        u_jou = c2.text_input("Jours", str(val['NbreJours']))
        if st.form_submit_button("Sauvegarder"):
            df.loc[idx, ['Prénom', 'Nom', 'Téléphone', 'Email', 'DateNav', 'NbreJours']] = [u_pre, u_nom, u_tel, u_mai, u_dna, u_jou]
            sauver_data(df)
            st.session_state.edit_idx = None
            st.rerun()

# --- AFFICHAGE DES FICHES ---
for idx, r in df.iterrows():
    
    # Sécurité affichage si vide
    tel = r['Téléphone'] if r['Téléphone'] else "📞 Non connu"
    mail = r['Email'] if r['Email'] else "✉️ Non connu"
    
    # Lien WhatsApp
    tel_wa = str(tel).replace(" ", "").replace("+", "")
    link_wa = f"https://wa.me/{tel_wa}"

    # DESIGN DE LA FICHE (Sans composants complexes qui cachent les infos)
    with st.container(border=True):
        col_titre, col_date = st.columns([2, 1])
        col_titre.markdown(f"### {r['Prénom']} **{str(r['Nom']).upper()}**")
        col_date.write(f"📅 **{r['DateNav']}** ({r['NbreJours']}j)")
        
        if r['Société']: st.caption(f"🏛️ {r['Société']}")
        
        # AFFICHAGE CLAIR DES CONTACTS
        st.write(f"📱 **Tel:** {tel}")
        st.write(f"📧 **Mail:** {mail}")
        
        # BOUTONS D'APPEL DIRECT (LIENS)
        st.markdown(f"[📞 Appeler](tel:{tel}) | [💬 WhatsApp]({link_wa}) | [✉️ Écrire](mailto:{mail})")
        
        st.divider()
        
        # ACTIONS : MODIFIER / REBOOK / SUPPRIMER
        b1, b2, b3 = st.columns(3)
        
        if b1.button("✏️ Modif", key=f"ed_{idx}", use_container_width=True):
            st.session_state.edit_idx = idx
            st.rerun()
            
        if b2.button("🔄 Book", key=f"rb_{idx}", use_container_width=True):
            new_r = r.copy()
            new_r['DateNav'] = "À définir"
            df = pd.concat([df, pd.DataFrame([new_r])], ignore_index=True)
            sauver_data(df)
            st.rerun()

        # LOGIQUE SUPPRIMER
        if st.session_state.del_confirm_idx == idx:
            if b3.button("⚠️ OK ?", key=f"conf_{idx}", type="primary", use_container_width=True):
                df = df.drop(idx).reset_index(drop=True)
                sauver_data(df)
                st.session_state.del_confirm_idx = None
                st.rerun()
        else:
            if b3.button("🗑️ Suppr", key=f"del_{idx}", use_container_width=True):
                st.session_state.del_confirm_idx = idx
                st.rerun()








































































































































































































































































































































































































































































