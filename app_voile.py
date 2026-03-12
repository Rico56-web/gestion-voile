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
    .fiche-globale { border-radius: 12px; background: white; margin-bottom: 15px; padding: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #ddd; }
    .border-cmn { border: 4px solid #0056b3 !important; background-color: #f0f7ff !important; }
    .statut-badge { padding: 4px 12px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; color: white; float: right; margin-left: 5px; }
    .calendar-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .calendar-table th { background-color: #1a2a6c; color: white; padding: 10px; border: 1px solid #ddd; }
    .calendar-table td { height: 50px; border: 1px solid #ddd; text-align: center; font-weight: bold; }
    .day-ok { background-color: #2ecc71 !important; color: white; }
    .day-attente { background-color: #f1c40f !important; color: black; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
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
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})

def safe_get(r, key):
    val = r.get(key)
    return str(val).strip() if pd.notna(val) and val is not None else ""

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "m_edit_idx" not in st.session_state: st.session_state.m_edit_idx = None
if "confirm_del" not in st.session_state: st.session_state.confirm_del = None

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m = st.columns(6)
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]
for i, name in enumerate(menu):
    if m[i].button(name, key=f"n_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.session_state.m_edit_idx = None; st.rerun()

df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
        new = {"DateNav": "01/01/2026", "NbreJours": "1", "Statut": "En attente", "Paiement": "Pas payé", "Société": "", "Prénom": "Nouveau", "Nom": "Contact", "Téléphone": "", "Email": "", "Prix": "0.00", "Notes": ""}
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json"); st.rerun()

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df_c.loc[idx]
        st.subheader("📝 Modifier Mission")
        u_pre = st.text_input("Prénom", value=safe_get(r, 'Prénom'))
        u_nom = st.text_input("Nom", value=safe_get(r, 'Nom'))
        u_soc = st.text_input("Société", value=safe_get(r, 'Société'))
        u_tel = st.text_input("Téléphone", value=safe_get(r, 'Téléphone'))
        u_mail = st.text_input("Email", value=safe_get(r, 'Email'))
        u_date = st.text_input("Date (JJ/MM/AAAA)", value=safe_get(r, 'DateNav'))
        u_jours = st.text_input("Nbre Jours", value=safe_get(r, 'NbreJours'))
        u_prix = st.text_input("Prix Total (€)", value=safe_get(r, 'Prix'))
        u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(safe_get(r, 'Statut')) if safe_get(r, 'Statut') in ["En attente", "OK", "Terminé", "Refusé"] else 0)
        u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=["Pas payé", "Payé"].index(safe_get(r, 'Paiement')) if safe_get(r, 'Paiement') in ["Pas payé", "Payé"] else 0)
        u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
        
        if st.button("💾 ENREGISTRER"):
            df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
            df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
            df_c.at[idx, 'NbreJours'] = u_jours
            df_c.at[idx, 'Prix'] = f"{float(u_prix or 0):.2f}"
            df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
            sauvegarder_data(df_c, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
    else:
        for i, r in df_c.iterrows():
            p_val = f"{float(safe_get(r, 'Prix') or 0):.2f}"
            soc = safe_get(r, 'Société')
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            h = f'<div class="fiche-globale {cl_b}">'
            h += f'<div class="societe-style">{soc or "PARTICULIER"}</div>'
            h += f'<div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>'
            h += f'📅 {safe_get(r, "DateNav")} ({safe_get(r, "NbreJours")}j) | 💰 <b>{p_val} €</b><br>'
            h += f'🏷️ Statut: {safe_get(r, "Statut")} | 💳 {safe_get(r, "Paiement")}</div>'
            st.markdown(h, unsafe_allow_html=True)
            c1, c2 = st.columns([1, 4])
            if c1.button("✏️", key=f"ec_{i}"): st.session_state.edit_idx = i; st.rerun()
            if c2.button("🗑️ SUPPRIMER", key=f"dc_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "contacts.json"); st.rerun()

# --- 5. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning Mensuel 2026")
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    sel_m_nom = st.selectbox("Mois", mois_noms, index=datetime.now().month - 1)
    sel_m = mois_noms.index(sel_m_nom) + 1
    
    jours_occ = {}
    for _, r in df_c.iterrows():
        try:
            dp = safe_get(r, 'DateNav').split('/')
            if int(dp[1]) == sel_m:
                for j in range(int(dp[0]), int(dp[0]) + int(safe_get(r, 'NbreJours'))):
                    jours_occ[j] = safe_get(r, 'Statut')
        except: continue

    cal_mat = calendar.monthcalendar(2026, sel_m)
    h_cal = '<table class="calendar-table"><thead><tr><th>Lun</th><th>Mar</th><th>Mer</th><th>Jeu</th><th>Ven</th><th>Sam</th><th>Dim</th></tr></thead><tbody>'
    for sem in cal_mat:
        h_cal += '<tr>'
        for jour in sem:
            cl = ""
            if jour != 0 and jour in jours_occ:
                cl = "day-ok" if jours_occ[jour] == "OK" else "day-attente"
            h_cal += f'<td class="{cl}">{jour if jour != 0 else ""}</td>'
        h_cal += '</tr>'
    st.markdown(h_cal + '</tbody></table>', unsafe_allow_html=True)

# --- 6. PAGE STATS ---
elif st.session_state.page == "STATS":
    st.subheader("📊 Historique Financier 2026")
    stats_data = []
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    for m_idx in range(1, 13):
        rec, prev, frs = 0.0, 0.0, 0.0
        if not df_c.empty:
            for _, r in df_c.iterrows():
                try:
                    rm = int(safe_get(r, 'DateNav').split('/')[1])
                    if rm == m_idx:
                        p = float(safe_get(r, 'Prix') or 0)
                        if safe_get(r, 'Paiement') == "Payé": rec += p
                        elif safe_get(r, 'Statut') == "OK": prev += p
                except: continue
        if not df_m.empty:
            for _, r in df_m.iterrows():
                try:
                    rm = int(safe_get(r, 'Date').split('/')[1])
                    if rm == m_idx: frs += float(safe_get(r, 'Prix') or 0)
                except: continue
        
        stats_data.append({
            "Mois": m_noms[m_idx-1],
            "Recettes (€)": f"{rec:.2f}",
            "Prévisions (€)": f"{prev:.2f}",
            "Frais (€)": f"{frs:.2f}",
            "Total (€)": f"{(rec - frs):.2f}"
        })
    
    st_df = pd.DataFrame(stats_data)
    # Ligne Total de fin
    t_rec = sum(float(x) for x in st_df["Recettes (€)"])
    t_pre = sum(float(x) for x in st_df["Prévisions (€)"])
    t_frs = sum(float(x) for x in st_df["Frais (€)"])
    tot_row = pd.DataFrame([{"Mois": "TOTAL", "Recettes (€)": f"{t_rec:.2f}", "Prévisions (€)": f"{t_pre:.2f}", "Frais (€)": f"{t_frs:.2f}", "Total (€)": f"{(t_rec - t_frs):.2f}"}])
    st.table(pd.concat([st_df, tot_row], ignore_index=True))

# --- 7. PAGE MAINTENANCE ---
elif st.session_state.page == "MAINT":
    st.subheader("🔧 Maintenance & Frais")
    if st.button("➕ NOUVEAU FRAIS", use_container_width=True):
        new_m = {"Date": datetime.now().strftime("%d/%m/%2026"), "Cause": "Description", "Prix": "0.00"}
        df_m = pd.concat([pd.DataFrame([new_m]), df_m], ignore_index=True)
        sauvegarder_data(df_m, "maint.json"); st.rerun()

    if st.session_state.m_edit_idx is not None:
        idx = st.session_state.m_edit_idx
        r = df_m.loc[idx]
        u_d = st.text_input("Date", value=safe_get(r, 'Date'))
        u_c = st.text_input("Cause", value=safe_get(r, 'Cause'))
        u_p = st.text_input("Prix (€)", value=safe_get(r, 'Prix'))
        if st.button("💾 ENREGISTRER"):
            df_m.at[idx, 'Date'], df_m.at[idx, 'Cause'] = u_d, u_c
            df_m.at[idx, 'Prix'] = f"{float(u_p or 0):.2f}"
            sauvegarder_data(df_m, "maint.json"); st.session_state.m_edit_idx = None; st.rerun()
    else:
        for i, r in df_m.iterrows():
            st.markdown(f'<div class="fiche-globale">📅 {safe_get(r, "Date")} | 🏷️ {safe_get(r, "Cause")} | 💰 <b>{float(safe_get(r, "Prix") or 0):.2f} €</b></div>', unsafe_allow_html=True)
            c1, c2 = st.columns([1, 4])
            if c1.button("✏️", key=f"em_{i}"): st.session_state.m_edit_idx = i; st.rerun()
            if c2.button("🗑️ SUPPRIMER", key=f"dm_{i}"):
                df_m = df_m.drop(i); sauvegarder_data(df_m, "maint.json"); st.rerun()









































































































































































































































































































































































































































































