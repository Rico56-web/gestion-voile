C'est le défi de l'affichage sur iPad : quand on ajoute des colonnes (comme le prix et les calculs), Streamlit a tendance à "comprimer" ou cacher le reste pour que ça tienne dans la largeur de l'écran.

Pour régler cela, j'ai réorganisé l'affichage de chaque fiche sous forme de blocs verticaux. Au lieu d'essayer de tout mettre sur une seule ligne, les informations sont maintenant empilées de façon claire.

🛠️ Ce que j'ai corrigé pour la visibilité :
Affichage hiérarchique : Le Statut (couleur) et l'Email sont désormais écrits en gros dans le corps de la fiche, pas seulement dans les petits menus.

Champs prioritaires : J'ai forcé l'apparition de l'Email, du Téléphone et du Statut dès l'ouverture de la fiche.

Boutons larges : Plus faciles à cliquer sur tablette.

🚀 Copiez ce code (Version "Haute Visibilité") :
Python
import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Intégrale", layout="wide")

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
            for col in ['PrixJour', 'Jours']:
                if col in df_load.columns:
                    df_load[col] = df_load[col].replace('', '0').fillna('0')
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
    if 'temp_date' in df_save.columns: df_save = df_save.drop(columns=['temp_date'])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta Visibility Fix", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
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
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique", "Paye", "PrixJour"]
    df = charger_data("contacts", cols)
    for c in cols:
        if c not in df.columns: df[c] = ""

    # --- NAVIGATION ---
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("💰 FINANCES", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        st.subheader("Planning & Recherche")
        
        search = st.text_input("🔍 Rechercher un nom...")
        vue_temps = st.selectbox("Période :", ["🚀 Prochaines Navigations", "📜 Archives", "🌍 Tout voir"])
        
        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        
        if vue_temps == "🚀 Prochaines Navigations":
            filt_df = filt_df[(filt_df['temp_date'] >= today) | (filt_df['temp_date'].isna())]
        elif vue_temps == "📜 Archives":
            filt_df = filt_df[filt_df['temp_date'] < today]

        filt_df = filt_df.sort_values(by="temp_date", ascending=(vue_temps != "📜 Archives"))

        for idx, row in filt_df.iterrows():
            bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
            p_icon = "✅ PAYÉ" if str(row['Paye']) == "Oui" else "⏳ À RÉGLER"
            
            # Calcul tarif
            try:
                v_p = float(str(row['PrixJour']).replace(',', '.') or 0)
                v_j = float(str(row['Jours']).replace(',', '.') or 0)
                total_f = int(v_p * v_j)
            except: total_f = 0
            
            # BLOC FICHE HAUTE VISIBILITÉ
            st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; border:2px solid #555; margin-bottom:10px; color:black;">
                <div style="display: flex; justify-content: space-between;">
                    <span style="font-size:1.2em; font-weight:bold;">📅 {row['DateNav']} ({row['Jours']}j)</span>
                    <span style="font-size:1.1em; font-weight:bold;">{row['Statut']}</span>
                </div>
                <div style="font-size:1.4em; margin-top:10px;">👤 <b>{row['Nom']}</b> {row['Prénom']}</div>
                <div style="margin-top:5px;">📧 {row['Email']} | 📞 {row['Téléphone']}</div>
                <div style="margin-top:5px; font-weight:bold; color:#2e7d32;">💰 {total_f}€ — {p_icon}</div>
                <div style="font-style:italic; font-size:0.9em; margin-top:5px;">💬 {row['Cause']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_edit, c_pay, c_det = st.columns(3)
            with c_edit:
                if st.button("✏️ Modifier", key=f"e_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            with c_pay:
                label_p = "💰 Encaisser" if str(row['Paye']) != "Oui" else "🔄 Annuler"
                if st.button(label_p, key=f"p_{idx}", use_container_width=True):
                    df.at[idx, 'Paye'] = "Oui" if str(row['Paye']) != "Oui" else "Non"
                    sauvegarder_data(df, "contacts"); st.rerun()
            with c_det:
                with st.expander("📝 Voir Notes"):
                    st.write(f"**Demande :** {row['Demande']}")
                    st.write(f"**Historique :** {row['Historique']}")

    # --- PAGE CALENDRIER (FINANCES) ---
    elif st.session_state.page == "CALENDRIER":
        st.subheader("💰 Bilan Financier")
        df['temp_date'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
        df['J_num'] = pd.to_numeric(df['Jours'], errors='coerce').fillna(0)
        df['P_num'] = pd.to_numeric(df['PrixJour'], errors='coerce').fillna(0)
        df['TotalFiche'] = df['J_num'] * df['P_num']
        
        df_ok = df[df['Statut'] == "🟢 OK"]
        encaisse = df_ok[df_ok['Paye'] == "Oui"]['TotalFiche'].sum()
        attendu = df_ok['TotalFiche'].sum()
        
        st.metric("SOLDE ENCAISSÉ", f"{int(encaisse)} €", f"sur {int(attendu)} €")
        st.markdown("---")

        now = datetime.now()
        for i in range(6):
            m, y = (now.month + i - 1) % 12 + 1, now.year + (now.month + i - 1) // 12
            month_name = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"][m-1]
            m_navs = df[(df['temp_date'].dt.month == m) & (df['temp_date'].dt.year == y) & (df['Statut'] == "🟢 OK")]
            t_j = m_navs['J_num'].sum()
            t_ok = m_navs[m_navs['Paye'] == "Oui"]['TotalFiche'].sum()

            st.write(f"**{month_name} {y}** : {int(t_j)}j d'occupation | Encaissé : **{int(t_ok)}€**")
            st.progress(min(t_j / 31, 1.0))

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        with st.form("f_full"):
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
                f_jours = st.text_input("Nombre de jours", value=str(init.get("Jours", "0")))
                f_prix = st.text_input("Tarif / Jour (€)", value=str(init.get("PrixJour", "20")))
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            with c2:
                f_nom = st.text_input("Nom", value=init.get("Nom", ""))
                f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
                f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
                f_ema = st.text_input("Email", value=init.get("Email", ""))
            
            f_paye = st.checkbox("Participation réglée", value=(str(init.get("Paye")) == "Oui"))
            f_cau = st.text_input("Motif Statut (Cause)", value=init.get("Cause", ""))
            f_dem = st.text_area("Précisions demande", value=init.get("Demande", ""))
            f_his = st.text_area("Historique / Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = {"DateNav": f_date, "Jours": f_jours.replace(',','.'), "PrixJour": f_prix.replace(',','.'), "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Paye": "Oui" if f_paye else "Non", "Téléphone": f_tel, "Email": f_ema, "Demande": f_dem, "Cause": f_cau, "Historique": f_his}
                if idx is not None: df.loc[idx] = new_row
                else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()

    # --- PAGE CHECKLIST ---
    elif st.session_state.page == "CHECK":
        st.subheader("Check-list")
        df_c = charger_data("checklist", ["Tâche"])
        nt = st.text_input("Nouvelle tâche")
        if st.button("Ajouter"):
            df_c = pd.concat([df_c, pd.DataFrame([{"Tâche": nt}])], ignore_index=True)
            sauvegarder_data(df_c, "checklist"); st.rerun()
        for i, r in df_c.iterrows():
            c_a, c_b = st.columns([5,1])
            c_a.write(f"• {r['Tâche']}")
            if c_b.button("Fait", key=f"c_{i}"):
                df_c = df_c.drop(i); sauvegarder_data(df_c, "checklist"); st.rerun()

            














