import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# Style CSS : Retour au design "Premium" mais léger pour iOS
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

# --- FONCTIONS GITHUB (Optimisées) ---
@st.cache_data(ttl=60)
def charger_data_vesta(nom_fichier, colonnes):
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

def sauvegarder_data_vesta(df, nom_fichier):
    repo = st.secrets["GITHUB_REPO"]
    token = st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{nom_fichier}.json"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    sha = res.json().get('sha') if res.status_code == 200 else None
    
    cols_s = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    json_d = df[cols_s].to_json(orient="records", indent=4, force_ascii=False)
    content_b64 = base64.b64encode(json_d.encode('utf-8')).decode('utf-8')
    data = {"message": "Vesta Update", "content": content_b64, "sha": sha} if sha else {"message": "Update", "content": content_b64}
    
    requests.put(url, headers=headers, json=data)
    st.cache_data.clear()

# --- INITIALISATION ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "page" not in st.session_state: st.session_state.page = "LISTE"
if "m_idx" not in st.session_state: st.session_state.m_idx = datetime.now().month

def nav(p):
    if "edit_idx" in st.session_state: del st.session_state.edit_idx
    st.session_state.page = p
    st.rerun()

# --- AUTH ---
if not st.session_state.authenticated:
    st.title("⚓ Accès Vesta")
    pwd = st.text_input("Code Skipper", type="password")
    if pwd == st.secrets["PASSWORD"]:
        st.session_state.authenticated = True
        st.rerun()
else:
    cols_base = ["DateNav", "Statut", "Nom", "Prénom", "Téléphone", "Email", "Paye", "PrixJour", "Passagers", "Historique"]
    df = charger_data_vesta("contacts", cols_base)
    
    # Menu Navigation
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if m2.button("🗓️ PLAN", use_container_width=True): nav("CALENDRIER")
    if m3.button("➕ NEW", use_container_width=True): nav("FORM")
    if m4.button("✅ CHECK", use_container_width=True): nav("CHECK")
    st.markdown("---")

    # --- PAGE LISTE (VISUEL COMPLET) ---
    if st.session_state.page == "LISTE":
        search = st.text_input("🔍 Rechercher un nom...")
        tab1, tab2 = st.tabs(["🚀 PROCHAINES", "📂 ARCHIVES"])
        
        # Tri intelligent par date
        df['sort_key'] = df['DateNav'].apply(lambda x: "".join(reversed(x.split('/'))) if '/' in str(x) else "0")
        auj = datetime.now().strftime('%Y%m%d')

        def afficher_cartes(df_tab):
            if df_tab.empty: st.info("Aucune fiche.")
            for idx, r in df_tab.iterrows():
                cl = "status-ok" if "🟢" in str(r['Statut']) else "status-attente" if "🟡" in str(r['Statut']) else "status-non"
                st.markdown(f"""
                <div class="client-card {cl}">
                    <span class="price-tag">{r['PrixJour']}€</span>
                    <b>{r['Nom']} {r['Prénom']}</b><br>
                    <small>📅 {r['DateNav']} | 👤 {r['Passagers']} pers.</small><br>
                    <div style="margin-top:5px;">
                        <span class="badge">📞 {r['Téléphone']}</span>
                        <span class="badge">✉️ {r['Email']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Modifier {r['Nom']}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.edit_idx = idx; st.session_state.page = "FORM"; st.rerun()

        with tab1:
            f_df = df[df['sort_key'] >= auj].sort_values('sort_key')
            if search: f_df = f_df[f_df['Nom'].str.contains(search, case=False)]
            afficher_cartes(f_df)
        with tab2:
            p_df = df[df['sort_key'] < auj].sort_values('sort_key', ascending=False).head(15)
            afficher_cartes(p_df)

    # --- PAGE FORMULAIRE (COMPLET) ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        
        with st.form("form_complet"):
            st.subheader("Détails de la fiche")
            c1, c2 = st.columns(2)
            f_nom = c1.text_input("NOM", value=init.get("Nom", ""))
            f_pre = c2.text_input("Prénom", value=init.get("Prénom", ""))
            f_tel = c1.text_input("Téléphone", value=init.get("Téléphone", ""))
            f_mail = c2.text_input("Email", value=init.get("Email", ""))
            
            st.markdown("---")
            c3, c4, c5 = st.columns([2,1,1])
            f_date = c3.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_pass = c4.number_input("Passagers", min_value=1, value=1 if not init.get("Passagers") else int(float(str(init.get("Passagers")).replace(',','.'))))
            f_prix = c5.text_input("Forfait €", value=init.get("PrixJour", "0"))
            
            f_stat = st.selectbox("Statut", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], 
                                  index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_his = st.text_area("Notes / Historique", value=init.get("Historique", ""))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                try:
                    datetime.strptime(f_date.strip(), '%d/%m/%Y')
                    new_data = {
                        "DateNav": f_date.strip(), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(),
                        "Statut": f_stat, "PrixJour": f_prix, "Passagers": str(f_pass),
                        "Téléphone": f_tel, "Email": f_mail, "Paye": "Oui" if "🟢" in f_stat else "Non", "Historique": f_his
                    }
                    if idx is not None: df.loc[idx] = new_data
                    else: df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
                    sauvegarder_data_vesta(df, "contacts")
                    nav("LISTE")
                except: st.error("Format date invalide (JJ/MM/AAAA)")
        
        c_del, c_ret = st.columns(2)
        if c_del.button("🗑️ SUPPRIMER LA FICHE", use_container_width=True) and idx is not None:
            df = df.drop(index=idx)
            sauvegarder_data_vesta(df, "contacts")
            nav("LISTE")
        if c_ret.button("🔙 ANNULER / RETOUR", use_container_width=True): nav("LISTE")

    # --- PLANNING (BOUTONS NAV SANS CLAVIER) ---
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

        cal = calendar.monthcalendar(datetime.now().year, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{datetime.now().year}"
                    occ = df[(df['DateNav'] == d_s) & (df['Statut'] == "🟢 OK")]
                    txt = f"🟢" if not occ.empty else str(day)
                    if cols[i].button(txt, key=f"d_{d_s}", use_container_width=True):
                        if not occ.empty:
                            for _, r in occ.iterrows(): st.info(f"⚓ {r['Nom']} - {r['Téléphone']}")
                        else: st.write(f"Libre le {d_s}")

    # --- CHECKLIST ---
    elif st.session_state.page == "CHECK":
        st.subheader("✅ Checklist Skipper")
        for item in ["Vannes", "Niveaux Moteur", "Gilets", "Gaz", "Briefing Passagers"]:
            st.checkbox(item, key=f"ch_{item}")
            



















































