C'est un véritable carnet de bord professionnel que nous sommes en train de peaufiner ! J'ai intégré toutes vos demandes de structure, de mise en forme automatique et de suivi financier.

🛠️ Les nouveautés de cette version :
Tableau de Bord Financier : Un bandeau bleu en haut du calendrier calcule en temps réel votre chiffre d'affaires (basé sur les statuts "🟢 OK").

Mise en forme Intelligente : Peu importe comment vous tapez, le NOM devient MAJUSCULE et le Prénom prend sa Majuscule initiale.

Réorganisation de la Fiche : L'ordre est désormais : Identité > Contact > Passagers > Forfait & Paiement.

Couleurs du Calendrier : Comme Streamlit ne permet pas nativement de colorer chaque bouton différemment, j'ai utilisé une astuce : le bouton affiche le nombre de passagers et change de style pour être immédiatement repérable.

🚀 Copiez ce code complet :
Python
import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Skipper", layout="wide")

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
    if 'temp_date_obj' in df_save.columns: df_save = df_save.drop(columns=['temp_date_obj'])
    if 'prix_num' in df_save.columns: df_save = df_save.drop(columns=['prix_num'])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta: Stats + Automations", "content": content_b64}
    if sha: data["sha"] = sha
    requests.put(url, headers=headers, json=data)

# --- SESSION STATE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "cal_date_sel" not in st.session_state: st.session_state.cal_date_sel = None

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols)
    df['temp_date_obj'] = pd.to_datetime(df['DateNav'], dayfirst=True, errors='coerce')

    # Navigation
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
        c_search, c_filter = st.columns([2, 1])
        with c_search: search = st.text_input("🔍 Rechercher...")
        opts_stat = ["🟢 OK", "🟡 Attente", "🔴 Pas OK"]
        with c_filter: f_statut = st.multiselect("Filtrer :", opts_stat, default=opts_stat)

        filt_df = df.copy()
        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]
        filt_df = filt_df[filt_df['Statut'].isin(f_statut)]
        
        for idx, row in filt_df.sort_values('temp_date_obj', ascending=True).iterrows():
            stat = row['Statut'] if row['Statut'] else "🟡 Attente"
            bg = "#c8e6c9" if "🟢" in stat else "#fff9c4" if "🟡" in stat else "#ffcdd2"
            est_paye = str(row['Paye']) == "Oui"
            
            st.markdown(f"""
            <div style="background-color:{bg}; padding:15px; border-radius:10px; border:1px solid #333; margin-bottom:10px; color:black;">
                <div style="display: flex; justify-content: space-between; font-weight:bold;">
                    <span>📅 {row['DateNav']}</span>
                    <span style="background: white; padding: 2px 8px; border-radius: 5px; border: 1px solid black;">{stat}</span>
                </div>
                <div style="font-size:1.3em; margin-top:8px;">👤 <b>{row['Nom']}</b> {row['Prénom']}</div>
                <div style="margin-top:5px;">📞 {row['Téléphone']} | 📧 {row['Email']}</div>
                <div style="margin-top:8px; font-weight:bold;">💰 {row['PrixJour']}€ — {'✅ PAYÉ' if est_paye else '⏳ À PAYER'} | 👥 {row['Passagers']} pers.</div>
            </div>
            """, unsafe_allow_html=True)
            
            c_ed, c_del = st.columns(2)
            if c_ed.button("✏️ Modifier", key=f"e_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()
            if c_del.button("🗑️ Supprimer", key=f"d_{idx}", use_container_width=True):
                df = df.drop(idx); sauvegarder_data(df, "contacts"); st.rerun()

    # --- PAGE PLANNING (FINANCES) ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        c_m, c_y = st.columns(2)
        m_nom = c_m.selectbox("Mois", mois_fr, index=datetime.now().month-1)
        m_idx = mois_fr.index(m_nom) + 1
        y_sel = c_y.selectbox("Année", list(range(2024, 2030)), index=list(range(2024, 2030)).index(datetime.now().year))
        
        # Calcul Finances
        df['prix_num'] = pd.to_numeric(df['PrixJour'], errors='coerce').fillna(0)
        rec_m = df[(df['temp_date_obj'].dt.month == m_idx) & (df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")]['prix_num'].sum()
        rec_a = df[(df['temp_date_obj'].dt.year == y_sel) & (df['Statut'] == "🟢 OK")]['prix_num'].sum()
        
        st.markdown(f"""<div style="background-color:#003366; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:15px;">
        <span style="font-size:1.1em;">Recettes {m_nom} : <b>{rec_m:,.0f}€</b></span> | <span>Année {y_sel} : <b>{rec_a:,.0f}€</b></span></div>""", unsafe_allow_html=True)

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
                    
                    btn_txt = str(day)
                    if not occ.empty:
                        nb_p = sum(pd.to_numeric(occ['Passagers'], errors='coerce').fillna(0))
                        btn_txt = f"{day} ({int(nb_p)}p)"
                    
                    if cols_w[i].button(btn_txt, key=f"b_{d_str}", use_container_width=True, type="primary" if not occ.empty else "secondary"):
                        st.session_state.cal_date_sel = d_str

        if st.session_state.cal_date_sel:
            st.info(f"Détails du {st.session_state.cal_date_sel}")
            sel_date = pd.to_datetime(st.session_state.cal_date_sel, dayfirst=True).date()
            details = df[(df['temp_date_obj'].dt.date == sel_date) & (df['Statut'] == "🟢 OK")]
            for _, r in details.iterrows():
                st.write(f"👤 **{r['Nom']} {r['Prénom']}** - 📞 {r['Téléphone']} ({r['Passagers']} pers.)")
            if st.button("Fermer"): st.session_state.cal_date_sel = None; st.rerun()

    # --- PAGE FORMULAIRE (RÉORGANISÉE) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        
        # Nettoyage Date
        date_aff = init.get("DateNav", "")
        if "-" in date_aff:
            try: date_aff = datetime.strptime(date_aff, '%Y-%m-%d').strftime('%d/%m/%Y')
            except: pass

        with st.form("f"):
            # 1. Identité
            f_nom = st.text_input("NOM (Majuscules auto)", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            
            # 2. Contact
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_email = st.text_input("Email", value=init.get("Email", ""))
            
            # 3. Logistique
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=date_aff)
            f_pass = st.number_input("Passagers", min_value=1, value=int(float(str(init.get("Passagers", 1)).replace(',','.'))) if init.get("Passagers") else 1)
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=0)
            f_his = st.text_area("Notes historiques", value=init.get("Historique", ""))
            
            st.markdown("---")
            # 4. Forfait (En bas)
            f_prix = st.text_input("Forfait (€)", value=str(init.get("PrixJour", "0")))
            f_paye = st.checkbox("Payé ✅", value=(init.get("Paye") == "Oui"))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    # Formatage auto
                    n_final = f_nom.upper()
                    p_final = f_pre.strip().capitalize()
                    d_save = pd.to_datetime(f_date, dayfirst=True).strftime('%d/%m/%Y')
                    
                    new = {"DateNav": d_save, "Nom": n_final, "Prénom": p_final, "Téléphone": f_tel, "Email": f_email,
                           "Passagers": str(f_pass), "Statut": f_stat, "PrixJour": f_prix, "Paye": "Oui" if f_paye else "Non", "Historique": f_his}
                    
                    if idx is not None:
                        for k, v in new.items(): df.at[idx, k] = v
                    else:
                        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    
                    sauvegarder_data(df, "contacts"); st.session_state.page = "LISTE"; st.rerun()
                except: st.error("⚠️ Date invalide (Format attendu : JJ/MM/AAAA)")
⚓ Les points clés pour vous :

            































