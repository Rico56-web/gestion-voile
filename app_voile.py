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
    }
    .status-ok { border-left-color: #2ecc71 !important; }
    .status-attente { border-left-color: #f1c40f !important; }
    .status-non { border-left-color: #e74c3c !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS GITHUB ---
@st.cache_data(ttl=10) # Cache réduit à 10s pour voir les changements direct
def charger_data_v4(nom_fichier, colonnes):
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

# --- NAVIGATION ---
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
    df = charger_data_v4("contacts", cols_base)
    
    # Menu principal
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if m2.button("🗓️ PLAN", use_container_width=True): nav("CALENDRIER")
    if m3.button("➕ NEW", use_container_width=True): nav("FORM")
    if m4.button("✅ CHECK", use_container_width=True): nav("CHECK")
    st.markdown("---")

    # --- LISTE ---
    if st.session_state.page == "LISTE":
        st.info(f"Nombre de fiches : {len(df)}")
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        df['sort_key'] = df['DateNav'].apply(lambda x: "".join(reversed(x.split('/'))) if '/' in str(x) else "0")
        auj = datetime.now().strftime('%Y%m%d')

        def afficher_cartes(df_tab):
            for idx, r in df_tab.iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                st.markdown(f'<div class="client-card {cl}"><b>{r["Nom"]} {r["Prénom"]}</b><br><small>📅 {r["DateNav"]} ({r.get("NbJours",1)}j)</small></div>', unsafe_allow_html=True)
                if st.button(f"Modifier {r['Prénom']} {r['Nom']}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1:
            afficher_cartes(df[df['sort_key'] >= auj].sort_values('sort_key'))
        with tab2:
            afficher_cartes(df[df['sort_key'] < auj].sort_values('sort_key', ascending=False).head(10))

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("form_final"):
            st.subheader("📝 Détails Navigation")
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            c1, c2, c3 = st.columns([2,1,1])
            f_date = c1.text_input("Date Début (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = c2.number_input("Nb Jours", min_value=1, value=int(init.get("NbJours", 1)) if init.get("NbJours") else 1)
            f_pass = c3.number_input("Pers.", min_value=1, value=int(float(str(init.get("Passagers") or 1))))
            
            # MENU STATUT (IMPORTANT)
            f_stat = st.selectbox("STATUT DU DOSSIER", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            
            f_tel = st.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_prix = st.text_input("Total €", value=init.get("PrixJour", "0"))
            f_his = st.text_area("Notes", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    datetime.strptime(f_date.strip(), '%d/%m/%Y')
                    new_rec = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(), "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass), "Téléphone": f_tel, "Email": init.get("Email",""), "Paye": "Oui", "Historique": f_his}
                    if idx is not None: df.loc[idx] = new_rec
                    else: df = pd.concat([df, pd.DataFrame([new_rec])], ignore_index=True)
                    sauvegarder_data(df, "contacts")
                    nav("LISTE")
                except: st.error("Date invalide")
        if st.button("🔙 RETOUR"): nav("LISTE")

    # --- PLANNING COULEURS (JAUNE & VERT) ---
    elif st.session_state.page == "CALENDRIER":
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
        c2.markdown(f"<h3 style='text-align:center;'>Mois {st.session_state.m_idx}</h3>", unsafe_allow_html=True)
        if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

        # Liste des jours colorés
        greens = []
        yellows = []
        for _, r in df.iterrows():
            try:
                start = datetime.strptime(r['DateNav'], '%d/%m/%Y')
                for j in range(int(r.get('NbJours', 1))):
                    d_c = (start + timedelta(days=j)).strftime('%d/%m/%Y')
                    if "🟢" in r['Statut']: greens.append(d_cur)
                    if "🟡" in r['Statut']: yellows.append(d_cur)
            except: pass

        cal = calendar.monthcalendar(datetime.now().year, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{datetime.now().year}"
                    # Logique de couleur
                    ico = str(day)
                    if d_s in greens: ico = "🟢"
                    elif d_s in yellows: ico = "🟡"
                    
                    if cols[i].button(ico, key=f"d_{d_s}", use_container_width=True):
                        st.write(f"Détails du {d_s} :")
                        # Afficher qui est là
                        for _, r in df.iterrows():
                            # (Vérification si le jour d_s tombe dans la plage du client r)
                            try:
                                sd = datetime.strptime(r['DateNav'], '%d/%m/%Y')
                                ed = sd + timedelta(days=int(r.get('NbJours', 1))-1)
                                target = datetime.strptime(d_s, '%d/%m/%Y')
                                if sd <= target <= ed:
                                    st.info(f"{r['Statut']} {r['Prénom']} {r['Nom']}")
                            except: pass





















































