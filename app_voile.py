import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. STYLE CSS (BOÎTE UNIQUE) ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    
    /* LA FICHE ENTIÈRE */
    .fiche-globale { 
        border: 2px solid #1a2a6c; 
        border-radius: 12px; 
        background-color: white;
        margin-bottom: 35px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        overflow: hidden;
    }
    
    .section-haute { padding: 20px; border-bottom: 1px solid #eee; }
    .section-basse { padding: 15px; background-color: #f8f9fc; } /* Zone notes et boutons */
    
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; margin: 0; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; }
    .statut-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; color: white; margin-left: 5px; }
    
    .btn-contact { 
        display: inline-block; padding: 8px 14px; border-radius: 6px; 
        text-decoration: none; color: white !important; font-size: 0.9rem; 
        font-weight: bold; margin-right: 8px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS ---
def to_f(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace('€', '').replace(' ', '').strip())
    except: return 0.0

def charger_data(file):
    try:
        repo, token = st.secrets["GITHUB_REPO"], st.secrets["GITHUB_TOKEN"]
        url = f"https://api.github.com/repos/{repo}/contents/{file}"
        res = requests.get(url, headers={"Authorization": f"token {token}"}, params={"v": time.time()})
        if res.status_code == 200:
            df = pd.DataFrame(json.loads(base64.b64decode(res.json()['content']).decode('utf-8')))
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

# --- 3. NAVIGATION ---
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
    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {r.get('Prénom','')} {r.get('Nom','')}")
            c1, c2, c3 = st.columns(3)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_prix = c3.text_input("Prix", value=str(r.get('Prix','0')))
            u_tel = c1.text_input("Téléphone", value=r.get('Téléphone',''))
            u_mail = c2.text_input("Email", value=r.get('Mail',''))
            u_soc = c3.text_input("Société", value=r.get('Société',''))
            u_statut = st.selectbox("Statut", ["En attente", "OK", "Refusé"], index=["En attente", "OK", "Refusé"].index(r.get('Statut', 'En attente')))
            u_paye = st.selectbox("Paiement", ["Pas payé", "Payé"], index=["Pas payé", "Payé"].index(r.get('Paiement', 'Pas payé')))
            u_notes = st.text_area("Notes", value=r.get('Notes',''))
            if st.form_submit_button("SAUVEGARDER"):
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Prix'] = u_pre, u_nom, to_f(u_prix)
                df.at[idx, 'Téléphone'], df.at[idx, 'Mail'], df.at[idx, 'Société'] = u_tel, u_mail, u_soc
                df.at[idx, 'Statut'], df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = u_statut, u_paye, u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("ANNULER"): st.session_state.edit_idx = None; st.rerun()
    else:
        for i, r in df.iterrows():
            tel, mail = str(r.get('Téléphone','')).strip(), str(r.get('Mail','')).strip()
            col_s = {"OK": "#2ecc71", "En attente": "#f1c40f", "Refusé": "#e74c3c"}.get(r.get('Statut'), "#95a5a6")
            col_p = "#2ecc71" if r.get('Paiement') == "Payé" else "#e74c3c"
            
            # --- OUVERTURE DE LA FICHE ---
            st.markdown(f"""
            <div class="fiche-globale">
                <div class="section-haute">
                    <div style="float:right;">
                        <span class="statut-badge" style="background:{col_s};">{r.get('Statut','En attente')}</span>
                        <span class="statut-badge" style="background:{col_p};">{r.get('Paiement','Pas payé')}</span>
                    </div>
                    <div class="prenom-style">{r.get('Prénom','')} {str(r.get('Nom','')).upper()}</div>
                    <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                    <p style="margin-top:10px;">🏢 <b>{r.get('Société','')}</b> | 💰 <b>{r.get('Prix',0)} €</b></p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                    <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                    <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                </div>
                <div class="section-basse">
            """, unsafe_allow_html=True)
            
            # --- CONTENU STREAMLIT (DANS LA SECTION BASSE) ---
            cn, cb = st.columns([0.65, 0.35])
            cn.write(f"**Notes :** {r.get('Notes','')}")
            with cb:
                if st.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                    st.session_state.edit_idx = i; st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    st.session_state[f"conf_{i}"] = True
                
                if st.session_state.get(f"conf_{i}"):
                    if st.checkbox("Confirmer ?", key=f"chk_{i}"):
                        if st.button("Valider", key=f"fdel_{i}", type="primary", use_container_width=True):
                            df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()
            
            # --- FERMETURE DE LA FICHE ---
            st.markdown('</div></div>', unsafe_allow_html=True)

# --- 5. PAGE MAINTENANCE (Même Structure) ---
elif st.session_state.page == "MAINT":
    st.markdown('<div class="page-title">🔧 REGISTRE DE MAINTENANCE</div>', unsafe_allow_html=True)
    # (Formulaire d'ajout identique...)
    for i, r in df_maint.iterrows():
        st.markdown(f"""<div class="fiche-globale"><div class="section-haute">
                <div class="prenom-style">{r.get('Objet','')}</div>
                <div class="contact-verif">📅 {r.get('Date','')} | 💰 {r.get('Montant',0)} €</div>
            </div><div class="section-basse">""", unsafe_allow_html=True)
        cn, cb = st.columns([0.65, 0.35])
        cn.write("Dépense liée à l'entretien du Vesta.")
        if cb.button("🗑️ SUPPRIMER", key=f"dm_{i}", use_container_width=True):
            df_maint = df_maint.drop(i); sauvegarder_data(df_maint, "maintenance.json"); st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

# --- 6. PAGE STATS ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 BILAN FINANCIER 2026</div>', unsafe_allow_html=True)
    acquis = df[(df['Statut']=="OK") & (df['Paiement']=="Payé")]['Prix'].apply(to_f).sum()
    prev = df[(df['Statut']=="En attente") | ((df['Statut']=="OK") & (df['Paiement']=="Pas payé"))]['Prix'].apply(to_f).sum()
    maint = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 ACQUIS", f"{acquis} €")
    c2.metric("⏳ PRÉVISIONNEL", f"{prev} €")
    c3.metric("🔧 FRAIS", f"{maint} €")
    st.divider()
    st.header(f"Bénéfice estimé : {acquis + prev - maint} €")





































































































































































































































































































































































































