import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
import html
import streamlit.components.v1 as components
from datetime import datetime, date

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
try:
    df_m = pd.read_json("maintenance.json")
except:
    df_m = pd.DataFrame(columns=["Date", "Travaux", "Montant", "Etat", "Priorité", "Commentaires"])

# --- NETTOYAGE AUTOMATIQUE DES DONNÉES ---
def harmoniser_paiements(val):
    v = str(val).strip().lower()
    if not v or "un" in v or "non" in v or "pas" in v:
        return "Non payé"
    if "pay" in v:
        return "Payé"
    return "Non payé"

# On applique le nettoyage sur toute la colonne d'un coup
if 'Paiement' in df_c.columns:
    df_c['Paiement'] = df_c['Paiement'].apply(harmoniser_paiements)

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
# =================================================================
# --- 5. PAGE CONTACTS (VERSION NETTOYÉE ET UNIQUE) ---
# =================================================================
if st.session_state.page == "CONTACTS":
    st.title("👥 Vesta - Missions")
    import html

    # --- 1. FONCTIONS ET PARAMÈTRES ---
    def safe(val):
        v = str(val).strip()
        if v.lower() in ["none", "nan", "", "null", "undefined"]: return ""
        return html.escape(v).replace("\n", " ").replace("\r", "")

    # Ajout de l'option "AUTRES" comme demandé
    LISTE_SOC = ["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"]
# --- 1. CONFIGURATION DES SOCIÉTÉS ---
    LISTE_SOC = ["PARTICULIER", "CLICK", "VOG", "CMN", "AUTRES"]

    # --- 2. CSS POUR LE BOUTON VERT ET NAVIGATION ---
    st.markdown("""
        <style>
        div.stButton > button:first-child[kind="primary"] {
            background-color: #27ae60 !important;
            border-color: #27ae60 !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    c_n1, c_n2, c_add = st.columns([1, 1, 2])
    view_arc = st.session_state.get('view_archive', False)

    if c_n1.button("📂 En Cours", use_container_width=True, type="secondary" if view_arc else "primary"):
        st.session_state.view_archive = False
        st.rerun()
    if c_n2.button("🗄️ Archives", use_container_width=True, type="primary" if view_arc else "secondary"):
        st.session_state.view_archive = True
        st.rerun()
    
    # Ce bouton utilisera maintenant le style VERT défini au-dessus
    if c_add.button("➕ NOUVELLE MISSION", type="primary", use_container_width=True):
        new_row = pd.DataFrame([{
            "Prénom": "", "Nom": "", "Société": "PARTICULIER", 
            "Téléphone": "", "Email": "", "Statut": "En attente", 
            "Paiement": "Non payé", "DateNav": "01/01/2026", 
            "Prix": "0", "NbreJours": "1", "NbrePers": "1", "Notes": ""
        }])
        df_c = pd.concat([new_row, df_c], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.session_state.edit_idx = 0 
        st.rerun()
  

    st.divider()

    # --- 3. FILTRAGE ---
    df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])] if view_arc else df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    # --- 4. BOUCLE D'AFFICHAGE DES FICHES ---
    for i, r in df_disp.iterrows():
        num_f = i + 1
        
        # Extraction et nettoyage des données
        p_nom = safe(r.get('Prénom', ''))
        n_nom = safe(r.get('Nom', '')).upper()
        nom_c = f"{p_nom} {n_nom}" if (p_nom or n_nom) else f"Fiche #{num_f}"
        soc   = safe(r.get('Société', 'PARTICULIER')).upper()
        tel   = safe(r.get('Téléphone', ''))
        mail  = safe(r.get('Email', ''))
        note  = safe(r.get('Notes', ''))
        prix  = safe(r.get('Prix', '0'))
        date  = safe(r.get('DateNav', r.get('Date', '--/--/--')))
        jours = safe(r.get('NbreJours', '1'))
        pers  = safe(r.get('NbrePers', '1'))
        
        # Logique de Statuts et Couleurs
        s_val = safe(r.get('Statut', 'En attente'))
        s_col = "#2ecc71" if "OK" in s_val.upper() else "#f1c40f" if "ATTENTE" in s_val.upper() else "#e74c3c"
        if "CMN" in soc: s_col = "#3498db" # Spécificité CMN en Bleu
        
        p_val = safe(r.get('Paiement', 'Non payé'))
        p_col = "#3498db" if "PAYÉ" in p_val.upper() else "#e67e22"

        # --- DESIGN DE LA FICHE (Optimisé iPhone) ---
        card_html = (
            f'<div style="border:2px solid #1a2a6c;border-radius:12px;padding:15px;margin-bottom:8px;background:white;color:black;">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
            f'<b style="color:#1a2a6c;font-size:1.1rem;">#{num_f} — {nom_c}</b>'
            f'<div style="text-align:right;display:flex;flex-direction:column;gap:4px;">'
            f'<span style="background:{s_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{s_val.upper()}</span>'
            f'<span style="background:{p_col};color:white;padding:2px 10px;border-radius:12px;font-size:0.7rem;font-weight:bold;">{p_val.upper()}</span>'
            f'</div></div>'
            f'<div style="color:#666;font-size:0.85rem;margin-bottom:4px;">🏢 {soc}</div>'
            f'<div style="font-size:0.8rem; color:#2980b9; margin-bottom:8px;">📞 {tel if tel else "---"} &nbsp;|&nbsp; 📧 {mail if mail else "---"}</div>'
            f'<div style="font-size:0.95rem;border-top:1px solid #eee;padding-top:8px;color:#333;display:flex;justify-content:space-between;">'
            f'<span>📅 <b>{date}</b> ({jours}j)</span><span>👥 <b>{pers} pers.</b> | 💰 <b>{prix} €</b></span></div>'
            f'{"<div style=\'margin-top:10px;padding:10px;background:#f8f9fa;border-left:4px solid #1a2a6c;font-size:0.85rem;border-radius:4px;\'>📝 " + note + "</div>" if note else ""}'
            f'<div style="margin-top:15px;display:flex;gap:8px;">'
            f'<a href="tel:{tel.replace(" ", "")}" style="flex:1;background:#34495e;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">📞 APPEL</a>'
            f'<a href="https://wa.me/{tel.replace(" ", "")}" style="flex:1;background:#25D366;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">💬 WA</a>'
            f'<a href="mailto:{mail}" style="flex:1;background:#e67e22;color:white !important;padding:12px 5px;border-radius:8px;text-decoration:none;text-align:center;font-size:0.8rem;font-weight:bold;">📧 MAIL</a>'
            f'</div></div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)

        # --- ACTIONS ---
        c_ed, c_del = st.columns([1, 3])
        if c_ed.button(f"✏️ Modifier {num_f}", key=f"ed_{i}", use_container_width=True):
            st.session_state.edit_idx = i
            st.rerun()
        if c_del.button(f"🗑️ Supprimer {num_f}", key=f"del_{i}", use_container_width=True):
            st.session_state.confirm_del_idx = i
            st.rerun()

        # --- FORMULAIRE D'ÉDITION COMPLET ---
        if st.session_state.get('edit_idx') == i:
            with st.expander(f"⚙️ ÉDITION #{num_f}", expanded=True):
                with st.form(f"f_edit_{i}"):
                    c1, c2 = st.columns(2)
                    u_pre = c1.text_input("Prénom", value=r.get('Prénom', ''))
                    u_nom = c2.text_input("Nom", value=r.get('Nom', ''))
                    
                    # Menu déroulant avec "AUTRES"
                    idx_soc = LISTE_SOC.index(soc) if soc in LISTE_SOC else 0
                    u_soc = c1.selectbox("Société", LISTE_SOC, index=idx_soc)
                    u_tel = c2.text_input("Téléphone", value=r.get('Téléphone', ''))
                    
                    u_mai = c1.text_input("Email", value=r.get('Email', ''))
                    u_dat = c2.text_input("Date (JJ/MM/AAAA)", value=date)
                    
                    c3, c4 = st.columns(2)
                    u_jr  = c3.text_input("Nombre de jours", value=jours)
                    u_ps  = c4.text_input("Nombre de personnes", value=pers)
                    u_prix = c3.text_input("Prix Total (€)", value=prix)
                    u_stat = c4.selectbox("Statut Mission", ["En attente", "OK", "Terminé", "Refusé"], 
                                          index=["En attente", "OK", "Terminé", "Refusé"].index(s_val) if s_val in ["En attente", "OK", "Terminé", "Refusé"] else 0)
                    u_paye = c3.selectbox("Suivi Paiement", ["Non payé", "Payé"], index=1 if "PAYÉ" in p_val.upper() else 0)
                    
                    u_note = st.text_area("Notes", value=r.get('Notes', ''))
                    
                    b_save, b_ann = st.columns(2)
                    if b_save.form_submit_button("✅ SAUVEGARDER", use_container_width=True):
                        df_c.at[i, 'Prénom'] = u_pre
                        df_c.at[i, 'Nom'] = u_nom
                        df_c.at[i, 'Société'] = u_soc
                        df_c.at[i, 'Téléphone'] = u_tel
                        df_c.at[i, 'Email'] = u_mai
                        df_c.at[i, 'DateNav'] = u_dat
                        df_c.at[i, 'NbreJours'] = u_jr
                        df_c.at[i, 'NbrePers'] = u_ps
                        df_c.at[i, 'Prix'] = u_prix
                        df_c.at[i, 'Statut'] = u_stat
                        df_c.at[i, 'Paiement'] = u_paye
                        df_c.at[i, 'Notes'] = u_note
                        sauvegarder_data(df_c, "contacts.json")
                        st.session_state.edit_idx = None
                        st.rerun()
                    if b_ann.form_submit_button("❌ ANNULER", use_container_width=True):
                        st.session_state.edit_idx = None
                        st.rerun()

        # --- CONFIRMATION SUPPRESSION ---
        if st.session_state.get('confirm_del_idx') == i:
            st.error(f"Supprimer la mission #{num_f} ?")
            cy, cn = st.columns(2)
            if cy.button("OUI ✅", key=f"y_{i}", use_container_width=True):
                df_c = df_c.drop(i).reset_index(drop=True)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state.confirm_del_idx = None
                st.rerun()
            if cn.button("NON ❌", key=f"n_{i}", use_container_width=True):
                st.session_state.confirm_del_idx = None
                st.rerun()
# =================================================================
# --- 6. PAGE PLANNING (DÉBUT DU BLOC) ---
# =================================================================
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning Vesta 2026")
    
    # RÉCUPÉRATION DE LA DATE DU JOUR
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    # 2. SÉLECTION MOIS/ANNÉE
    col_m, col_y = st.columns(2)
    with col_m:
        m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        sel_m = m_noms.index(st.selectbox("Mois", m_noms, index=aujourdhui.month - 1)) + 1
    with col_y:
        sel_y = st.selectbox("Année", [2026, 2027, 2028], index=0)

    # 3. LOGIQUE DE CALCUL DES COULEURS (HORS COLONNES)
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
                is_paye = ("pay" in p_val or "paid" in p_val) and not any(x in p_val for x in ["un", "pas", "non"])
                
                # Définition de la couleur du rond
                if this_date < aujourdhui:
                    current_c = "#3498db" if is_paye else "#e74c3c" # Bleu si payé / Rouge si impayé
                elif "ok" in s_val:
                    current_c = "#2ecc71" # Vert
                elif "attente" in s_val:
                    current_c = "#f1c40f" # Jaune
                else:
                    current_c = "transparent"
                
                # Gestion de la durée (NbreJours)
                n_j = int(r.get('NbreJours', 1))
                for j in range(dv, dv + n_j):
                    if j in jours_occ:
                        # Priorité au rouge en cas de conflit
                        old_c = jours_occ[j]["c"]
                        if "#e74c3c" in [current_c, old_c]: final_c = "#e74c3c"
                        else: final_c = current_c
                        jours_occ[j] = {"c": final_c}
                    else:
                        jours_occ[j] = {"c": current_c}
        except:
            continue

# 4. AFFICHAGE DU CALENDRIER HTML (AVEC JOURS DE LA SEMAINE)
    jours_semaine = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    
    h_cal = '<table style="width:100%; border-collapse: collapse; text-align: center; background: white; color: black;">'
    
    # --- AJOUT DE L'EN-TÊTE DES JOURS ---
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
                # Texte blanc si le rond est coloré, sinon noir
                txt_c = "white" if bg != "transparent" else "black"
                
                # Création du rond si occupé, sinon chiffre simple
                if bg != "transparent":
                    circle = f'<div style="background:{bg}; color:{txt_c}; border-radius:50%; width:32px; height:32px; line-height:32px; margin:auto; font-weight:bold; font-size:13px;">{jour}</div>'
                else:
                    circle = f'<span style="color:black;">{jour}</span>'
                
                h_cal += f'<td style="border:0.5px solid #eee; height:55px;">{circle}</td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    
    st.markdown(h_cal, unsafe_allow_html=True)
    st.caption("🔴 Passé Impayé | 🔵 Passé Payé | 🟢 Confirmé | 🟡 En attente")

    # 5. DÉTAILS DES RÉSERVATIONS DU MOIS
    st.markdown(f"#### 📋 Liste des sorties - {m_noms[sel_m-1]}")
    
    res_list = []
    ca_encaisse = 0.0
    ca_attente = 0.0

    for _, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' in d_str:
                parts = d_str.split('/')
                if int(parts[1]) == sel_m and (int(parts[2]) == sel_y or int(parts[2])+2000 == sel_y):
                    if str(r.get('Statut','')).lower() not in ["refusé", "archivé"]:
                        res_list.append(r)
                        # Calcul CA
                        prix = float(str(r.get('Prix', '0')).replace('€','').strip() or 0)
                        p_val = str(r.get('Paiement', '')).lower()
                        if ("pay" in p_val) and not any(x in p_val for x in ["un", "non"]):
                            ca_encaisse += prix
                        else:
                            ca_attente += prix
        except:
            continue

    if not res_list:
        st.info("Aucune navigation prévue.")
    else:
        # Tri par jour
        res_list.sort(key=lambda x: int(str(x.get('DateNav')).split('/')[0]))
        
# --- BOUCLE DE LA LISTE DES RÉSERVATIONS (CORRIGÉE SANS NAMEERROR) ---
        for res in res_list:
            p_v = str(res.get('Paiement', '')).lower()
            is_p = ("pay" in p_v) and not any(x in p_v for x in ["un", "non"])
            p_color = "#27ae60" if is_p else "#e67e22"
            
            s_v = str(res.get('Statut', 'En attente'))
            s_color = "#2ecc71" if s_v == "OK" else "#f1c40f" if s_v == "En attente" else "#e74c3c"
            
            nom_c = f"{res.get('Prénom')} {res.get('Nom','').upper()}"
            nom_famille = res.get('Nom','')
            # On crée une clé unique basée sur le nom et la date pour éviter le NameError
            unique_key = f"btn_{nom_famille}_{str(res.get('DateNav')).replace('/','')}"

            # AFFICHAGE HTML (Identique à ce qu'on voulait pour l'iPhone)
            st.markdown(f"""
            <div style="padding: 15px; border-left: 6px solid {p_color}; background: white; color: black; border-radius: 10px; margin-bottom: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.1); border: 1px solid #eee;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="font-size: 1.1rem; font-weight: bold;">{nom_c}</div>
                    <div style="text-align: right;">
                        <span style="background:{s_color}; color:white; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:bold;">{s_v}</span><br>
                        <span style="background:{p_color}; color:white; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:bold; margin-top:4px; display:inline-block;">{'PAYÉ' if is_p else 'À PAYER'}</span>
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 0.9rem;">
                    📅 <b>{res.get('DateNav')}</b> | ⛵ {res.get('NbreJours', 1)}j | 💰 <b>{res.get('Prix')} €</b><br>
                    <small style="color: #555;">🏢 {res.get('Société','-')}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # LE BOUTON AVEC LA CLÉ CORRIGÉE
            if st.button(f"🔎 VOIR LA FICHE DE {nom_famille.upper()}", key=unique_key, use_container_width=True):
                st.session_state.search_contact = nom_famille
                st.session_state.page = "CONTACTS"
                st.rerun()

    # 6. RÉCAPITULATIF FINANCIER DU MOIS
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Missions", len(res_list))
    c2.metric("Encaissé", f"{ca_encaisse:.2f} €")
    c3.metric("À percevoir", f"{ca_attente:.2f} €")

# --- FIN DU BLOC PLANNING ---
# =================================================================
# --- 7. PAGE STATS (VERSION FINALE VALIDÉE) ---
# ================================================================
if st.session_state.page == "STATS":
    st.title("📊 Vesta - Pilotage")

    # --- 1. FONCTIONS DE NETTOYAGE ---
    def clean_p(val):
        try:
            if not val or str(val).lower() in ["nan", "none", ""]: return 0.0
            s = "".join(c for c in str(val) if c.isdigit() or c in ".,-")
            return float(s.replace(",", "."))
        except: return 0.0

    def get_month(date_str):
        try:
            parts = str(date_str).split('/')
            if len(parts) >= 2:
                m_num = int(parts[1])
                months = ["Janv", "Févr", "Mars", "Avril", "Mai", "Juin", "Juil", "Août", "Sept", "Oct", "Nov", "Déc"]
                return f"{m_num:02d} - {months[m_num-1]}"
        except: return "99 - Inconnu"
        return "99 - Inconnu"

    # Préparation
    df_st = df_c.copy()
    df_st['PrixNum'] = df_st['Prix'].apply(clean_p)
    df_st['Mois'] = df_st['DateNav'].apply(get_month)

    # --- 2. FILTRES STRICTS ---
    mask_paye = df_st['Paiement'].astype(str).apply(lambda x: x.strip().upper() == "PAYÉ")
    df_encaisse = df_st[mask_paye]
    
    mask_futur = (df_st['Statut'].astype(str).str.upper() == "OK") & (~mask_paye)
    df_futur = df_st[mask_futur]

    # --- 3. RÉSUMÉ COMPACT (iPhone) ---
    tot_r = df_encaisse['PrixNum'].sum()
    tot_f = df_futur['PrixNum'].sum()
    
    c1, c2 = st.columns(2)
    c1.metric("💰 REEL", f"{tot_r:,.0f}€")
    c2.metric("🕒 FUTUR", f"{tot_f:,.0f}€")
    st.write(f"**📈 TOTAL PRÉVU : {tot_r + tot_f:,.0f} €**")

    st.divider() # <--- VERIFIEZ BIEN L'ALIGNEMENT ICI

    # --- 4. VISION MENSUELLE ---
    st.subheader("📅 Calendrier Mensuel")
    df_plan = df_st[mask_paye | mask_futur]
    if not df_plan.empty:
        mensuel = df_plan.groupby('Mois').agg(CA=('PrixNum', 'sum'), Missions=('Nom', 'count')).sort_index()
        st.table(mensuel.style.format({"CA": "{:.0f} €"}))
    else:
        st.info("Aucune donnée.")

    st.divider()

    # --- 5. DÉTAIL DES MOIS (RÉDUIT MOBILE) ---
    st.subheader("✅ PAYÉ")
    st.dataframe(df_encaisse[['DateNav', 'Nom', 'Prix']], use_container_width=True, hide_index=True)

    st.subheader("⏳ À VENIR (OK)")
    st.dataframe(df_futur[['DateNav', 'Nom', 'Prix']], use_container_width=True, hide_index=True)

# =================================================================
# --- 8. PAGE MAINTENANCE (CONFIRMATION DE SUPPRESSION) ---
# =================================================================
elif st.session_state.page == "MAINT":
    st.subheader("🔧 Maintenance & Frais")
    
    # Init du state de confirmation si inexistant
    if 'm_confirm_del' not in st.session_state:
        st.session_state.m_confirm_del = None

    # 1. BOUTON NOUVEAU
    if st.button("➕ AJOUTER UN NOUVEAU FRAIS", use_container_width=True):
        new_m = {"Date": datetime.now().strftime("%d/%m/%Y"), "Travaux": "Nouvel achat", "Montant": 0.0}
        df_m = pd.concat([pd.DataFrame([new_m]), df_m], ignore_index=True)
        sauvegarder_data(df_m, "maintenance.json")
        st.rerun()

    st.divider()

    # 2. ZONE D'ÉDITION
    if st.session_state.get('m_edit_idx') is not None:
        idx = st.session_state.m_edit_idx
        if idx in df_m.index:
            r = df_m.loc[idx]
            with st.form("edit_maint_form"):
                u_d = st.text_input("Date", str(r.get('Date', '')))
                u_t = st.text_input("Travaux", str(r.get('Travaux', r.get('Cause', ''))))
                u_m = st.text_input("Montant (€)", str(r.get('Montant', r.get('Prix', '0'))))
                
                c_b1, c_b2 = st.columns(2)
                if c_b1.form_submit_button("💾 ENREGISTRER"):
                    df_m.at[idx, 'Date'] = u_d
                    df_m.at[idx, 'Travaux'] = u_t
                    df_m.at[idx, 'Montant'] = float(u_m.replace('€','').replace(',','.').strip() or 0)
                    sauvegarder_data(df_m, "maintenance.json")
                    st.session_state.m_edit_idx = None
                    st.rerun()
                if c_b2.form_submit_button("❌ ANNULER"):
                    st.session_state.m_edit_idx = None
                    st.rerun()
    
    # 3. LISTE ET SUPPRESSION SÉCURISÉE
    else:
        for i, r in df_m.iterrows():
            # Affichage de la fiche
            st.markdown(f'''
            <div style="border:1px solid #eee; padding:12px; border-radius:10px; background:white; color:black; margin-bottom:5px;">
                <b>📅 {r.get("Date", "N/A")}</b> | 🛠️ {r.get("Travaux", r.get("Cause",""))} | 💰 {float(r.get("Montant", r.get("Prix",0))):.2f} €
            </div>
            ''', unsafe_allow_html=True)
            
            # Si on a cliqué sur supprimer pour CETTE fiche
            if st.session_state.m_confirm_del == i:
                st.error("❗ Confirmer la suppression ?")
                col_c1, col_c2 = st.columns(2)
                if col_c1.button("✅ OUI, SUPPRIMER", key=f"conf_yes_{i}", use_container_width=True):
                    df_m = df_m.drop(i).reset_index(drop=True)
                    sauvegarder_data(df_m, "maintenance.json")
                    st.session_state.m_confirm_del = None
                    st.rerun()
                if col_c2.button("NON, ANNULER", key=f"conf_no_{i}", use_container_width=True):
                    st.session_state.m_confirm_del = None
                    st.rerun()
            else:
                # Affichage normal des boutons
                c1, c2 = st.columns(2)
                if c1.button("✏️ Modifier", key=f"edit_{i}", use_container_width=True):
                    st.session_state.m_edit_idx = i
                    st.rerun()
                if c2.button("🗑️ Supprimer", key=f"del_req_{i}", use_container_width=True):
                    st.session_state.m_confirm_del = i
                    st.rerun()
    # --- 4. TABLEAU RÉCAPITULATIF GLOBAL (TRIÉ PAR DATE) ---
    st.divider()
    st.write("📊 **Historique de l'entretien (Du plus récent au plus ancien)**")

    if not df_m.empty:
        # 1. On crée une copie pour ne pas abîmer les données sources
        df_tableau = df_m.copy()
        
        # 2. Conversion forcée en vraie date pour pouvoir TRIER
        # On transforme le Timestamp 1774569600000 en objet date Python
        df_tableau['Date_Tri'] = pd.to_datetime(df_tableau['Date'], errors='coerce')
        
        # 3. TRI : du plus récent au plus ancien
        df_tableau = df_tableau.sort_values(by='Date_Tri', ascending=False)

        # 4. FORMATAGE de l'affichage (JJ/MM/AAAA)
        df_tableau['Date'] = df_tableau['Date_Tri'].dt.strftime('%d/%m/%Y').fillna("Date inconnue")

        # 5. Gestion des noms de colonnes (Compatibilité anciens fichiers)
        if 'Cause' in df_tableau.columns and 'Travaux' not in df_tableau.columns:
            df_tableau = df_tableau.rename(columns={'Cause': 'Travaux'})
        if 'Prix' in df_tableau.columns and 'Montant' not in df_tableau.columns:
            df_tableau = df_tableau.rename(columns={'Prix': 'Montant'})

        # 6. AFFICHAGE DU TABLEAU
        st.dataframe(
            df_tableau[['Date', 'Travaux', 'Montant']], 
            column_config={
                "Date": st.column_config.TextColumn("Date 📅"),
                "Travaux": st.column_config.TextColumn("Nature des travaux 🔧"),
                "Montant": st.column_config.NumberColumn("Coût (€)", format="%.2f €"),
            },
            use_container_width=True,
            hide_index=True
        )

        # Total en bas du tableau
        total_m = pd.to_numeric(df_tableau['Montant'], errors='coerce').sum()
        st.success(f"💰 **Total cumulé des frais de maintenance : {total_m:,.2f} €**")
    else:
        st.info("Aucun frais enregistré pour le moment.")  
        # --- SYSTÈME D'ALERTE MAINTENANCE PRÉVENTIVE ---
    # Remplace '2450' par une variable si tu saisis tes heures ailleurs
    heures_actuelles = 2450  # Seuil que tu as fixé
    seuil_vidange = 2450
    
    if heures_actuelles >= seuil_vidange:
        st.error(f"⚠️ **ALERTE ENTRETIEN MOTEUR**")
        st.markdown(f"""
        **Heures moteur : {heures_actuelles} h** Il est temps d'effectuer la **vidange moteur** (Seuil : {seuil_vidange} h).
        """)
        if st.button("✅ MARQUER VIDANGE COMME FAITE"):
            # Crée un frais automatique pour la vidange
            new_v = {
                "Date": datetime.now().strftime("%d/%m/%Y"), 
                "Travaux": f"Vidange moteur faite à {heures_actuelles}h", 
                "Montant": 0.0
            }
            df_m = pd.concat([pd.DataFrame([new_v]), df_m], ignore_index=True)
            sauvegarder_data(df_m, "maintenance.json")
            st.success("Entretien enregistré ! N'oublie pas de modifier le montant du forfait.")
            st.rerun()
    st.divider()

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
        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































