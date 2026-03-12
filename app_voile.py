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
    
    button[data-testid="baseButton-primary"] { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    button[data-testid="baseButton-secondary"] { background-color: #ffffff !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; }

    .fiche-globale { 
        border: 2px solid #1a2a6c; 
        border-radius: 12px; 
        background: white; 
        margin-bottom: 10px; 
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .prenom-style { font-size: 1.5rem; font-weight: bold; color: #1a2a6c; }
    .societe-style { color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }
    .btn-contact { display: inline-block; padding: 10px 14px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 8px; margin-top: 10px; }
    .notes-box { background-color: #f8f9fa; border-left: 5px solid #1a2a6c; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 0.95rem; color: #2c3e50; }
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
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

def safe_get(r, key):
    val = r.get(key)
    if pd.isna(val) or val is None: return ""
    return str(val).replace('"', '&quot;').replace("'", "&apos;").strip()

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    if m[i].button(name, use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.session_state.confirm_del = None; st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
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
        # FORMULAIRE MODIF
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader("📝 Modifier")
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
            if st.form_submit_button("💾 ENREGISTRER"):
                d = {'DateNav':u_date,'Statut':u_statut,'Paiement':u_paye,'Prix':u_prix,'Société':u_soc,'Prénom':u_pre,'Nom':u_nom,'Téléphone':u_tel,'Email':u_mail,'Notes':u_notes}
                for k,v in d.items(): df.at[idx, k] = v
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()

    else:
        # LISTE DES FICHES
        if not df.empty:
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            for i, r in df_disp.iterrows():
                tel, mail, soc, note = safe_get(r, 'Téléphone'), safe_get(r, 'Email'), safe_get(r, 'Société'), safe_get(r, 'Notes')
                c_s = "#3498db" if "TERM" in r['Statut'].upper() else "#2ecc71" if "OK" in r['Statut'].upper() else "#e74c3c" if "REFUS" in r['Statut'].upper() else "#f1c40f"
                c_p = "#2ecc71" if "PAYÉ" in r['Paiement'].upper() else "#e74c3c"
                html_note = f'<div class="notes-box">📝 {note}</div>' if note else ""

                st.markdown(f"""
                <div class="fiche-globale">
                    <span class="statut-badge" style="background:{c_p};">{r['Paiement']}</span>
                    <span class="statut-badge" style="background:{c_s};">{r['Statut']}</span>
                    <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                    <div class="prenom-style">{r['Prénom']} {r['Nom'].upper()}</div>
                    <div style="color:#e67e22; font-weight:bold; margin-top:5px; font-size:1.1rem;">📞 {tel}</div>
                    <p style="margin: 8px 0;">📅 <b>{r['DateNav']}</b> | 💰 <b>{r['Prix']} €</b></p>
                    {html_note}
                    <div style="margin-top:15px; border-top: 1px solid #eee; padding-top:10px;">
                        <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                        <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # GESTION DES BOUTONS AVEC CONFIRMATION
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                
                if st.session_state.confirm_del == i:
                    if st.button("⚠️ CONFIRMER SUPPRESSION", key=f"conf_{i}", type="primary", use_container_width=True):
                        df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.session_state.confirm_del = None; st.rerun()
                    if st.button("❌ Annuler", key=f"ann_{i}", use_container_width=True):
                        st.session_state.confirm_del = None; st.rerun()
                else:
                    if c2.button("🗑️", key=f"del_{i}"):
                        st.session_state.confirm_del = i; st.rerun()

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
















































































































































































































































































































































































































































