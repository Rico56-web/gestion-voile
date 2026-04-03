
import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import os
import html
import streamlit.components.v1 as components
from datetime import datetime, date
# --- FONCTIONS DE SÉCURITÉ ---
def clean_text(text):
    """Nettoie le texte pour éviter de casser le JSON (supprime retours à la ligne et guillemets)"""
    if text is None or pd.isna(text): 
        return ""
    # Remplace les guillemets doubles par des simples et supprime les sauts de ligne
    return str(text).replace("\n", " ").replace('"', "'").strip()

def safe_val(val, default=0):
    """Convertit en entier sans planter"""
    try:
        if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan": return default
        clean = "".join(filter(str.isdigit, str(val).split('.')[0]))
        return int(clean) if clean else default
    except: return default 
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
# --- 5. PAGE CONTACTS (VERSION FINALE + DURÉE NAVIGATION) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    if 'mode_saisie' not in st.session_state: st.session_state.mode_saisie = False
    if 'edit_idx' not in st.session_state: st.session_state.edit_idx = None
    if 'confirm_del_idx' not in st.session_state: st.session_state.confirm_del_idx = None
    if 'view_archive' not in st.session_state: st.session_state.view_archive = False

    if st.session_state.mode_saisie:
        st.markdown('<div class="main-header">📝 FICHE CONTACT</div>', unsafe_allow_html=True)
        idx = st.session_state.edit_idx
        is_edit = idx is not None and idx < len(df_c)
        c_ref = df_c.iloc[idx] if is_edit else {}

        with st.form("form_contact_2026"):
            c1, c2 = st.columns(2)
            f_pre = c1.text_input("👤 Prénom", value=str(c_ref.get('Prénom', '')))
            f_nom = c2.text_input("📛 NOM", value=str(c_ref.get('Nom', '')))
            f_tel = st.text_input("📞 Téléphone", value=str(c_ref.get('Téléphone', '')))
            f_eml = st.text_input("📧 Email", value=str(c_ref.get('Email', '')))
            f_soc = st.text_input("🏢 Société", value=str(c_ref.get('Société', 'PARTICULIER')))
            
            c3, col_paie = st.columns(2)
            l_statuts = ["En attente", "Ok", "Refusé", "Terminé"]
            curr_s = str(c_ref.get('Statut', 'En attente')).capitalize()
            s_idx = l_statuts.index(curr_s) if curr_s in l_statuts else 0
            f_statut = c3.selectbox("🚦 Statut Dossier", options=l_statuts, index=s_idx)
            
            p_val_f = str(c_ref.get('Paiement', '')).strip().upper()
            p_idx = 1 if ("PAY" in p_val_f and "NON" not in p_val_f) else 0
            f_paie = col_paie.selectbox("💰 État Paiement", options=["Non payé", "Payé"], index=p_idx)

            # --- LIGNE LOGISTIQUE : DATE / JOURS / PERSONNES ---
            c5, c6, c7 = st.columns([1.5, 1, 1])
            f_dat = c5.text_input("📅 Date Nav", value=str(c_ref.get('DateNav', '')))
            f_jou = c6.number_input("⏳ Jours", min_value=1, value=int(safe_val(c_ref.get('Nbre de jours'), 1)))
            f_per = c7.number_input("👥 Pers", min_value=1, value=int(safe_val(c_ref.get('Nbre de personnes'), 1)))
            
            f_pri = st.number_input("💵 Prix Total (€)", min_value=0, value=int(safe_val(c_ref.get('Prix'), 0)))
            f_com = st.text_area("💬 Notes", value=str(c_ref.get('Commentaires', '')))

            bs1, bs2 = st.columns(2)
            if bs1.form_submit_button("💾 ENREGISTRER", use_container_width=True):
                new_d = {
                    "Prénom": f_pre, "Nom": f_nom.upper(), "Téléphone": f_tel, "Email": f_eml, 
                    "Société": f_soc.upper(), "Statut": f_statut, "DateNav": f_dat, 
                    "Nbre de jours": f_jou, "Nbre de personnes": f_per, "Prix": f_pri, 
                    "Paiement": str(f_paie), "Commentaires": clean_text(f_com)
                }
                if is_edit: df_c.iloc[idx] = new_d
                else: df_c = pd.concat([df_c, pd.DataFrame([new_d])], ignore_index=True)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.mode_saisie = False
                st.rerun()

            if bs2.form_submit_button("🔙 RETOUR", use_container_width=True):
                st.session_state.mode_saisie = False
                st.rerun()

    else:
        st.markdown('<div class="main-header">📇 CONTACTS 2026</div>', unsafe_allow_html=True)
        
        n1, n2, n3 = st.columns([1, 1, 1.2])
        if n1.button("⛵ EN COURS", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
            st.session_state.view_archive = False
            st.rerun()
        if n2.button("📦 ARCHIVES", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
            st.session_state.view_archive = True
            st.rerun()
        if n3.button("➕ NOUVEAU", use_container_width=True, type="primary"):
            st.session_state.mode_saisie = True; st.session_state.edit_idx = None; st.rerun()

        col_search, col_reset = st.columns([4, 1])
        search_q = col_search.text_input("🔍 Rechercher...", "").strip().upper()
        if col_reset.button("🔙"): st.rerun()

        st.divider()

        is_paye = df_c['Paiement'].astype(str).str.upper().str.contains("PAY", na=False) & \
                  ~df_c['Paiement'].astype(str).str.upper().str.contains("NON", na=False)
        mask_arch = df_c['Statut'].astype(str).str.upper().str.contains("TERMINÉ|REFUSÉ", na=False) & is_paye
        df_visu = df_c[mask_arch].copy() if st.session_state.view_archive else df_c[~mask_arch].copy()

        if search_q:
            m_s = (df_visu['Nom'].astype(str).str.upper().str.contains(search_q, na=False) | 
                  df_visu['Société'].astype(str).str.upper().str.contains(search_q, na=False))
            df_visu = df_visu[m_s]
        for i, r in df_visu.iterrows():
            st_b = str(r.get('Statut','En attente')).capitalize()
            nom_v, pre_v = str(r.get('Nom','')).upper(), str(r.get('Prénom','')).capitalize()
            soc_v = str(r.get('Société','')).upper()
            tel_v = str(r.get('Téléphone',''))
            eml_v = str(r.get('Email',''))
            
            p_val_brut = str(r.get('Paiement', '')).strip().upper()
            p_status, p_color = ("✅ PAYÉ", "#0047AB") if ("PAY" in p_val_brut and "NON" not in p_val_brut) else ("⚠️ NON PAYÉ", "#e74c3c")
            
            color_map = {"Ok": "#27ae60", "Refusé": "#e74c3c", "Terminé": "#34495e", "En attente": "#f39c12"}
            base_col = "#0047AB" if "CMN" in soc_v else color_map.get(st_b, "#f39c12")
            label_soc = f"🏢 {soc_v}" if soc_v != nom_v else "👤 PARTICULIER"
            nb_jours = int(safe_val(r.get('Nbre de jours'), 1))

            # --- CARTE AVEC COORDONNÉES RÉAPPARUES ---
            html_card = f"""
            <div style="border:5px solid {base_col};border-left:20px solid {base_col};padding:15px;border-radius:15px;background-color:white;margin-bottom:12px;box-shadow:5px 5px 15px rgba(0,0,0,0.1);">
                <span style="float:right;color:{p_color};font-weight:bold;border:2px solid {p_color};padding:2px 5px;border-radius:5px;font-size:0.8rem;">{p_status}</span>
                <div style="font-size:1.25rem;font-weight:bold;color:{base_col};margin-bottom:2px;display:flex;align-items:center;">
                    <span style="background-color:{base_col};color:white;min-width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;font-size:0.9rem;margin-right:12px;">{i+1}</span>
                    {nom_v} {pre_v}
                </div>
                <div style="font-weight:bold;color:#666;margin-left:40px;font-size:0.85rem;text-transform:uppercase;">{label_soc}</div>
                
                <hr style="border:0;border-top:1px solid #eee;margin:12px 0;">
                
                <div style="margin-left:5px; margin-bottom:10px;">
                    <div style="font-size:1.05rem; font-weight:bold; color:#333;">📞 {tel_v if tel_v not in ['nan','None',''] else '---'}</div>
                    <div style="font-size:0.9rem; color:#555;">📧 {eml_v if eml_v not in ['nan','None',''] else '---'}</div>
                </div>

                <div style="display:flex;justify-content:space-between;align-items:center;background:#f8f9fa;padding:8px 12px;border-radius:8px;border:1px solid #eee;">
                    <div style="text-align:center;">
                        <div style="font-size:0.6rem;color:#888;">DATE & DURÉE</div>
                        <div style="font-size:0.85rem;font-weight:bold;">{r.get('DateNav','-')} ({nb_jours}j)</div>
                    </div>
                    <div style="text-align:center;">
                        <div style="font-size:0.6rem;color:#888;">PRIX</div>
                        <div style="font-size:0.85rem;font-weight:bold;color:#27ae60;">{r.get('Prix','0')}€</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(html_card, unsafe_allow_html=True)

            # --- BOUTONS D'ACTION RAPIDE ---
            t_clean = str(tel_v).replace(" ","")
            st.markdown(f"""
                <div style="display:flex;gap:8px;margin-bottom:10px;">
                    <a href="tel:{t_clean}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:14px;">📞 APPEL</a>
                    <a href="https://wa.me/{t_clean}" style="flex:1;text-align:center;background:#25D366;color:white;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;font-size:14px;">🟢 WA</a>
                    <a href="mailto:{eml_v}" style="flex:1;text-align:center;background:#f0f2f6;color:black;text-decoration:none;padding:12px;border-radius:10px;font-weight:bold;border:1px solid #ccc;font-size:14px;">✉️ MAIL</a>
                </div>
            """, unsafe_allow_html=True)

            # Boutons Modifier / Supprimer (le reste du code est inchangé)
            g1, g2 = st.columns(2)
            if g1.button(f"✏️ MODIFIER {i+1}", key=f"ed_v_{i}", use_container_width=True):
                st.session_state.edit_idx = i; st.session_state.mode_saisie = True; st.rerun()
            # ... (suite du bouton supprimer)
      
# =================================================================
# --- 6. PAGE PLANNING (VUE MOIS + LISTE + BILAN FINANCIER) ---
# =================================================================
elif st.session_state.page == "PLANNING":
    # Optimisation de la largeur pour iPhone 16
    st.markdown("""<style>.block-container { padding: 10px !important; } table { width: 100% !important; border-collapse: collapse; }</style>""", unsafe_allow_html=True)
    st.markdown('<div class="main-header">🗓️ PLANNING VESTA 2026</div>', unsafe_allow_html=True)

    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    # Sélecteurs de période
    col_m, col_y = st.columns([1.5, 1])
    with col_m:
        m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        sel_m = m_noms.index(st.selectbox("Mois", m_noms, index=aujourdhui.month - 1)) + 1
    with col_y:
        sel_y = st.selectbox("Année", [2026, 2027, 2028], index=0)

    # --- INITIALISATION DES DONNÉES ---
    jours_occ = {}
    total_mois = 0
    nb_sorties = 0
    missions_list = []

    for idx, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' not in d_str: continue
            parts = d_str.split('/')
            dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
            if yv < 100: yv += 2000
            
            if mv == sel_m and yv == sel_y:
                s_val = str(r.get('Statut', '')).strip().lower()
                if any(x in s_val for x in ["refusé", "archivé", "supprimé"]): continue
                
                # Données pour la liste et le bilan
                r_idx = r.copy()
                r_idx['original_idx'] = idx
                missions_list.append(r_idx)
                total_mois += float(safe_val(r.get('Prix'), 0))
                nb_sorties += 1
                
                # Couleurs du Calendrier
                this_date = date(yv, mv, dv)
                soc_val = str(r.get('Société', '')).strip().upper()
                p_val = str(r.get('Paiement', '')).strip().upper()
                is_paye = ("PAY" in p_val) and ("NON" not in p_val)
                
                if this_date < aujourdhui: color = "#0047AB" if is_paye else "#e74c3c"
                elif "CMN" in soc_val: color = "#0047AB"
                elif "ok" in s_val: color = "#27ae60"
                elif "attente" in s_val: color = "#f39c12"
                else: color = "transparent"
                
                n_j = int(safe_val(r.get('Nbre de jours'), 1))
                for j in range(dv, dv + n_j):
                    if j <= 31:
                        if j in jours_occ and (color == "#e74c3c" or color == "#0047AB"): 
                            jours_occ[j] = {"c": color}
                        elif j not in jours_occ: 
                            jours_occ[j] = {"c": color}
        except: continue

    # --- 1. DESSIN DU CALENDRIER (VUE MOIS) ---
    import calendar
    jours_sem = ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"]
    h_cal = '<table style="width:100%; text-align: center; table-layout: fixed; background: white; border: 1px solid #eee; border-radius:10px; overflow:hidden;">'
    h_cal += '<tr style="background: #f1f3f5;">'
    for js in jours_sem: h_cal += f'<td style="padding: 8px 0; font-size: 11px; font-weight: bold; border: 0.5px solid #eee;">{js}</td>'
    h_cal += '</tr>'
    
    cal_mat = calendar.monthcalendar(sel_y, sel_m)
    for sem in cal_mat:
        h_cal += '<tr>'
        for jour in sem:
            if jour == 0: h_cal += '<td style="height:45px; border:0.5px solid #f8f9fa;"></td>'
            else:
                bg = jours_occ.get(jour, {}).get("c", "transparent")
                txt_c = "white" if bg != "transparent" else "black"
                is_today = (jour == aujourdhui.day and sel_m == aujourdhui.month and sel_y == aujourdhui.year)
                border_s = "2px solid #0047AB" if is_today else "none"
                circle = f'<div style="background:{bg}; color:{txt_c}; border-radius:50%; width:28px; height:28px; line-height:28px; margin:auto; font-weight:bold; font-size:12px; border:{border_s};">{jour}</div>'
                h_cal += f'<td style="border:0.5px solid #eee; height:48px;">{circle}</td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    st.markdown(h_cal, unsafe_allow_html=True)

    # --- 2. LISTE DES MISSIONS DU MOIS ---
    st.markdown(f"#### 📋 Détails de {m_noms[sel_m-1]}")
    if not missions_list:
        st.caption("Aucune mission prévue.")
    else:
        df_m = pd.DataFrame(missions_list)
        df_m['j_int'] = df_m['DateNav'].apply(lambda x: int(x.split('/')[0]) if '/' in str(x) else 0)
        df_m = df_m.sort_values('j_int')

        for _, row in df_m.iterrows():
            soc = str(row.get('Société','')).upper()
            c_line = "#0047AB" if "CMN" in soc else "#27ae60"
            n_jours = int(safe_val(row.get('Nbre de jours'), 1))
            j_deb = int(row['j_int'])
            date_txt = f"{j_deb}" if n_jours <= 1 else f"{j_deb}➔{j_deb + n_jours - 1}"
            
            st.markdown(f"""
                <div style="display: flex; padding: 10px 5px; border-bottom: 1px solid #eee; background: white; align-items: center;">
                    <div style="background: {c_line}; color: white; border-radius: 8px; padding: 4px; min-width: 50px; text-align: center; font-weight: bold; margin-right: 10px;">
                        {date_txt}<br><span style="font-size: 0.5rem;">JOUR</span>
                    </div>
                    <div style="flex-grow: 1;">
                        <b style="font-size: 0.9rem;">{str(row.get('Nom','')).upper()}</b><br>
                        <small style="color: #666;">{soc} ({row.get('Prix','0')}€)</small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"🔍 VOIR FICHE : {str(row.get('Nom','')).upper()}", key=f"p_goto_{row['original_idx']}", use_container_width=True):
                st.session_state.edit_idx = row['original_idx']
                st.session_state.mode_saisie = True
                st.session_state.page = "CONTACTS"
                st.rerun()

    # --- 3. BILAN FINANCIER (BAS DE PAGE) ---
    st.markdown(f"""
        <div style="background: #f8f9fa; padding: 12px; border-radius: 12px; border: 1px solid #ddd; margin-top: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #555;">
                <span>Nombre de sorties :</span><b>{nb_sorties}</b>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 1.1rem; font-weight: bold; border-top: 2px solid #0047AB; margin-top: 8px; padding-top: 8px;">
                <span>TOTAL DU MOIS :</span><span style="color: #0047AB;">{total_mois:,.0f} €</span>
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

    # --- Initialisation des données ---
    df_st = df_c.copy()
    
    if not df_st.empty and 'Prix' in df_st.columns:
        df_st['PrixNum'] = df_st['Prix'].apply(clean_val)
        df_st['M_Sort'], df_st['Mois'] = zip(*df_st['DateNav'].apply(get_month_info))
        
        # Calcul du CA
        def calc_ca(x):
            p_val = str(x.get('Paiement', '')).upper()
            s_val = str(x.get('Statut', '')).upper()
            if "PAYÉ" in p_val or s_val == "OK":
                return x['PrixNum']
            return 0.0
            
        df_st['CA_Calcul'] = df_st.apply(calc_ca, axis=1)

    # --- Affichage des résultats ---
    st.subheader("📅 Synthèse Mensuelle 2026")
    if not df_st.empty:
        mensuel = df_st.groupby(['M_Sort', 'Mois'])['CA_Calcul'].sum().reset_index()
        st.table(mensuel[['Mois', 'CA_Calcul']].set_index('Mois').style.format("{:.0f} €"))

    col1, col2 = st.columns(2)
    tot_enc = df_st[df_st['Paiement'].astype(str).str.contains("PAYÉ", case=False, na=False)]['PrixNum'].sum()
    tot_avr = df_st[(df_st['Statut'].astype(str) == "OK") & (~df_st['Paiement'].astype(str).str.contains("PAYÉ", case=False, na=False))]['PrixNum'].sum()
    
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



































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































