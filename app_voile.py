import streamlit as st
import pandas as pd
import json, base64, requests, calendar
import urllib.parse
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<div class="page-title">🔐 ACCÈS SÉCURISÉ</div>', unsafe_allow_html=True)
    password = st.text_input("Entrez le code d'accès :", type="password")
    if st.button("SE CONNECTER", use_container_width=True):
        if password == "SKIPPER2026": 
            st.session_state.authenticated = True
            st.rerun()
        else: st.error("Code incorrect ❌")
    st.stop()

# Initialisation des états
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "view_mode" not in st.session_state: st.session_state.view_mode = "FUTURES"
if "cible_annuelle" not in st.session_state: st.session_state.cible_annuelle = 15000.0
for k in ["edit_idx", "edit_s_idx", "edit_f_idx", "edit_n_idx"]:
    if k not in st.session_state: st.session_state[k] = None

st.markdown("""<style>
    .main-title { color: #1a2a6c; font-size: 1.6rem; font-weight: bold; text-align: center; margin-bottom: 5px; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 15px; }
    .client-card { background: white; padding: 15px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #ddd; position: relative; }
    .status-badge { position: absolute; top: 10px; right: 10px; padding: 5px 10px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; border: 1px solid #ccc; }
    .cal-table { width: 100%; border-collapse: collapse; table-layout: fixed; background: white; }
    .cal-table td { height: 60px; text-align: center; border: 1px solid #ddd; font-weight: bold; vertical-align: top; padding: 5px; }
    .day-ok { background-color: #2ecc71 !important; color: white !important; }
    .day-cmn { background-color: #3498db !important; color: white !important; }
    .btn-contact { display: inline-block; padding: 8px 12px; border-radius: 5px; text-decoration: none; color: white !important; font-weight: bold; margin-right: 5px; font-size: 0.8rem; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE DONNÉES ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        res = requests.get(f"https://api.github.com/repos/{repo}/contents/{file}", headers={"Authorization": f"token {token}"})
        if res.status_code == 200: 
            return pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
    except: pass
    return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4, force_ascii=False).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": f"Update {file}", "content": content, "sha": sha})
    st.cache_data.clear()

def to_f(v): 
    try: return float(str(v).replace("€","").replace(",",".").replace(" ",""))
    except: return 0.0

def fmt_p(v): return f"{to_f(v):,.2f} €".replace(",", " ").replace(".", ",")

def parse_d(d):
    try: return datetime.strptime(str(d).strip().replace("-","/"), '%d/%m/%Y')
    except: return datetime(2000, 1, 1)

# Chargement
df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","BUDGET"), ("📖 LOG","LOGBOOK"), ("📄 FACT","FACTURE"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
for i, (l, p) in enumerate(menu):
    if m_cols[i].button(l, key=f"btn_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.rerun()

# --- 4. PAGES ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    
    # --- BARRE DE RECHERCHE ---
    search_term = st.text_input("🔍 Rechercher par Nom ou Prénom", "").strip().lower()
    
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True, type="primary" if st.session_state.view_mode=="FUTURES" else "secondary"): st.session_state.view_mode="FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", use_container_width=True, type="primary" if st.session_state.view_mode=="PASSÉES" else "secondary"): st.session_state.view_mode="PASSÉES"; st.rerun()
    
    st.button("➕ NOUVELLE FICHE", on_click=lambda: st.session_state.update({"edit_idx":"NEW", "page":"FORM"}), use_container_width=True)
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        today = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Filtre Passées / Futures
        data = df[df['dt'] >= today] if st.session_state.view_mode=="FUTURES" else df[df['dt'] < today]
        
        # --- LOGIQUE DE RECHERCHE ---
        if search_term:
            data = data[
                (data['Nom'].str.lower().str.contains(search_term, na=False)) | 
                (data['Prénom'].str.lower().str.contains(search_term, na=False))
            ]
        
        if data.empty:
            st.info("Aucun résultat pour cette recherche.")
        else:
            for i, r in data.sort_values('dt', ascending=(st.session_state.view_mode=="FUTURES")).iterrows():
                soc = str(r.get('Société','')).upper()
                statut = str(r.get('Statut','🟡 Attente'))
                tel = str(r.get('Téléphone', r.get('Tel', ''))).strip()
                mail = str(r.get('Mail', '')).strip()
                tel_link = tel.replace(" ", "").replace(".", "").replace("-", "")
                if tel_link.startswith("0"): tel_link = "33" + tel_link[1:]
                badge_color = "#2ecc71" if "OK" in statut.upper() or "🟢" in statut else ("#e74c3c" if "🔴" in statut else "#f1c40f")

                st.markdown(f"""<div class="client-card" style="border-left: 10px solid {"#3498db" if soc=="CMN" else "#ccc"};">
                    <div class="status-badge" style="color:{badge_color}; border-color:{badge_color}; background:{badge_color}15;">{statut}</div>
                    <b style="font-size:1.1rem;">{r.get('Prénom','')} {r.get('Nom','').upper()}</b><br>
                    🏢 <b>{soc}</b> | 📅 {r.get('DateNav')} ({r.get('NbJours','1')}j)<br>
                    📞 {tel} | ✉️ {mail}<br><br>
                    <a href="tel:{tel_link}" class="btn-contact" style="background:#3498db;">📞 Appel</a>
                    <a href="https://wa.me/{tel_link}" target="_blank" class="btn-contact" style="background:#25d366;">💬 WhatsApp</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Mail</a>
                </div>""", unsafe_allow_html=True)
                ce, cd = st.columns([1, 4])
                if ce.button("✏️ Modifier", key=f"ed_l_{i}"): st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
                if cd.checkbox("🗑️", key=f"del_l_{i}"):
                    if st.button("Confirmer suppression", key=f"conf_l_{i}"): df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()

elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING & CROISIÈRES</div>', unsafe_allow_html=True)
    
    # 1. Barre de contrôle en haut
    c_date, c_check = st.columns([2, 1])
    p_y = c_date.selectbox("An", [2025, 2026, 2027], index=1)
    p_m = c_date.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    # La fameuse case à cocher
    opt_wa = c_check.checkbox("💬 Option Groupe", value=False)

    # ... (Code du calendrier inchangé ici) ...
    # [On saute la partie calcul 'occu' et l'affichage de la table pour aller aux détails]

    st.markdown("---")
    st.subheader(f"👥 Détails {calendar.month_name[p_m]}")
    
    if not df.empty and not df_mois.empty:
        groupes = df_mois.groupby('DateNav')
        
        for date_nav, gp in groupes:
            tels = []
            noms = []
            st.markdown(f"**📅 {date_nav}**")
            
            for _, r in gp.iterrows():
                n_c = f"{r.get('Prénom','')} {r.get('Nom','').upper()}"
                st.markdown(f"• {n_c} ({r.get('Société','')})")
                
                # On prépare les numéros au cas où
                t = str(r.get('Téléphone','')).strip().replace(" ","")
                if t: 
                    if t.startswith("0"): t = "33" + t[1:]
                    tels.append(t)
                    noms.append(n_c)

            # --- LA CONDITION DE VERROUILLAGE ---
            # Le bouton ne s'affiche QUE SI opt_wa est VRAI (coché)
            if opt_wa and len(gp) > 1 and tels:
                msg = urllib.parse.quote(f"Bonjour à tous ({', '.join(noms)}), navigation du {date_nav}...")
                url_wa = f"https://wa.me/{tels[0]}?text={msg}"
                st.markdown(f"""
                    <a href="{url_wa}" target="_blank" style="background-color:#25d366; color:white; padding:8px 12px; display:inline-block; text-decoration:none; border-radius:15px; font-size:0.8rem; font-weight:bold; margin-top:5px;">
                        💬 CRÉER GROUPE WHATSAPP
                    </a>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    s_y = st.selectbox("Année", [2025, 2026, 2027], index=1)
    obj = st.number_input("Cible annuelle (€)", value=float(st.session_state.cible_annuelle), step=1000.0)
    st.session_state.cible_annuelle = obj
    if not df.empty: df['dt'] = df['DateNav'].apply(parse_d)
    if not df_f.empty: df_f['dt'] = df_f['Date'].apply(parse_d)
    res, t_rev, t_fra, t_net, t_pre = [], 0, 0, 0, 0
    for i in range(1, 13):
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f)) if not df.empty else 0
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f)) if not df_f.empty else 0
        prev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & (df['Statut'].str.contains("OK|🟢|🟡", na=False))]['PrixJour'].apply(to_f)) if not df.empty else 0
        t_rev += rev; t_fra += fr; t_net += (rev-fr); t_pre += prev
        res.append({"M": i, "Rev": int(rev), "Frais": int(fr), "Net": int(rev-fr), "Prév": int(prev)})
    st.write(f"📈 **Réalisé (OK) : {int(t_rev)} / {int(obj)}**")
    st.progress(min(t_rev/obj, 1.0) if obj > 0 else 0.0)
    st.table(pd.DataFrame(res).set_index('M'))
    st.markdown(f'<div style="background:#1a2a6c;color:white;padding:15px;border-radius:10px;text-align:center;font-weight:bold;">TOTAL NET : {fmt_p(t_net)}</div>', unsafe_allow_html=True)

elif st.session_state.page == "FRAIS":
    st.markdown('<div class="page-title">💰 GESTION DES FRAIS</div>', unsafe_allow_html=True)
    c_df = df_f
    c_idx = st.session_state.edit_f_idx
    c_file = "frais.json"
    
    if c_idx is not None:
        init = c_df.loc[c_idx].to_dict() if (c_idx != "NEW" and not c_df.empty) else {}
        with st.form("edit_frais"):
            st.subheader("📝 " + ("MODIFIER LE FRAIS" if c_idx != "NEW" else "NOUVEAU FRAIS"))
            d_f = st.text_input("Date", init.get("Date", datetime.now().strftime("%d/%m/%Y")))
            m_f = st.text_input("Montant (€)", str(init.get("Montant", "0")))
            n_f = st.text_area("Libellé / Note", init.get("Note", ""))
            
            if st.form_submit_button("✅ SAUVEGARDER"):
                row = {"Date": d_f, "Montant": m_f, "Note": n_f}
                if c_idx == "NEW": 
                    c_df = pd.concat([c_df, pd.DataFrame([row])], ignore_index=True)
                else: 
                    for k,v in row.items(): c_df.at[c_idx, k] = v
                sauvegarder_data(c_df, c_file)
                st.session_state.edit_f_idx = None
                st.rerun()
            
            if st.form_submit_button("❌ ANNULER"):
                st.session_state.edit_f_idx = None
                st.rerun()
    else:
        st.button("➕ AJOUTER UN FRAIS", on_click=lambda: st.session_state.update({"edit_f_idx":"NEW"}), use_container_width=True)
        
        if not c_df.empty:
            # Affichage des frais avec détails
            for i, r in c_df.iterrows():
                st.markdown(f"""
                <div class="client-card" style="border-left: 5px solid #e74c3c; background: white;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="font-size:1.1rem;">{r.get('Date')}</b>
                        <span style="color:#e74c3c; font-weight:bold; font-size:1.2rem;">{r.get('Montant')} €</span>
                    </div>
                    <div style="color:#555; margin-top:5px; font-style:italic;">
                        📌 {r.get('Note', 'Sans libellé')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_f_{i}"): 
                    st.session_state.edit_f_idx = i
                    st.rerun()
                if c2.button("🗑️ Supprimer", key=f"del_f_{i}"): 
                    c_df = c_df.drop(i)
                    sauvegarder_data(c_df, c_file)
                    st.rerun()
        else:
            st.info("Aucun frais enregistré.")
                
elif st.session_state.page == "LOGBOOK":
    st.markdown('<div class="page-title">📖 JOURNAL DE BORD</div>', unsafe_allow_html=True)
    
    df_log = charger_data("logbook.json")
    
    # Gestion de l'index d'édition pour le Logbook
    if "edit_log_idx" not in st.session_state: st.session_state.edit_log_idx = None

    # --- FORMULAIRE D'ÉDITION (Affiché si on clique sur Modifier ou Nouvelle Étape) ---
    if st.session_state.edit_log_idx is not None:
        idx = st.session_state.edit_log_idx
        # Pré-remplissage si modification
        init = df_log.loc[idx].to_dict() if (idx != "NEW" and not df_log.empty) else {}
        
        with st.form("f_log_edit"):
            st.subheader("📝 " + ("MODIFIER L'ÉTAPE" if idx != "NEW" else "NOUVELLE ÉTAPE"))
            c1, c2 = st.columns(2)
            d_lieu = c1.text_input("Port (Départ)", init.get("Depart", ""))
            d_met = c2.selectbox("Météo", ["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"], 
                                 index=["☀️ Beau", "☁️ Couvert", "🌧️ Pluie", "🌬️ Vent fort"].index(init.get("Meteo", "☀️ Beau")))
            
            c3, c4 = st.columns(2)
            d_h = c3.number_input("Heures Moteur (Départ)", value=float(init.get("H_Dep", 0.0)), step=0.1)
            d_mi = c4.number_input("Loch / Milles (Départ)", value=float(init.get("M_Dep", 0.0)), step=0.1)
            
            obs = st.text_area("Observations", init.get("Observations", ""), height=80)
            
            st.markdown("---")
            c5, c6 = st.columns(2)
            a_lieu = c5.text_input("Port (Arrivée)", init.get("Arrivee", ""))
            a_h = st.number_input("Heures Moteur (Arrivée)", value=float(init.get("H_Arr", 0.0)), step=0.1)
            a_mi = st.number_input("Loch / Milles (Arrivée)", value=float(init.get("M_Arr", 0.0)), step=0.1)

            col_b1, col_b2 = st.columns(2)
            if col_b1.form_submit_button("✅ ENREGISTRER"):
                bilan_milles = round(a_mi - d_mi, 1)
                bilan_heures = round(a_h - d_h, 1)
                nueva_row = {
                    "Date": init.get("Date", datetime.now().strftime("%d/%m/%Y")),
                    "Depart": d_lieu, "Arrivee": a_lieu,
                    "H_Dep": d_h, "H_Arr": a_h, "H_Bilan": bilan_heures,
                    "M_Dep": d_mi, "M_Arr": a_mi, "M_Bilan": bilan_milles,
                    "Meteo": d_met, "Observations": obs
                }
                
                if idx == "NEW":
                    df_log = pd.concat([df_log, pd.DataFrame([nueva_row])], ignore_index=True)
                else:
                    for k, v in nueva_row.items(): df_log.at[idx, k] = v
                
                sauvegarder_data(df_log, "logbook.json")
                st.session_state.edit_log_idx = None
                st.rerun()
            
            if col_b2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_log_idx = None
                st.rerun()

    else:
        # --- AFFICHAGE DE L'HISTORIQUE ---
        st.button("➕ NOUVELLE ÉTAPE", on_click=lambda: st.session_state.update({"edit_log_idx":"NEW"}), use_container_width=True)
        
        if not df_log.empty:
            for i in reversed(df_log.index):
                r = df_log.loc[i]
                b_m = r.get('M_Bilan', 0)
                b_h = r.get('H_Bilan', 0)
                
                st.markdown(f"""
                <div class="client-card" style="border-left: 8px solid #1a2a6c; background:#f8f9fa; margin-bottom:5px;">
                    <b>📅 {r.get('Date')}</b> | {r.get('Depart')} ➡️ {r.get('Arrivee')} <br>
                    <div style="background:#eef2f3; padding:5px; border-radius:5px; margin:5px 0; font-weight:bold; color:#1a2a6c; font-size:0.9rem;">
                        🚢 {b_m} mn | ⚙️ {b_h} h moteur | {r.get('Meteo')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"edit_log_btn_{i}"):
                    st.session_state.edit_log_idx = i
                    st.rerun()
                if c2.button("🗑️ Supprimer ", key=f"del_log_{i}"):
                    df_log = df_log.drop(i)
                    sauvegarder_data(df_log, "logbook.json")
                    st.rerun()
        else:
            st.info("Aucun logbook enregistré.")
            
elif st.session_state.page == "FACTURE":
    st.markdown('<div class="page-title">📄 FACTURATION & ARCHIVES</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    f_y = c1.selectbox("Année", [2025, 2026, 2027], index=1)
    f_m = c2.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    
    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        mask_base = (df['dt'].dt.year == f_y) & (df['dt'].dt.month == f_m) & (df['Société'].str.upper() == "CMN")
        df_mois = df[mask_base].copy()
        
        # --- 1. LES SORTIES À FACTURER (Statut OK / 🟢) ---
        df_a_envoyer = df_mois[df_mois['Statut'].str.contains("OK|🟢", na=False)]
        
        # --- 2. LES ARCHIVES ---
        df_attente = df_mois[df_mois['Statut'].str.contains("Attente|🟡|Facturé", na=False)]
        df_paye = df_mois[df_mois['Statut'].str.contains("Payé|✅|Paye", na=False, case=False)]

        st.subheader("💰 À FACTURER CE MOIS")
        if not df_a_envoyer.empty:
            total = sum(df_a_envoyer['PrixJour'].apply(to_f))
            
            # Construction du corps du mail
            corps = f"Bonjour Jean-Michel,\n\nCi-après le détail de la facturation des sorties CMN du mois de {calendar.month_name[f_m]} {f_y} :\n\n"
            for _, r in df_a_envoyer.sort_values('dt').iterrows():
                corps += f"- Le {r['DateNav']} ({r.get('Nom','')}) : {fmt_p(r['PrixJour'])}\n"
            corps += f"\nTOTAL À RÉGLER : {fmt_p(total)}\n\nBonne réception,\nEric CLAVREUL"
            
            st.info(f"Montant détecté : {fmt_p(total)}")
            txt = st.text_area("Aperçu du message", corps, height=200)
            
            dest, cc, sujet = "tresorier@cmn-asso.fr", "eric.clavreul@gmail.com", f"Facturation Skipper - {calendar.month_name[f_m]} {f_y}"
            
            # --- BOUTON IPHONE (Mail natif) ---
            params = urllib.parse.urlencode({'cc': cc, 'subject': sujet, 'body': txt})
            st.markdown(f'''
                <a href="mailto:{dest}?{params}" style="background-color:#1a2a6c; color:white; padding:15px; display:block; text-align:center; text-decoration:none; border-radius:10px; font-weight:bold; margin-bottom:10px;">
                    📱 ENVOYER VIA IPHONE (Mail)
                </a>
            ''', unsafe_allow_html=True)
            
            # --- BOUTON PC (Gmail) ---
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={dest}&cc={cc}&sujet={urllib.parse.quote(sujet)}&body={urllib.parse.quote(txt)}"
            st.markdown(f'''
                <a href="{gmail_url}" target="_blank" style="background-color:#db4437; color:white; padding:15px; display:block; text-align:center; text-decoration:none; border-radius:10px; font-weight:bold;">
                    💻 ENVOYER VIA GMAIL (PC)
                </a>
            ''', unsafe_allow_html=True)
        else:
            st.info("Aucune nouvelle sortie '🟢 OK' à facturer pour ce mois.")

        # --- SECTION ARCHIVES ---
        st.markdown("---")
        st.subheader("📂 ÉTAT DES PAIEMENTS")
        c_att, c_ok = st.columns(2)
        
        with c_att:
            st.markdown("<b style='color:#f39c12;'>⏳ EN ATTENTE / ENVOYÉ</b>", unsafe_allow_html=True)
            if not df_attente.empty:
                for _, r in df_attente.sort_values('dt', ascending=False).iterrows():
                    st.caption(f"• {r['DateNav']} : {r.get('Nom','')} ({fmt_p(r['PrixJour'])})")
            else: st.write("Rien en attente")

        with c_ok:
            st.markdown("<b style='color:#27ae60;'>✅ PAYÉ / ARCHIVÉ</b>", unsafe_allow_html=True)
            if not df_paye.empty:
                for _, r in df_paye.sort_values('dt', ascending=False).iterrows():
                    st.caption(f"• {r['DateNav']} : {r.get('Nom','')} ({fmt_p(r['PrixJour'])})")
            else: st.write("Aucun archivé")

elif st.session_state.page == "NOTES":
    st.markdown('<div class="page-title">📝 MES NOTES & MÉMOS</div>', unsafe_allow_html=True)
    
    # 1. Chargement des données des notes
    df_n = charger_data("notes.json")
    
    # Gestion de l'index d'édition pour les notes
    if "edit_n_idx" not in st.session_state: st.session_state.edit_n_idx = None

    # --- FORMULAIRE D'ÉDITION ---
    if st.session_state.edit_n_idx is not None:
        idx = st.session_state.edit_n_idx
        init = df_n.loc[idx].to_dict() if (idx != "NEW" and not df_n.empty) else {}
        
        with st.form("f_note_edit"):
            st.subheader("📝 " + ("MODIFIER LA NOTE" if idx != "NEW" else "NOUVELLE NOTE"))
            titre_n = st.text_input("Titre", init.get("Titre", ""))
            contenu_n = st.text_area("Contenu", init.get("Contenu", ""), height=200)
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ ENREGISTRER"):
                row = {
                    "Titre": titre_n, 
                    "Contenu": contenu_n, 
                    "Date": datetime.now().strftime("%d/%m/%Y")
                }
                if idx == "NEW":
                    df_n = pd.concat([df_n, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k, v in row.items(): df_n.at[idx, k] = v
                
                sauvegarder_data(df_n, "notes.json")
                st.session_state.edit_n_idx = None
                st.rerun()
            
            if c2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_n_idx = None
                st.rerun()
    else:
        # --- AFFICHAGE DES NOTES ---
        st.button("➕ AJOUTER UNE NOTE", on_click=lambda: st.session_state.update({"edit_n_idx":"NEW"}), use_container_width=True)
        
        if not df_n.empty:
            # On affiche les notes (de la plus récente à la plus ancienne)
            for i in reversed(df_n.index):
                r = df_n.loc[i]
                st.markdown(f"""
                <div class="client-card" style="border-left: 5px solid #f39c12; background: white;">
                    <div style="display:flex; justify-content:space-between; color:#7f8c8d; font-size:0.8rem; margin-bottom:5px;">
                        <span>📅 {r.get('Date', '')}</span>
                    </div>
                    <b style="font-size:1.1rem; color:#2c3e50;">{r.get('Titre', 'Sans titre')}</b><br>
                    <div style="white-space: pre-wrap; color:#34495e; margin-top:10px; font-size:0.95rem;">{r.get('Contenu', '')}</div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_n_{i}"): 
                    st.session_state.edit_n_idx = i
                    st.rerun()
                if c2.button("🗑️ Supprimer la note", key=f"del_n_{i}"): 
                    df_n = df_n.drop(i)
                    sauvegarder_data(df_n, "notes.json")
                    st.rerun()
        else:
            st.info("Aucune note enregistrée. Idéal pour noter les codes de pontons, rappels techniques, etc.")

elif st.session_state.page == "SECU":
    st.markdown('<div class="page-title">🛡️ SÉCURITÉ & ARMEMENT</div>', unsafe_allow_html=True)
    
    # 1. Chargement des données spécifiques à la sécurité
    df_s = charger_data("secu.json")
    
    # Gestion de l'index d'édition
    if "edit_s_idx" not in st.session_state: st.session_state.edit_s_idx = None

    # --- FORMULAIRE D'AJOUT / MODIF ---
    if st.session_state.edit_s_idx is not None:
        idx = st.session_state.edit_s_idx
        init = df_s.loc[idx].to_dict() if (idx != "NEW" and not df_s.empty) else {}
        
        with st.form("f_secu_edit"):
            st.subheader("🚩 " + ("MODIFIER LE POINT" if idx != "NEW" else "NOUVEAU POINT DE CONTRÔLE"))
            item = st.text_input("Matériel ou Point de contrôle", init.get("Item", ""))
            obs_s = st.text_area("État / Emplacement / Date limite", init.get("Note", ""))
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ ENREGISTRER"):
                row = {"Item": item, "Note": obs_s}
                if idx == "NEW":
                    df_s = pd.concat([df_s, pd.DataFrame([row])], ignore_index=True)
                else:
                    for k, v in row.items(): df_s.at[idx, k] = v
                sauvegarder_data(df_s, "secu.json")
                st.session_state.edit_s_idx = None
                st.rerun()
            
            if c2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_s_idx = None
                st.rerun()
    else:
        # --- AFFICHAGE DE LA LISTE DE SÉCURITÉ ---
        st.button("➕ AJOUTER UN ÉLÉMENT", on_click=lambda: st.session_state.update({"edit_s_idx":"NEW"}), use_container_width=True)
        
        if not df_s.empty:
            for i, r in df_s.iterrows():
                st.markdown(f"""
                <div class="client-card" style="border-left: 5px solid #27ae60; background: white;">
                    <b style="font-size:1.1rem; color:#2c3e50;">⚓ {r.get('Item')}</b><br>
                    <span style="color:#7f8c8d; font-size:0.9rem;">{r.get('Note', '')}</span>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                if c1.button("✏️", key=f"ed_s_{i}"): 
                    st.session_state.edit_s_idx = i
                    st.rerun()
                if c2.button("🗑️ Supprimer", key=f"del_s_{i}"): 
                    df_s = df_s.drop(i)
                    sauvegarder_data(df_s, "secu.json")
                    st.rerun()
        else:
            st.info("Aucun élément de sécurité enregistré. Commencez par en ajouter un (ex: Gilets, Fusées, Radeau...).")

elif st.session_state.page == "FORM":
    st.markdown('<div class="page-title">📝 FICHE NAVIGATION</div>', unsafe_allow_html=True)
    idx = st.session_state.edit_idx
    init = df.loc[idx].to_dict() if (idx != "NEW" and not df.empty) else {}
    
    with st.form("f_form"):
        st_v = st.selectbox("Statut", ["🟢 OK", "🟡 Attente", "🔴 Annulé"], index=1)
        c1, c2 = st.columns(2)
        p, n = c1.text_input("Prénom", init.get("Prénom","")), c2.text_input("Nom", init.get("Nom",""))
        s = st.text_input("Société", init.get("Société",""))
        c3, c4 = st.columns(2)
        d, j = c3.text_input("Date (JJ/MM/AAAA)", init.get("DateNav","")), c4.text_input("Jours", str(init.get("NbJours","1")))
        t = st.text_input("Tél", init.get("Téléphone", init.get("Tel", "")))
        ml = st.text_input("Mail", init.get("Mail", ""))
        pr = st.text_input("Prix", str(init.get("PrixJour","0")))
        
        if st.form_submit_button("SAUVEGARDER"):
            row = {"Prénom":p, "Nom":n, "Société":s, "Téléphone":t, "Mail":ml, "DateNav":d, "NbJours":j, "PrixJour":pr, "Statut":st_v}
            if idx=="NEW": 
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            else: 
                for k,v in row.items(): df.at[idx,k]=v
            sauvegarder_data(df, "contacts.json")
            st.session_state.page="LISTE"
            st.rerun()
            
    if st.button("Annuler"):
        st.session_state.page = "LISTE"
        st.rerun()






















































































































































































































































































































