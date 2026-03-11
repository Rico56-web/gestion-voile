import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. STYLE CSS ---
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; }
    .fiche-globale { border: 2px solid #1a2a6c; border-radius: 12px; background: white; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); overflow: hidden; }
    .section-haute { padding: 20px; border-bottom: 1px solid #eee; }
    .section-basse { padding: 15px; background-color: #f8f9fc; }
    .prenom-style { font-size: 1.6rem; font-weight: bold; color: #1a2a6c; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; display: inline-block; margin-bottom: 5px; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 6px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 5px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE BASE ---
def to_f(val):
    try: return float(str(val).replace(',', '.').replace('€', '').replace(' ', '').strip())
    except: return 0.0

def safe_get_index(liste, valeur):
    try: return liste.index(valeur)
    except: return 0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
if m1.button("📋 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"; st.rerun()
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
            st.subheader(f"Détails complets : {r.get('Prénom','')} {r.get('Nom','')}")
            # Champs organisés selon ton ordre mais groupés
            c1, c2, c3 = st.columns(3)
            u_date_nav = c1.text_input("Date Nav", r.get('Date Nav',''))
            u_nb_jours = c2.text_input("Nb jours", r.get('Nb jours',''))
            u_statut = c3.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=safe_get_index(["En attente", "OK", "Terminé", "Refusé"], r.get('Statut')))

            c4, c5, c6 = st.columns(3)
            u_nom = c4.text_input("Nom", r.get('Nom',''))
            u_pre = c5.text_input("Prénom", r.get('Prénom',''))
            u_tel = c6.text_input("Téléphone", r.get('Téléphone',''))

            c7, c8, c9 = st.columns(3)
            u_mail = c7.text_input("Mail", r.get('Mail',''))
            u_paye = c8.selectbox("Paiement", ["Pas payé", "Payé"], index=safe_get_index(["Pas payé", "Payé"], r.get('Paiement')))
            u_prix = c9.text_input("Prix (€)", str(r.get('Prix','0')))

            # Champs de maintenance (disponibles ici mais masqués sur la fiche)
            st.divider()
            c10, c11, c12 = st.columns(3)
            u_milles = c10.text_input("Milles", r.get('Milles',''))
            u_hres = c11.text_input("Heures moteur", r.get('Heures moteur',''))
            u_pass = c12.text_input("Passager", r.get('Passager',''))

            u_notes = st.text_area("Notes", r.get('Notes',''))

            if st.form_submit_button("💾 ENREGISTRER"):
                data_upd = {
                    'Date Nav': u_date_nav, 'Nb jours': u_nb_jours, 'Statut': u_statut,
                    'Nom': u_nom, 'Prénom': u_pre, 'Téléphone': u_tel, 'Mail': u_mail,
                    'Paiement': u_paye, 'Prix': to_f(u_prix), 'Milles': u_milles,
                    'Heures moteur': u_hres, 'Passager': u_pass, 'Notes': u_notes
                }
                for k, v in data_upd.items(): df.at[idx, k] = v
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("❌ ANNULER"): st.session_state.edit_idx = None; st.rerun()
    else:
        df_disp = df[df['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df[~df['Statut'].isin(["Terminé", "Refusé"])]
        
        for i, r in df_disp.iterrows():
            tel = str(r.get('Téléphone','')).strip()
            mail = str(r.get('Mail','')).strip()
            
            # Gestion Statut & Paiement (Couleurs)
            s_val = str(r.get('Statut','')).upper()
            col_s = "#3498db" if "TERM" in s_val else "#2ecc71" if "OK" in s_val else "#e74c3c" if "REFUS" in s_val else "#f1c40f"
            p_val = str(r.get('Paiement','')).upper()
            txt_p = "Payé" if "PAY" in p_val and "PAS" not in p_val and "UN" not in p_val else "Pas payé"
            col_p = "#2ecc71" if txt_p == "Payé" else "#e74c3c"

            st.markdown(f"""
            <div class="fiche-globale">
                <div class="section-haute">
                    <div style="float:right; text-align:right;">
                        <span class="statut-badge" style="background:{col_s};">{r.get('Statut','En attente')}</span><br>
                        <span class="statut-badge" style="background:{col_p};">{txt_p}</span>
                    </div>
                    <div class="prenom-style">{r.get('Prénom','')} {str(r.get('Nom','')).upper()}</div>
                    <div style="color:#e67e22; font-weight:bold;">📞 {tel} | ✉️ {mail}</div>
                    <p style="margin-top:10px;">
                        📅 <b>{r.get('Date Nav','--')}</b> ({r.get('Nb jours','?')} j.) | 🏢 <b>{r.get('Société','')}</b> | 💰 <b>{r.get('Prix',0)} €</b>
                    </p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                </div>
                <div class="section-basse">
            """, unsafe_allow_html=True)
            c_n, c_b = st.columns([0.7, 0.3])
            c_n.write(f"**Notes :** {r.get('Notes','')}")
            if c_b.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)
















































































































































































































































































































































































































