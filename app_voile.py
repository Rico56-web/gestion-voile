import streamlit as st
import pd
import json
import requests
import base64
import time
from datetime import datetime

# --- CONFIGURATION GITHUB ---
REPO = st.secrets["GITHUB_REPO"]
TOKEN = st.secrets["GITHUB_TOKEN"]

def charger_data(fichier):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
        res = requests.get(url, headers={"Authorization": f"token {TOKEN}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, fichier):
    url = f"https://api.github.com/repos/{REPO}/contents/{fichier}"
    res = requests.get(url, headers={"Authorization": f"token {TOKEN}"})
    sha = res.json()['sha'] if res.status_code == 200 else None
    content = json.dumps(df.to_dict(orient="records"), indent=4, ensure_ascii=False)
    data = {"message": f"Maj {fichier}", "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'), "sha": sha}
    requests.put(url, headers={"Authorization": f"token {TOKEN}"}, json=data)

def safe_get(row, col):
    return str(row[col]) if col in row and pd.notnull(row[col]) else ""

# --- STYLE CSS (LE RÉEL) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""
    <style>
    .fiche-globale { background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); position: relative; }
    .border-cmn { border: 3px solid #3498db !important; }
    .statut-badge { float: right; padding: 4px 10px; border-radius: 15px; color: white; font-size: 11px; font-weight: bold; margin-left: 5px; }
    .societe-style { color: #7f8c8d; font-size: 12px; font-weight: bold; }
    .prenom-style { font-size: 18px; font-weight: bold; color: #2c3e50; margin: 5px 0; }
    .notes-box { background: #f9f9f9; padding: 8px; border-radius: 5px; font-size: 13px; margin-top: 10px; border-left: 3px solid #ddd; }
    .btn-contact { display: inline-block; padding: 8px 15px; border-radius: 5px; color: white !important; text-decoration: none !important; font-size: 13px; margin-right: 5px; margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- CHARGEMENT ---
df_c = charger_data("contacts.json")
if "page" not in st.session_state: st.session_state.page = "PLANNING"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "view_archive" not in st.session_state: st.session_state.view_archive = False

# --- TRI CHRONOLOGIQUE ---
if not df_c.empty and 'DateNav' in df_c.columns:
    try:
        df_c['temp_date'] = pd.to_datetime(df_c['DateNav'], format='%d/%m/%Y', errors='coerce')
        df_c = df_c.sort_values(by='temp_date', ascending=True).drop(columns=['temp_date'])
    except: pass

# --- BARRE LATÉRALE (TON MENU) ---
with st.sidebar:
    st.title("⚓ Vesta 2026")
    if st.button("📅 PLANNING", use_container_width=True): st.session_state.page = "PLANNING"
    if st.button("👤 CONTACTS", use_container_width=True): st.session_state.page = "CONTACTS"
    if st.button("🔧 MAINTENANCE", use_container_width=True): st.session_state.page = "MAINTENANCE"
    if st.button("📝 NOTES", use_container_width=True): st.session_state.page = "NOTES"
    if st.button("📊 STATS", use_container_width=True): st.session_state.page = "STATS"

# --- PAGE CONTACTS (LA COMPLÈTE) ---
if st.session_state.page == "CONTACTS":
    st.title("👤 Gestion des Contacts")
    
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
        new = {"DateNav": datetime.now().strftime("%d/%m/2026"), "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()

    c1, c2 = st.columns(2)
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        with st.form("edit_form"):
            u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
            u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
            u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
            u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
            u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
            u_date = st.text_input("Date (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
            u_jours = st.text_input("Jours", value=safe_get(r, 'NbreJours'))
            u_prix = st.text_input("Prix (€)", value=safe_get(r, 'Prix'))
            u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=0)
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=0)
            u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
            if st.form_submit_button("💾 ENREGISTRER"):
                df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
                df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
                df_c.at[idx, 'NbreJours'], df_c.at[idx, 'Prix'] = u_jours, u_prix
                df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
                sauvegarder_data(df_c, "contacts.json"); st.session_state.edit_idx = None; st.rerun()

    else:
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
        for i, r in df_disp.iterrows():
            soc, s_val, pay_val = safe_get(r, 'Société'), safe_get(r, 'Statut'), safe_get(r, 'Paiement')
            c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
            c_p = "#FF0000" if "PAS" in pay_val.upper() else "#2ecc71"
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            
            st.markdown(f'''<div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
                <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
                📅 <b>{safe_get(r, "DateNav")}</b> ({safe_get(r, "NbreJours")} jrs) | 💰 <b>{safe_get(r, "Prix")} €</b><br>
                📞 {safe_get(r, "Téléphone")} | ✉️ {safe_get(r, "Email")}
                <div class="notes-box">📝 {safe_get(r, "Notes") or "."}</div>
                <div class="container-boutons">
                    <a href="tel:{safe_get(r, "Téléphone")}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="https://wa.me/{safe_get(r, "Téléphone").replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                    <a href="mailto:{safe_get(r, "Email")}" class="btn-contact" style="background:#e67e22;">Mail</a>
                </div>
            </div>''', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"btn_{i}"): st.session_state.edit_idx = i; st.rerun()

# --- PAGE PLANNING (LE CALENDRIER) ---
elif st.session_state.page == "PLANNING":
    st.title("📅 Planning")
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Nov.", "Déc."]
    sel_mois = st.selectbox("Mois", range(1, 13), index=datetime.now().month - 1, format_func=lambda x: mois_noms[x-1])
    missions_dict = {str(safe_get(r, 'DateNav')).strip(): safe_get(r, 'Société') for _, r in df_c.iterrows()}
    import calendar
    cal = calendar.Calendar(firstweekday=0)
    jours_cal = cal.monthdatescalendar(2026, sel_mois)
    cols_h = st.columns(7)
    for i, j in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]): cols_h[i].write(f"**{j}**")
    for sem in jours_cal:
        cols = st.columns(7)
        for i, d in enumerate(sem):
            if d.month == sel_mois:
                d_str, bg, bord, info = d.strftime("%d/%m/%Y"), "#ffffff", "1px solid #eee", ""
                if d_str in missions_dict:
                    info = missions_dict[d_str][:10]
                    bg = "#e3f2fd" if "CMN" in info.upper() else "#ffffff"
                    bord = "2px solid #3498db" if "CMN" in info.upper() else "1px solid #2ecc71"
                cols[i].markdown(f'''<div style="background:{bg}; border:{bord}; padding:10px 2px; border-radius:5px; text-align:center; min-height:65px;"><div style="font-weight:bold;">{d.day}</div><div style="font-size:9px; color:#555;">{info}</div></div>''', unsafe_allow_html=True)

# --- MAINTENANCE & STATS ---
elif st.session_state.page == "MAINTENANCE":
    st.title("🔧 Maintenance")
    df_m = charger_data("maint.json")
    st.table(df_m)
elif st.session_state.page == "STATS":
    st.title("📊 Statistiques")
    if not df_c.empty:
        st.metric("Revenu Total 2026", f"{sum([float(x) for x in df_c['Prix'] if x]):.2f} €")
        st.bar_chart(df_c['Société'].value_counts())





























































































































































































































































































































































































































































































