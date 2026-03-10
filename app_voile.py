import requests
import base64
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import calendar
import urllib.parse

# --- 🛠️ FONCTIONS DE SÉCURITÉ (À METTRE EN HAUT) ---

def to_f(val):
    """ Convertit n'importe quel texte en nombre décimal propre """
    try: 
        if pd.isna(val) or val == "": return 0.0
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except: return 0.0

def parse_d(d_str):
    """ Convertit une date texte (JJ/MM/AAAA) en objet Date utilisable par Python """
    try: return datetime.strptime(str(d_str), "%d/%m/%Y")
    except: return datetime(2000, 1, 1)

def fmt_p(v):
    """ Formate un nombre en euros (ex: 1250,50 €) """
    return f"{v:,.2f} €".replace(",", " ").replace(".", ",")

# --- FIN DU BLOC DE SÉCURITÉ ---

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

# --- 2. FONCTIONS DE DONNÉES (VERSION NETTOYÉE) ---
@st.cache_data(ttl=1)
def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        if res.status_code == 200:
            content = res.json()['content']
            decoded = base64.b64decode(content).decode('utf-8')
            return pd.DataFrame(json.loads(decoded))
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erreur technique sur {file} : {e}")
        return pd.DataFrame()

def sauvegarder_data(df, file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"})
        sha = res.json().get('sha') if res.status_code == 200 else None
        
        # Encodage sécurisé en JSON UTF-8
        json_data = df.to_json(orient="records", indent=4, force_ascii=False)
        content = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
        
        requests.put(url, headers={"Authorization": f"token {token}"}, 
                     json={"message": f"Update {file}", "content": content, "sha": sha})
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erreur de sauvegarde : {e}")


# Chargement
df = charger_data("contacts.json")
df_f = charger_data("frais.json")
df_n = charger_data("notes.json")
df_s = charger_data("secu.json")

# --- 3. MENU ---
st.markdown('<div class="main-title">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m_cols = st.columns(8)
menu = [("📋 LISTE","LISTE"), ("🗓️ PLAN","PLANNING"), ("💰 STATS","STATS"), ("📖 LOG","LOGBOOK"), ("📄 FACT","FACTURE"), ("🛟 SÉCU","SECU"), ("🔧 MAINT","FRAIS"), ("📝 NOTES","NOTES")]
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
    
    # 1. Barre de contrôle (Mois / Année / Option)
    c_date, c_check = st.columns([2, 1])
    p_y = c_date.selectbox("An", [2025, 2026, 2027], index=1)
    p_m = c_date.selectbox("Mois", range(1, 13), index=datetime.now().month-1, format_func=lambda x: calendar.month_name[x])
    opt_wa = c_check.checkbox("💬 Option Groupe", value=False)

    occu = {}
    df_mois = pd.DataFrame() # Initialisation pour éviter l'erreur

    if not df.empty:
        # On prépare les dates
        df['dt'] = df['DateNav'].apply(parse_d)
        # On crée la variable df_mois pour le mois sélectionné
        df_mois = df[(df['dt'].dt.year == p_y) & (df['dt'].dt.month == p_m)].sort_values('dt')
        
        # Remplissage du calendrier visuel
        for _, r in df.iterrows():
            statut_str = str(r.get('Statut','')).upper()
            if "🔴" not in statut_str and "ANNULÉ" not in statut_str:
                d_s, nb_j = r['dt'], int(to_f(r.get('NbJours', 1)))
                for j in range(nb_j):
                    curr = d_s + timedelta(days=j)
                    if curr.year == p_y and curr.month == p_m:
                        soc = str(r.get('Société','')).upper()
                        occu[curr.day] = "day-cmn" if soc == "CMN" else "day-ok"

    # --- AFFICHAGE DU CALENDRIER ---
    cal = calendar.monthcalendar(p_y, p_m)
    h = '<table class="cal-table"><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr>'
    for wk in cal:
        h += '<tr>'
        for d in wk:
            style = f'class="{occu[d]}"' if d in occu else ''
            h += f'<td {style}>{d if d != 0 else ""}</td>'
        h += '</tr>'
    st.markdown(h + '</table>', unsafe_allow_html=True)

    # --- DÉTAILS ET BOUTONS ---
    st.markdown("---")
    st.subheader(f"👥 Détails {calendar.month_name[p_m]}")
    
    if not df_mois.empty:
        groupes = df_mois.groupby('DateNav')
        
        for date_nav, gp in groupes:
            tels, noms = [], []
            st.markdown(f"**📅 {date_nav}**")
            
            for _, r in gp.iterrows():
                n_c = f"{r.get('Prénom','')} {r.get('Nom','').upper()}"
                st.markdown(f"• {n_c} ({r.get('Société','')})")
                
                # Récupération propre du téléphone
                t = str(r.get('Téléphone','')).strip().replace(" ","").replace(".","")
                if t and t != "nan": 
                    if t.startswith("0"): t = "33" + t[1:]
                    tels.append(t)
                    noms.append(n_c)

            # --- LE VERROU : Affichage conditionnel du bouton ---
            if opt_wa and len(gp) > 1 and tels:
                msg = urllib.parse.quote(f"Bonjour à tous ({', '.join(noms)}), navigation du {date_nav}...")
                url_wa = f"https://wa.me/{tels[0]}?text={msg}"
                st.markdown(f"""
                    <a href="{url_wa}" target="_blank" style="background-color:#25d366; color:white; padding:8px 12px; display:inline-block; text-decoration:none; border-radius:15px; font-size:0.8rem; font-weight:bold; margin-top:5px;">
                        💬 CRÉER GROUPE WHATSAPP
                    </a>
                """, unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    else:
        st.info("Aucune navigation ce mois-ci.")
        
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 TABLEAU DE BORD SÉCURISÉ</div>', unsafe_allow_html=True)
    
    if df.empty:
        st.warning("⚠️ Aucune donnée trouvée.")
    else:
        # 1. Préparation & Filtre Année
        df['dt'] = df['DateNav'].apply(parse_d)
        an_sel = st.selectbox("Choisir l'année", [2026, 2027, 2028], index=0)
        df_an = df[df['dt'].dt.year == an_sel].copy()
        
        # 2. Logique de tri ultra-précise
        def classifier_ligne(r):
            statut = str(r.get('Statut','')).lower()
            paye_col = str(r.get('Paye','')).lower()
            combinaison = statut + " " + paye_col
            
            # A. On élimine les annulations direct
            if any(m in combinaison for m in ["annulé", "annule", "🔴"]):
                return "IGNORE"
            
            # B. On cherche si c'est payé (mots clés positifs)
            est_regle = any(m in combinaison for m in ["payé", "paye", "ok", "✅", "🟢"])
            
            if est_regle:
                return "ENCAISSE"
            else:
                return "PREVISIONNEL"

        # Application de la logique
        df_an['Type'] = df_an.apply(classifier_ligne, axis=1)
        df_an['Mnt'] = df_an['PrixJour'].apply(to_f)
        df_an['Mois_Num'] = df_an['dt'].dt.month

        # 3. Chargement des frais
        df_f = charger_data("frais.json")
        if not df_f.empty:
            df_f['dt_f'] = df_f['Date'].apply(parse_d)
            df_f_an = df_f[df_f['dt_f'].dt.year == an_sel].copy()
            df_f_an['Mnt_F'] = df_f_an['Montant'].apply(to_f)
            df_f_an['Mois_F'] = df_f_an['dt_f'].dt.month
        else:
            df_f_an = pd.DataFrame()

        # 4. Construction du tableau compact
        recap = []
        for m in range(1, 13):
            d_m = df_an[df_an['Mois_Num'] == m]
            
            val_enc = int(d_m[d_m['Type'] == "ENCAISSE"]['Mnt'].sum())
            val_prev = int(d_m[d_m['Type'] == "PREVISIONNEL"]['Mnt'].sum())
            
            # Calcul des frais pour ce mois
            f_m = 0
            if not df_f_an.empty:
                f_m = int(df_f_an[df_f_an['Mois_F'] == m]['Mnt_F'].sum())
            
            if (val_enc + val_prev + f_m) > 0:
                recap.append({
                    "M": m,
                    "Encaissé": val_enc,
                    "Prév.": val_prev,
                    "Frais": f_m,
                    "Net": val_enc - f_m
                })

        if recap:
            st.table(pd.DataFrame(recap))
            
            # Totaux
            t_enc = sum(i['Encaissé'] for i in recap)
            t_prev = sum(i['Prév.'] for i in recap)
            t_frais = sum(i['Frais'] for i in recap)
            
            st.success(f"💰 **Encaissé Réel :** {t_enc} | ⏳ **Total en attente :** {t_prev}")
            st.error(f"🔧 **Total Frais :** {t_frais} | ⚓ **Bénéfice Net :** {t_enc - t_frais}")
        else:
            st.info(f"Aucune activité enregistrée pour {an_sel}")
        
elif st.session_state.page == "FACTURE":
    st.markdown('<div class="page-title">📄 FACTURATION & ARCHIVES</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    f_y = c1.selectbox("Année", [2025, 2026, 2027,2028], index=1)
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
            # --- LA CORRECTION ---
       for i, r in df_fact.iterrows():
       # On ajoute to_f() ici pour "nettoyer" le prix avant l'affichage
         prix_nettoye = to_f(r.get('PrixJour', 0))
         corps += f"- Le {r['DateNav']} ({r.get('Nom','')}) : {fmt_p(prix_nettoye)}\n"
            # Construction du corps du mail
            corps = f"Bonjour Jean-Michel,\n\nCi-après le détail de la facturation des sorties CMN du mois de {calendar.month_name[f_m]} {f_y} :\n\n"
            
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








































































































































































































































































































































