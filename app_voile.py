import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta - Gestion Planning", layout="wide")

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
            return pd.DataFrame(json.loads(decoded))
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    # Nettoyage avant sauvegarde : on s'assure que tout est en texte
    df_save = df.copy()
    if 'temp_date' in df_save.columns: df_save = df_save.drop(columns=['temp_date'])
    json_data = df_save.to_json(orient="records", indent=4)
    content_b64 = base64.b64encode(json_data.encode('utf-8')).decode('utf-8')
    data = {"message": "Update Vesta", "content": content_b64}
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
    cols = ["DateNav", "Jours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Cause", "Demande", "Historique"]
    df = charger_data("contacts", cols)
    for c in cols:
        if c not in df.columns: df[c] = ""

    # Navigation
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if c1.button("📅 PLANNING", use_container_width=True):
        st.session_state.page = "LISTE"
        st.rerun()
    if c2.button("➕ NOUVEAU", use_container_width=True):
        if "edit_idx" in st.session_state: del st.session_state.edit_idx
        st.session_state.page = "FORM"
        st.rerun()
    if c3.button("✅ CHECK-LIST", use_container_width=True):
        st.session_state.page = "CHECK"
        st.rerun()
    st.markdown("---")

    # --- PAGE LISTE ---
    if st.session_state.page == "LISTE":
        st.subheader("Planning Vesta")
        
        # Filtres
        c_p, c_t = st.columns(2)
        with c_p:
            vue_temps = st.selectbox("Période :", ["🚀 Prochaines Navigations", "📜 Archives", "🌍 Tout voir"])
        with c_t:
            tri_mode = st.selectbox("Trier par :", ["📅 Date", "🔤 Nom"])

        options_statut = ["🟢 OK", "🟡 Attente", "🔴 Pas OK"]
        f_statut = st.multiselect("Statuts à afficher :", options_statut, default=options_statut)
        search = st.text_input("🔍 Chercher un nom...")
        
        # --- LOGIQUE DE TRI ET FILTRAGE ---
        filt_df = df.copy()
        
        # Conversion robuste des dates pour le tri interne
        filt_df['temp_date'] = pd.to_datetime(filt_df['DateNav'], dayfirst=True, errors='coerce')
        today = datetime.now().normalize()

        # Filtrage Statut
        filt_df = filt_df[filt_df['Statut'].isin(f_statut)]
        
        # Filtrage Temps
        if vue_temps == "🚀 Prochaines Navigations":
            # On garde ce qui est aujourd'hui/futur OU ce qui n'a pas de date valide (pour ne pas le perdre)
            filt_df = filt_df[(filt_df['temp_date'] >= today) | (filt_df['temp_date'].isna())]
        elif vue_temps == "📜 Archives":
            filt_df = filt_df[filt_df['temp_date'] < today]

        # Recherche
        if search:
            filt_df = filt_df[filt_df['Nom'].str.contains(search, case=False) | filt_df['Prénom'].str.contains(search, case=False)]

        # Tri Final
        if tri_mode == "📅 Date":
            ordre = True if vue_temps != "📜 Archives" else False
            filt_df = filt_df.sort_values(by="temp_date", ascending=ordre, na_position='last')
        else:
            filt_df = filt_df.sort_values(by="Nom")

        # Affichage
        if filt_df.empty:
            st.warning("Aucun résultat pour ces filtres.")
        else:
            for idx, row in filt_df.iterrows():
                bg = "#c8e6c9" if "🟢" in str(row['Statut']) else "#fff9c4" if "🟡" in str(row['Statut']) else "#ffcdd2"
                jours_txt = f"({row['Jours']}j)" if row['Jours'] and str(row['Jours']) != "0" else ""
                
                st.markdown(f"""
                <div style="background-color:{bg}; padding:12px; border-radius:10px; border:1px solid #999; margin-bottom:8px; color:black;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight:bold; font-size:1.1em;">📅 {row['DateNav']} {jours_txt}</span>
                        <span style="font-size:1.2em;">{row['Statut']}</span>
                    </div>
                    <div style="font-size:1.3em; margin: 5px 0;">👤 <b>{row['Nom']}</b> {row['Prénom']}</div>
                    <div style="font-size:0.9em; color:#444;">💬 {row['Cause']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    st.markdown(f'<a href="tel:{row["Téléphone"]}"><button style="width:100%; background:#2e7d32; color:white; border:none; padding:10px; border-radius:5px;">📞 Appel</button></a>', unsafe_allow_html=True)
                with b2:
                    if st.button("✏️ Modifier", key=f"ed_{idx}", use_container_width=True):
                        st.session_state.edit_idx = idx
                        st.session_state.page = "FORM"
                        st.rerun()
                with b3:
                    if st.button("🗑️ Suppr.", key=f"del_{idx}", use_container_width=True):
                        df = df.drop(idx)
                        sauvegarder_data(df, "contacts")
                        st.rerun()
                with b4:
                    with st.expander("Plus d'infos"):
                        st.write(f"📧 **Email:** {row['Email']}")
                        st.write(f"📝 **Demande:** {row['Demande']}")
                        st.write(f"📜 **Note:** {row['Historique']}")

    # --- PAGE FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        st.subheader("📝 Fiche Contact")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols}
        if not init.get("Statut"): init["Statut"] = "🟡 Attente"

        with st.form("form_nav"):
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.text_input("Date (Format recommandé: JJ/MM/AAAA)", value=init.get("DateNav", ""))
                f_jours = st.number_input("Nombre de jours", min_value=0, value=int(init.get("Jours", 0)) if init.get("Jours") else 0)
                f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init["Statut"]))
            with c2:
                f_nom = st.text_input("Nom", value=init.get("Nom", ""))
                f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
                f_cau = st.text_input("Motif Statut", value=init.get("Cause", ""))
            
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_ema = st.text_input("Email", value=init.get("Email", ""))
            f_dem = st.text_area("Précisions demande", value=init.get("Demande", ""))
            f_his = st.text_area("Historique / Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                new_row = {"DateNav": f_date, "Jours": str(f_jours), "Statut": f_stat, "Nom": f_nom, "Prénom": f_pre, "Téléphone": f_tel, "Email": f_ema, "Cause": f_cau, "Demande": f_dem, "Historique": f_his}
                if idx is not None: df.loc[idx] = new_row
                else: df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                sauvegarder_data(df, "contacts")
                st.session_state.page = "LISTE"
                st.rerun()

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


            






