
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import html
import streamlit.components.v1 as components
from datetime import datetime, date
 
# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

 # --- AJOUTER CE BLOC AU TOUT DÉBUT DE TON SCRIPT (HORS DU IF PAGE) ---
if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None
 
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
        if password == "Skipper2026":
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
 
if "page" not in st.session_state:
    st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state:
    st.session_state.view_archive = False
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "m_edit_idx" not in st.session_state:
    st.session_state.m_edit_idx = None
if "maint_confirm_del" not in st.session_state:
    st.session_state.maint_confirm_del = None
 
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
 
# --- NETTOYAGE AUTOMATIQUE DES DONNÉES ---
def harmoniser_paiements(val):
    v = str(val).strip().lower()
    if not v or "un" in v or "non" in v or "pas" in v:
        return "Non payé"
    if "pay" in v:
        return "Payé"
    return "Non payé"
 
if 'Paiement' in df_c.columns:
    df_c['Paiement'] = df_c['Paiement'].apply(harmoniser_paiements)
 
# --- TRI CHRONOLOGIQUE ---
if not df_c.empty and 'DateNav' in df_c.columns:
    try:
        df_c['DateNav'] = df_c['DateNav'].astype(str).str.strip()
        df_c['temp_date'] = pd.to_datetime(df_c['DateNav'], format='%d/%m/%Y', errors='coerce')
        df_c = df_c.sort_values(by='temp_date', ascending=True, na_position='last')
        df_c = df_c.drop(columns=['temp_date'])
    except: pass

# =================================================================
# --- 5. PAGE CONTACTS (VERSION CORRIGÉE DIV & ACTIONS) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.title("👥 Vesta - Missions")
    
    # 1. Configuration & Style bouton vert
    LISTE_SOC = ["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"]
    st.markdown("""<style> div.stButton > button:first-child[kind="primary"] { background-color: #27ae60 !important; border-color: #27ae60 !important; color: white !important; } </style>""", unsafe_allow_html=True)
 
    c_n1, c_n2, c_add = st.columns([1, 1, 2])
    view_arc = st.session_state.get('view_archive', False)
 
    if c_n1.button("📂 En Cours", use_container_width=True, type="secondary" if view_arc else "primary"):
        st.session_state.view_archive = False
        st.rerun()
    if c_n2.button("🗄️ Archives", use_container_width=True, type="primary" if view_arc else "secondary"):
        st.session_state.view_archive = True
        st.rerun()
    
    if c_add.button("➕ NOUVELLE MISSION", type="primary", use_container_width=True):
        new_row = pd.DataFrame([{"Prénom": "", "Nom": "", "Société": "PARTICULIER", "Téléphone": "", "Email": "", "Statut": "En attente", "Paiement": "Non payé", "DateNav": datetime.now().strftime("%d/%m/%Y"), "Prix": "0", "NbreJours": "1", "NbrePers": "1", "Notes": ""}])
        df_c = pd.concat([new_row, df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.session_state.edit_idx = 0 
        st.rerun()
 
    st.divider()
    df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if view_arc else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]
 
    for i, r in df_disp.iterrows():
        num_f = i + 1
        # Nettoyage des données
        p_nom = str(r.get('Prénom', '')).strip()
        n_nom = str(r.get('Nom', '')).strip().upper()
        nom_c = f"{p_nom} {n_nom}" if (p_nom or n_nom) else f"Fiche #{num_f}"
        soc = str(r.get('Société', 'PARTICULIER')).upper()
        tel = str(r.get('Téléphone', '')).strip()
        mail = str(r.get('Email', '')).strip()
        
        # Couleurs Statuts
        s_val = str(r.get('Statut', 'En attente'))
        s_col = "#2ecc71" if "OK" in s_val.upper() else "#f1c40f" if "ATTENTE" in s_val.upper() else "#e74c3c"
        if "CMN" in soc: s_col = "#3498db"
        
        p_val = str(r.get('Paiement', 'Non payé'))
        p_col = "#3498db" if "PAYÉ" in p_val.upper() else "#e67e22"
 
        # Construction dynamique des boutons d'action (évite le bug des DIV vides)
        btn_html = '<div style="margin-top:15px;display:flex;gap:8px;">'
        if tel and len(tel) > 5:
            tel_clean = tel.replace(" ", "").replace(".", "")
            btn_html += f'<a href="tel:{tel_clean}" style="flex:1;background:#34495e;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">📞 APPEL</a>'
            btn_html += f'<a href="https://wa.me/{tel_clean}" style="flex:1;background:#25D366;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">💬 WA</a>'
        if mail and "@" in mail:
            btn_html += f'<a href="mailto:{mail}" style="flex:1;background:#e67e22;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">📧 MAIL</a>'
        btn_html += '</div>'
 
        card_html = f"""
            <div style="border:2px solid #1a2a6c;border-radius:12px;padding:15px;margin-bottom:8px;background:white;color:black;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">
                    <b style="color:#1a2a6c;font-size:1.1rem;">#{num_f} — {nom_c}</b>
                    <div style="text-align:right;display:flex;flex-direction:column;gap:4px;">
                        <span style="background:{s_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{s_val.upper()}</span>
                        <span style="background:{p_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{p_val.upper()}</span>
                    </div>
                </div>
                <div style="color:#666;font-size:0.85rem;margin-bottom:4px;">🏢 {soc}</div>
                <div style="font-size:0.8rem; color:#2980b9; margin-bottom:8px;">📞 {tel if tel else "---"} | 📧 {mail if mail else "---"}</div>
                <div style="font-size:0.95rem;border-top:1px solid #eee;padding-top:8px;color:#333;display:flex;justify-content:space-between;">
                    <span>📅 <b>{r.get('DateNav', '--/--/--')}</b></span><span>💰 <b>{r.get('Prix', '0')} €</b></span>
                </div>
                {btn_html}
            </div>"""
        st.markdown(card_html, unsafe_allow_html=True)
 
        # Actions Streamlit (Modifier / Supprimer)
        c_ed, c_del = st.columns([1, 1])
        if c_ed.button(f"✏️ Modifier", key=f"ed_{i}", use_container_width=True):
            st.session_state.edit_idx = i
            st.rerun()
        if c_del.button(f"🗑️ Supprimer", key=f"del_{i}", use_container_width=True):
            st.session_state.confirm_del_idx = i
            st.rerun()
        # --- LOGIQUE DE SUPPRESSION (FENÊTRE DE CONFIRMATION) ---
    if st.session_state.confirm_del_idx is not None:
        idx = st.session_state.confirm_del_idx
        client_nom = df_c.iloc[idx].get('Prénom', 'Client')
        st.warning(f"⚠️ Supprimer définitivement la fiche de **{client_nom}** ?")
        c1, c2 = st.columns(2)
        if c1.button("✅ OUI, SUPPRIMER", use_container_width=True):
            df_c = df_c.drop(idx).reset_index(drop=True)
            sauvegarder_data(df_c, "contacts.json")
            st.session_state.confirm_del_idx = None
            st.success("Fiche supprimée.")
            st.rerun()
        if c2.button("❌ ANNULER", use_container_width=True):
            st.session_state.confirm_del_idx = None
            st.rerun()
        st.divider()

    # --- AFFICHAGE DES FICHES ---
    df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if view_arc else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    for i, r in df_disp.iterrows():
        # ... (Garde ton bloc HTML card_html et btn_html ici) ...
        st.markdown(card_html, unsafe_allow_html=True)

        # BOUTONS ACTIONS (Corrigés avec clés uniques)
        c_ed, c_del = st.columns(2)
        
        # Action Modifier
        if c_ed.button(f"✏️ Modifier", key=f"btn_edit_{i}", use_container_width=True):
            st.session_state.edit_idx = i
            st.rerun()
            
        # Action Supprimer (Déclenche la confirmation en haut de page)
        if c_del.button(f"🗑️ Supprimer", key=f"btn_del_{i}", use_container_width=True):
            st.session_state.confirm_del_idx = i
            st.rerun()

    # --- FORMULAIRE D'ÉDITION (S'affiche si edit_idx n'est pas None) ---
    if st.session_state.edit_idx is not None:
        st.divider()
        idx = st.session_state.edit_idx
        st.subheader(f"📝 Modification : {df_c.iloc[idx]['Prénom']}")
        
        with st.form(f"form_edit_{idx}"):
            f_pre = st.text_input("Prénom", value=df_c.iloc[idx]['Prénom'])
            f_nom = st.text_input("Nom", value=df_c.iloc[idx]['Nom'])
            f_soc = st.selectbox("Société", ["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"], index=["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"].index(df_c.iloc[idx]['Société']))
            f_stat = st.selectbox("Statut", ["En attente", "OK", "Terminé", "Refusé"], index=["En attente", "OK", "Terminé", "Refusé"].index(df_c.iloc[idx]['Statut']))
            
            col_save, col_cancel = st.columns(2)
            if col_save.form_submit_button("💾 ENREGISTRER"):
                df_c.at[idx, 'Prénom'] = f_pre
                df_c.at[idx, 'Nom'] = f_nom
                df_c.at[idx, 'Société'] = f_soc
                df_c.at[idx, 'Statut'] = f_stat
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.edit_idx = None
                st.success("Modification enregistrée !")
                st.rerun()
            if col_cancel.form_submit_button("❌ FERMER"):
                st.session_state.edit_idx = None
                st.rerun()
        # Le formulaire d'édition reste identique à ton modèle précédent...
# =================================================================
# --- 6. PAGE PLANNING ---
# =================================================================
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning Vesta 2026")
    
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    col_m, col_y = st.columns(2)
    with col_m:
        m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        sel_m = m_noms.index(st.selectbox("Mois", m_noms, index=aujourdhui.month - 1)) + 1
    with col_y:
        sel_y = st.selectbox("Année", [2026, 2027, 2028], index=0)

    jours_occ = {}
    for _, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' not in d_str: continue
            parts = d_str.split('/')
            dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
            if yv < 100: yv += 2000
            
            if mv == sel_m and yv == sel_y:
                s_val = str(r.get('Statut', '')).strip().lower()
                if s_val in ["", "archivé", "archive", "supprimé", "refusé"]: continue
                
                this_date = date(yv, mv, dv)
                p_val = str(r.get('Paiement', '')).strip().lower()
                is_paye = ("pay" in p_val) and not any(x in p_val for x in ["un", "pas", "non"])
                
                if this_date < aujourdhui:
                    current_c = "#3498db" if is_paye else "#e74c3c"
                elif "ok" in s_val:
                    current_c = "#2ecc71"
                elif "attente" in s_val:
                    current_c = "#f1c40f"
                else:
                    current_c = "transparent"
                
                n_j = int(r.get('NbreJours', 1))
                for j in range(dv, dv + n_j):
                    if j in jours_occ:
                        old_c = jours_occ[j]["c"]
                        if "#e74c3c" in [current_c, old_c]: final_c = "#e74c3c"
                        else: final_c = current_c
                        jours_occ[j] = {"c": final_c}
                    else:
                        jours_occ[j] = {"c": current_c}
        except: continue

    jours_semaine = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    h_cal = '<table style="width:100%; border-collapse: collapse; text-align: center; background: white; color: black;">'
    h_cal += '<tr style="background: #f8f9fa; font-weight: bold; border-bottom: 2px solid #eee;">'
    for js in jours_semaine:
        h_cal += f'<td style="padding: 10px; border: 0.5px solid #eee; font-size: 12px; color: #666;">{js}</td>'
    h_cal += '</tr>'
    
    cal_mat = calendar.monthcalendar(sel_y, sel_m)
    for sem in cal_mat:
        h_cal += '<tr>'
        for jour in sem:
            if jour == 0:
                h_cal += '<td style="height:50px; border:0.5px solid #eee;"></td>'
            else:
                bg = jours_occ.get(jour, {}).get("c", "transparent")
                txt_c = "white" if bg != "transparent" else "black"
                if bg != "transparent":
                    circle = f'<div style="background:{bg}; color:{txt_c}; border-radius:50%; width:32px; height:32px; line-height:32px; margin:auto; font-weight:bold; font-size:13px;">{jour}</div>'
                else:
                    circle = f'<span style="color:black;">{jour}</span>'
                h_cal += f'<td style="border:0.5px solid #eee; height:55px;">{circle}</td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    
    st.markdown(h_cal, unsafe_allow_html=True)
    st.caption("🔴 Passé Impayé | 🔵 Passé Payé | 🟢 Confirmé | 🟡 En attente")

    st.markdown(f"#### 📋 Liste des sorties - {m_noms[sel_m-1]}")
    res_list = []
    ca_enc = 0.0
    ca_att = 0.0

    for _, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' in d_str:
                p = d_str.split('/')
                if int(p[1]) == sel_m and (int(p[2]) == sel_y or int(p[2])+2000 == sel_y):
                    if str(r.get('Statut','')).lower() not in ["refusé", "archivé"]:
                        res_list.append(r)
                        px = float(str(r.get('Prix', '0')).replace('€','').strip() or 0)
                        pv = str(r.get('Paiement', '')).lower()
                        if ("pay" in pv) and not any(x in pv for x in ["un", "non"]): ca_enc += px
                        else: ca_att += px
        except: continue

    if not res_list:
        st.info("Aucune navigation prévue.")
    else:
        res_list.sort(key=lambda x: int(str(x.get('DateNav')).split('/')[0]))
        for res in res_list:
            pv = str(res.get('Paiement', '')).lower()
            isp = ("pay" in pv) and not any(x in pv for x in ["un", "non"])
            p_col = "#27ae60" if isp else "#e67e22"
            sv = str(res.get('Statut', 'En attente'))
            s_col = "#2ecc71" if sv == "OK" else "#f1c40f" if sv == "En attente" else "#e74c3c"
            
            st.markdown(f"""
            <div style="padding: 15px; border-left: 6px solid {p_col}; background: white; color: black; border-radius: 10px; margin-bottom: 10px; border: 1px solid #eee;">
                <div style="display: flex; justify-content: space-between;">
                    <b>{res.get('Prénom')} {res.get('Nom','').upper()}</b>
                    <span style="background:{s_col}; color:white; padding:3px 8px; border-radius:6px; font-size:11px;">{sv}</span>
                </div>
                <div style="font-size: 0.9rem; margin-top: 5px;">
                    📅 {res.get('DateNav')} | 💰 <b>{res.get('Prix')} €</b><br>
                    <small>{'PAYÉ' if isp else 'À PAYER'}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)

# =================================================================
# --- 7. PAGE STATS ---
# =================================================================
elif st.session_state.page == "STATS":
    st.title("📊 Vesta - Pilotage & Frais")

    def clean_val(val):
        try:
            if not val or str(val).lower() in ["nan", "none", ""]: return 0.0
            s = "".join(c for c in str(val) if c.isdigit() or c in ".,-")
            return float(s.replace(",", "."))
        except: return 0.0

    def get_month_info(date_str):
        try:
            parts = str(date_str).split('/')
            if len(parts) >= 2:
                m_num = int(parts[1])
                months = ["Janv", "Févr", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
                return m_num, f"{m_num:02d}-{months[m_num-1]}"
        except: pass
        return 99, "99-Inconnu"

    df_st = df_c.copy()
    if not df_st.empty and 'Prix' in df_st.columns:
        df_st['PrixNum'] = df_st['Prix'].apply(clean_val)
        df_st['M_Sort'], df_st['Mois'] = zip(*df_st['DateNav'].apply(get_month_info))
        df_st['CA_Calcul'] = df_st.apply(lambda x: x['PrixNum'] if (str(x['Paiement']).upper() == "PAYÉ" or str(x['Statut']).upper() == "OK") else 0.0, axis=1)
    
    st.subheader("📅 Synthèse Mensuelle 2026")
    if not df_st.empty:
        mensuel = df_st.groupby(['M_Sort', 'Mois'])['CA_Calcul'].sum().reset_index()
        st.table(mensuel[['Mois', 'CA_Calcul']].set_index('Mois').style.format("{:.0f} €"))

    col1, col2 = st.columns(2)
    tot_enc = df_st[df_st['Paiement'].astype(str).str.upper() == "PAYÉ"]['PrixNum'].sum()
    tot_avr = df_st[(df_st['Statut'].astype(str).str.upper() == "OK") & (df_st['Paiement'].astype(str).str.upper() != "PAYÉ")]['PrixNum'].sum()
    
    col1.metric("💰 ENCAISSÉ", f"{tot_enc:,.0f}€")
    col2.metric("🕒 À VENIR", f"{tot_avr:,.0f}€")

    st.subheader("⏳ Missions à venir (Détail)")
    df_avr = df_st[(df_st['Statut'].astype(str).str.upper() == "OK") & (df_st['Paiement'].astype(str).str.upper() != "PAYÉ")].copy()
    if not df_avr.empty:
        tab = df_avr[['DateNav', 'Nom', 'PrixNum']]
        tab.columns = ['📅 Date', '👤 Client', '💰 €']
        st.table(tab.set_index('📅 Date'))
# =================================================================
# --- 8. PAGE MAINTENANCE (VERSION PERMANENTE GITHUB 2026) ---
# =================================================================
if st.session_state.page == "MAINT":
    st.title("🔧 Maintenance Vesta")
 
    # 1. CHARGEMENT VIA GITHUB
    file_path_m = 'maintenance.json'
    df_m = charger_data(file_path_m)
    
    if df_m.empty:
        df_m = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])
 
    # 2. INTERFACE DE SAISIE
    with st.expander("➕ Ajouter une nouvelle dépense", expanded=True):
        f_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"), key="m_date")
        f_obj = st.text_input("Objet (ex: Taxes DGAN, Révision)", key="m_obj")
        f_mt = st.number_input("Montant (€)", min_value=0.0, step=1.0, key="m_mt")
        
        if st.button("💾 ENREGISTRER SUR GITHUB", type="primary", use_container_width=True):
            if f_obj:
                nouvelle_ligne = pd.DataFrame([{
                    "Date": f_date,
                    "Objet": f_obj,
                    "Montant": float(f_mt),
                    "Statut": "OK"
                }])
                df_m = pd.concat([df_m, nouvelle_ligne], ignore_index=True)
                
                # SAUVEGARDE SUR GITHUB
                sauvegarder_data(df_m, file_path_m)
                
                st.balloons()
                st.success(f"Enregistré : {f_obj}")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("Veuillez entrer un 'Objet'.")
 
    st.divider()
 
    # 3. AFFICHAGE DE L'HISTORIQUE
    if not df_m.empty:
        total_frais = pd.to_numeric(df_m['Montant'], errors='coerce').sum()
        st.metric("TOTAL CUMULÉ 2026", f"{total_frais:.2f} €")
 
        for index, item in df_m.iloc[::-1].iterrows():
            with st.expander(f"📅 {item['Date']} - {item['Objet']} ({item['Montant']}€)"):
                if st.button(f"🗑️ Supprimer", key=f"del_m_{index}", use_container_width=True):
                    df_m = df_m.drop(index).reset_index(drop=True)
                    sauvegarder_data(df_m, file_path_m)
                    st.rerun()
 
    # 4. ZONE DE DANGER
    st.write("---")
    with st.expander("⚠️ Zone de Danger"):
        if st.checkbox("Confirmer la suppression totale"):
            if st.button("🔴 VIDER LE FICHIER", type="primary", use_container_width=True):
                df_vide = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])
                sauvegarder_data(df_vide, file_path_m)
                st.rerun()

# =================================================================
# --- 9. PAGE FACTURES (ANALYSE & ENVOI CMN OPTIMISÉ) ---
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
        # Conversion temporaire pour le filtrage
        df_fact = df_c.copy()
        df_fact['dt'] = pd.to_datetime(df_fact['DateNav'], format='%d/%m/%Y', errors='coerce')
        
        # Filtre : Société CMN + Mois + Année
        mask_cmn = (df_fact['Société'].astype(str).str.upper() == "CMN") & \
                   (df_fact['dt'].dt.month == index_mois) & \
                   (df_fact['dt'].dt.year == sel_annee)
        
        df_cmn_mois = df_fact[mask_cmn].copy()
        
        if not df_cmn_mois.empty:
            st.subheader(f"Missions CMN - {sel_mois} {sel_annee}")
            
            # Nettoyage des prix pour le calcul
            def clean_prix(x):
                try:
                    s = "".join(c for c in str(x) if c.isdigit() or c in ".,")
                    return float(s.replace(",", "."))
                except: return 0.0
 
            df_cmn_mois['PrixNum'] = df_cmn_mois['Prix'].apply(clean_prix)
            total_cmn = df_cmn_mois['PrixNum'].sum()
            
            # Affichage du tableau de contrôle sur l'iPhone
            st.table(df_cmn_mois[['DateNav', 'Nom', 'Prix']].set_index('DateNav'))
            st.metric("Total à facturer", f"{total_cmn:.2f} €")
            
            # --- 3. PRÉPARATION DU TEXTE ALIGNÉ (12 ET 3 ESPACES) ---
            st.divider()
            st.subheader("✉️ Rapport pour le Trésorier")
            
            lignes_missions = []
            esp12 = " " * 12
            esp3  = " " * 3
            
            for _, row in df_cmn_mois.iterrows():
                d_str = str(row['DateNav']).ljust(10)
                n_str = str(row['Nom'])
                p_str = f"{row['PrixNum']:.2f} €"
                # Assemblage de la ligne demandée
                lignes_missions.append(f"{d_str}{esp12}{n_str}{esp3}{p_str}")
            
            texte_missions = "\n".join(lignes_missions)
            
            destinataire = "tresorier@cmn-asso.fr, aurelienfaucheux@gmail.com"
            objet = f"Facturation Missions Vesta - {sel_mois} {sel_annee}"
            
            # Utilisation des TRIPLES GUILLEMETS pour éviter la SyntaxError
            corps_mail = f"""Bonjour,
 
J'espère que vous allez bien ! ⛵
 
Voici le récapitulatif des navigations de la CMN concernant le mois de {sel_mois} {sel_annee} :
 
{texte_missions}
 
Le montant total s'élève à {total_cmn:.2f} €.
 
Merci d'avance pour le règlement et à très vite sur l'eau !
 
Amicalement,
Eric (vesta)"""
 
            # --- 4. ZONE D'ENVOI ET COPIE ---
            st.text_area("Copier ce texte pour Gmail :", corps_mail, height=300)
            
            st.info(f"**Destinataire :** {destinataire}\n\n**Objet :** {objet}")
            
            import urllib.parse
            mail_link = f"mailto:{destinataire}?subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            
            st.link_button("🚀 TENTER L'ENVOI DIRECT (MAILTO)", mail_link, use_container_width=True)
            st.caption("Note : Si le bouton bloque, utilise le copier-coller du texte ci-dessus dans ton appli Gmail.")
            
        else:
            st.info(f"Aucune mission CMN trouvée pour {sel_mois} {sel_annee}.")
    else:
        st.warning("La base de données 'Contacts' est vide.")

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



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































