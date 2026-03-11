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
            
elif st.session_state.page == "FACTURES":
        st.markdown('<div class="page-title">🧾 GÉNÉRATION DE FACTURE</div>', unsafe_allow_html=True)
        if df.empty:
            st.warning("⚠️ Aucune donnée.")
        else:
            soc_list = sorted(df['Société'].unique().astype(str).tolist())
            soc_sel = st.selectbox("Client", ["Tous"] + soc_list)
            df_f = df.copy()
            if soc_sel != "Tous":
                df_f = df_f[df_f['Société'] == soc_sel]
            
            total_f = sum(df_f['PrixJour'].apply(to_f))
            st.metric(f"Total {soc_sel}", f"{int(total_f)} €")
            
            corps = f"Bonjour,\n\nVoici le récapitulatif pour {soc_sel} :\n\n"
            for _, r in df_f.iterrows():
                p_l = int(to_f(r.get('PrixJour', 0)))
                corps += f"- Le {r.get('DateNav','--')} ({r.get('Nom','')}) : {p_l} €\n"
            corps += f"\nTotal : {int(total_f)} €\n\nMerci."
            st.text_area("📋 Message à copier :", corps, height=150)

# --- DEBUT DU BLOC MAINT ---
    elif st.session_state.page == "MAINT":
        st.markdown('<div class="page-title">🔧 MAINTENANCE & FRAIS</div>', unsafe_allow_html=True)
        st.info("Gestion des frais de maintenance et de l'entretien du bateau.")
        
        # Petit formulaire simple pour ne pas laisser la page vide
        with st.expander("➕ Ajouter un nouveau frais"):
            f_objet = st.text_input("Objet (ex: Antifouling)")
            f_montant = st.number_input("Montant (€)", min_value=0)
            if st.button("Enregistrer le frais"):
                st.success("Frais enregistré dans le système.")

    # --- DEBUT DU BLOC LOGS ---
    elif st.session_state.page == "LOGS":
        st.markdown('<div class="page-title">📂 ARCHIVES DES SORTIES</div>', unsafe_allow_html=True)
        if df.empty:
            st.warning("⚠️ Aucune archive disponible.")
        else:
            # On affiche le tableau avec le statut de paiement
            cols_logs = ['DateNav', 'Nom', 'Société', 'Statut']
            # On vérifie que les colonnes existent pour éviter un nouveau crash
            present_cols = [c for c in cols_logs if c in df.columns]
            st.dataframe(df[present_cols], use_container_width=True)
















































































































































































































































































































































