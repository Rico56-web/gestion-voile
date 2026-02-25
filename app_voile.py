Import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion & Finances", layout="wide")

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
            # S'assurer que les colonnes numériques ne sont pas vides
            if 'PrixJour' in df_load.columns:
                df_load['PrixJour'] = df_load['PrixJour'].replace('', '0')
            if 'Jours' in df_load.columns:
                df_load['Jours'] = df_load['Jours'].replace('', '0')
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
    # Suppression des colonnes de calcul temporaires avant sauvegarde
    for c in ['J_num', 'P_num', 'TotalFiche']:
        if c in df_save.columns: df_save = df_save.drop(columns=[c])
    
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Update Vesta Robust Calculations", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "page" not in st.session_state:
    st.session_state.page = "LISTE"

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

    # Navigation
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📋 LISTE", use_container_width=True): st.session_state.page = "LISTE"; st.rerun()
    if c2.button("💰 FINANCES", use_container_width=True): st.session_state.page = "CALENDRIER"; st.rerun()
    if c3.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"; st.rerun()
    if c4.button("✅ CHECK", use_container_width=True): st.session_state.page = "CHECK"; st.rerun()
    st.markdown("---")

    # --- PAGE CALENDRIER & FINANCES ---
    if st.session_state.page == "CALENDRIER":
        st.subheader("💰 Bilan Financier & Occupation")
        
        df['temp_date'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')
        df['J_num'] = pd.to_numeric(df['Jours'], errors='coerce').fillna(0)
        df['P_num'] = pd.to_numeric(df['PrixJour'], errors='coerce').fillna(0)
        df['TotalFiche'] = df['J_num'] * df['P_num']
        
        df_ok_all = df[df['Statut'] == "🟢 OK"]
        total_global_attendu = df_ok_all['TotalFiche'].sum()
        total_global_encaisse = df_ok_all[df_ok_all['Paye'] == "Oui"]['TotalFiche'].sum()
        
        st.metric("SOLDE TOTAL ENCAISSÉ", f"{int(total_global_encaisse)} €", f"sur {int(total_global_attendu)} € attendus")
        st.markdown("---")

        now = datetime.now()
        for i in range(6):
            m = (now.month + i - 1) % 12 + 1
            y = now.year + (now.month + i - 1) // 12
            month_name = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"][m-1]
            
            month_navs = df[(df['temp_date'].dt.month == m) & (df['temp_date'].dt.year == y) & (df['Statut'] == "🟢 OK")]
            total_jours = month_navs['J_num'].sum()
            total_mensuel_du = month_navs['TotalFiche'].sum()
            total_mensuel_ok = month_navs[month_navs['Paye'] == "Oui"]['TotalFiche'].sum()

            st.markdown(f"#### {month_name} {y}")
            c_occ, c_fin = st.columns(2)
            c_occ.write(f"Occupation : **{int(total_jours)} j**")
            c_occ.progress(min(total_jours / 31, 1.0))
            c_fin.write(f"Caisse : **{int(total_mensuel_ok)}€** / {int(total_mensuel_du)}€")
            c_fin.progress(min(total_mensuel_ok / total_mensuel_du, 1.0) if total_mensuel_du > 0 else 0)
            st.markdown("---")

    # --- PAGE LISTE ---
    elif st.session_state.page == "LISTE":
        st.subheader("Planning Vesta")
        vue_temps = st.selectbox("Période :", ["🚀 Prochaines Navigations", "📜 Archives", "🌍 Tout voir"])
        
        filt_df = df.copy()
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if vue_temps == "🚀 Prochaines Navigations":
            filt_df = filt_df[(filt_df['temp_date'] >= today) | (filt_df['temp_date'].isna())]
        elif vue_temps == "📜 Archives":
            filt_df = filt_df[filt_df['temp_date'] < today]

        filt_df = filt_df.sort_values(by="temp_date", ascending=(vue_temps != "📜 Archives"))

        for idx, row in filt_df.iterrows():
            bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
            p_icon = "✅💰" if str(row['Paye']) == "Oui" else "⏳"
            
            # CALCUL SÉCURISÉ POUR L'AFFICHAGE
            try:
                val_prix = float(str(row['PrixJour']).replace(',', '.') or 0)
                val_jours = float(str(row['Jours']).replace(',', '.') or 0)
                total_fiche = int(val_prix * val_jours)
            except:
                total_fiche = 0
            
            st.markdown(f'<div style="background-color:{bg}; padding:10px; border-radius:10px; border:1px solid #999; margin-bottom:5px; color:black;"><b>{row["DateNav"]}</b> | {row["Prénom"]} {row["Nom"]} | <b>{total_fiche}€</b> {p_icon}</div>', unsafe_allow_html=True)
            c_edit, c_pay, c_det = st.columns(3)
            with c_edit:
                if st.button("✏️ Modif", key=f"e_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            with c_pay:
                label_p = "Marquer Payé" if str(row['Paye']) != "Oui" else "Annuler Payé"
                if st.button(label_p, key=f"p_{idx}", use_container_width=True):
                    df.at[idx, 'Paye'] = "Oui" if str(row['Paye']) != "Oui" else "Non"
                    sauvegarder_data(df, "contacts"); st.rerun()
            with c_det:
                with st.expander("Détails"):
                    st.write(f"Tarif : {row['PrixJour']}€/j x {row['Jours']}j")
                    st.write(f"Tél: {row['Téléphone']}")

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact & Tarif")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        
        with st.form("f_nav"):
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
                f_jours = st.text_input("Nb Jours", value=str(init.get("Jours", "0")))
                f_prix = st.text_input("Prix par Jour (€)", value=str(init.get("PrixJour", "20")))
            with c2:
                f_nom = st.text_input("Nom", value=init.get("Nom", ""))
                f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            
            f_paye = st.checkbox("Participation déjà réglée", value=(str(init.get("Paye")) == "Oui"))
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_ema = st.text_input("Email", value=init.get("Email", ""))
            f_dem = st.text_area("Précisions", value=init.get("Demande", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                # Nettoyage des virgules en points pour les calculs
                clean_jours = f_jours.replace(',', '.')
                clean_prix = f_prix.replace(',', '.')
                new_row = {**init, "DateNav": f_date, "Jours": clean_jours, "PrixJour": clean_prix, "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Paye": "Oui" if f_paye else "Non", "Téléphone": f_tel, "Email": f_ema, "Demande": f_dem}
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


            











