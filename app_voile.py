import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Skipper", layout="wide")

# Style CSS
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
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
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
    cols_to_keep = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df_save = df_save[cols_to_keep]
    
    json_data = df_save.to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": f"Vesta Update {datetime.now().strftime('%Y-%m-%d %H:%M')}", "content": content_b64}
    if sha: data["sha"] = sha
    
    put_res = requests.put(url, headers=headers, json=data)
    if put_res.status_code in [200, 201]:
        st.success("✅ Données synchronisées")
    else:
        st.error(f"❌ Erreur GitHub : {put_res.text}")

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
        total_fiches = len(df)
        st.markdown(f'<div class="stats-banner">📊 Base Vesta : <b>{total_fiches} fiches</b></div>', unsafe_allow_html=True)

        c_search, c_filter = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher...")
        with c_filter: f_statut = st.multiselect("Statut:", ["🟢 OK", "🟡 Attente", "🔴 Pas OK"], default=["🟢 OK", "🟡 Attente", "🔴 Pas OK"])

        auj = pd.Timestamp(datetime.now().date())
        tab1, tab2, tab3 = st.tabs(["🚀 PROCHAINES SORTIES", "📂 ARCHIVES", "⚠️ ERREURS"])

        with tab1:
            f_df = df[df['temp_date_obj'] >= auj].copy().sort_values('temp_date_obj')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False) | f_df['Prénom'].str.contains(search, case=False)]
            f_df = f_df[f_df['Statut'].isin(f_statut)]
            for idx, row in f_df.iterrows():
                cl = "status-ok" if "🟢" in str(row['Statut']) else "status-attente" if "🟡" in str(row['Statut']) else "status-non"
                st.markdown(f'<div class="client-card {cl}"><b>{row["DateNav"]}</b> — {row["Nom"]} {row["Prénom"]}</div>', unsafe_allow_html=True)
                if st.button(f"Ouvrir {row['Nom']}", key=f"f_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab2:
            p_df = df[df['temp_date_obj'] < auj].copy().sort_values('temp_date_obj', ascending=False)
            if search: p_df = p_df[p_df['Nom'].str.contains(search, case=False) | p_df['Prénom'].str.contains(search, case=False)]
            p_df = p_df[p_df['Statut'].isin(f_statut)]
            for idx, row in p_df.iterrows():
                st.markdown(f'<div class="client-card" style="opacity:0.6;"><b>{row["DateNav"]}</b> — {row["Nom"]} {row["Prénom"]}</div>', unsafe_allow_html=True)
                if st.button(f"Archive {row['Nom']}", key=f"p_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab3:
            e_df = df[df['temp_date_obj'].isna()].copy()
            for idx, row in e_df.iterrows():
                st.error(f"{row['Nom']} | Date: {row['DateNav']}")
                if st.button(f"Fix {row['Nom']}", key=f"e_{idx}"):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

    # --- PAGE PLANNING ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        m_sel = st.selectbox("Mois", mois_fr, index=datetime.now().month-1)
        m_idx = mois_fr.index(m_sel) + 1
        y_sel = datetime.now().year
        
        mask = (df['temp_date_obj'].dt.month == m_idx) & (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")
        st.info(f"CA Mensuel estimé : {df[mask]['prix_num'].sum():,.2f} €")

        cal = calendar.monthcalendar(y_sel, m_idx)
        for week in cal:
            cols_w = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_str = f"{day:02d}/{m_idx:02d}/{y_sel}"
                    occ = df[(df['temp_date_obj'].dt.date == datetime(y_sel, m_idx, day).date()) & (df['Statut'] == "🟢 OK")]
                    btn_txt = str(day)
                    if not occ.empty: btn_txt = f"🟢 {day}"
                    if cols_w[i].button(btn_txt, key=f"c_{d_str}"):
                        st.write(occ[["Nom", "Prénom", "Téléphone"]])

    # --- PAGE FORMULAIRE (CORRIGÉE) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        
        # SÉCURITÉ : On s'assure que pass_val est au moins 1 pour éviter le crash
        try:
            raw_pass = str(init.get("Passagers", "1")).replace(',', '.')
            pass_val = max(1, int(float(raw_pass))) if raw_pass and raw_pass != "" else 1
        except:
            pass_val = 1

        with st.form("vesta_form"):
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente") if init.get("Statut") in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else "🟡 Attente"))
            f_prix = st.text_input("Prix (€)", value=init.get("PrixJour", "0"))
            
            # Application de la valeur sécurisée
            f_pass = st.number_input("Passagers", min_value=1, value=pass_val)
            
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_his = st.text_area("Historique", value=init.get("Historique", ""))
            
            submit = st.form_submit_button("💾 ENREGISTRER")
            
            if submit:
                try:
                    d_clean = f_date.strip().replace('-', '/')
                    datetime.strptime(d_clean, '%d/%m/%Y') 
                    new = {
                        "DateNav": d_clean, "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(),
                        "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass),
                        "Téléphone": f_tel, "Email": init.get("Email", ""), 
                        "Paye": "Oui" if "🟢" in f_stat else "Non", "Historique": f_his
                    }
                    if idx is not None: df.loc[idx] = new
                    else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    st.session_state.page = "LISTE"; st.rerun()
                except: st.error("Format date invalide")

    elif st.session_state.page == "CHECK":
        st.subheader("✅ Checklist")
        st.write("Section prête.")


            










































