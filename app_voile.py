import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. STYLE CSS (Interface complète) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 12px; background: white; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }
    .section-haute { padding: 20px; border-bottom: 1px solid #eee; }
    .section-basse { padding: 15px; background-color: #f8f9fc; }
    .prenom-style { font-size: 1.6rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; margin-bottom: 5px; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 5px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
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
    return default if pd.isna(val) or val is None else val

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
if m1.button("📋 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.session_state.edit_idx = None; st.rerun()
if m2.button("💰 STATS", use_container_width=True): st.session_state.page = "STATS"; st.rerun()
if m3.button("🔧 MAINT", use_container_width=True): st.session_state.page = "MAINT"; st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    c_f, c_p = st.columns(2)
    if c_f.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c_p.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}")
            c1, c2, c3 = st.columns(3)
            u_date_nav = c1.text_input("Date Nav", value=safe_get(r, 'DateNav'))
            u_nb_jours = c2.text_input("Nb jours", value=str(safe_get(r, 'NbJours')))
            u_statut = c3.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], 
                                    index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut', 'En attente')))

            c4, c5, c6 = st.columns(3)
            u_nom = c4.text_input("Nom", value=safe_get(r, 'Nom'))
            u_pre = c5.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_tel = c6.text_input("Téléphone", value=safe_get(r, 'Téléphone'))

            c7, c8, c9 = st.columns(3)
            u_email = c7.text_input("Email", value=safe_get(r, 'Email'))
            u_paye = c8.selectbox("Paiement", ["Pas payé", "Payé"], 1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_prix = c9.text_input("Prix Total (€)", value=str(safe_get(r, 'Prix', '0')))

            u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))

            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'DateNav'] = u_date_nav
                df.at[idx, 'NbJours'] = u_nb_jours
                df.at[idx, 'Statut'] = u_statut
                df.at[idx, 'Nom'] = u_nom
                df.at[idx, 'Prénom'] = u_pre
                df.at[idx, 'Téléphone'] = u_tel
                df.at[idx, 'Email'] = u_email
                df.at[idx, 'Paiement'] = u_paye
                df.at[idx, 'Prix'] = float(u_prix.replace(',','.'))
                df.at[idx, 'Société'] = u_soc
                df.at[idx, 'Notes'] = u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("❌ ANNULER"): st.session_state.edit_idx = None; st.rerun()
    
    else:
        # Filtrage Archives / Futures
        if st.session_state.view_archive:
            df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])]
        else:
            df_disp = df[~df['Statut'].isin(["Terminé", "Refusé"])]

        for i, r in df_disp.iterrows():
            tel = safe_get(r, 'Téléphone')
            mail = safe_get(r, 'Email')
            
            s_val = safe_get(r, 'Statut').upper()
            col_s = "#3498db" if "TERM" in s_val else "#2ecc71" if "OK" in s_val else "#e74c3c" if "REFUS" in s_val else "#f1c40f"
            
            p_val = safe_get(r, 'Paiement').upper()
            col_p = "#2ecc71" if p_val == "PAYÉ" else "#e74c3c"

            st.markdown(f"""
            <div class="fiche-globale">
                <div class="section-haute">
                    <div style="float:right; text-align:right;">
                        <span class="statut-badge" style="background:{col_s};">{safe_get(r, 'Statut', 'En attente')}</span><br>
                        <span class="statut-badge" style="background:{col_p};">{safe_get(r, 'Paiement', 'Pas payé')}</span>
                    </div>
                    <div class="prenom-style">{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}</div>
                    <div style="color:#e67e22; font-weight:bold;">📞 {tel} | ✉️ {mail}</div>
                    <p style="margin-top:10px;">
                        📅 <b>{safe_get(r, 'DateNav')}</b> ({safe_get(r, 'NbJours')} j.) | 🏢 <b>{safe_get(r, 'Société')}</b> | 💰 <b>{safe_get(r, 'Prix')} €</b>
                    </p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                </div>
                <div class="section-basse">
            """, unsafe_allow_html=True)
            
            cn, ce, cd = st.columns([0.5, 0.25, 0.25])
            cn.write(f"**Notes :** {safe_get(r, 'Notes')}")
            if ce.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.rerun()
            if cd.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)




















































































































































































































































































































































































































