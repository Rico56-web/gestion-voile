import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

# Date du jour en français
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
now = datetime.now()
date_bandeau = f"📅 {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"

st.markdown(f"""<style>
    .main-header {{ font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }}
    .date-header {{ text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }}
    button[data-testid="baseButton-primary"] {{ background-color: #ff4b4b !important; color: white !important; }}
    button[data-testid="baseButton-secondary"] {{ background-color: white !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; }}
    .fiche-globale {{ border-radius: 12px; background: white; margin-bottom: 15px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #ddd; }}
    .border-cmn {{ border: 4px solid #0056b3 !important; background-color: #f0f7ff !important; }}
    .prenom-style {{ font-size: 1.5rem; font-weight: bold; color: #1a2a6c; }}
    .societe-style {{ color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; }}
    .statut-badge {{ padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }}
    .container-boutons {{ display: flex; gap: 8px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 12px; }}
    .btn-contact {{ flex: 1; text-align: center; padding: 12px 5px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.9rem; font-weight: bold; }}
    .notes-box {{ background-color: #fdf2e9; border-left: 5px solid #e67e22; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 0.95rem; color: #2c3e50; }}
</style>""", unsafe_allow_html=True)

# --- 2. SÉCURITÉ ACCÈS ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("ACCÉDER"):
        if password == "SKIPPER2026":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect.")
    st.stop()

# --- 3. FONCTIONS DONNÉES ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            # S'assurer que les nouvelles colonnes existent
            for col in ['Notes', 'Société', 'NbreJours', 'Paiement']:
                if col not in df.columns: df[col] = ""
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})

def safe_get(r, key):
    val = r.get(key)
    return str(val).strip() if pd.notna(val) and val is not None else ""

# --- 4. NAVIGATION ---
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

m = st.columns(7)
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES", "LOG"]
for i, name in enumerate(menu):
    if m[i].button(name, key=f"nav_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()

df_c = charger_data("contacts.json")

# --- PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if st.button("➕ NOUVELLE MISSION", type="secondary", use_container_width=True):
        new = {"DateNav": now.strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("🚀 MISSIONS", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        with st.form("edit_form"):
            st.subheader("📝 Modifier la fiche")
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_date = st.text_input("Date (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
            u_jours = st.text_input("Nombre de Jours", value=safe_get(r, 'NbreJours'))
            u_prix = st.text_input("Prix (€)", value=safe_get(r, 'Prix'))
            u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut')) if safe_get(r, 'Statut') in ["En attente", "OK", "Terminé", "Refusé"] else 0)
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=1 if safe_get(r, 'Paiement') == "Payé" else 0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
                df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
                df_c.at[idx, 'NbreJours'], df_c.at[idx, 'Prix'] = u_jours, u_prix
                df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
                sauvegarder_data(df_c, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
        if st.button("Annuler"): st.session_state.edit_idx = None; st.rerun()

    else:
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
        for i, r in df_disp.iterrows():
            tel = safe_get(r, 'Téléphone')
            mail = safe_get(r, 'Email')
            soc = safe_get(r, 'Société')
            notes = safe_get(r, 'Notes')
            jours = safe_get(r, 'NbreJours') or "1"
            s_val = safe_get(r, 'Statut')
            pay_val = safe_get(r, 'Paiement')
            
            c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
            c_p = "#2ecc71" if "PAYÉ" == pay_val.upper() else "#e74c3c"
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            
            # WhatsApp link clean
            wa_tel = tel.replace(" ", "").replace("+", "")

            # AFFICHAGE DE LA FICHE
            st.markdown(f'''<div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
                <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
                📅 <b>{safe_get(r, "DateNav")}</b> ({jours} jours) | 💰 <b>{safe_get(r, "Prix")} €</b><br>
                
                <div class="notes-box">📝 <b>Notes :</b> {notes if notes else "Aucune note."}</div>

                <div class="container-boutons">
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 APPEL</a>
                    <a href="https://wa.me/{wa_tel}" target="_blank" class="btn-contact" style="background:#25D366;">💬 WHATSAPP</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ EMAIL</a>
                </div>
            </div>''', unsafe_allow_html=True)

            col1, col2 = st.columns([1, 4])
            if col1.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
            if col2.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "contacts.json"); st.rerun()

# --- FIN DU CODE ---


































































































































































































































































































































































































































































