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
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 12px; background: white; margin-bottom: 15px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .prenom-style { font-size: 1.5rem; font-weight: bold; color: #1a2a6c; }
    .societe-style { color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }
    .container-boutons { display: flex; gap: 8px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 12px; flex-wrap: nowrap; }
    .btn-contact { flex: 1; text-align: center; padding: 10px 5px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.85rem; font-weight: bold; }
    .notes-box { background-color: #f8f9fa; border-left: 5px solid #1a2a6c; padding: 12px; border-radius: 4px; margin: 12px 0; font-size: 0.95rem; color: #2c3e50; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            if 'NbreJours' not in df.columns: df['NbreJours'] = "1"
            return df
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
    return str(val).strip()

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
menu_names = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_names):
    if m[i].button(name, use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.session_state.confirm_del = None; st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
        new_row = {"DateNav": "01/01/2026", "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0", "Notes": ""}
        df = pd.concat([pd.DataFrame([new_row]), df], ignore_index=True)
        sauvegarder_data(df, "contacts.json"); st.rerun()

    c1, c2 = st.columns(2)
    v_arc = st.session_state.view_archive
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not v_arc else "secondary"):
        st.session_state.view_archive = False; st.session_state.confirm_del = None; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if v_arc else "secondary"):
        st.session_state.view_archive = True; st.session_state.confirm_del = None; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        st.subheader("📝 Modifier")
        
        u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
        u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
        u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
        u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
        u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
        u_date = st.text_input("Date début", value=safe_get(r, 'DateNav'))
        u_jours = st.text_input("Nombre de jours", value=safe_get(r, 'NbreJours'))
        u_prix = st.text_input("Prix total (€)", value=safe_get(r, 'Prix'))
        
        statuts = ["En attente", "OK", "Terminé", "Refusé"]
        s_val = safe_get(r, 'Statut')
        s_idx = statuts.index(s_val) if s_val in statuts else 0
        u_statut = st.selectbox("Statut", statuts, index=s_idx)
        
        paiements = ["Pas payé", "Payé"]
        p_val = safe_get(r, 'Paiement')
        p_idx = paiements.index(p_val) if p_val in paiements else 0
        u_paye = st.selectbox("Paiement", paiements, index=p_idx)
        
        u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
        
        if st.button("💾 ENREGISTRER", type="primary", use_container_width=True):
            df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Société'] = u_pre, u_nom, u_soc
            df.at[idx, 'Téléphone'], df.at[idx, 'Email'], df.at[idx, 'DateNav'] = u_tel, u_mail, u_date
            df.at[idx, 'NbreJours'], df.at[idx, 'Prix'] = u_jours, u_prix
            df.at[idx, 'Statut'], df.at[idx, 'Paiement'] = u_statut, u_paye
            df.at[idx, 'Notes'] = u_notes
            sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
        if st.button("Annuler", use_container_width=True):
            st.session_state.edit_idx = None; st.rerun()

    else:
        if not df.empty:
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            for i, r in df_disp.iterrows():
                tel, mail, soc = safe_get(r, 'Téléphone'), safe_get(r, 'Email'), safe_get(r, 'Société')
                jours = safe_get(r, 'NbreJours') or "1"
                p_val, s_val = safe_get(r, 'Paiement'), safe_get(r, 'Statut')
                
                c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
                c_p = "#2ecc71" if "PAYÉ" in p_val.upper() else "#e74c3c"
                
                info_tel = f'<div style="color:#e67e22; font-weight:bold; font-size:0.95rem;">📞 {tel}</div>' if tel else ""
                info_mail = f'<div style="color:#7f8c8d; font-size:0.85rem;">✉️ {mail}</div>' if mail else ""
                
                st.markdown(f"""
                <div class="fiche-globale">
                    <span class="statut-badge" style="background:{c_p};">{p_val if p_val else "Pas payé"}</span>
                    <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                    <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    {info_tel} {info_mail}
                    <p style="margin: 8px 0; font-size:1.05rem;">
                        📅 <b>{safe_get(r, 'DateNav')}</b> <span style="color:#7f8c8d; font-size:0.9rem;">({jours} jrs)</span> | 💰 <b>{safe_get(r, 'Prix')} €</b>
                    </p>
                    <div class="notes-box">📝 {safe_get(r, 'Notes') or "."}</div>
                    <div class="container-boutons">
                        <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                        <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Mail</a>
                    </div>
                </div>"""
                
                if st.session_state.confirm_del == i:
                    col1, col2 = st.columns(2)
                    if col1.button("⚠️ CONFIRMER", key=f"conf_{i}", type="primary", use_container_width=True):
                        df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.session_state.confirm_del = None; st.rerun()
                    if col2.button("❌ ANNULER", key=f"ann_{i}", use_container_width=True):
                        st.session_state.confirm_del = None; st.rerun()
                else:
                    c1, c2 = st.columns([1, 4])
                    if c1.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.session_state.confirm_del = None; st.rerun()
                    if c2.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True): st.session_state.confirm_del = i; st.rerun()

# --- 5. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning des missions")
    if not df.empty:
        df_plan = df[~df['Statut'].isin(["Terminé", "Refusé"])].copy()
        for i, r in df_plan.sort_values('DateNav').iterrows():
            with st.expander(f"📅 {safe_get(r, 'DateNav')} | {safe_get(r, 'Société') or 'CLIENT'}"):
                st.write(f"**Skipper :** {safe_get(r, 'Prénom')} {safe_get(r, 'Nom')}")
                st.write(f"**Durée :** {safe_get(r, 'NbreJours')} jour(s)")
                if st.button("Ouvrir la fiche", key=f"p_{i}"):
                    st.session_state.page = "CONTACTS"; st.session_state.edit_idx = i; st.rerun()






























































































































































































































































































































































































































































