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
    
    /* BOUTONS NAVIGATION */
    button[data-testid="baseButton-primary"] { background-color: #ff4b4b !important; color: white !important; border: none !important; }
    button[data-testid="baseButton-secondary"] { background-color: #f0f2f6 !important; color: #31333f !important; border: 1px solid #d3d6db !important; }

    /* DESIGN DES FICHES */
    .fiche-globale { 
        border: 2px solid #1a2a6c; 
        border-radius: 12px; 
        background: white; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
        padding: 15px; 
    }
    .prenom-style { 
        font-size: 1.4rem; font-weight: bold; color: #1a2a6c; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; float: right; margin-left: 5px; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 8px; margin-top: 10px; }
    .societe-style { color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    .notes-box { background-color: #f9f9f9; border: 1px dashed #d3d6db; padding: 8px; border-radius: 5px; margin: 10px 0; font-size: 0.9rem; color: #2c3e50; }
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

def safe_get(r, key, default=""):
    val = r.get(key)
    if pd.isna(val) or val is None: return default
    s = str(val).strip()
    return s if s else default

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

st.markdown(f'<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
menu_list = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_list):
    active = (st.session_state.page == name)
    if m[i].button(name, use_container_width=True, key=f"nav_v12_{name}", type="primary" if active else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.rerun()

df = charger_data("contacts.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    c1, c2 = st.columns(2)
    v_arc = st.session_state.view_archive
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not v_arc else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if v_arc else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            col1, col2, col3, col4 = st.columns(4)
            u_date = col1.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_statut = col2.selectbox("Statut Mission", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))
            u_prix = col3.text_input("Prix (€)", value=safe_get(r, 'Prix', '0'))
            u_paye = col4.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'DateNav'], df.at[idx, 'Statut'], df.at[idx, 'Paiement'] = u_date, u_statut, u_paye
                df.at[idx, 'Prix'], df.at[idx, 'Notes'] = u_prix, u_notes
                df.at[idx, 'Société'], df.at[idx, 'Prénom'], df.at[idx, 'Nom'] = u_soc, u_pre, u_nom
                df.at[idx, 'Téléphone'], df.at[idx, 'Email'] = u_tel, u_mail
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("Annuler"): st.session_state.edit_idx = None; st.rerun()
    else:
        if not df.empty:
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if v_arc else df[~df['Statut'].isin(["Terminé", "Refusé"])]
            for i, r in df_disp.iterrows():
                tel, mail, soc, note = safe_get(r, 'Téléphone'), safe_get(r, 'Email'), safe_get(r, 'Société'), safe_get(r, 'Notes')
                s_val, p_val = safe_get(r, 'Statut').upper(), safe_get(r, 'Paiement').upper()
                c_s = "#3498db" if "TERM" in s_val else "#2ecc71" if "OK" in s_val else "#e74c3c" if "REFUS" in s_val else "#f1c40f"
                c_p = "#2ecc71" if "PAYÉ" == p_val else "#e74c3c"
                
                # Construction propre du HTML pour éviter l'affichage de texte brut
                html_fiche = f"""
                <div class="fiche-globale">
                    <span class="statut-badge" style="background:{c_p};">{safe_get(r, 'Paiement', 'Pas payé')}</span>
                    <span class="statut-badge" style="background:{c_s};">{safe_get(r, 'Statut')}</span>
                    <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    <div style="color:#e67e22; font-weight:bold; margin-top:5px;">📞 {tel}</div>
                    <p style="margin: 5px 0;">📅 <b>{safe_get(r, 'DateNav')}</b> | 💰 <b>{safe_get(r, 'Prix', '0')} €</b></p>
                    {f'<div class="notes-box">📝 {note}</div>' if note else ''}
                    <div style="margin-top:10px;">
                        <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                        <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    </div>
                </div>
                """
                st.markdown(html_fiche, unsafe_allow_html=True)
                
                c_edit, c_del = st.columns([1, 3])
                if c_edit.button("✏️ Modifier", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                if st.session_state.confirm_del == i:
                    if st.button("✅ CONFIRMER SUPPRESSION", key=f"conf_{i}"):
                        df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.session_state.confirm_del = None; st.rerun()
                    if st.button("❌ ANNULER", key=f"ann_{i}"): st.session_state.confirm_del = None; st.rerun()
                else:
                    if c_del.button("🗑️ Supprimer", key=f"del_{i}"): st.session_state.confirm_del = i; st.rerun()

# --- 5. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning des Navigations")
    if not df.empty:
        df_plan = df[~df['Statut'].isin(["Terminé", "Refusé"])].copy()
        for i, r in df_plan.sort_values('DateNav').iterrows():
            with st.expander(f"📅 {safe_get(r, 'DateNav')} | {safe_get(r, 'Société', 'CLIENT')} | {safe_get(r, 'Prénom')}"):
                st.write(f"**Statut :** {safe_get(r, 'Statut')} | **Prix :** {safe_get(r, 'Prix')} €")
                if safe_get(r, 'Notes'): st.info(f"Note : {safe_get(r, 'Notes')}")






































































































































































































































































































































































































































