import requests, base64, json, time
import streamlit as st
import pandas as pd

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
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            if 'NbreJours' not in df.columns: df['NbreJours'] = "1"
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
for i, name in enumerate(["CONTACTS", "PLANNING", "STATS", "MAINT", "FACTURES", "NOTES"]):
    if m[i].button(name, key=f"nav_{name}", use_container_width=True, type="primary" if st.session_state.page == name else "secondary"):
        st.session_state.page = name; st.session_state.edit_idx = None; st.session_state.confirm_del = None; st.rerun()

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
        u_date = st.text_input("Date début", value=safe_get(r, 'DateNav'))
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
                notes = safe_get(r, 'Notes') or "."

                # --- BLOC HTML COMPACT (EVITE LE TEXTE BRUT) ---
                h = f'<div class="fiche-globale {cl_b}">'
                h += f'<span class="statut-badge" style="background:{c_p};">{p_val}</span>'
                h += f'<span class="statut-badge" style="background:{c_s};">{s_val}</span>'
                h += f'<div class="societe-style">{soc if soc else "CLIENT PARTICULIER"}</div>'
                h += f'<div class="prenom-style">{safe_get(r, "Prénom")} {safe_get(r, "Nom").upper()}</div>'
                h += f'{i_tel}{i_mail}'
                h += f'<p style="margin:8px 0;">📅 <b>{safe_get(r, "DateNav")}</b> ({jours} jrs) | 💰 <b>{safe_get(r, "Prix")} €</b></p>'
                h += f'<div class="notes-box">📝 {notes}</div>'
                h += f'<div class="container-boutons">'
                h += f'<a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>'
                h += f'<a href="https://wa.me/{tel.replace(" ","")}" class="btn-contact" style="background:#25D366;">WhatsApp</a>'
                h += f'<a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Mail</a>'
                h += f'</div></div>'
                
                st.markdown(h, unsafe_allow_html=True)
                
                if st.session_state.confirm_del == i:
                    if st.button("⚠️ CONFIRMER SUPPRESSION", key=f"conf_{i}", type="primary", use_container_width=True):
                        df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.session_state.confirm_del = None; st.rerun()
                    if st.button("Annuler", key=f"ann_{i}", use_container_width=True):
                        st.session_state.confirm_del = None; st.rerun()
                else:
                    col1, col2 = st.columns([1, 4])
                    if col1.button("✏️", key=f"ed_{i}"): st.session_state.edit_idx = i; st.rerun()
                    if col2.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True): st.session_state.confirm_del = i; st.rerun()

# --- À insérer dans la section PAGE PLANNING ---
elif st.session_state.page == "PLANNING":
    st.subheader("🗓️ Calendrier des Missions 2026")
    
    if not df.empty:
        # 1. Sélection du mois
        mois_liste = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                      "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        current_month_idx = 2  # Par défaut Mars (mois actuel en 2026)
        
        sel_mois = st.selectbox("Choisir le mois", mois_liste, index=current_month_idx)
        mois_num = mois_liste.index(sel_mois) + 1
        
        # 2. Préparation des données du calendrier
        # On crée un dictionnaire des jours occupés : {jour: statut}
        jours_occupes = {}
        
        for _, r in df.iterrows():
            try:
                date_str = safe_get(r, 'DateNav')
                # On attend le format JJ/MM/AAAA
                d, m, y = map(int, date_str.split('/'))
                
                if m == mois_num and y == 2026:
                    nb_j = int(safe_get(r, 'NbreJours') or 1)
                    statut = safe_get(r, 'Statut')
                    
                    # Remplir chaque jour de la mission
                    for j in range(d, d + nb_j):
                        # Priorité au statut "OK" sur "En attente" si chevauchement
                        if j not in jours_occupes or statut == "OK":
                            jours_occupes[j] = statut
            except:
                continue

        # 3. Affichage du Calendrier (Grille HTML)
        import calendar
        cal = calendar.monthcalendar(2026, mois_num)
        jours_semaine = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
        
        cols = st.columns(7)
        for i, jour_nom in enumerate(jours_semaine):
            cols[i].markdown(f"<center><b>{jour_nom}</b></center>", unsafe_allow_html=True)
            
        for semaine in cal:
            cols = st.columns(7)
            for i, jour in enumerate(semaine):
                if jour == 0:
                    cols[i].write("")
                else:
                    bg_color = "white"
                    text_color = "#333"
                    border = "1px solid #ddd"
                    
                    if jour in jours_occupes:
                        statut = jours_occupes[jour]
                        if statut == "OK":
                            bg_color = "#2ecc71" # Vert
                            text_color = "white"
                        elif statut == "En attente":
                            bg_color = "#f1c40f" # Jaune
                            text_color = "black"
                    
                    cols[i].markdown(f"""
                        <div style="background-color:{bg_color}; color:{text_color}; 
                        border:{border}; border-radius:5px; padding:10px; text-align:center; 
                        font-weight:bold; margin-bottom:5px;">
                        {jour}
                        </div>""", unsafe_allow_html=True)

        st.divider()
        
        # 4. Rappel Liste sous le calendrier
        st.subheader("📋 Détails du mois")
        df_mois = []
        for _, r in df.iterrows():
            try:
                _, m, y = map(int, safe_get(r, 'DateNav').split('/'))
                if m == mois_num and y == 2026:
                    df_mois.append(r)
            except: continue
            
        if df_mois:
            for r in df_mois:
                s = safe_get(r, 'Statut')
                color = "green" if s == "OK" else "orange"
                st.markdown(f"""
                **{safe_get(r, 'DateNav')}** ({safe_get(r, 'NbreJours')}j) : 
                {safe_get(r, 'Prénom')} {safe_get(r, 'Nom').upper()} 
                - <span style="color:{color}; font-weight:bold;">{s}</span>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucune mission prévue pour ce mois.")
    else:
        st.warning("Aucune donnée disponible. Créez un contact d'abord.")





































































































































































































































































































































































































































































