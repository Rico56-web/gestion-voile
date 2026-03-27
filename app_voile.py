import requests, base64, json, time, calendar
import streamlit as st
import pandas as pd
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

# --- 5. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    st.title("👥 Vesta - Missions")
    
# --- 1. LE FORMULAIRE DE MODIFICATION ---
    if st.session_state.get('edit_idx') is not None:
        idx = st.session_state.edit_idx
        r = df_c.iloc[idx]
        
        with st.expander(f"📝 MODIFIER : {r.get('Prénom','')} {r.get('Nom','')}", expanded=True):
            with st.form(key=f"edit_form_secure_{idx}"):
                c1, c2 = st.columns(2)
                u_pre = c1.text_input("Prénom", value=str(r.get('Prénom', '')))
                u_nom = c2.text_input("Nom", value=str(r.get('Nom', '')))
                u_soc = c1.text_input("Société", value=str(r.get('Société', 'PARTICULIER')))
                u_tel = c2.text_input("Téléphone", value=str(r.get('Téléphone', '')))
                u_mail = st.text_input("Email", value=str(r.get('Email', '')))
                
                c_st, c_pa = st.columns(2)
                l_s = ["En attente", "OK", "Refusé", "Terminé"]
                u_statut = c_st.selectbox("Statut Mission", l_s, index=l_s.index(r.get('Statut')) if r.get('Statut') in l_s else 0)
                # --- REMPLACEZ LA LIGNE 134 PAR CE BLOC ---
                options_p = ["Non payé", "Payé"]
                val_actuelle = str(r.get('Paiement', '')).lower()

                # On définit l'index : 1 (Payé) si on trouve "pay" ou "paid", sinon 0
                idx_p = 1 if ("pay" in val_actuelle and "non" not in val_actuelle and "un" not in val_actuelle) else 0

                u_paye = c_pa.selectbox("Paiement", options_p, index=idx_p)
                
                c3, c4, c5 = st.columns(3)
                u_date = c3.text_input("Date Nav", value=str(r.get('DateNav', '')))
                
                # --- SÉCURITÉ POUR LES NOMBRES (Évite le ValueError) ---
                try:
                    val_jours = int(float(r.get('NbreJours', 1)))
                except:
                    val_jours = 1
                try:
                    val_pers = int(float(r.get('NbrePers', 1)))
                except:
                    val_pers = 1
                
                u_jours = c4.number_input("Jours", value=val_jours, min_value=1)
                u_pers = c5.number_input("Pers.", value=val_pers, min_value=1)
                
                u_prix = st.text_input("Prix total (€)", value=str(r.get('Prix', '0.00')))
                u_comm = st.text_area("Commentaires", value=str(r.get('Commentaires', '')))

                # --- BOUTON D'ENREGISTREMENT (Indispensable ici) ---
                submitted = st.form_submit_button("💾 ENREGISTRER LES MODIFICATIONS")

                if submitted:
                    df_c.at[idx, 'Prénom'] = u_pre
                    df_c.at[idx, 'Nom'] = u_nom
                    df_c.at[idx, 'Société'] = u_soc
                    df_c.at[idx, 'Téléphone'] = u_tel
                    df_c.at[idx, 'Email'] = u_mail
                    df_c.at[idx, 'Statut'] = u_statut
                    df_c.at[idx, 'Paiement'] = u_paye
                    df_c.at[idx, 'Prix'] = u_prix
                    df_c.at[idx, 'DateNav'] = u_date
                    df_c.at[idx, 'NbreJours'] = u_jours
                    df_c.at[idx, 'NbrePers'] = u_pers
                    df_c.at[idx, 'Commentaires'] = u_comm
                    
                    sauvegarder_data(df_c, "contacts.json")
                    st.session_state.edit_idx = None
                    st.rerun()

        if st.button("❌ Fermer sans enregistrer", key="close_edit"):
            st.session_state.edit_idx = None
            st.rerun()

 # --- 2. NAVIGATION AVEC INDICATEUR D'ÉTAT ---
    st.divider()
    n1, n2, n3 = st.columns(3)
    
    view_arc = st.session_state.get('view_archive', False)

    if n1.button("📂 En Cours", key="nav_active", use_container_width=True, type="primary" if not view_arc else "secondary"):
        st.session_state.view_archive = False
        st.rerun()

    if n2.button("🗄️ Archives", key="nav_archive", use_container_width=True, type="primary" if view_arc else "secondary"):
        st.session_state.view_archive = True
        st.rerun()

    if n3.button("➕ Ajouter", key="nav_add_new", use_container_width=True):
        new_row = {"Prénom": "Nouveau", "Nom": "Contact", "Société": "PARTICULIER", "Statut": "En attente", "Paiement": "Non payé"}
        df_c = pd.concat([df_c, pd.DataFrame([new_row])], ignore_index=True)
        sauvegarder_data(df_c, "contacts.json")
        st.session_state.edit_idx = len(df_c) - 1
        st.rerun()

    # --- 3. CRÉATION DE DF_DISP (Indispensable avant la boucle) ---
    if view_arc:
        df_disp = df_c[df_c['Statut'].isin(["Terminé", "Refusé"])]
    else:
        df_disp = df_c[~df_c['Statut'].isin(["Terminé", "Refusé"])]

    # --- 4. AFFICHAGE DES FICHES ---
    for i, r in df_disp.iterrows():
        # 1. On récupère la valeur brute enregistrée (ex: "Payé", "Paid", "Non payé")
        p_brut = str(r.get('Paiement', 'Non payé')).strip()
        p_test = p_brut.lower()
        
        # 2. LA RÈGLE DÉFINITIVE (Celle qui commande le badge)
        # On est "Payé" si : le mot contient 'pay' ou 'paid' 
        # ET qu'il n'y a pas 'non', 'un' ou 'pas'
        is_p_ok = ("pay" in p_test or "paid" in p_test) and ("non" not in p_test and "un" not in p_test and "pas" not in p_test)
        
        # 3. ON DÉFINIT LE TEXTE ET LA COULEUR DU BADGE
        p_label = "Payé" if is_p_ok else "Non payé"
        p_col = "#27ae60" if is_p_ok else "#e67e22" # Vert si OK, Orange sinon
        
        # 4. STATUT (OK, En attente, etc.)
        s = str(r.get('Statut', 'En attente'))
        s_col = "#2ecc71" if s == "OK" else "#f1c40f" if s == "En attente" else "#e74c3c"
        
        
        # --- INFOS CONTACT ---
        t_raw = str(r.get('Téléphone','')).strip()
        t_link = t_raw.replace(" ", "").replace(".", "").replace("-", "")
        mail = str(r.get('Email', '')).strip()

        # HTML Premium (Forçage noir pour iPhone)
        # --- HTML DU BADGE (CORRIGÉ POUR ÉVITER LE NAMEERROR) ---
        h = f'''
        <div style="border: 2px solid #1a2a6c; border-radius: 10px; padding: 15px; margin-bottom: 15px; background-color: white; color: black;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <b style="font-size: 1.1rem; color: #1a2a6c;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b>
                <div>
                    <span style="background:{s_col}; color:white; padding:2px 8px; border-radius:5px; font-size:0.7rem; font-weight:bold;">{s}</span>
                    <span style="background:{p_col}; color:white; padding:2px 8px; border-radius:5px; font-size:0.7rem; font-weight:bold; margin-left:5px;">{p_label}</span>
                </div>
            </div>
            <div style="color: #666; font-size: 0.8rem; font-weight: bold; margin-bottom: 10px;">🏢 {str(r.get('Société','PARTICULIER')).upper()}</div>
            <div style="font-size: 0.9rem; color: black; line-height: 1.4;">
                📅 <b>Date :</b> {r.get('DateNav','--')}<br>
                💰 <b>Prix :</b> {r.get('Prix','0.00')} €<br>
                ⛵ <b>Jours :</b> {r.get('NbreJours', 1)} | 👥 <b>Pers :</b> {r.get('NbrePers', 1)}
            </div>
            <div style="margin-top: 15px; display: flex; gap: 5px;">
                <a href="tel:{t_link}" style="flex:1; background:#3498db; color:white; padding:10px; border-radius:8px; text-decoration:none; text-align:center; font-weight:bold; font-size:0.7rem;">APPEL</a>
                <a href="https://wa.me/{t_link}" style="flex:1; background:#25D366; color:white; padding:10px; border-radius:8px; text-decoration:none; text-align:center; font-weight:bold; font-size:0.7rem;">WA</a>
            </div>
        </div>
        '''
        st.markdown(h, unsafe_allow_html=True)  
# --- BOUTONS ACTIONS (✏️ et 🗑️) ---
        c_ed, c_del = st.columns([1, 4])
        suffix = "arc" if view_arc else "act"
        
        # Bouton Modifier
        if c_ed.button("✏️", key=f"btn_ed_{suffix}_{i}"):
            st.session_state.edit_idx = i
            st.rerun()

        # LOGIQUE DE CONFIRMATION DE SUPPRESSION
        confirm_key = f"confirm_del_{suffix}_{i}"
        
        if not st.session_state.get(confirm_key, False):
            if c_del.button("🗑️ SUPPRIMER CETTE MISSION", key=f"btn_del_{suffix}_{i}", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()
        else:
            c_del.warning("⚠️ Confirmer la suppression ?")
            b1, b2 = c_del.columns(2)
            if b1.button("✅ OUI", key=f"yes_{confirm_key}", use_container_width=True):
                df_c = df_c.drop(i).reset_index(drop=True)
                sauvegarder_data(df_c, "contacts.json")
                st.session_state[confirm_key] = False
                st.rerun()
            if b2.button("❌ NON", key=f"no_{confirm_key}", use_container_width=True):
                st.session_state[confirm_key] = False
                st.rerun()

# =================================================================
# --- 6. PAGE PLANNING (BIEN ALIGNÉE SUR LE BORD GAUCHE) ---
# =================================================================
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Planning Vesta 2026")
    
    # 1. RÉCUPÉRATION DE LA DATE DU JOUR
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    # 2. SÉLECTION MOIS/ANNÉE
    col_m, col_y = st.columns(2)
    with col_m:
        m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        sel_m = m_noms.index(st.selectbox("Mois", m_noms, index=aujourdhui.month - 1)) + 1
    with col_y:
        sel_y = st.selectbox("Année", [2026, 2027, 2028], index=0)

    # 3. FILTRAGE ET LOGIQUE DES COULEURS
        jours_occ = {}
        for _, r in df_c.iterrows():
            try:
                d_str = str(r.get('DateNav', '')).strip()
                if '/' not in d_str: continue
                parts = d_str.split('/')
                dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
                if yv < 100: yv += 2000
                
                # --- LA LIGNE 311 EST ICI (BIEN ALIGNÉE) ---
                if mv == sel_m and yv == sel_y:
                    s_val = str(r.get('Statut', '')).strip().lower()
                    p_val = str(r.get('Paiement', '')).strip().lower()
                    
                    # On ignore les fiches vides ou archivées
                    if s_val in ["", "archivé", "archive", "supprimé"]:
                        continue
                    
                    this_date = date(yv, mv, dv)
 # --- DÉTECTION "ZÉRO ERREUR" ---
                    p_val = str(r.get('Paiement', '')).strip().lower()
                    
                    # On définit très largement ce qui est PAYÉ
                    # Si ça contient "pay" ou "paid"
                    contient_pay = ("pay" in p_val) or ("paid" in p_val)
                    
                    # On définit ce qui ANNULE le paiement (le négatif)
                    # Si ça contient "un" (unpaid) ou "pas" (pas payé) ou "non"
                    est_negatif = ("un" in p_val) or ("pas" in p_val) or ("non" in p_val)
                    
                    # La règle finale :
                    is_paye = contient_pay and not est_negatif
                    
                    # --- CALCUL COULEUR ---
                    if this_date < aujourdhui:
                        # PASSÉ : Bleu si payé, Rouge si impayé
                        if is_paye:
                            current_c = "#3498db" # BLEU
                        else:
                            current_c = "#e74c3c" # ROUGE
                    elif "ok" in s_val:
                        current_c = "#2ecc71" # VERT
                    elif "attente" in s_val:
                        current_c = "#f1c40f" # JAUNE
                    else:
                        current_c = "transparent"
                        
             

                    # --- GESTION DES CONFLITS ---
                    n_j = int(r.get('NbreJours', 1))
                    for j in range(dv, dv + n_j):
                        if j in jours_occ:
                            old_c = jours_occ[j]["c"]
                            if "#e74c3c" in [current_c, old_c]: final_c = "#e74c3c"
                            elif "#2ecc71" in [current_c, old_c]: final_c = "#2ecc71"
                            else: final_c = current_c
                            jours_occ[j] = {"c": final_c}
                        else:
                            jours_occ[j] = {"c": current_c}
            except: 
                continue

        # 4. AFFICHAGE DU CALENDRIER
        h_cal = '<table style="width:100%; border-collapse: collapse; text-align: center;">'
        cal_mat = calendar.monthcalendar(sel_y, sel_m)
        for sem in cal_mat:
            h_cal += '<tr>'
            for jour in sem:
                if jour == 0:
                    h_cal += '<td style="height:45px; border:0.5px solid #eee;"></td>'
                else:
                    bg = jours_occ.get(jour, {}).get("c", "transparent")
                    txt_c = "white" if bg in ["#3498db", "#e74c3c", "#2ecc71"] else "black"
                    circle = f'<div style="background:{bg}; color:{txt_c}; border-radius:50%; width:30px; height:30px; line-height:30px; margin:auto; font-weight:bold; font-size:13px;">{jour}</div>'
                    h_cal += f'<td style="border:0.5px solid #eee; height:48px;">{circle if bg != "transparent" else jour}</td>'
            h_cal += '</tr>'
        h_cal += '</table>'
        st.markdown(h_cal, unsafe_allow_html=True)
        st.write("🔴 Impayé | 🔵 Payé | 🟢 OK | 🟡 Attente")
# --- NOUVEAU : LISTE DÉTAILLÉE DES RÉSERVATIONS DU MOIS ---
        st.markdown(f"### 📋 Détails des réservations - {m_noms[sel_m-1]} {sel_y}")
        
        # On filtre les données pour le mois et l'année sélectionnés
        reservations_mois = []
        for _, r in df_c.iterrows():
            try:
                d_str = str(r.get('DateNav', '')).strip()
                if '/' in d_str:
                    parts = d_str.split('/')
                    d_m, d_y = int(parts[1]), int(parts[2])
                    if d_y < 100: d_y += 2000
                    
                    if d_m == sel_m and d_y == sel_y:
                        # On ne prend pas les refusés ou archivés dans le planning
                        if str(r.get('Statut','')).lower() not in ["refusé", "archivé"]:
                            reservations_mois.append(r)
            except:
                continue

        if not reservations_mois:
            st.info("Aucune réservation pour ce mois.")
        else:
            # Création d'un petit tableau propre ou de fiches compactes
            for res in reservations_mois:
                # Logique de couleur pour le paiement dans la liste
                p_val = str(res.get('Paiement', '')).lower()
                is_p = ("pay" in p_val) and not any(x in p_val for x in ["non", "pas", "un"])
                p_txt = "✅ PAYÉ" if is_p else "⏳ À PAYER"
                p_color = "#27ae60" if is_p else "#e67e22"
                
                # Affichage d'une ligne stylisée
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; 
                            padding: 10px; border-bottom: 1px solid #eee; background: white; color: black;">
                    <div style="flex: 2;">
                        <b>{res.get('DateNav', '--')}</b> | {res.get('Prénom','')} {res.get('Nom','').upper()}
                        <br><small style="color: #666;">{res.get('Société','PARTICULIER')}</small>
                    </div>
                    <div style="flex: 1; text-align: center;">
                        ⛵ <b>{res.get('NbreJours', 1)} jrs</b>
                    </div>
                    <div style="flex: 1; text-align: right;">
                        <b style="font-size: 1.1rem;">{res.get('Prix', '0')} €</b><br>
                        <span style="color: {p_color}; font-size: 0.7rem; font-weight: bold;">{p_txt}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
# --- NOUVEAU : RÉCAPITULATIF DU MOIS SÉLECTIONNÉ ---
        st.divider()
        
        # Calcul des compteurs pour le mois affiché
        missions_mois = 0
        ca_encaisse = 0.0
        ca_attente = 0.0
        
        for _, r in df_c.iterrows():
            try:
                d_str = str(r.get('DateNav', '')).strip()
                if '/' in d_str:
                    parts = d_str.split('/')
                    if int(parts[1]) == sel_m and int(parts[2]) == sel_y:
                        missions_mois += 1
                        prix = float(str(r.get('Prix', '0')).replace('€','').strip() or 0)
                        
                        # Utilisation de notre nouvelle logique de paiement
                        p_val = str(r.get('Paiement', '')).lower()
                        if "pay" in p_val and "non" not in p_val and "un" not in p_val:
                            ca_encaisse += prix
                        else:
                            ca_attente += prix
            except:
                continue

        # Affichage en colonnes
        c1, c2, c3 = st.columns(3)
        c1.metric("Missions ce mois", f"{missions_mois}")
        c2.metric("Encaissé", f"{ca_encaisse:.2f} €", delta_color="normal")
        c3.metric("À percevoir", f"{ca_attente:.2f} €", delta="- " if ca_attente > 0 else None)

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
        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































