import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Skipper", layout="wide")

# Style CSS : Orange si vide, Blanc si rempli + Design des cartes de la liste
st.markdown("""
    <style>
    /* Champs de saisie */
    div[data-baseweb="input"] input:placeholder-shown { background-color: #fff3e0 !important; } 
    div[data-baseweb="textarea"] textarea:placeholder-shown { background-color: #fff3e0 !important; }
    
    /* Cartes de la liste */
    .client-card {
        background-color: white; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        border-left: 10px solid #ccc;
    }
    .status-ok { border-left-color: #4caf50 !important; }
    .status-attente { border-left-color: #ffeb3b !important; }
    .status-non { border-left-color: #f44336 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
def charger_data(nom_fichier, colonnes):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        content = res.json()
        decoded = base64.b64decode(content['content']).decode('utf-8')
        if decoded.strip():
            df_load = pd.DataFrame(json.loads(decoded))
            for col in colonnes:
                if col not in df_load.columns: df_load[col] = ""
            return df_load
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    df_save = df.copy()
    for c in ['temp_date_obj', 'prix_num']:
        if c in df_save.columns: df_save = df_save.drop(columns=[c])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta: Mise à jour", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "cal_date_sel" not in st.session_state: st.session_state.cal_date_sel = None

# --- AUTHENTIFICATION ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols)
    
    def clean_prix(val):
        if pd.isna(val) or val == "": return 0.0
        s = str(val).replace('€', '').replace(' ', '').replace(',', '.').strip()
        try: return float(s)
        except: return 0.0

    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
    df['prix_num'] = df['PrixJour'].apply(clean_prix)

    # --- BARRE DE NAVIGATION ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("🗓️ PLANNING", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE LISTE (AVEC ONGLETS PASSÉ/FUTUR) ---
    if st.session_state.page == "LISTE":
        c_search, c_filter = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher un nom...")
        with c_filter: f_statut = st.multiselect("Filtrer Statut :", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])

        # Séparation des données
        aujourdhui = pd.Timestamp(datetime.now().date())
        
        tab_futur, tab_passe = st.tabs(["🚀 PROCHAINES SORTIES", "📂 ARCHIVES (PASSÉ)"])

        with tab_futur:
            # Tri : Plus proche en premier
            futur_df = df[df['temp_date_obj'] >= aujourdhui].copy().sort_values('temp_date_obj', ascending=True)
            if search: futur_df = futur_df[futur_df['Nom'].str.contains(search, case=False) | futur_df['Prénom'].str.contains(search, case=False)]
            futur_df = futur_df[futur_df['Statut'].isin(f_statut)]
            
            if futur_df.empty:
                st.info("Aucune navigation prévue.")
            for idx, row in futur_df.iterrows():
                stat = row['Statut'] if row['Statut'] else "🟡 Attente"
                status_class = "status-ok" if "🟢" in stat else "status-attente" if "🟡" in stat else "status-non"
                st.markdown(f'<div class="client-card {status_class}"><span style="color:#666; font-size:0.9em;">📅 {row["DateNav"]}</span><br><b style="color:black; font-size:1.2em;">{row["Nom"]} {row["Prénom"]}</b><span style="float:right; font-weight:bold;">{stat}</span></div>', unsafe_allow_html=True)
                if st.button(f"Modifier {row['Nom']}", key=f"fut_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab_passe:
            # Tri : Plus récent en premier (pour voir la dernière sortie en haut)
            passe_df = df[df['temp_date_obj'] < aujourdhui].copy().sort_values('temp_date_obj', ascending=False)
            if search: passe_df = passe_df[passe_df['Nom'].str.contains(search, case=False) | passe_df['Prénom'].str.contains(search, case=False)]
            passe_df = passe_df[passe_df['Statut'].isin(f_statut)]
            
            if passe_df.empty:
                st.info("Aucun historique pour le moment.")
            for idx, row in passe_df.iterrows():
                stat = row['Statut'] if row['Statut'] else "🟡 Attente"
                status_class = "status-ok" if "🟢" in stat else "status-attente" if "🟡" in stat else "status-non"
                st.markdown(f'<div class="client-card {status_class}" style="opacity:0.7;"><span style="color:#666; font-size:0.9em;">📅 {row["DateNav"]} (Terminé)</span><br><b style="color:black; font-size:1.2em;">{row["Nom"]} {row["Prénom"]}</b><span style="float:right; font-weight:bold;">{stat}</span></div>', unsafe_allow_html=True)
                if st.button(f"Voir historique {row['Nom']}", key=f"pas_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    # --- PAGE PLANNING ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        cm, cy = st.columns(2)
        m_idx = mois_fr.index(cm.selectbox("Mois", mois_fr, index=datetime.now().month-1)) + 1
        y_sel = cy.selectbox("Année", list(range(2024, 2030)), index=list(range(2024, 2030)).index(datetime.now().year))
        
        mask_m = (df['temp_date_obj'].dt.month == m_idx) & (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")
        mask_a = (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")
        rec_m = df[mask_m]['prix_num'].sum()
        rec_a = df[mask_a]['prix_num'].sum()
        
        st.markdown(f"""<div style="background-color:#003366; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px;">
        💰 Recettes {mois_fr[m_idx-1]} : <b>{rec_m:,.2f} €</b> | 📈 Cumul Annuel {y_sel} : <b>{rec_a:,.2f} €</b></div>""", unsafe_allow_html=True)

        cal = calendar.monthcalendar(y_sel, m_idx)
        cols_h = st.columns(7)
        for i, j in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]): cols_h[i].write(f"**{j}**")
        
        for week in cal:
            cols_w = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{day:02d}/{m_idx:02d}/{y_sel}"
                    t_date = datetime(y_sel, m_idx, day).date()
                    occ = df[(df['temp_date_obj'].dt.date == t_date) & (df['Statut'] == "🟢 OK")]
                    
                    btn_label = str(day)
                    if not occ.empty:
                        total_p = sum(pd.to_numeric(occ['Passagers'], errors='coerce').fillna(0))
                        icon = "🔴" if total_p == 1 else "🟠" if total_p <= 3 else "🟢"
                        btn_label = f"{icon} {day} ({int(total_p)}p)"
                    
                    if cols_w[i].button(btn_label, key=f"b_{d_str}", use_container_width=True):
                        st.session_state.cal_date_sel = d_str

        if st.session_state.cal_date_sel:
            st.markdown("---")
            st.subheader(f"⚓ Détails du {st.session_state.cal_date_sel}")
            sel_date = pd.to_datetime(st.session_state.cal_date_sel, dayfirst=True).date()
            details = df[(df['temp_date_obj'].dt.date == sel_date) & (df['Statut'] == "🟢 OK")]
            
            if details.empty:
                st.info("Aucune réservation validée.")
            else:
                for _, r in details.iterrows():
                    with st.expander(f"👤 {r['Nom']} {r['Prénom']} - {r['Passagers']} pers.", expanded=True):
                        st.write(f"📞 **Tel:** {r['Téléphone']} | 📧 **Email:** {r['Email']}")
                        st.write(f"💰 **Prix:** {r['PrixJour']}€ | ✅ **Payé:** {r['Paye']}")
                        st.write(f"📝 **Notes:** {r['Historique']}")
            if st.button("Fermer les détails"):
                st.session_state.cal_date_sel = None; st.rerun()

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        
        with st.form("fiche_nav"):
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""), placeholder="NOM DU CLIENT")
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""), placeholder="Prénom")
            f_tel = c1.text_input("Téléphone", value=init.get("Téléphone", ""), placeholder="06...")
            f_email = c2.text_input("Email", value=init.get("Email", ""), placeholder="mail@exemple.com")
            st.markdown("---")
            c3, c4 = st.columns(2)
            f_date = c3.text_input("Date Navigation (JJ/MM/AAAA)", value=init.get("DateNav", ""), placeholder="JJ/MM/AAAA")
            f_pass = c4.number_input("Passagers", min_value=1, value=int(float(str(init.get("Passagers", 1)).replace(',','.'))) if init.get("Passagers") else 1)
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente") if init.get("Statut") in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else "🟡 Attente"))
            st.markdown("---")
            c5, c6 = st.columns([2, 1])
            f_prix = c5.text_input("Forfait (€)", value=str(init.get("PrixJour", "0")))
            f_paye = c6.checkbox("✅ PAYÉ", value=(init.get("Paye") == "Oui"))
            st.markdown("---")
            f_his = st.text_area("Historique (D: Demande / R: Réponse)", value=init.get("Historique", ""), height=100)
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    d_clean = f_date.strip().replace('-', '/')
                    d_obj = datetime.strptime(d_clean, '%d/%m/%Y')
                    new_rec = {
                        "DateNav": d_obj.strftime('%d/%m/%Y'),
                        "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(),
                        "Téléphone": f_tel, "Email": f_email, "Passagers": str(f_pass),
                        "Statut": f_stat, "PrixJour": f_prix, "Paye": "Oui" if f_paye else "Non",
                        "Historique": f_his
                    }
                    if idx is not None:
                        for k, v in new_rec.items(): df.at[idx, k] = v
                    else:
                        df = pd.concat([df, pd.DataFrame([new_rec])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    st.session_state.page = "LISTE"
                    st.rerun()
                except: st.error("⚠️ FORMAT DATE : Utilisez JJ/MM/AAAA")

    # --- PAGE CHECK ---
    elif st.session_state.page == "CHECK":
        st.subheader("✅ Checklist Skipper")
        st.info("Cette section sera bientôt disponible pour gérer vos inventaires et sécurités.")


            








































