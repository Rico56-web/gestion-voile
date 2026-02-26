import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime, timedelta
import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Vesta Skipper", layout="wide")

# --- FONCTIONS GITHUB (SÉCURISÉES) ---
@st.cache_data(ttl=2) # Cache ultra-court pour voir les modifs instantanément
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
    data = {"message": "Vesta Fix Juin", "content": content_b64, "sha": sha} if sha else {"message": "Update", "content": content_b64}
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
    
    # Barre de Navigation
    m1, m2, m3 = st.columns(3)
    if m1.button("📋 LISTE", use_container_width=True): nav("LISTE")
    if m2.button("🗓️ PLANNING", use_container_width=True): nav("CALENDRIER")
    if m3.button("➕ NOUVEAU", use_container_width=True): nav("FORM")
    st.markdown("---")

    # --- LISTE ---
    if st.session_state.page == "LISTE":
        st.write(f"**Total : {len(df)} fiches**")
        df['sort_key'] = df['DateNav'].apply(lambda x: "".join(reversed(str(x).replace(" ","").split('/'))) if '/' in str(x) else "0")
        sub_df = df.sort_values('sort_key', ascending=False)
        for idx, r in sub_df.iterrows():
            st.markdown(f"**{r['Statut']} {r['Prénom']} {r['Nom']}** - {r['DateNav']}")
            if st.button(f"Ouvrir {r['Prénom']} {r['Nom']}", key=f"btn_{idx}", use_container_width=True):
                st.session_state.edit_idx = idx
                st.session_state.page = "FORM"
                st.rerun()

    # --- FORMULAIRE ---
    elif st.session_state.page == "FORM":
        idx = st.session_state.get("edit_idx")
        init = df.loc[idx].to_dict() if idx is not None else {c: "" for c in cols_base}
        with st.form("f_v7"):
            f_stat = st.selectbox("STATUT", ["🟡 Attente", "🟢 OK", "🔴 Pas OK"], index=["🟡 Attente", "🟢 OK", "🔴 Pas OK"].index(init.get("Statut", "🟡 Attente")))
            f_nom = st.text_input("NOM", value=init.get("Nom", ""))
            f_pre = st.text_input("Prénom", value=init.get("Prénom", ""))
            f_date = st.text_input("Date (JJ/MM/AAAA)", value=init.get("DateNav", ""))
            f_nbj = st.number_input("Nb Jours", min_value=1, value=int(init.get("NbJours", 1)) if init.get("NbJours") else 1)
            f_pass = st.number_input("Passagers", min_value=1, value=int(float(str(init.get("Passagers") or 1))))
            f_tel = st.text_input("Tel", value=init.get("Téléphone", ""))
            f_mail = st.text_input("Email", value=init.get("Email", ""))
            if st.form_submit_button("SAUVEGARDER"):
                new = {"DateNav": f_date.strip(), "NbJours": str(f_nbj), "Nom": f_nom.upper(), "Prénom": f_pre.capitalize(), "Statut": f_stat, "PrixJour": init.get("PrixJour","0"), "Passagers": str(f_pass), "Téléphone": f_tel, "Email": f_mail, "Paye": "Oui", "Historique": init.get("Historique","")}
                if idx is not None: df.loc[idx] = new
                else: df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                sauvegarder_data(df, "contacts")
                nav("LISTE")
        if st.button("RETOUR"): nav("LISTE")

    # --- CALENDRIER (FIX JUIN) ---
    elif st.session_state.page == "CALENDRIER":
        mois_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        c1, c2, c3 = st.columns([1,2,1])
        if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
        c2.markdown(f"<h3 style='text-align:center;'>{mois_fr[st.session_state.m_idx-1]}</h3>", unsafe_allow_html=True)
        if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

        # Logique de scan ultra-précise
        occu = {} 
        for _, r in df.iterrows():
            try:
                # Nettoyage de la date (enlève espaces éventuels)
                d_clean = str(r['DateNav']).strip().replace(" ", "")
                start = datetime.strptime(d_clean, '%d/%m/%Y')
                for j in range(int(r.get('NbJours', 1))):
                    d_c = (start + timedelta(days=j)).strftime('%d/%m/%Y')
                    if d_c not in occu: occu[d_c] = []
                    occu[d_c].append(r)
            except: pass

        cal = calendar.monthcalendar(datetime.now().year, st.session_state.m_idx)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day != 0:
                    d_s = f"{day:02d}/{st.session_state.m_idx:02d}/{datetime.now().year}"
                    btn_label = str(day)
                    if d_s in occu:
                        # Si au moins un est OK -> Vert, sinon Jaune
                        if any("🟢" in str(x['Statut']) for x in occu[d_s]): btn_label = "🟢"
                        else: btn_label = "🟡"
                    
                    if cols[i].button(btn_label, key=f"d_{d_s}", use_container_width=True):
                        if d_s in occu:
                            for res in occu[d_s]:
                                st.info(f"{res['Statut']} {res['Prénom']} {res['Nom']}")
                                st.write("👤" * int(float(str(res.get('Passagers', 1)))))
                        else: st.write("Libre")




















































