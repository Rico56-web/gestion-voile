import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. STYLE CSS ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")
st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 20px; border-bottom: 3px solid #1a2a6c; }
    .fiche-complete { border: 2px solid #1a2a6c; border-radius: 12px; overflow: hidden; margin-bottom: 25px; background-color: white; }
    .zone-infos { padding: 18px; background: white; }
    .zone-actions { padding: 15px; background: #f1f3f6; border-top: 1px solid #1a2a6c; }
    .prenom-style { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; }
    .nom-style { font-size: 1.2rem; text-transform: uppercase; color: #555; }
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; margin: 5px 0; }
    .statut-badge { padding: 4px 10px; border-radius: 15px; font-size: 0.85rem; font-weight: bold; color: white; margin-left: 5px; display: inline-block; }
    .btn-contact { 
        display: inline-block; padding: 8px 15px; border-radius: 5px; 
        text-decoration: none; color: white !important; font-size: 0.9rem; 
        font-weight: bold; margin-right: 10px; margin-top: 12px;
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
        list_statut = ["En attente", "OK", "Refusé"]
        idx_s = list_statut.index(r.get('Statut')) if r.get('Statut') in list_statut else 0
        list_paye = ["Pas payé", "Payé"]
        idx_p = list_paye.index(r.get('Paiement')) if r.get('Paiement') in list_paye else 0

        with st.form("edit_full"):
            st.subheader(f"Détails : {r.get('Prénom','')} {r.get('Nom','')}")
            c1, c2, c3 = st.columns(3)
            u_pre = c1.text_input("Prénom", value=r.get('Prénom',''))
            u_nom = c2.text_input("Nom", value=r.get('Nom',''))
            u_prix = c3.text_input("Prix (€)", value=str(r.get('Prix','0')))
            
            s1, s2, s3 = st.columns(3)
            u_tel = s1.text_input("Téléphone", value=r.get('Téléphone',''))
            u_mail = s2.text_input("Email", value=r.get('Mail',''))
            u_soc = s3.text_input("Société", value=r.get('Société',''))

            st.divider()
            f1, f2 = st.columns(2)
            u_statut = f1.selectbox("Statut Mission", list_statut, index=idx_s)
            u_paiement = f2.selectbox("Paiement", list_paye, index=idx_p)
            u_notes = st.text_area("Notes", value=r.get('Notes',''), height=150)
            
            b1, b2 = st.columns(2)
            if b1.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Prix'] = u_pre, u_nom, to_f(u_prix)
                df.at[idx, 'Téléphone'], df.at[idx, 'Mail'], df.at[idx, 'Société'] = u_tel, u_mail, u_soc
                df.at[idx, 'Statut'], df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = u_statut, u_paiement, u_notes
                sauvegarder_data(df, "contacts.json")
                st.session_state.edit_idx = None; st.rerun()
            if b2.form_submit_button("❌ ANNULER"):
                st.session_state.edit_idx = None; st.rerun()
    else:
        search = st.text_input("🔍 Rechercher...").lower()
        mask = df['Nom'].astype(str).str.lower().str.contains(search, na=False) | \
               df['Prénom'].astype(str).str.lower().str.contains(search, na=False)

        for i, r in df[mask].iterrows():
            tel = str(r.get('Téléphone', '')).strip()
            mail = str(r.get('Mail', '')).strip()
            col_s = {"OK": "#2ecc71", "En attente": "#f1c40f", "Refusé": "#e74c3c"}.get(r.get('Statut'), "#95a5a6")
            col_p = "#2ecc71" if r.get('Paiement') == "Payé" else "#e74c3c"
            
            st.markdown(f"""
            <div class="fiche-complete">
                <div class="zone-infos">
                    <div style="float:right;">
                        <span class="statut-badge" style="background:{col_s};">{r.get('Statut', 'En attente')}</span>
                        <span class="statut-badge" style="background:{col_p};">{r.get('Paiement', 'Pas payé')}</span>
                    </div>
                    <div class="prenom-style">{r.get('Prénom','')} {str(r.get('Nom','')).upper()}</div>
                    <div class="contact-verif">📞 {tel} | ✉️ {mail}</div>
                    <p>🏢 <b>{r.get('Société','')}</b> | 💰 <b>{r.get('Prix', 0)} €</b></p>
                    <div style="margin-top:10px;">
                        <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                        <a href="mailto:{mail}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                        <a href="https://wa.me/{tel.replace(' ','')}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                    </div>
                </div>
                <div class="zone-actions">
            """, unsafe_allow_html=True)
            
            cn, cb = st.columns([0.65, 0.35])
            with cn:
                st.write(f"**Notes :** {r.get('Notes','')}")
            with cb:
                # Bouton Modifier habituel
                if st.button("✏️ MODIFIER", key=f"btn_{i}", use_container_width=True):
                    st.session_state.edit_idx = i; st.rerun()
                
                st.write("---") # Petite séparation
                
                # Zone de suppression compacte
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True, type="secondary"):
                    st.session_state[f"confirm_del_{i}"] = True
                
                # Si on a cliqué sur supprimer, la case apparaît juste en dessous
                if st.session_state.get(f"confirm_del_{i}", False):
                    confirm = st.checkbox("⚠️ Confirmer ?", key=f"chk_{i}")
                    if st.button("Valider la suppression", key=f"final_del_{i}", type="primary", use_container_width=True):
                        if confirm:
                            df = df.drop(i)
                            sauvegarder_data(df, "contacts.json")
                            del st.session_state[f"confirm_del_{i}"]
                            st.rerun()
                        else:
                            st.warning("Cochez la case !")
            
            st.markdown('</div></div>', unsafe_allow_html=True)

# --- 5. PAGE STATS ---
elif st.session_state.page == "STATS":
    st.markdown('<div class="page-title">📊 BILAN FINANCIER 2026</div>', unsafe_allow_html=True)
    if not df.empty:
        acquis = df[(df['Statut']=="OK") & (df['Paiement']=="Payé")]['Prix'].apply(to_f).sum()
        prev = df[(df['Statut']=="En attente") | ((df['Statut']=="OK") & (df['Paiement']=="Pas payé"))]['Prix'].apply(to_f).sum()
        maint = df_maint['Montant'].apply(to_f).sum() if not df_maint.empty else 0.0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 ACQUIS", f"{acquis} €")
        c2.metric("⏳ PRÉVISIONNEL", f"{prev} €")
        c3.metric("🔧 FRAIS", f"{maint} €")
        st.divider()
        st.subheader("Bénéfice estimé (Acquis + Prév. - Frais)")
        st.header(f"{acquis + prev - maint} €")



































































































































































































































































































































































































