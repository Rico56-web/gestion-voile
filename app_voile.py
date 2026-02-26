import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# Style CSS
st.markdown("""
    <style>
    .client-card {
        background-color: #ffffff; padding: 15px; border-radius: 10px; 
        margin-bottom: 10px; border: 1px solid #eee; border-left: 10px solid #ccc;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 10px;
        font-size: 0.8em; background-color: #f4f4f4; margin-right: 5px; color: #555;
    }
    .price-tag { font-weight: bold; color: #2c3e50; float: right; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=30)
def charger_data(nom_fichier, colonnes):
    try:
        repo = st.secrets["GITHUB_REPO"]
        token = st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
        headers = {"Authorization": f"token {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            decoded = base64.b64decode(res.json()['content']).decode('utf-8')
            df_l = pd.DataFrame(json.loads(decoded))
            for c in colonnes:
                if c not in df_l.columns: df_l[c] = ""
            if "NbJours" not in df_l.columns: df_l["NbJours"] = "1"
            return df_l
    except: pass
    return pd.DataFrame(columns=colonnes)

def sauvegarder_data(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    cols_s = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    json_d = df[cols_s].to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
    data = {"message": "Update Vesta", "content": content_b64, "sha": sha} if sha else {"message": "Update", "content": content_b64}
    requests.put(url, headers=headers, json=data)
    st.cache_data.clear()

# --- INITIALISATION ---
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

def nav(p):
    if "edit_idx" in st.session_state: del st.session_state.edit_idx
    st.session_state.page = p
    st.rerun()

# --- AUTH ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "NbJours", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data("contacts", cols_base)
    
    # Navigation
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if m2.button("🗓️ PLAN", use_container_width=True): nav("CALENDRIER")
    if m3.button("➕ NEW", use_container_width=True): nav("FORM")
    if m4.button("✅ CHECK", use_container_width=True): nav("CHECK")
    st.markdown("---")

    # --- LISTE ---
    if st.session_state.page == "LISTE":
        st.markdown(f'<div style="text-align:right; color:gray;">Total : {len(df)} fiches</div>', unsafe_allow_html=True)
        search = st.text_input("🔍 Rechercher un nom...")
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        
        df['sort_key'] = df['DateNav'].apply(lambda x: "".join(reversed(x.split('/'))) if '/' in str(x) else "0")
        auj = datetime.now().strftime('%Y%m%d')

        def afficher_cartes(df_tab):
            for idx, r in df_tab.iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                nb_j = f"({r['NbJours']} jours)" if str(r['NbJours']) != "1" else ""
                st.markdown(f"""
                <div class="client-card {cl}">
                    <span class="price-tag">{r['PrixJour']}€</span>
                    <b>{r['Nom']} {r['Prénom']}</b><br>
                    <small>📅 {r['DateNav']} {nb_j} | 👤 {r['Passagers']} pers.</small>
                </div>
                """, unsafe_allow_html=True)
                # Bouton avec Prénom NOM
                label_btn = f"Modifier {r['Prénom']} {r['Nom']}"
                if st.button(label_btn, key=f"btn_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1:
            f_df = df[df['sort_key'] >= auj].sort_values('sort_key')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False)]
            afficher_cartes(f_df)
        with tab2:
            p_df = df[df['sort_key'] < auj].sort_values('sort_key', ascending=False).head(10)
            afficher_cartes(p_df)

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        
        with st.form("form_v3"):
            st.subheader("📝 Fiche Navigation")
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c1.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_mail = c2.text_input("Email", value=init.get("Email", ""))
            
            st.markdown("---")
            c3, c4, c5, c6 = st.columns([2,1,1,1])
            f_date = c3.text_input("Date Début (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = c4.number_input("Nombre de jours", min_value=1, value=int(init.get("NbJours", 1)) if init.get("NbJours") else 1)
            f_pass = c5.number_input("Passagers", min_value=1, value=int(float(str(init.get("Passagers") or 1))))
            f_prix = c6.text_input("Total €", value=init.get("PrixJour", "0"))
            
            f_stat = st.selectbox("Statut Dossier", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente") if init.get("Statut") in ["🟡 Attente", "🟢 OK", "🔴 Pas OK"] else "🟡 Attente"))
            
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    datetime.strptime(f_date.strip(), '%d/%m/%Y')
                    new = {
                        "DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(),
                        "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass),
                        "Téléphone": f_tel, "Email": f_mail, "Paye": "Oui" if "🟢" in f_stat else "Non", "Historique": f_his
                    }
                    if idx is not None: df.loc[idx] = new
                    else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    nav("LISTE")
                except: st.error("Format date invalide")
        
        if st.button("🔙 RETOUR", use_container_width=True): nav("LISTE")
        if idx is not None and st.button("🗑️ SUPPRIMER"):
            df = df.drop(index=idx); sauvegarder_data(df, "contacts"); nav("LISTE")

    # --- PLANNING MULTI-JOURS ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"):
            st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1
            st.rerun()
        c2.markdown(f"<h3 style='text-align:center;'>{mois_fr[st.session_state.m_idx-1]}</h3>", unsafe_allow_html=True)
        if c3.button("▶️"):
            st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1
            st.rerun()

        # Construction de la liste des jours occupés
        occu_dates = {}
        for _, r in df[df['Statut'] == "🟢 OK"].iterrows():
            try:
                start = datetime.strptime(r['DateNav'], '%d/%m/%Y')
                jours = int(r['NbJours'] or 1)
                for j in range(jours):
                    d_occ = (start + timedelta(days=j)).strftime('%d/%m/%Y')
                    if d_occ not in occu_dates: occu_dates[d_occ] = []
                    occu_dates[d_occ].append(f"{r['Prénom']} {r['Nom']}")
            except: pass

        cal = calendar.monthcalendar(datetime.now().year, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{datetime.now().year}"
                    est_occupe = d_s in occu_dates
                    if cols[i].button(f"🟢" if est_occupe else str(day), key=f"d_{d_s}", use_container_width=True):
                        if est_occupe:
                            for client in occu_dates[d_s]: st.info(f"⚓ {client}")
                        else: st.write(f"Libre le {d_s}")




















































