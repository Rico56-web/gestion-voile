import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; }
    .fiche-complete { border: 2px solid #1a2a6c; border-radius: 12px; overflow: hidden; margin-bottom: 25px; background-color: white; }
    .zone-infos { padding: 18px; background: white; }
    .zone-actions { padding: 15px; background: #f1f3f6; border-top: 1px solid #1a2a6c; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; margin: 5px 0; }
    .btn-contact { display: inline-block; padding: 8px 15px; border-radius: 5px; text-decoration: none; color: white !important; font-size: 0.9rem; font-weight: bold; margin-right: 10px; margin-top: 10px; }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS DE NETTOYAGE & GITHUB ---
def to_f(val):
    """ Nettoie la saisie (ex: '150,50 €' -> 150.5) pour éviter les '0' """
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        s = str(val).replace(',', '.').replace('€', '').replace(' ', '').strip()
        return float(s)
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
            # Nettoyage automatique des noms de colonnes (espaces invisibles)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        return pd.DataFrame()
    except: return pd.DataFrame()

def sauvegarder_data(df, file):
    repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/contents/{file}"
    res = requests.get(url, headers={"Authorization": f"token {token}"})
    sha = res.json().get('sha') if res.status_code == 200 else None
    content = base64.b64encode(df.to_json(orient="records", indent=4).encode('utf-8')).decode('utf-8')
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update", "content": content, "sha": sha})

# --- 3. INITIALISATION & NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

st.markdown('<div class="main-header">⚓ SKIPPER VESTA 2026</div>', unsafe_allow_html=True)

m = st.columns(6)
pages = [("📋 CONTACTS","CONTACTS"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(pages):
    if m[i].button(label, use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.session_state.edit_idx = None; st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":

    # --- MODE ÉDITION (DÉTAILS) ---
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        st.subheader(f"📝 Modification : {r['Prénom']} {r['Nom']}")
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_tel = c1.text_input("Téléphone", value=r.get('Téléphone',''))
            u_mail = c2.text_input("Email", value=r.get('Mail',''))
            u_soc = c1.text_input("Société", value=r.get('Société',''))
            # On affiche le prix tel quel pour modification
            u_prix = c2.text_input("Prix (€)", value=str(r.get('Prix','0')))
            u_notes = st.text_area("Notes / Livre de bord", value=r.get('Notes',''), height=150)
            
            b_save, b_cancel = st.columns(2)
            if b_save.form_submit_button("💾 SAUVEGARDER"):
                # On applique to_f ICI avant de sauvegarder pour garantir un nombre
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'] = u_pre, u_nom
                df.at[idx, 'Téléphone'], df.at[idx, 'Mail'] = u_tel, u_mail
                df.at[idx, 'Société'], df.at[idx, 'Notes'] = u_soc, u_notes
                df.at[idx, 'Prix'] = to_f(u_prix) 
                
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None; st.success("Enregistré !"); time.sleep(0.5); st.rerun()
            if b_cancel.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None; st.rerun()

    # --- MODE AFFICHAGE LISTE ---
    else:
        search = st.text_input("🔍 Rechercher un contact...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            val_prix = to_f(r.get('Prix', 0)) # Sécurité affichage
            
            st.markdown(f"""
            <div class="fiche-complete">
                <div class="zone-infos">
                    <div class="prenom-style">{r['Prénom']}</div>
                    <div class="nom-style">{str(r['Nom']).upper()}</div>
                    <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                    <p style="margin-top:10px;">🏢 <b>{r.get('Société','')}</b> | 💰 <b>{val_prix} €</b></p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">WhatsApp</a>
                </div>
                <div class="zone-actions">
            """, unsafe_allow_html=True)
            
            c_notes, c_btns = st.columns([0.7, 0.3])
            with c_notes:
                st.markdown(f"**Notes :** \n{r.get('Notes', '*(Vide)*')}")
            with c_btns:
                if st.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                    st.session_state.edit_idx = i; st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    if st.checkbox("Confirmer ?", key=f"chk_{i}"):
                        df = df.drop(i)
                        sauvegarder_data(df, "contacts.json")
                        st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)

# --- 5. PAGE STATS ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 RÉSULTAT NET</div>', unsafe_allow_html=True)
    if not df.empty:
        # On force le nettoyage sur toute la colonne pour le calcul
        total_ca = df['Prix'].apply(to_f).sum()
        total_maint = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("CA TOTAL", f"{total_ca} €")
        c2.metric("MAINTENANCE", f"{total_maint} €")
        c3.metric("NET", f"{total_ca - total_maint} €")
    else:
        st.write("Aucune donnée disponible.")































































































































































































































































































































































































