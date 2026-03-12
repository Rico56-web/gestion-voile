import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    
    /* STYLE DES FICHES */
    .fiche-globale { 
        border: 2px solid #1a2a6c; 
        border-radius: 12px; 
        background: white; 
        margin-bottom: 10px; 
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .prenom-style { font-size: 1.4rem; font-weight: bold; color: #1a2a6c; }
    .societe-style { color: #7f8c8d; font-style: italic; font-weight: bold; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-bottom: 5px; }
    .statut-badge { padding: 2px 10px; border-radius: 10px; font-size: 0.75rem; font-weight: bold; color: white; float: right; margin-left: 5px; }
    .notes-box { background-color: #f1f2f6; border-left: 5px solid #1a2a6c; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 0.9rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update", "content": content, "sha": sha})

def safe_get(r, key):
    val = r.get(key)
    if pd.isna(val) or val is None: return ""
    return str(val).strip()

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    if m[i].button(name, use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if st.button("➕ NOUVEAU CONTACT", use_container_width=True):
        new_row = {"DateNav": "01/01/2026", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0", "Notes": ""}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        sauvegarder_data(df, "contacts.json"); st.rerun()

    c1, c2 = st.columns(2)
    v_arc = st.session_state.view_archive
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not v_arc else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if v_arc else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        # --- FORMULAIRE DE MODIFICATION ---
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader("📝 Modification")
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_soc = st.text_input("Société / Bateau", value=safe_get(r, 'Société'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_date = st.text_input("Date", value=safe_get(r, 'DateNav'))
            u_prix = st.text_input("Prix (€)", value=safe_get(r, 'Prix'))
            u_statut = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut') or "En attente"))
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            if st.form_submit_button("💾 SAUVEGARDER"):
                d = {'DateNav':u_date,'Statut':u_statut,'Paiement':u_paye,'Prix':u_prix,'Société':u_soc,'Prénom':u_pre,'Nom':u_nom,'Téléphone':u_tel,'Email':u_mail,'Notes':u_notes}
                for k,v in d.items(): df.at[idx, k] = v
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()

    else:
        # --- AFFICHAGE DES FICHES ---
        if not df.empty:
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            for i, r in df_disp.iterrows():
                tel = safe_get(r, 'Téléphone')
                mail = safe_get(r, 'Email')
                note = safe_get(r, 'Notes')
                
                # Badges de couleur
                c_s = "#3498db" if "TERM" in r['Statut'].upper() else "#2ecc71" if "OK" in r['Statut'].upper() else "#e74c3c"
                c_p = "#2ecc71" if "PAYÉ" in r['Paiement'].upper() else "#e74c3c"

                # Contenu de la fiche (SANS les boutons de contact)
                st.markdown(f"""
                <div class="fiche-globale">
                    <span class="statut-badge" style="background:{c_p};">{r['Paiement']}</span>
                    <span class="statut-badge" style="background:{c_s};">{r['Statut']}</span>
                    <div class="societe-style">{safe_get(r, 'Société') or "PARTICULIER"}</div>
                    <div class="prenom-style">{r['Prénom']} {r['Nom'].upper()}</div>
                    <p style="margin:5px 0;">📅 <b>{r['DateNav']}</b> | 💰 <b>{r['Prix']} €</b></p>
                    {f'<div class="notes-box">📝 {note}</div>' if note else ''}
                </div>
                """, unsafe_allow_html=True)

                # BOUTONS NATIFS STREAMLIT (Plus de bug possible !)
                bt1, bt2, bt3, bt4, bt5 = st.columns([1,1,1,1,1])
                
                if tel:
                    bt1.link_button("📞 Tel", f"tel:{tel}")
                    bt2.link_button("💬 WA", f"https://wa.me/{tel.replace(' ','')}")
                if mail:
                    bt3.link_button("✉️ Mail", f"mailto:{mail}")
                
                if bt4.button("✏️", key=f"ed_{i}"):
                    st.session_state.edit_idx = i; st.rerun()
                if bt5.button("🗑️", key=f"del_{i}"):
                    df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()
                st.divider()

# --- 5. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning")
    if not df.empty:
        df_plan = df[~df['Statut'].isin(["Terminé", "Refusé"])].copy()
        for i, r in df_plan.sort_values('DateNav').iterrows():
            with st.expander(f"📅 {safe_get(r, 'DateNav')} | {safe_get(r, 'Société') or 'CLIENT'}"):
                st.write(f"**Contact :** {r['Prénom']} {r['Nom']}")
                if st.button("Ouvrir la fiche", key=f"p_{i}"):
                    st.session_state.page = "CONTACTS"; st.session_state.edit_idx = i; st.rerun()














































































































































































































































































































































































































































