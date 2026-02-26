import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Skipper", layout="wide")

# Style CSS amélioré
st.markdown("""
    <style>
    div[data-baseweb="input"] input:placeholder-shown { background-color: #fff3e0 !important; } 
    div[data-baseweb="textarea"] textarea:placeholder-shown { background-color: #fff3e0 !important; }
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
    .stats-banner {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
        border: 1px solid #d1d5db;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB (SÉCURISÉES) ---
def charger_data(nom_fichier, colonnes):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            content = res.json()
            decoded = base64.b64decode(content['content']).decode('utf-8')
            if decoded.strip():
                data_json = json.loads(decoded)
                df_load = pd.DataFrame(data_json)
                for col in colonnes:
                    if col not in df_load.columns: df_load[col] = ""
                return df_load
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    df_save = df.copy()
    # On ne garde que les colonnes réelles pour le JSON
    cols_to_keep = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df_save = df_save[cols_to_keep]
    
    json_data = df_save.to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": f"Vesta Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": content_b64}
    if sha: data["sha"] = sha
    
    put_res = requests.put(url, headers=headers, json=data)
    if put_res.status_code in [200, 201]:
        st.success("✅ Sauvegarde GitHub réussie !")
    else:
        st.error(f"❌ Erreur sauvegarde : {put_res.text}")

# --- INITIALISATION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols_base)
    
    # Préparation technique (non sauvegardée)
    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
    
    def clean_prix(val):
        if pd.isna(val) or val == "": return 0.0
        s = str(val).replace('€', '').replace(' ', '').replace(',', '.').strip()
        try: return float(s)
        except: return 0.0
    df['prix_num'] = df['PrixJour'].apply(clean_prix)

    # --- NAVIGATION ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("🗓️ PLANNING", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        # Indicateur de santé des données
        total_fiches = len(df)
        fiches_sans_date = df['temp_date_obj'].isna().sum()
        
        st.markdown(f"""<div class="stats-banner">📊 Base de données : <b>{total_fiches} fiches au total</b> 
        {f'| ⚠️ {fiches_sans_date} fiches avec erreur de date' if fiches_sans_date > 0 else ''}</div>""", unsafe_allow_html=True)

        c_search, c_filter = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher un nom...")
        with c_filter: f_statut = st.multiselect("Filtrer :", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])

        aujourdhui = pd.Timestamp(datetime.now().date())
        tab_futur, tab_passe, tab_erreurs = st.tabs(["🚀 PROCHAINES SORTIES", "📂 ARCHIVES", "⚠️ ERREURS FORMAT"])

        with tab_futur:
            f_df = df[df['temp_date_obj'] >= aujourdhui].copy().sort_values('temp_date_obj')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False) | f_df['Prénom'].str.contains(search, case=False)]
            f_df = f_df[f_df['Statut'].isin(f_statut)]
            for idx, row in f_df.iterrows():
                stat = row['Statut'] or "🟡 Attente"
                cl = "status-ok" if "🟢" in stat else "status-attente" if "🟡" in stat else "status-non"
                st.markdown(f'<div class="client-card {cl}"><b>{row["DateNav"]}</b> — {row["Nom"]} {row["Prénom"]} ({stat})</div>', unsafe_allow_html=True)
                if st.button(f"Modifier {row['Nom']}", key=f"f_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab_passe:
            p_df = df[df['temp_date_obj'] < aujourdhui].copy().sort_values('temp_date_obj', ascending=False)
            if search: p_df = p_df[p_df['Nom'].str.contains(search, case=False) | p_df['Prénom'].str.contains(search, case=False)]
            p_df = p_df[p_df['Statut'].isin(f_statut)]
            for idx, row in p_df.iterrows():
                stat = row['Statut'] or "🟡 Attente"
                cl = "status-ok" if "🟢" in stat else "status-attente" if "🟡" in stat else "status-non"
                st.markdown(f'<div class="client-card {cl}" style="opacity:0.6;"><b>{row["DateNav"]}</b> — {row["Nom"]} {row["Prénom"]}</div>', unsafe_allow_html=True)
                if st.button(f"Voir {row['Nom']}", key=f"p_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab_erreurs:
            e_df = df[df['temp_date_obj'].isna()].copy()
            if not e_df.empty:
                st.warning("Ces fiches ont une date mal écrite et n'apparaissent pas dans le calendrier.")
                for idx, row in e_df.iterrows():
                    st.error(f"Fiche de {row['Nom']} - Date saisie : '{row['DateNav']}'")
                    if st.button(f"Réparer {row['Nom']}", key=f"e_{idx}"):
                        st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            else:
                st.success("Aucune erreur de format détectée.")

    # --- PAGES PLANNING & FORM (Inchangées mais sécurisées) ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        cm, cy = st.columns(2)
        m_idx = mois_fr.index(cm.selectbox("Mois", mois_fr, index=datetime.now().month-1)) + 1
        y_sel = cy.selectbox("Année", list(range(2024, 2030)), index=list(range(2024, 2030)).index(datetime.now().year))
        
        mask_m = (df['temp_date_obj'].dt.month == m_idx) & (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")
        mask_a = (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")
        rec_m = df[mask_m]['prix_num'].sum()
        rec_a = df[mask_a]['prix_num'].sum()
        
        st.markdown(f"""<div style="background-color:#003366; color:white; padding:15px; border-radius:10px; text-align:center;">
        💰 Mensuel : {rec_m:,.2f} € | 📈 Annuel : {rec_a:,.2f} €</div>""", unsafe_allow_html=True)

        cal = calendar.monthcalendar(y_sel, m_idx)
        cols_h = st.columns(7)
        for i, d_nom in enumerate(["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]): cols_h[i].write(f"**{d_nom}**")
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
                        btn_label = f"{'🔴' if total_p==1 else '🟠' if total_p<=3 else '🟢'} {day} ({int(total_p)}p)"
                    if cols_w[i].button(btn_label, key=f"cal_{d_str}", use_container_width=True):
                        st.session_state.cal_date_sel = d_str
        
        if st.session_state.get("cal_date_sel"):
            sel_date = pd.to_datetime(st.session_state.cal_date_sel, dayfirst=True).date()
            details = df[(df['temp_date_obj'].dt.date == sel_date) & (df['Statut'] == "🟢 OK")]
            for _, r in details.iterrows():
                st.info(f"👤 {r['Nom']} {r['Prénom']} | 📞 {r['Téléphone']} | 💰 {r['PrixJour']}€")

    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("f_form"):
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_date = st.text_input("Date Navigation (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_prix = st.text_input("Prix (€)", value=init.get("PrixJour", "0"))
            f_pass = st.number_input("Passagers", min_value=1, value=int(float(str(init.get("Passagers", 1)).replace(',','.'))) if init.get("Passagers") else 1)
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_email = st.text_input("Email", value=init.get("Email", ""))
            f_paye = st.checkbox("Payé", value=(init.get("Paye") == "Oui"))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    # Forcer le format de date propre
                    d_clean = f_date.strip().replace('-', '/')
                    datetime.strptime(d_clean, '%d/%m/%Y') 
                    new_rec = {
                        "DateNav": d_clean, "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(),
                        "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass),
                        "Téléphone": f_tel, "Email": f_email, "Paye": "Oui" if f_paye else "Non", "Historique": f_his
                    }
                    if idx is not None: df.loc[idx] = new_rec
                    else: df = pd.concat([df, pd.DataFrame([new_rec])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    st.session_state.page = "LISTE"; st.rerun()
                except: st.error("Date invalide (JJ/MM/AAAA)")

    elif st.session_state.page == "CHECK":
        st.subheader("✅ Checklist")
        st.write("Section à configurer.")


            









































