import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
from datetime import datetime

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
    .btn-contact {{ flex: 1; text-align: center; padding: 10px 5px; border-radius: 8px; text-decoration: none !important; color: white !important; font-size: 0.85rem; font-weight: bold; }}
    .notes-box {{ background-color: #f8f9fa; border-left: 5px solid #1a2a6c; padding: 10px; border-radius: 4px; margin: 10px 0; font-size: 0.95rem; }}
    .calendar-table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }}
    .calendar-table th {{ background-color: #1a2a6c; color: white; padding: 10px; border: 1px solid #ddd; }}
    .calendar-table td {{ height: 50px; border: 1px solid #ddd; text-align: center; font-weight: bold; }}
    .day-ok {{ background-color: #2ecc71 !important; color: white; }}
    .day-attente {{ background-color: #f1c40f !important; color: black; }}
</style>""", unsafe_allow_html=True)

# --- 2. SÉCURITÉ ACCÈS ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("ACCÉDER"):
        if password == "SKIPPER2026":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Code incorrect.")
    st.stop()

# --- 3. FONCTIONS DONNÉES ---
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

# --- 4. NAVIGATION & ENTÊTE ---
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None
if "m_edit_idx" not in st.session_state: st.session_state.m_edit_idx = None
if "maint_confirm_del" not in st.session_state: st.session_state.maint_confirm_del = None

# PASSAGE À 7 COLONNES ET AJOUT DE "LOG"
m = st.columns(7) 
menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES", "LOG"]

for i, name in enumerate(menu):
    if m[i].button(name, key=f"nav_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.session_state.edit_idx = None
        st.session_state.m_edit_idx = None
        st.rerun()
        
# --- CHARGEMENT DES DONNÉES ---
df_c = charger_data("contacts.json")
df_m = charger_data("maint.json")

# --- TRI CHRONOLOGIQUE SÉCURISÉ (Version Robuste) ---
if not df_c.empty and 'DateNav' in df_c.columns:
    try:
        # On s'assure que DateNav est bien du texte et on nettoie les espaces
        df_c['DateNav'] = df_c['DateNav'].astype(str).str.strip()
        
        # Création de la colonne de tri
        df_c['temp_date'] = pd.to_datetime(
            df_c['DateNav'], 
            format='%d/%m/%Y', 
            errors='coerce'
        )
        
        # Tri : les dates valides d'abord, les erreurs à la fin
        df_c = df_c.sort_values(by='temp_date', ascending=True, na_position='last')
        
        # On enlève la colonne technique
        df_c = df_c.drop(columns=['temp_date'])
    except Exception:
        pass
  # --- 5. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    if "contact_confirm_del" not in st.session_state:
        st.session_state.contact_confirm_del = None

    # Bouton Nouveau Contact
    if st.button("➕ NOUVEAU CONTACT", type="secondary", use_container_width=True):
        new = {
            "DateNav": datetime.now().strftime("%d/%m/2026"), 
            "NbreJours": "1", 
            "Statut": "En attente", 
            "Paiement": "Pas payé", 
            "Société": "", 
            "Prénom": "Nouveau", 
            "Nom": "Contact", 
            "Téléphone": "", 
            "Email": "", 
            "Prix": "0.00", 
            "Notes": ""
        }
        df_c = pd.concat([pd.DataFrame([new]), df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.rerun()

    # Navigation Archives / Missions Futures
    c1, c2 = st.columns(2)
    if c1.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False
        st.rerun()
    if c2.button("📁 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True
        st.rerun()

    # --- MODE ÉDITION ---
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
        u_jours = st.text_input("Nombre de Jours", value=safe_get(r, 'NbreJours'))
        u_prix = st.text_input("Prix Total (€)", value=safe_get(r, 'Prix'))
        
        stats_list = ["En attente", "OK", "Terminé", "Refusé"]
        u_stat = st.selectbox("Statut", stats_list, index=stats_list.index(safe_get(r, 'Statut')) if safe_get(r, 'Statut') in stats_list else 0)
        
        pays_list = ["Pas payé", "Payé"]
        u_paye = st.selectbox("Paiement", pays_list, index=pays_list.index(safe_get(r, 'Paiement')) if safe_get(r, 'Paiement') in pays_list else 0)
        
        u_notes = st.text_area("Notes", value=safe_get(r, 'Notes'))
        
        if st.button("💾 ENREGISTRER", type="primary", use_container_width=True):
            df_c.at[idx, 'Prénom'], df_c.at[idx, 'Nom'], df_c.at[idx, 'Société'] = u_pre, u_nom, u_soc
            df_c.at[idx, 'Téléphone'], df_c.at[idx, 'Email'], df_c.at[idx, 'DateNav'] = u_tel, u_mail, u_date
            df_c.at[idx, 'NbreJours'] = u_jours
            try:
                df_c.at[idx, 'Prix'] = f"{float(u_prix or 0):.2f}"
            except:
                df_c.at[idx, 'Prix'] = "0.00"
            df_c.at[idx, 'Statut'], df_c.at[idx, 'Paiement'], df_c.at[idx, 'Notes'] = u_stat, u_paye, u_notes
            sauvegarder_data(df_c, "contacts.json")
            st.session_state.edit_idx = None
            st.rerun()
            
        if st.button("Annuler", use_container_width=True):
            st.session_state.edit_idx = None
            st.rerun()

    # --- AFFICHAGE DE LA LISTE ---
    else:
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if st.session_state.view_archive else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
        
    for i, r in df_disp.iterrows():
            # --- 1. DÉFINITION AVEC TESTS D'ORTHOGRAPHE ---
            s_val = safe_get(r, 'Statut')
            pay_val = safe_get(r, 'Paiement')
            soc = safe_get(r, 'Société') or safe_get(r, 'Societe')
            
            # Test Téléphone (avec et sans accent)
            tel = safe_get(r, 'Téléphone')
            if not tel: tel = safe_get(r, 'Telephone')
            if not tel: tel = ""
            
            # Test Email
            mail = safe_get(r, 'Email')
            if not mail: mail = safe_get(r, 'E-mail')
            if not mail: mail = ""
            
            date_nav = safe_get(r, 'DateNav')
            jours = safe_get(r, 'NbreJours') or "1"
            try:
                p_val = f"{float(safe_get(r, 'Prix') or 0):.2f}"
            except:
                p_val = "0.00"        
            # Couleurs
            c_s = "#3498db" if "TERM" in s_val.upper() else "#2ecc71" if "OK" in s_val.upper() else "#e74c3c" if "REFUS" in s_val.upper() else "#f1c40f"
            c_p = "#FF0000" if "PAS PAYÉ" in pay_val.upper() or "NON PAYÉ" in pay_val.upper() else "#2ecc71"
            cl_b = "border-cmn" if "CMN" in soc.upper() else ""
            
            # Fiche HTML
            h = f'''<div class="fiche-globale {cl_b}">
                <span class="statut-badge" style="background:{c_p};">{pay_val}</span>
                <span class="statut-badge" style="background:{c_s};">{s_val}</span>
                <div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>
                <div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>
                
                <div style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #1a2a6c; font-size: 1rem;">
                    📅 <b>Date :</b> {date_nav}<br>
                    ⛵ <b>Durée :</b> {jours} jour(s)<br>
                    💰 <b>Montant :</b> {p_val} €
                </div>

                <div style="margin-bottom:10px; font-size: 1.1rem;">
                    📞 <b>{tel}</b><br>
                    ✉️ {mail}
                </div>

                <div class="notes-box">📝 {safe_get(r, "Notes") or "."}</div>

                <div class="container-boutons">
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="https://wa.me/{tel.replace(" ","")}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Mail</a>
                </div>
            </div>'''
            st.markdown(h, unsafe_allow_html=True)
            
            # Gestion Suppression / Edition
            if st.session_state.contact_confirm_del == i:
                st.warning("⚠️ Supprimer cette fiche ?")
                cy, cn = st.columns(2)
                if cy.button("✅ OUI", key=f"y_{i}"):
                    df_c = df_c.drop(i)
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.contact_confirm_del = None
                    st.rerun()
                if cn.button("NON", key=f"n_{i}"):
                    st.session_state.contact_confirm_del = None
                    st.rerun()
            else:
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_{i}"):
                    st.session_state.edit_idx = i
                    st.rerun()
                if c2.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    st.session_state.contact_confirm_del = i
                    st.rerun()
                    
# --- 6. PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning Mensuel 2026")
    m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    sel_m_nom = st.selectbox("Mois", m_noms, index=now.month - 1)
    sel_m = m_noms.index(sel_m_nom) + 1
    
    jours_occ = {}
    for _, r in df_c.iterrows():
        try:
            date_str = safe_get(r, 'DateNav').replace(" ", "")
            dp = date_str.split('/')
            m_val, y_val = int(dp[1]), int(dp[2])
            if y_val == 26: y_val = 2026
            if m_val == sel_m and y_val == 2026:
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
    
    st.markdown("---")
    st.subheader("📋 Liste détaillée du mois")
    found = False
    for _, r in df_c.iterrows():
        try:
            m = int(safe_get(r, 'DateNav').split('/')[1])
            if m == sel_m:
                found = True
                s = safe_get(r, 'Statut')
                c = "green" if s == "OK" else "orange"
                st.markdown(f"📅 **{safe_get(r, 'DateNav')}** ({safe_get(r, 'NbreJours')}j) : {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()} - <span style='color:{c}; font-weight:bold;'>{s}</span>", unsafe_allow_html=True)
        except: continue
    if not found: st.info("Aucune mission ce mois-ci.")


# --- 7. PAGE STATS ---
elif st.session_state.page == "STATS":
    st.subheader("📊 Historique Financier 2026")
    stats_data = []
    m_courts = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
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
        stats_data.append({"Mois": m_courts[m_idx-1], "Recettes (€)": f"{rec:.2f}", "Prévisions (€)": f"{prev:.2f}", "Frais (€)": f"{frs:.2f}", "Total (€)": f"{(rec - frs):.2f}"})
    st_df = pd.DataFrame(stats_data)
    t_rec = sum(float(x) for x in st_df["Recettes (€)"])
    t_pre = sum(float(x) for x in st_df["Prévisions (€)"])
    t_frs = sum(float(x) for x in st_df["Frais (€)"])
    tot_row = pd.DataFrame([{"Mois": "TOTAL", "Recettes (€)": f"{t_rec:.2f}", "Prévisions (€)": f"{t_pre:.2f}", "Frais (€)": f"{t_frs:.2f}", "Total (€)": f"{(t_rec - t_frs):.2f}"}])
    st.table(pd.concat([st_df, tot_row], ignore_index=True).set_index("Mois"))

# --- 8. PAGE MAINTENANCE ---
elif st.session_state.page == "MAINT":
    st.subheader("🔧 Maintenance & Frais")
    if st.button("➕ NOUVEAU FRAIS", use_container_width=True):
        new_m = {"Date": now.strftime("%d/%m/2026"), "Cause": "Achat", "Prix": "0.00"}
        df_m = pd.concat([pd.DataFrame([new_m]), df_m], ignore_index=True)
        sauvegarder_data(df_m, "maint.json"); st.rerun()

    if st.session_state.m_edit_idx is not None:
        idx = st.session_state.m_edit_idx
        r = df_m.loc[idx]
        u_d, u_c, u_p = st.text_input("Date", r['Date']), st.text_input("Cause", r['Cause']), st.text_input("Prix", r['Prix'])
        if st.button("💾 ENREGISTRER"):
            df_m.at[idx, 'Date'], df_m.at[idx, 'Cause'], df_m.at[idx, 'Prix'] = u_d, u_c, f"{float(u_p or 0):.2f}"
            sauvegarder_data(df_m, "maint.json"); st.session_state.m_edit_idx = None; st.rerun()
    else:
        for i, r in df_m.iterrows():
            st.markdown(f'<div class="fiche-globale">📅 {r["Date"]} | 🏷️ {r["Cause"]} | 💰 <b>{float(r["Prix"] or 0):.2f} €</b></div>', unsafe_allow_html=True)
            if st.session_state.maint_confirm_del == i:
                st.warning("Confirmer la suppression ?")
                c1, c2 = st.columns(2)
                if c1.button("✅ OUI", key=f"ym_{i}"): df_m = df_m.drop(i); sauvegarder_data(df_m, "maint.json"); st.session_state.maint_confirm_del = None; st.rerun()
                if c2.button("NON", key=f"nm_{i}"): st.session_state.maint_confirm_del = None; st.rerun()
            else:
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"em_{i}"): st.session_state.m_edit_idx = i; st.rerun()
                if c2.button("🗑️", key=f"dm_{i}"): st.session_state.maint_confirm_del = i; st.rerun()

# --- 9. PAGE FACTURES ---
elif st.session_state.page == "FACTURES":
    st.subheader("📄 Facturation Mensuelle (CMN)")
    prev_m_idx = now.month - 1 if now.month > 1 else 12
    prev_y = now.year if now.month > 1 else now.year - 1
    m_noms_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    nom_mois_prev = m_noms_fr[prev_m_idx - 1]
    
    st.info(f"Missions CMN de {nom_mois_prev} {prev_y}")
    missions_potentielles = []
    if not df_c.empty:
        for idx, r in df_c.iterrows():
            try:
                date_str = safe_get(r, 'DateNav').replace(" ", "")
                dp = date_str.split('/')
                m, y = int(dp[1]), int(dp[2])
                if y < 100: y += 2000
                if m == prev_m_idx and y == prev_y and "CMN" in safe_get(r, 'Société').upper() and safe_get(r, 'Paiement') != "Payé":
                    missions_potentielles.append({"id": idx, "Date": safe_get(r, 'DateNav'), "Client": f"{safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()}", "Prix": float(safe_get(r, 'Prix') or 0)})
            except: continue

    if not missions_potentielles: st.warning("Aucune mission CMN à facturer.")
    else:
        selection = {}; total_sel = 0.0
        for m in missions_potentielles:
            c1, c2, c3 = st.columns([1, 3, 2])
            if c1.checkbox("", value=True, key=f"s_{m['id']}"):
                selection[m['id']] = m; total_sel += m['Prix']
            c2.write(f"{m['Date']} - {m['Client']}"); c3.write(f"{m['Prix']:.2f} €")
        
        if total_sel > 0:
            corps = st.text_area("Message :", f"Bonjour,\n\nPrestations {nom_mois_prev} :\n" + "".join([f"- {m['Date']} : {m['Client']} | {m['Prix']:.2f}€\n" for m in selection.values()]) + f"\nTOTAL : {total_sel:.2f}€\n\nMerci.")
            if st.button(f"📧 CONFIRMER ({total_sel:.2f} €)"):
                for m_id in selection.keys(): df_c.at[m_id, 'Paiement'] = "Payé"; df_c.at[m_id, 'Statut'] = "Terminé"
                sauvegarder_data(df_c, "contacts.json")
                import urllib.parse
                mailto = f"mailto:tresorier@cmn-asso.fr?subject=Facture {nom_mois_prev}&body={urllib.parse.quote(corps)}"
                st.markdown(f'<a href="{mailto}" target="_blank" style="display:block;text-align:center;background:#2ecc71;color:white;padding:15px;text-decoration:none;border-radius:10px;font-weight:bold;">🚀 ENVOYER LE MAIL</a>', unsafe_allow_html=True)

# --- 10. PAGE NOTES ---
elif st.session_state.page == "NOTES":
    st.subheader("📝 Bloc-notes Professionnel")
    
    # 1. Chargement initial dans la session si ce n'est pas déjà fait
    if "memo_temp" not in st.session_state:
        df_n = charger_data("notes.json")
        if not df_n.empty and 'contenu' in df_n.columns:
            st.session_state.memo_temp = str(df_n.iloc[0]['contenu'])
        else:
            st.session_state.memo_temp = ""

    # 2. Zone de texte utilisant la variable en session
    # L'astuce est de NE PAS mettre 'value=' mais de laisser l'utilisateur écrire
    nouveau_memo = st.text_area(
        "Tes notes pour la saison 2026 :", 
        value=st.session_state.memo_temp,
        height=400,
        placeholder="Saisis tes codes de port ou rappels ici...",
        key="note_editor" # Clé unique pour stabiliser la saisie
    )
    
    # 3. Bouton de sauvegarde
    if st.button("💾 ENREGISTRER LES NOTES", type="primary", use_container_width=True):
        # On récupère ce qui a été tapé dans le text_area
        df_sauvegarde = pd.DataFrame([{"contenu": nouveau_memo}])
        sauvegarder_data(df_sauvegarde, "notes.json")
        
        # On met à jour la session pour le prochain affichage
        st.session_state.memo_temp = nouveau_memo
        st.success("✅ Notes sauvegardées sur GitHub !")
        time.sleep(1)
        st.rerun()

# --- 11. PAGE LIVRE DE BORD (LOG) ---
elif st.session_state.page == "LOG":
    st.subheader("📖 Livre de Bord")
    
    # 1. Initialisation des états
    if "log_edit_idx" not in st.session_state: st.session_state.log_edit_idx = None
    if "log_confirm_del" not in st.session_state: st.session_state.log_confirm_del = None

    # 2. Chargement des données
    df_log = charger_data("logbook.json")

    # 3. Nettoyage automatique des doublons (Sécurité)
    if not df_log.empty:
        avant = len(df_log)
        df_log = df_log.drop_duplicates(subset=['Date', 'PortDep', 'MotArr'], keep='first')
        if len(df_log) != avant:
            sauvegarder_data(df_log, "logbook.json")

# 4. Statistiques et Totalisateurs (Calculés à partir du 21/02)
    if not df_log.empty:
        # --- CONFIGURATION INITIALE (VALEURS AU 21/02) ---
        # Remplacez ces chiffres par les vrais relevés de vos compteurs ce jour-là
        MILLES_INITIAUX = 0.0  
        HEURES_INITIALES = 0.0 

        # Conversion des colonnes en numérique pour éviter les erreurs
        df_log['TotalMil'] = pd.to_numeric(df_log['TotalMil'], errors='coerce').fillna(0)
        df_log['TotalMot'] = pd.to_numeric(df_log['TotalMot'], errors='coerce').fillna(0)
        df_log['MotArr'] = pd.to_numeric(df_log['MotArr'], errors='coerce').fillna(0)
        df_log['MilArr'] = pd.to_numeric(df_log['MilArr'], errors='coerce').fillna(0)

        # Calcul du cumul saison (Somme de toutes les navigations enregistrées)
        cumul_milles_saison = df_log['TotalMil'].sum()
        cumul_heures_saison = df_log['TotalMot'].sum()
        
        # Calcul des Totalisateurs réels (Valeur initiale + Cumul saison)
        total_milles_bateau = MILLES_INITIAUX + cumul_milles_saison
        total_heures_bateau = HEURES_INITIALES + cumul_heures_saison

        st.markdown(f"""
            <div style="background:#1a2a6c; color:white; padding:15px; border-radius:10px; margin-bottom:20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="text-align:center; border-bottom:1px solid rgba(255,255,255,0.2); padding-bottom:10px; margin-bottom:10px;">
                    🚢 <b>VESTA SKIPPER 2026 - ÉTAT DES COMPTEURS</b>
                </div>
                <div style="display: flex; justify-content: space-around; text-align:center;">
                    <div>
                        <small>CUMUL DEPUIS LE 21/02</small><br>
                        <span style="font-size:1.2rem;"><b>{cumul_milles_saison:.1f} MN</b> | <b>{cumul_heures_saison:.1f} h</b></span>
                    </div>
                    <div style="border-left: 1px solid rgba(255,255,255,0.3); padding-left:20px;">
                        <small>TOTALISATEURS GÉNÉRAUX</small><br>
                        <span style="font-size:1.2rem;"><b>{total_milles_bateau:.1f} MN</b> | <b>{total_heures_bateau:.1f} h</b></span>
                    </div>
                </div>
                <div style="text-align:center; font-size:0.7rem; margin-top:10px; opacity:0.8;">
                    Valeurs initiales au 21/02 : {MILLES_INITIAUX} MN / {HEURES_INITIALES} h
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 5. Mode Édition ou Nouvelle Entrée
    is_editing = st.session_state.log_edit_idx is not None
    if is_editing:
        idx = st.session_state.log_edit_idx
        r_data = df_log.loc[idx]
        titre_form = "📝 MODIFIER LA NAVIGATION"
        bouton_label = "💾 ENREGISTRER LES MODIFICATIONS"
    else:
        r_data = None
        titre_form = "➕ NOUVELLE NAVIGATION"
        bouton_label = "💾 ENREGISTRER AU LIVRE DE BORD"

    with st.expander(titre_form, expanded=is_editing):
        c1, c2 = st.columns(2)
        l_date = c1.text_input("Date", value=safe_get(r_data, 'Date') if is_editing else datetime.now().strftime("%d/%m/%Y"))
        l_meteo = c2.text_input("Météo (Vent/Mer)", value=safe_get(r_data, 'Meteo') if is_editing else "")

        st.divider()
        col_dep, col_arr = st.columns(2)
        
        with col_dep:
            st.markdown("### 🛫 Départ")
            l_port_dep = st.text_input("Port de départ", value=safe_get(r_data, 'PortDep') if is_editing else "")
            val_mot_dep = float(r_data['MotDep']) if (is_editing and 'MotDep' in r_data) else 0.0
            val_mil_dep = float(r_data['MilDep']) if (is_editing and 'MilDep' in r_data) else 0.0
            l_mot_dep = st.number_input("Compteur Moteur Départ (h)", value=val_mot_dep, step=0.1, key="md_input")
            l_mil_dep = st.number_input("Compteur Milles Départ (MN)", value=val_mil_dep, step=0.1, key="ld_input")
            
        with col_arr:
            st.markdown("### 🛬 Arrivée")
            l_port_arr = st.text_input("Port d'arrivée", value=safe_get(r_data, 'PortArr') if is_editing else "")
            val_mot_arr = float(r_data['MotArr']) if (is_editing and 'MotArr' in r_data) else 0.0
            val_mil_arr = float(r_data['MilArr']) if (is_editing and 'MilArr' in r_data) else 0.0
            l_mot_arr = st.number_input("Compteur Moteur Arrivée (h)", value=val_mot_arr, step=0.1, key="ma_input")
            l_mil_arr = st.number_input("Compteur Milles Arrivée (MN)", value=val_mil_arr, step=0.1, key="la_input")

        st.divider()
        diff_mot = round(l_mot_arr - l_mot_dep, 1)
        diff_mil = round(l_mil_arr - l_mil_dep, 1)
        
        st.info(f"✨ **Calcul automatique :** +{diff_mot} h moteur | +{diff_mil} MN parcourus")
        l_obs = st.text_area("Observations", value=safe_get(r_data, 'Observations') if is_editing else "")
        
        c_save, c_annul = st.columns(2)
        if c_save.button(bouton_label, type="primary", use_container_width=True):
            entree = {
                "Date": l_date, "Meteo": l_meteo, 
                "PortDep": l_port_dep, "PortArr": l_port_arr,
                "MotDep": l_mot_dep, "MotArr": l_mot_arr, 
                "MilDep": l_mil_dep, "MilArr": l_mil_arr,
                "TotalMot": diff_mot, "TotalMil": diff_mil, 
                "Observations": l_obs
            }
            if is_editing:
                for k, v in entree.items(): df_log.at[idx, k] = v
            else:
                df_log = pd.concat([pd.DataFrame([entree]), df_log], ignore_index=True)
            
            sauvegarder_data(df_log, "logbook.json")
            st.session_state.log_edit_idx = None
            st.success("Enregistré !"); time.sleep(0.5); st.rerun()
            
        if is_editing and c_annul.button("❌ ANNULER", use_container_width=True):
            st.session_state.log_edit_idx = None; st.rerun()

    st.markdown("---")

    # 6. Affichage de l'Historique
    if not df_log.empty:
        for i, e in df_log.iterrows():
            # Détection CMN pour couleur bleue
            is_cmn = "CMN" in str(safe_get(e, 'PortDep')).upper() or "CMN" in str(safe_get(e, 'PortArr')).upper()
            color_border = "#0055ff" if is_cmn else "#1a2a6c"
            bg_card = "#f0f8ff" if is_cmn else "#ffffff"

            st.markdown(f"""
            <div style="background:{bg_card}; padding:15px; border-radius:10px; border:1px solid #ddd; border-left:8px solid {color_border}; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding-bottom:5px;">
                    <span style="font-weight:bold; color:#1a2a6c;">📅 {safe_get(e, 'Date')}</span>
                    <span style="color:{color_border}; font-weight:bold;">📍 {safe_get(e, 'PortDep')} ➜ {safe_get(e, 'PortArr')}</span>
                </div>
                <div style="margin-top:10px; font-size:0.9rem;">
                    ☁️ {safe_get(e, 'Meteo')} | ⚙️ <b>+{safe_get(e, 'TotalMot')}h</b> | ⛵ <b>+{safe_get(e, 'TotalMil')} MN</b>
                </div>
                <div style="margin-top:5px; font-size:0.85rem; color:#666; font-style:italic;">"{safe_get(e, 'Observations')}"</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Actions
            c1, c2 = st.columns(2)
            if c1.button("📝 MODIFIER", key=f"ed_l_{i}", use_container_width=True):
                st.session_state.log_edit_idx = i; st.rerun()
            if c2.button("🗑️ SUPPRIMER", key=f"del_l_{i}", use_container_width=True):
                df_log = df_log.drop(i); sauvegarder_data(df_log, "logbook.json"); st.rerun()
    else:
        st.info("Aucun trajet dans le livre de bord.")
        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































