import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    button[data-testid="baseButton-primary"] { background-color: #ff4b4b !important; color: white !important; }
    button[data-testid="baseButton-secondary"] { background-color: white !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; }
    .fiche-globale { border-radius: 12px; background: white; margin-bottom: 15px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .border-normal { border: 2px solid #1a2a6c; }
    .border-cmn { border: 4px solid #0056b3 !important; background-color: #f0f7ff !important; }
    .prenom-style { font-size: 1.5rem; font-weight: bold; color: #1a2a6c; }
    .societe-style { color: #7f8c8d; font-style: italic; font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid #eee; }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }
    .container-boutons { display: flex; gap: 8px; margin-top: 15px; border-top: 1px solid #eee; padding-top: 12px; }
    .btn-contact { flex: 1; text-align: center; padding: 10px 5px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.85rem; font-weight: bold; }
    .notes-box { background-color: #f8f9fa; border-left: 5px solid #1a2a6c; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 0.95rem; }
    .cal-case { border-radius: 8px; padding: 15px 5px; text-align: center; font-weight: bold; border: 1px solid #eee; margin: 2px; font-size: 1.1rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            return df
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
    return str(val).strip() if pd.notna(val) and val is not None else ""

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m = st.columns(6)
menu_names = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu_names):
    if m[i].button(name, key=f"nav_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.rerun()

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
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if v_arc else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        st.subheader("📝 Modifier")
        u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
        u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
        u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
        u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
        u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
        u_date = st.text_input("Date début (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
        u_jours = st.text_input("Nombre de jours", value=safe_get(r, 'NbreJours'))
        u_prix = st.text_input("Prix total (€)", value=safe_get(r, 'Prix'))
        u_statut = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut')) if safe_get(r, 'Statut') in ["En attente", "OK", "Terminé", "Refusé"] else 0)
        u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=["Pas payé", "Payé"].index(safe_get(r, 'Paiement')) if safe_get(r, 'Paiement') in ["Pas payé", "Payé"] else 0)
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
                p_val, s_val, jours = safe_get(r, 'Paiement'), safe_get(r, 'Statut'), safe_get(r, 'NbreJours') or "1"
                c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
                c_p = "#2ecc71" if "PAYÉ" in p_val.upper() else "#e74c3c"
                cl_b = "border-cmn" if "CMN" in soc.upper() else "border-normal"
                i_tel = f'<div style="color:#e67e22;font-weight:bold;">📞 {tel}</div>' if tel else ""
                i_mail = f'<div style="color:#7f8c8d;font-size:0.85rem;">✉️ {mail}</div>' if mail else ""
                
                h = f'<div class="fiche-globale {cl_b}"><span class="statut-badge" style="background:{c_p};">{p_val}</span><span class="statut-badge" style="background:{c_s};">{s_val}</span><div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div><div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>{i_tel}{i_mail}<p style="margin:8px 0;">📅 <b>{safe_get(r, "DateNav")}</b> ({jours} jrs) | 💰 <b>{safe_get(r, "Prix")} €</b></p><div class="notes-box">📝 {safe_get(r, "Notes") or "."}</div><div class="container-boutons"><a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a><a href="https://wa.me/{tel.replace(" ","")}" class="btn-contact" style="background:#25D366;">WhatsApp</a><a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Mail</a></div></div>'
                st.markdown(h, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                if c2.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

# --- 5. PAGE PLANNING (CALENDRIER) ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Calendrier des Missions")
    
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    sel_mois_nom = st.selectbox("Choisir le mois", mois_noms, index=datetime.now().month - 1)
    sel_m = mois_noms.index(sel_mois_nom) + 1

    # Dictionnaire des jours occupés {jour: statut}
    jours_occ = {}
    for _, r in df.iterrows():
        try:
            d_part = safe_get(r, 'DateNav').split('/')
            d, m, y = int(d_part[0]), int(d_part[1]), int(d_part[2])
            if m == sel_m and y == 2026:
                nb = int(safe_get(r, 'NbreJours') or 1)
                stut = safe_get(r, 'Statut')
                for j in range(d, d + nb):
                    if j not in jours_occ or stut == "OK": jours_occ[j] = stut
        except: continue

    # Affichage Calendrier
    cal_mat = calendar.monthcalendar(2026, sel_m)
    cols_h = st.columns(7)
    for i, j_nom in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]):
        cols_h[i].markdown(f"<center><b>{j_nom}</b></center>", unsafe_allow_html=True)

    for semaine in cal_mat:
        cols = st.columns(7)
        for i, jour in enumerate(semaine):
            if jour == 0: cols[i].write("")
            else:
                bg = "white"
                txt = "#333"
                if jour in jours_occ:
                    if jours_occ[jour] == "OK": bg, txt = "#2ecc71", "white"
                    elif jours_occ[jour] == "En attente": bg, txt = "#f1c40f", "black"
                cols[i].markdown(f'<div class="cal-case" style="background:{bg}; color:{txt};">{jour}</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Récapitulatif du mois")
    found = False
    for _, r in df.iterrows():
        try:
            m = int(safe_get(r, 'DateNav').split('/')[1])
            if m == sel_m:
                found = True
                s = safe_get(r, 'Statut')
                c = "green" if s == "OK" else "orange"
                st.markdown(f"**{safe_get(r, 'DateNav')}** ({safe_get(r, 'NbreJours')}j) : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()} - <span style='color:{c}; font-weight:bold;'>{s}</span>", unsafe_allow_html=True)
        except: continue
    if not found: st.info("Rien de prévu ce mois-ci.")

# --- PAGES SUIVANTES (À REMPLIR) ---
else:
    st.info(f"Page {st.session_state.page} en cours de développement.")






































































































































































































































































































































































































































































