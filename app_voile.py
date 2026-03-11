import requests
import base64
import streamlit as st
import pandas as pd
import json
import time

# --- 1. CONFIGURATION & STYLE CSS ---
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

st.markdown("""<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1a2a6c; text-align: center; margin-bottom: 25px; border-bottom: 3px solid #1a2a6c; }
    .page-title { background: #1a2a6c; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    
    .fiche-globale { 
        border: 2px solid #1a2a6c; border-radius: 12px; background-color: white;
        margin-bottom: 35px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow: hidden;
    }
    
    .section-haute { padding: 20px; border-bottom: 1px solid #eee; background: white; }
    .section-basse { padding: 15px; background-color: #f8f9fc; } 
    
    .prenom-style { 
        font-size: 1.7rem; font-weight: bold; color: #1a2a6c; margin: 0; line-height: 1.2;
        word-wrap: break-word; overflow: visible;
    }
    
    .contact-verif { font-family: monospace; color: #e67e22; font-weight: bold; font-size: 1.1rem; margin: 5px 0; }
    .statut-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; color: white; margin-left: 5px; display: inline-block; margin-bottom: 5px; }
    
    .btn-contact { 
        display: inline-block; padding: 8px 14px; border-radius: 6px; 
        text-decoration: none; color: white !important; font-size: 0.9rem; 
        font-weight: bold; margin-right: 8px; margin-top: 10px;
    }
</style>""", unsafe_allow_html=True)

# --- 2. FONCTIONS TECHNIQUES ---
def to_f(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').replace('€', '').replace(' ', '').strip())
    except: return 0.0

def safe_get_index(liste, valeur, par_defaut=0):
    try:
        val_clean = str(valeur).strip().lower()
        for i, item in enumerate(liste):
            if item.lower() == val_clean: return i
        return par_defaut
    except: return par_defaut

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
    requests.put(url, headers={"Authorization": f"token {token}"}, json={"message": "Update Vesta", "content": content, "sha": sha})

# --- 3. NAVIGATION ---
if "page" not in st.session_state: st.session_state.page = "CONTACTS"
if "view_archive" not in st.session_state: st.session_state.view_archive = False
if "edit_idx" not in st.session_state: st.session_state.edit_idx = None

df = charger_data("contacts.json")
df_maint = charger_data("maintenance.json")

st.markdown('<div class="main-header">⚓ VESTA SKIPPER 2026</div>', unsafe_allow_html=True)
m = st.columns(6)
p_config = [("📋 CONTACTS","CONTACTS"), ("💰 STATS","STATS"), ("🔧 MAINT","MAINT")]
for i, (label, p) in enumerate(p_config):
    if m[i].button(label, key=f"nav_{p}", use_container_width=True, type="primary" if st.session_state.page==p else "secondary"):
        st.session_state.page = p; st.session_state.edit_idx = None; st.rerun()

# --- 4. PAGE CONTACTS ---
if st.session_state.page == "CONTACTS":
    
    c_f, c_p = st.columns(2)
    if c_f.button("🚀 MISSIONS FUTURES", use_container_width=True, type="primary" if not st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = False; st.rerun()
    if c_p.button("📁 ARCHIVES (PASSÉES)", use_container_width=True, type="primary" if st.session_state.view_archive else "secondary"):
        st.session_state.view_archive = True; st.rerun()

    st.divider()

    # Liste des statuts incluant "Terminé"
    s_list = ["En attente", "OK", "Terminé", "Refusé"]
    p_list = ["Pas payé", "Payé"]

    if st.session_state.edit_idx is not None:
        idx = st.session_state.edit_idx
        r = df.loc[idx]
        with st.form("edit_form"):
            st.subheader(f"Modifier : {r.get('Prénom','')} {r.get('Nom','')}")
            c1, c2, c3 = st.columns(3)
            u_pre, u_nom, u_soc = c1.text_input("Prénom", r.get('Prénom','')), c2.text_input("Nom", r.get('Nom','')), c3.text_input("Société", r.get('Société',''))
            u_date, u_jours, u_prix = c1.text_input("Date", r.get('Date','')), c2.text_input("Jours", str(r.get('Jours',''))), c3.text_input("Prix total", str(r.get('Prix','0')))
            u_tel, u_mail = c1.text_input("Tél", r.get('Téléphone','')), c2.text_input("Email", r.get('Mail',''))
            
            u_statut = st.selectbox("Statut Mission", s_list, index=safe_get_index(s_list, r.get('Statut')))
            u_paye = st.selectbox("Paiement", p_list, index=safe_get_index(p_list, r.get('Paiement')))
            u_notes = st.text_area("Notes", value=r.get('Notes',''))
            
            if st.form_submit_button("💾 ENREGISTRER"):
                df.at[idx, 'Prénom'], df.at[idx, 'Nom'], df.at[idx, 'Société'] = u_pre, u_nom, u_soc
                df.at[idx, 'Date'], df.at[idx, 'Jours'], df.at[idx, 'Prix'] = u_date, u_jours, to_f(u_prix)
                df.at[idx, 'Téléphone'], df.at[idx, 'Mail'], df.at[idx, 'Statut'] = u_tel, u_mail, u_statut
                df.at[idx, 'Paiement'], df.at[idx, 'Notes'] = u_paye, u_notes
                sauvegarder_data(df, "contacts.json"); st.session_state.edit_idx = None; st.rerun()
            if st.form_submit_button("❌ ANNULER"): st.session_state.edit_idx = None; st.rerun()
    
    else:
        # LOGIQUE DE FILTRAGE : Terminé et Refusé vont en archive
        if st.session_state.view_archive:
            df_display = df[df['Statut'].isin(["Terminé", "Refusé"])]
        else:
            df_display = df[~df['Statut'].isin(["Terminé", "Refusé"])]

        for i, r in df_display.iterrows():
            tel = str(r.get('Téléphone','')).strip()
            s_val, p_val = str(r.get('Statut','')).upper().strip(), str(r.get('Paiement','')).upper().strip()
            
            # Couleurs des badges
            if s_val == "OK": col_s = "#2ecc71"
            elif s_val == "TERMINÉ": col_s = "#3498db" # Bleu pour terminé
            elif s_val == "REFUSÉ": col_s = "#e74c3c"
            else: col_s = "#f1c40f" # Jaune

            # Correction Unpaid et couleur Paiement
            if ("PAY" in p_val) and ("PAS" not in p_val) and ("UN" not in p_val):
                col_p, txt_p = "#2ecc71", "Payé"
            else:
                col_p, txt_p = "#e74c3c", "Pas payé"

            tel_clean = tel.replace(' ', '').replace('-', '').replace('+', '')

            st.markdown(f"""
            <div class="fiche-globale">
                <div class="section-haute">
                    <div style="float:right; text-align:right;">
                        <span class="statut-badge" style="background:{col_s};">{r.get('Statut','En attente')}</span><br>
                        <span class="statut-badge" style="background:{col_p};">{txt_p}</span>
                    </div>
                    <div class="prenom-style">{r.get('Prénom','')} {str(r.get('Nom','')).upper()}</div>
                    <div class="contact-verif">📞 {tel} | ✉️ {str(r.get('Mail',''))}</div>
                    <p style="margin-top:10px; font-size:1.1rem;">
                        📅 <b>{r.get('Date','--')}</b> ({r.get('Jours','?')} j.) | 🏢 <b>{r.get('Société','')}</b> | 💰 <b>{r.get('Prix',0)} €</b>
                    </p>
                    <a href="tel:{tel}" class="btn-contact" style="background:#3498db;">📞 Appeler</a>
                    <a href="mailto:{r.get('Mail','')}" class="btn-contact" style="background:#e67e22;">✉️ Email</a>
                    <a href="https://wa.me/{tel_clean}" class="btn-contact" style="background:#25D366;">💬 WhatsApp</a>
                </div>
                <div class="section-basse">
            """, unsafe_allow_html=True)
            
            c_notes, c_btns = st.columns([0.65, 0.35])
            c_notes.write(f"**Notes :** {r.get('Notes','')}")
            with c_btns:
                if st.button("✏️ MODIFIER", key=f"ed_{i}", use_container_width=True):
                    st.session_state.edit_idx = i; st.rerun()
                if st.button("🗑️ SUPPRIMER", key=f"del_{i}", use_container_width=True):
                    st.session_state[f"ask_del_{i}"] = True
                if st.session_state.get(f"ask_del_{i}"):
                    if st.checkbox("Confirmer ?", key=f"chk_{i}"):
                        if st.button("Valider", key=f"fdel_{i}", type="primary", use_container_width=True):
                            df = df.drop(i); sauvegarder_data(df, "contacts.json"); st.rerun()
            st.markdown('</div></div>', unsafe_allow_html=True)













































































































































































































































































































































































































