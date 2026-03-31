import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import html
from datetime import datetime, date

# =================================================================
# --- 1. FONCTIONS OUTILS (CENTRALISÉES) ---
# =================================================================

def get_month_info(date_str):
    try:
        parts = str(date_str).split('/')
        if len(parts) >= 2:
            m_num = int(parts[1])
            months = ["Janv", "Févr", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
            return m_num, f"{m_num:02d}-{months[m_num-1]}"
    except: pass
    return 99, "99-Inconnu"

def clean_val(val):
    try:
        if val is None or str(val).lower() in ["nan", "none", ""]: return 0.0
        s = "".join(c for c in str(val) if c.isdigit() or c in ".,-")
        return float(s.replace(",", "."))
    except: return 0.0

def safe(val):
    if val is None or str(val).lower() in ["nan", "none"]: return ""
    return str(val).strip()

# =================================================================
# --- 2. CONFIGURATION & STYLE ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

now = datetime.now()
jours_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
date_bandeau = f"📅 {jours_fr[now.weekday()]} {now.day} {mois_fr[now.month-1]} {now.year}"

st.markdown(f"""<style>
    .main-header {{ font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 5px; }}
    .date-header {{ text-align: center; color: #7f8c8d; font-weight: bold; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; padding-bottom: 10px; }}
    button[data-testid="baseButton-primary"] {{ background-color: #ff4b4b !important; color: white !important; }}
    button[data-testid="baseButton-secondary"] {{ background-color: white !important; color: #1a2a6c !important; border: 1px solid #1a2a6c !important; }}
</style>""", unsafe_allow_html=True)

# =================================================================
# --- 3. SÉCURITÉ ACCÈS ---
# =================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("ACCÉDER"):
        if password == "Skipper2026":
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect.")
    st.stop()

# =================================================================
# --- 4. FONCTIONS GITHUB (DONNÉES) ---
# =================================================================
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            content = base64.b64decode(res.json()['content']).decode('utf-8')
            return pd.DataFrame(json.loads(content))
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
        requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    except: st.error(f"Erreur de sauvegarde sur {file}")

# =================================================================
# --- 5. NAVIGATION & INITIALISATION ---
# =================================================================
st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
st.markdown(f'<div class="date-header">{date_bandeau}</div>', unsafe_allow_html=True)

if "page" not in st.session_state: st.session_state.page = "CONTACTS"

menu = ["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES", "LOG"]
cols = st.columns(len(menu))

for i, name in enumerate(menu):
    if cols[i].button(name, key=f"nav_{name}", use_container_width=True, 
                      type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name
        st.rerun()

# Chargement des bases
df_c = charger_data("contacts.json")
df_m = charger_data("maintenance.json")

# Harmonisation auto des paiements (pour éviter le basculement "Payé")
def harmoniser_paiements(val):
    v = str(val).strip().lower()
    if "pay" in v and not any(x in v for x in ["un", "non", "pas"]): return "Payé"
    return "Non payé"

if not df_c.empty and 'Paiement' in df_c.columns:
    df_c['Paiement'] = df_c['Paiement'].apply(harmoniser_paiements)

# Tri chronologique des missions
if not df_c.empty and 'DateNav' in df_c.columns:
    df_c['temp_date'] = pd.to_datetime(df_c['DateNav'], format='%d/%m/%Y', errors='coerce')
    df_c = df_c.sort_values(by='temp_date', ascending=True, na_position='last').drop(columns=['temp_date'])
# =================================================================
# --- 5. PAGE CONTACTS (VERSION ROBUSTE ANTI-DIV) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.markdown('<div class="main-header">👥 GESTION DES MISSIONS</div>', unsafe_allow_html=True)
    import html
    from datetime import datetime

    def safe(val):
        if val is None or str(val).lower() in ["none", "nan", "", "null"]: return ""
        return html.escape(str(val)).replace("\n", " ").replace("\r", "")

    LISTE_SOC = ["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"]

    # --- BARRE D'OUTILS ---
    c_n1, c_n2, c_add = st.columns([1, 1, 2])
    view_arc = st.session_state.get('view_archive', False)

    if c_n1.button("📂 EN COURS", use_container_width=True, type="secondary" if view_arc else "primary"):
        st.session_state.view_archive = False
        st.rerun()
    if c_n2.button("🗄️ ARCHIVES", use_container_width=True, type="primary" if view_arc else "secondary"):
        st.session_state.view_archive = True
        st.rerun()
    
    if c_add.button("➕ NOUVEAU CONTACT", type="primary", use_container_width=True):
        new_row = pd.DataFrame([{"Prénom": "", "Nom": "Nouveau", "Société": "PARTICULIER", "Statut": "En attente", "Paiement": "Non payé", "DateNav": datetime.now().strftime("%d/%m/%Y"), "Prix": "0", "NbreJours": "1", "NbrePers": "1", "Téléphone": "", "Email": "", "Notes": ""}])
        df_c = pd.concat([new_row, df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.session_state.edit_idx = 0 
        st.rerun()

    st.divider()

    # --- FILTRAGE ---
    statuts_arc = ["Terminé", "Refusé", "Annulé"]
    df_disp = df_c[df_c['Statut'].isin(statuts_arc)] if view_arc else df_c[~df_c['Statut'].isin(statuts_arc)]

    # --- BOUCLE D'AFFICHAGE ---
    for i, r in df_disp.iterrows():
        with st.container():
            num_f = i + 1
            p_nom = safe(r.get('Prénom', ''))
            n_nom = safe(r.get('Nom', '')).upper()
            nom_c = f"{p_nom} {n_nom}" if (p_nom or n_nom) else f"Fiche #{num_f}"
            soc   = safe(r.get('Société', 'PARTICULIER')).upper()
            tel   = safe(r.get('Téléphone', ''))
            mail  = safe(r.get('Email', ''))
            note  = safe(r.get('Notes', ''))
            prix  = safe(r.get('Prix', '0'))
            date_v = safe(r.get('DateNav', '--/--/--'))
            jours = safe(r.get('NbreJours', '1'))
            pers  = safe(r.get('NbrePers', '1'))
            
            s_val = safe(r.get('Statut', 'En attente'))
            s_col = "#0056b3" if "CMN" in soc else ("#2ecc71" if "OK" in s_val.upper() else "#f1c40f" if "ATTENTE" in s_val.upper() else "#e74c3c")
            
            v_paye_brute = str(r.get('Paiement', 'Non payé')).upper()
            is_paid = "PAY" in v_paye_brute and "NON" not in v_paye_brute
            p_col = "#3498db" if is_paid else "#e67e22"

            clean_tel = "".join(filter(str.isdigit, tel)) if tel else ""
            wa_link = f"33{clean_tel[1:]}" if clean_tel.startswith("0") else clean_tel

            # --- GÉNÉRATION DU HTML SANS SAUTS DE LIGNE INTERNES (PLUS FIABLE) ---
            card = f'<div style="border:2px solid #1a2a6c;border-radius:12px;padding:15px;margin-bottom:10px;background:white;color:black;box-shadow:2px 2px 8px rgba(0,0,0,0.1);">'
            card += f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
            card += f'<b style="color:#1a2a6c;font-size:1.1rem;">#{num_f} — {nom_c}</b>'
            card += f'<div style="text-align:right;display:flex;flex-direction:column;gap:4px;">'
            card += f'<span style="background:{s_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{s_val.upper()}</span>'
            card += f'<span style="background:{p_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{"PAYÉ" if is_paid else "NON PAYÉ"}</span></div></div>'
            card += f'<div style="color:#444;font-size:0.9rem;margin-top:8px;font-weight:bold;">🏢 {soc}</div>'
            card += f'<div style="font-size:0.82rem;color:#2980b9;margin:8px 0;border-bottom:1px solid #eee;padding-bottom:8px;">📞 {tel if tel else "---"} | 📧 {mail if mail else "---"}</div>'
            card += f'<div style="font-size:0.9rem;color:#333;display:flex;justify-content:space-between;margin-top:5px;"><span>📅 <b>{date_v}</b> ({jours}j)</span><span>👥 <b>{pers} pers.</b> | 💰 <b>{prix}€</b></span></div>'
            if note: card += f'<div style="margin-top:10px;padding:8px;background:#f8f9fa;border-left:4px solid #1a2a6c;font-size:0.8rem;border-radius:4px;">📝 {note}</div>'
            
            # Liens de contact
            card += f'<div style="margin-top:15px;display:flex;gap:8px;">'
            if clean_tel:
                card += f'<a href="tel:{clean_tel}" style="flex:1;background:#5D6D7E;color:white !important;padding:10px 2px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.75rem;font-weight:bold;">📞 APPEL</a>'
                card += f'<a href="https://wa.me/{wa_link}" target="_blank" style="flex:1;background:#25D366;color:white !important;padding:10px 2px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.75rem;font-weight:bold;">💬 WA</a>'
            if mail:
                card += f'<a href="mailto:{mail}" style="flex:1;background:#E67E22;color:white !important;padding:10px 2px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.75rem;font-weight:bold;">📧 MAIL</a>'
            card += '</div></div>'

            # Affichage de la carte
            st.write(card, unsafe_allow_html=True)

            # --- ACTIONS (BOUTONS STREAMLIT NATIFS) ---
            c_ed, c_del = st.columns(2)
            if c_ed.button(f"✏️ MODIFIER #{num_f}", key=f"ed_{i}", use_container_width=True):
                st.session_state.edit_idx = i
                st.rerun()
            if c_del.button(f"🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                df_c = df_c.drop(i).reset_index(drop=True)
                sauvegarder_data(df_c, "contacts.json")
                st.rerun()

            # --- FORMULAIRE D'ÉDITION ---
            if st.session_state.get('edit_idx') == i:
                with st.expander(f"⚙️ ÉDITION #{num_f}", expanded=True):
                    with st.form(f"form_edit_{i}"):
                        c1, c2 = st.columns(2)
                        u_pre = c1.text_input("Prénom", value=p_nom)
                        u_nom = c2.text_input("Nom", value=n_nom)
                        u_soc = c1.selectbox("Société", LISTE_SOC, index=LISTE_SOC.index(soc) if soc in LISTE_SOC else 0)
                        u_tel = c2.text_input("Téléphone", value=tel)
                        u_mai = c1.text_input("Email", value=mail)
                        u_dat = c2.text_input("Date", value=date_v)
                        c3, c4, c5 = st.columns(3)
                        u_jr = c3.text_input("Jours", value=jours)
                        u_ps = c4.text_input("Pers.", value=pers)
                        u_px = c5.text_input("Prix €", value=prix)
                        u_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé", "Annulé"], index=["En attente", "OK", "Terminé", "Refusé", "Annulé"].index(s_val) if s_val in ["En attente", "OK", "Terminé", "Refusé", "Annulé"] else 0)
                        u_paye = st.selectbox("Paiement", ["Non payé", "Payé"], index=1 if is_paid else 0)
                        u_note = st.text_area("Notes", value=note)

                        if st.form_submit_button("💾 ENREGISTRER"):
                            df_c.at[i, 'Prénom'], df_c.at[i, 'Nom'], df_c.at[i, 'Société'] = u_pre, u_nom, u_soc
                            df_c.at[i, 'Téléphone'], df_c.at[i, 'Email'], df_c.at[i, 'DateNav'] = u_tel, u_mai, u_dat
                            df_c.at[i, 'NbreJours'], df_c.at[i, 'NbrePers'], df_c.at[i, 'Prix'] = u_jr, u_ps, u_px
                            df_c.at[i, 'Statut'], df_c.at[i, 'Paiement'], df_c.at[i, 'Notes'] = u_stat, u_paye, u_note
                            sauvegarder_data(df_c, "contacts.json")
                            st.session_state.edit_idx = None
                            st.rerun()
            
            st.markdown('<br>', unsafe_allow_html=True)
# =================================================================
# --- 4. PAGE PLANNING (VERSION IDENTIQUE À HIER - LISTE SOUS CAL) ---
# =================================================================
if st.session_state.page == "PLANNING":
    st.markdown('<div class="main-header">📅 PLANNING VESTA 2026</div>', unsafe_allow_html=True)
    import calendar as cal_logic
    from datetime import datetime

    # --- 1. SÉLECTEUR DE MOIS (COMPACT) ---
    c1, c2 = st.columns(2)
    sel_m = c1.selectbox("Mois", list(range(1, 13)), index=datetime.now().month - 1)
    sel_y = c2.selectbox("Année", [2025, 2026, 2027], index=1)

    # --- 2. AFFICHAGE DU CALENDRIER VISUEL (GRILLE VIDE) ---
    cal_mat = cal_logic.monthcalendar(sel_y, sel_m)
    month_name = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"][sel_m-1]
    
    cal_html = f'<div style="text-align:center; font-weight:bold; margin-bottom:5px; color:#1a2a6c;">{month_name} {sel_y}</div>'
    cal_html += '<table style="width:100%; border-collapse:collapse; font-size:0.8rem; text-align:center; background:white; color:black;">'
    cal_html += '<tr style="background:#f0f2f6;"><th>L</th><th>M</th><th>M</th><th>J</th><th>V</th><th>S</th><th>D</th></tr>'
    
    # On récupère les jours occupés pour ce mois
    jours_occupes = []
    for _, r in df_c.iterrows():
        try:
            d_nav = pd.to_datetime(r.get('DateNav', ''), dayfirst=True)
            if d_nav.month == sel_m and d_nav.year == sel_y:
                jours_occupes.append(d_nav.day)
        except: continue

    for week in cal_mat:
        cal_html += '<tr>'
        for day in week:
            if day == 0:
                cal_html += '<td style="padding:8px; border:1px solid #eee;"></td>'
            else:
                bg = "#1a2a6c; color:white; font-weight:bold; border-radius:50%;" if day in jours_occupes else ""
                cal_html += f'<td style="padding:8px; border:1px solid #eee;"><span style="display:inline-block; width:20px; height:20px; line-height:20px; {bg}">{day}</span></td>'
        cal_html += '</tr>'
    cal_html += '</table>'
    st.markdown(cal_html, unsafe_allow_html=True)

    st.write("---")

    # --- 3. LISTE DES MISSIONS (LE MENU LISTE QUE TU AIMES) ---
    st.subheader(f"📋 Missions de {month_name}")
    
    # Filtrage des données pour le mois sélectionné
    df_c['temp_date'] = pd.to_datetime(df_c['DateNav'], dayfirst=True, errors='coerce')
    df_mois = df_c[(df_c['temp_date'].dt.month == sel_m) & (df_c['temp_date'].dt.year == sel_y)].sort_values('temp_date')

    if df_mois.empty:
        st.info("Aucune mission prévue pour ce mois.")
    else:
        for _, r in df_mois.iterrows():
            soc = str(r.get('Société', 'PARTICULIER')).upper()
            nom = f"{r.get('Prénom', '')} {r.get('Nom', '')}".upper()
            date_v = r.get('DateNav', '')
            statut = r.get('Statut', 'En attente')
            
            # CODE COULEUR : Bleu si CMN, sinon Marine
            couleur_bandeau = "#0056b3" if "CMN" in soc else "#1a2a6c"
            
            mission_html = f"""
            <div style="border-left:5px solid {couleur_bandeau}; padding:10px; margin-bottom:10px; background:#f8f9fa; border-radius:4px; color:black;">
                <div style="display:flex; justify-content:space-between;">
                    <b style="color:{couleur_bandeau};">{date_v}</b>
                    <span style="font-size:0.8rem; font-weight:bold; color:#555;">{soc}</span>
                </div>
                <div style="font-size:1rem; margin-top:3px;">{nom}</div>
                <div style="font-size:0.75rem; color:#666;">Statut: {statut}</div>
            </div>
            """
            st.markdown(mission_html, unsafe_allow_html=True)
# =================================================================
# --- 7. PAGE STATS (VERSION RESTAURÉE & OPTIMISÉE) ---
# =================================================================
if st.session_state.page == "STATS":
    st.title("📊 Vesta - Pilotage & Frais")

    # --- 1. PRÉPARATION DES DONNÉES ---
    df_st = df_c.copy()
    if not df_st.empty and 'Prix' in df_st.columns:
        df_st['PrixNum'] = df_st['Prix'].apply(clean_val)
        
        # Extraction mois/année pour le tri
        month_data = df_st['DateNav'].apply(get_month_info)
        df_st['M_Sort'] = [x[0] for x in month_data]
        df_st['Mois'] = [x[1] for x in month_data]
        
        # Calcul CA : Basé sur Paiement PAYÉ ou Statut OK
        mask_paye = df_st['Paiement'].astype(str).str.upper().str.strip() == "PAYÉ"
        mask_ok = df_st['Statut'].astype(str).str.upper() == "OK"
        df_st['CA_Calcul'] = df_st.apply(lambda x: x['PrixNum'] if (mask_paye[x.name] or mask_ok[x.name]) else 0.0, axis=1)
    else:
        df_st = pd.DataFrame(columns=['M_Sort', 'Mois', 'CA_Calcul', 'PrixNum', 'Paiement', 'Statut', 'Société'])

    # Récupération Frais Maintenance
    df_maint_stats = charger_data('maintenance.json')
    if not df_maint_stats.empty and 'Date' in df_maint_stats.columns:
        m_data_f = df_maint_stats['Date'].apply(get_month_info)
        df_maint_stats['M_Sort'] = [x[0] for x in m_data_f]
        df_maint_stats['Mois'] = [x[1] for x in m_data_f]
        df_maint_stats['FraisNum'] = df_maint_stats['Montant'].apply(clean_val)
    else:
        df_maint_stats = pd.DataFrame(columns=['M_Sort', 'Mois', 'FraisNum'])

    # --- 2. SYNTHÈSE MENSUELLE ---
    st.subheader("📅 Synthèse Mensuelle 2026")
    stats_ca = df_st.groupby(['M_Sort', 'Mois'])['CA_Calcul'].sum().reset_index()
    stats_fr = df_maint_stats.groupby(['M_Sort', 'Mois'])['FraisNum'].sum().reset_index()
    
    mensuel = pd.merge(stats_ca, stats_fr, on=['M_Sort', 'Mois'], how='outer').fillna(0)
    mensuel.columns = ['M_Sort', 'Mois', 'CA', 'Frais']
    mensuel = mensuel.sort_values('M_Sort')
    mensuel['Net'] = mensuel['CA'] - mensuel['Frais']
    
    if not mensuel.empty:
        st.table(mensuel[['Mois', 'CA', 'Frais', 'Net']].set_index('Mois').style.format("{:.0f} €"))
    
    st.divider()
    
    # --- 3. VISUALISATION GRAPHIQUE (RESTAURÉE) ---
    st.subheader("📈 Analyse de l'Activité")
    if not mensuel.empty:
        # Courbe Evolution CA vs Frais
        st.write("**Évolution mensuelle (€)**")
        chart_data = mensuel.set_index('Mois')[['CA', 'Frais']]
        st.line_chart(chart_data, color=["#2ecc71", "#e74c3c"]) # Vert = CA, Rouge = Frais
        
        # Répartition par Société
        if 'Société' in df_st.columns:
            st.write("**Répartition Clients (Nombre de missions)**")
            stats_soc = df_st['Société'].value_counts()
            st.dataframe(stats_soc, use_container_width=True)
    else:
        st.info("Données insuffisantes pour les graphiques.")

    # --- 4. INDICATEURS DE TRÉSORERIE ---
    st.divider()
    col1, col2 = st.columns(2)
    tot_encaisse = df_st[df_st['Paiement'].astype(str).str.upper().str.strip() == "PAYÉ"]['PrixNum'].sum()
    # À venir = Missions OK mais non payées
    mask_a_venir = (df_st['Statut'].astype(str).str.upper() == "OK") & (df_st['Paiement'].astype(str).str.upper().str.strip() != "PAYÉ")
    tot_a_venir = df_st[mask_a_venir]['PrixNum'].sum()
    
    col1.metric("💰 ENCAISSÉ", f"{tot_encaisse:,.0f}€")
    col2.metric("🕒 À VENIR", f"{tot_a_venir:,.0f}€")

    # --- 5. DÉTAIL MISSIONS À VENIR (RESTAURÉ) ---
    st.subheader("⏳ Missions à venir (Détail)")
    df_avenir = df_st[mask_a_venir].copy()

    if not df_avenir.empty:
        tableau_mobile = df_avenir[['DateNav', 'Nom', 'PrixNum']]
        tableau_mobile.columns = ['📅 Date', '👤 Client', '💰 €']
        
        # Tri chronologique
        tableau_mobile['sort'] = pd.to_datetime(tableau_mobile['📅 Date'], format='%d/%m/%Y', errors='coerce')
        tableau_mobile = tableau_mobile.sort_values('sort').drop(columns=['sort'])
        
        st.table(tableau_mobile.set_index('📅 Date'))
    else:
        st.info("Aucune mission en attente de paiement.")

    # --- 6. ARCHIVAGE ---
    st.divider()
    with st.expander("📁 Archivage de la Saison"):
        annee_archive = datetime.now().year
        if st.button(f"📦 ARCHIVER LES MISSIONS {annee_archive}", use_container_width=True):
            mask_arch = df_c['Statut'].isin(["Terminé", "Refusé"])
            df_a_archiver = df_c[mask_arch]
            df_qui_reste = df_c[~mask_arch]
            
            if not df_a_archiver.empty:
                sauvegarder_data(df_a_archiver, f"archives_{annee_archive}.json")
                sauvegarder_data(df_qui_reste, "contacts.json")
                st.success("Archive créée avec succès !")
                time.sleep(1)
                st.rerun()
    
# =================================================================
# --- 8. PAGE MAINTENANCE (VERSION OPTIMISÉE IPHONE 2026) ---
# =================================================================
if st.session_state.page == "MAINT":
    st.title("🔧 Maintenance Vesta")

    # 1. CHARGEMENT DES DONNÉES
    file_path_m = 'maintenance.json'
    df_m = charger_data(file_path_m)
    
    if df_m.empty:
        df_m = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])

    # --- 2. INTERFACE DE SAISIE DYNAMIQUE ---
    
    # Initialisation de l'état du formulaire dans la mémoire de la session
    if 'show_maint_form' not in st.session_state:
        st.session_state.show_maint_form = False

    # Barre d'outils supérieure
    col_nav1, col_nav2 = st.columns([2, 1])
    
    if not st.session_state.show_maint_form:
        if col_nav1.button("➕ AJOUTER UNE DÉPENSE", use_container_width=True, type="primary"):
            st.session_state.show_maint_form = True
            st.rerun()
    else:
        if col_nav2.button("❌ FERMER", use_container_width=True):
            st.session_state.show_maint_form = False
            st.rerun()

    # Affichage du formulaire (uniquement si activé)
    if st.session_state.show_maint_form:
        with st.form("form_maint_new"):
            st.write("### 📝 Nouvelle Saisie")
            f_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            f_obj = st.text_input("Objet (ex: Taxes, Révision, Accastillage)")
            f_mt = st.number_input("Montant (€)", min_value=0.0, step=1.0)
            
            submit = st.form_submit_button("💾 ENREGISTRER SUR GITHUB", use_container_width=True)
            
            if submit:
                if f_obj:
                    # Création de la nouvelle ligne
                    nouvelle_ligne = pd.DataFrame([{
                        "Date": f_date,
                        "Objet": f_obj,
                        "Montant": float(f_mt),
                        "Statut": "OK"
                    }])
                    df_m = pd.concat([df_m, nouvelle_ligne], ignore_index=True)
                    
                    # Sauvegarde sur GitHub
                    sauvegarder_data(df_m, file_path_m)
                    
                    # Fermeture automatique du formulaire
                    st.session_state.show_maint_form = False
                    
                    st.balloons()
                    st.success(f"Enregistré : {f_obj}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un 'Objet'.")

    st.divider()

 # 3. AFFICHAGE DE L'HISTORIQUE ET TOTAL
    if not df_m.empty:
        df_m['Montant'] = pd.to_numeric(df_m['Montant'], errors='coerce').fillna(0)
        total_frais = df_m['Montant'].sum()
        st.metric("TOTAL CUMULÉ 2026", f"{total_frais:,.2f} €")

        st.write("### 📋 Historique des frais")
        
        # On parcourt l'historique (du plus récent au plus ancien)
        for index, item in df_m.iloc[::-1].iterrows():
            # Clé unique pour le mode édition de chaque ligne
            edit_key = f"edit_mode_{index}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            with st.expander(f"📅 {item['Date']} - {item['Objet']} ({item['Montant']}€)"):
                
                if not st.session_state[edit_key]:
                    # --- AFFICHAGE CLASSIQUE ---
                    col_a, col_b = st.columns(2)
                    if col_a.button("✏️ Modifier", key=f"btn_edit_{index}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                    
                    if col_b.button("🗑️ Supprimer", key=f"btn_del_{index}", use_container_width=True):
                        df_m = df_m.drop(index).reset_index(drop=True)
                        sauvegarder_data(df_m, file_path_m)
                        st.rerun()
                else:
                    # --- MODE ÉDITION (DANS L'EXPANDER) ---
                    st.info("Mode modification activé")
                    new_date = st.text_input("Date", item['Date'], key=f"in_date_{index}")
                    new_obj = st.text_input("Objet", item['Objet'], key=f"in_obj_{index}")
                    new_mt = st.number_input("Montant (€)", value=float(item['Montant']), key=f"in_mt_{index}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Sauver", key=f"save_{index}", use_container_width=True, type="primary"):
                        # Mise à jour des données
                        df_m.at[index, 'Date'] = new_date
                        df_m.at[index, 'Objet'] = new_obj
                        df_m.at[index, 'Montant'] = new_mt
                        sauvegarder_data(df_m, file_path_m)
                        st.session_state[edit_key] = False # On ferme le mode édition
                        st.success("Modifié !")
                        time.sleep(0.5)
                        st.rerun()
                        
                    if c2.button("🚫 Annuler", key=f"cancel_{index}", use_container_width=True):
                        st.session_state[edit_key] = False
                        st.rerun()
    else:
        st.info("Aucune dépense enregistrée.")

    # 4. ZONE DE DANGER
    st.write("---")
    with st.expander("⚠️ Zone de Danger"):
        st.write("Attention, cette action est irréversible.")
        if st.checkbox("Confirmer la suppression totale de l'historique"):
            if st.button("🔴 VIDER LE FICHIER MAINTENANCE", type="primary", use_container_width=True):
                df_vide = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])
                sauvegarder_data(df_vide, file_path_m)
                st.rerun()

# =================================================================
# --- 9. PAGE FACTURES (ANALYSE & ENVOI CMN OPTIMISÉ IPHONE) ---
# =================================================================
if st.session_state.page == "FACTURES":
    st.title("📑 Facturation & Rapports")

    # --- 1. SÉLECTION DU MOIS ---
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    
    col_m, col_a = st.columns(2)
    sel_mois = col_m.selectbox("Choisir le mois", mois_noms, index=maintenant.month - 1)
    sel_annee = col_a.selectbox("Année", [2025, 2026, 2027], index=1)
    index_mois = mois_noms.index(sel_mois) + 1

    # --- 2. FILTRAGE ET CALCULS ---
    if not df_c.empty:
        df_fact = df_c.copy()
        df_fact['dt'] = pd.to_datetime(df_fact['DateNav'], format='%d/%m/%Y', errors='coerce')
        
        mask_cmn = (df_fact['Société'].astype(str).str.upper() == "CMN") & \
                   (df_fact['dt'].dt.month == index_mois) & \
                   (df_fact['dt'].dt.year == sel_annee)
        
        df_cmn_mois = df_fact[mask_cmn].copy()
        
        if not df_cmn_mois.empty:
            st.subheader(f"Missions CMN - {sel_mois} {sel_annee}")
            
            df_cmn_mois['PrixNum'] = df_cmn_mois['Prix'].apply(clean_val)
            total_cmn = df_cmn_mois['PrixNum'].sum()
            
            st.table(df_cmn_mois[['DateNav', 'Nom', 'Prix']].set_index('DateNav'))
            st.metric("Total à facturer", f"{total_cmn:.2f} €")
            
            # --- 3. PRÉPARATION DU TEXTE ---
            st.divider()
            st.subheader("✉️ Rapport pour le Trésorier")
            
            lignes_missions = []
            for _, row in df_cmn_mois.iterrows():
                d_str = str(row['DateNav']).ljust(10)
                n_str = str(row['Nom'])
                p_str = f"{row['PrixNum']:.2f} €"
                lignes_missions.append(f"{d_str}{' '*12}{n_str}{' '*3}{p_str}")
            
            texte_missions = "\n".join(lignes_missions)
            destinataire = "tresorier@cmn-asso.fr, aurelienfaucheux@gmail.com"
            objet = f"Facturation Missions Vesta - {sel_mois} {sel_annee}"
            
            corps_mail = f"Bonjour,\n\nVoici le récapitulatif CMN de {sel_mois} {sel_annee} :\n\n{texte_missions}\n\nTotal : {total_cmn:.2f} €.\n\nMerci,\nEric (Vesta)"

            st.text_area("Texte prêt à copier :", corps_mail, height=200)
            
            import urllib.parse
            mail_link = f"mailto:{destinataire}?subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            gmail_link = f"googlegmail:///co?to={destinataire}&subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            
            c_b1, c_b2 = st.columns(2)
            c_b1.link_button("🚀 GMAIL", gmail_link, use_container_width=True)
            c_b2.link_button("✉️ MAIL", mail_link, use_container_width=True)
          # --- 4. SUIVI DES ENVOIS (LOGIQUE DYNAMIQUE) ---
            st.divider()
            df_suivi = charger_data('suivi_envois.json')
            if df_suivi.empty:
                df_suivi = pd.DataFrame(columns=["Mois", "Annee", "DateEnvoi", "Total"])

            # On vérifie si le mois sélectionné est déjà dans le fichier JSON
            deja_envoye = df_suivi[(df_suivi['Mois'] == sel_mois) & (df_suivi['Annee'] == sel_annee)]

            if not deja_envoye.empty:
                # SI DÉJÀ ENVOYÉ : On affiche le message de succès (et pas le bouton)
                dernier = deja_envoye.iloc[-1]
                st.success(f"✅ Envoyé le {dernier['DateEnvoi']}")
                
                # Optionnel : un bouton discret pour corriger en cas d'erreur
                if st.button("🔄 RE-VALIDER (Si erreur)", use_container_width=True):
                    st.info("Le bouton d'envoi va réapparaître.")
                    # Ici on pourrait supprimer la ligne, mais le plus simple est de laisser le rerun
                    st.rerun()
            
            else:
                # SI PAS ENCORE ENVOYÉ : On affiche le gros bouton rouge/bleu
                if st.button("✔️ MARQUER COMME ENVOYÉ", type="primary", use_container_width=True):
                    nouvelle_trace = pd.DataFrame([{
                        "Mois": sel_mois,
                        "Annee": sel_annee,
                        "DateEnvoi": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                        "Total": f"{total_cmn:.2f} €"
                    }])
                    df_suivi = pd.concat([df_suivi, nouvelle_trace], ignore_index=True)
                    sauvegarder_data(df_suivi, 'suivi_envois.json')
                    st.success("Enregistré !")
                    time.sleep(1)
                    st.rerun()

            # L'historique reste visible en bas dans tous les cas
            with st.expander("🕒 Historique des envois"):
                if not df_suivi.empty:
                    st.dataframe(df_suivi.iloc[::-1], use_container_width=True, hide_index=True)  

# =================================================================
# --- 11. PAGE NOTES (VERSION COMPLÈTE AVEC MODIFICATION) ---
# =================================================================
if st.session_state.page == "NOTES":
    st.title("📝 Notes & Commentaires")

    # 1. CHARGEMENT ET SÉCURISATION DES DONNÉES
    file_path_notes = 'notes.json'
    df_n = charger_data(file_path_notes)
    
    # Force la structure pour éviter les KeyError
    if df_n.empty or 'Date' not in df_n.columns:
        df_n = pd.DataFrame(columns=["Date", "Sujet", "Commentaires", "Statut"])

    # --- 2. INTERFACE D'AJOUT DYNAMIQUE ---
    if 'show_notes_form' not in st.session_state:
        st.session_state.show_notes_form = False

    col_n1, col_n2 = st.columns([2, 1])
    
    if not st.session_state.show_notes_form:
        if col_n1.button("➕ NOUVELLE NOTE", use_container_width=True, type="primary"):
            st.session_state.show_notes_form = True
            st.rerun()
    else:
        if col_n2.button("❌ FERMER", key="close_notes_form", use_container_width=True):
            st.session_state.show_notes_form = False
            st.rerun()

    if st.session_state.show_notes_form:
        with st.form("form_notes_new"):
            st.write("### ✍️ Rédiger une note")
            fn_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            fn_sujet = st.text_input("Sujet (ex: Moteur, Amarrage, Électricité)")
            fn_comm = st.text_area("Commentaires")
            
            submit_n = st.form_submit_button("💾 ENREGISTRER LA NOTE", use_container_width=True)
            
            if submit_n:
                if fn_sujet:
                    nouvelle_note = pd.DataFrame([{
                        "Date": fn_date,
                        "Sujet": fn_sujet,
                        "Commentaires": fn_comm,
                        "Statut": "OK"
                    }])
                    df_n = pd.concat([df_n, nouvelle_note], ignore_index=True)
                    sauvegarder_data(df_n, file_path_notes)
                    st.session_state.show_notes_form = False
                    st.success("Note enregistrée !")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un sujet.")

    st.divider()

    # --- 3. AFFICHAGE & MODIFICATION DE L'HISTORIQUE ---
    if not df_n.empty:
        st.write(f"### 📋 Carnet de bord ({len(df_n)} notes)")
        
        for index, item in df_n.iloc[::-1].iterrows():
            # Clé d'édition unique pour cette note
            n_edit_key = f"note_edit_mode_{index}"
            if n_edit_key not in st.session_state:
                st.session_state[n_edit_key] = False

            with st.expander(f"📌 {item['Date']} - {item['Sujet']}"):
                
                if not st.session_state[n_edit_key]:
                    # --- VUE LECTURE ---
                    st.write(f"**Commentaire :**\n{item['Commentaires']}")
                    
                    c_na, c_nb = st.columns(2)
                    if c_na.button("✏️ Modifier", key=f"n_btn_edit_{index}", use_container_width=True):
                        st.session_state[n_edit_key] = True
                        st.rerun()
                    
                    if c_nb.button("🗑️ Supprimer", key=f"n_btn_del_{index}", use_container_width=True):
                        df_n = df_n.drop(index).reset_index(drop=True)
                        sauvegarder_data(df_n, file_path_notes)
                        st.rerun()
                else:
                    # --- VUE ÉDITION ---
                    st.info("Modification en cours...")
                    ed_n_date = st.text_input("Date", item['Date'], key=f"ed_n_d_{index}")
                    ed_n_sujet = st.text_input("Sujet", item['Sujet'], key=f"ed_n_s_{index}")
                    ed_n_comm = st.text_area("Commentaires", item['Commentaires'], key=f"ed_n_c_{index}")
                    
                    cn1, cn2 = st.columns(2)
                    if cn1.button("💾 Sauver", key=f"n_save_mod_{index}", use_container_width=True, type="primary"):
                        df_n.at[index, 'Date'] = ed_n_date
                        df_n.at[index, 'Sujet'] = ed_n_sujet
                        df_n.at[index, 'Commentaires'] = ed_n_comm
                        sauvegarder_data(df_n, file_path_notes)
                        st.session_state[n_edit_key] = False
                        st.success("C'est fait !")
                        time.sleep(0.5)
                        st.rerun()
                        
                    if cn2.button("🚫 Annuler", key=f"n_cancel_mod_{index}", use_container_width=True):
                        st.session_state[n_edit_key] = False
                        st.rerun()
    else:
        st.info("Aucune note enregistrée.")
# =================================================================
# --- 10. PAGE LOG (CONSULTATION DES ARCHIVES) ---
# =================================================================
elif st.session_state.page == "LOG":
    st.title("📂 Archives & Logs")
    
    annee_actuelle = datetime.now().year
    nom_archive = f"archives_{annee_actuelle}.json"
    
    df_arch = charger_data(nom_archive)
    
    if not df_arch.empty:
        st.write(f"### 📋 Missions Archivées {annee_actuelle}")
        st.dataframe(df_arch, use_container_width=True)
    else:
        st.info("Aucune archive trouvée pour cette saison.")

# --- FIN DU FICHIER ---
        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































