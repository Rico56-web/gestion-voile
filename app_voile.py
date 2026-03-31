import streamlit as st
import pandas as pd
import pandas.io.json as pdjson
import os
import json
from datetime import datetime
import time

# =================================================================
# --- 1. CONFIGURATION & CHARGEMENT ---
# =================================================================
st.set_page_config(page_title="Vesta Skipper 2026", layout="wide")

def charger_data(fichier):
    if os.path.exists(fichier):
        with open(fichier, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return pd.DataFrame(data)
    return pd.DataFrame()

def sauvegarder_data(df, fichier):
    df.to_json(fichier, orient='records', force_ascii=False, indent=4)

# Initialisation des données
df_c = charger_data('contacts.json')

if 'page' not in st.session_state:
    st.session_state.page = "CONTACTS"

# Style Global pour mobile
st.markdown("""
    <style>
    .main-header { font-size: 24px; font-weight: bold; color: #1a2a6c; margin-bottom: 20px; text-align: center; }
    .stButton>button { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# =================================================================
# --- 2. LOGIQUE DE NAVIGATION ---
# =================================================================

# --- PAGE : MODIFIER_CONTACT (Formulaire) ---
if st.session_state.page == "MODIFIER_CONTACT":
    idx = st.session_state.get('id_a_modifier')
    if idx is not None:
        ligne = df_c.loc[idx]
        st.markdown(f"### 📝 Modifier : {ligne['Prénom']} {ligne['Nom']}")
        
        with st.form("form_edit"):
            c1, c2 = st.columns(2)
            new_nom = c1.text_input("Nom", value=ligne['Nom'])
            new_pre = c2.text_input("Prénom", value=ligne['Prénom'])
            
            new_soc = st.selectbox("Société", ["CMN", "PARTICULIER", "CLICK", "VOG", "AUTRE"], 
                                   index=0 if "CMN" in str(ligne['Société']).upper() else 1)
            
            c3, c4 = st.columns(2)
            new_tel = c3.text_input("Téléphone", value=ligne['Téléphone'])
            new_mai = c4.text_input("Email", value=ligne['Email'])
            
            c5, c6 = st.columns(2)
            new_dat = c5.text_input("Date (JJ/MM/AAAA)", value=ligne['DateNav'])
            new_pri = c6.number_input("Prix (€)", value=float(ligne['Prix']))
            
            c7, c8, c9 = st.columns(3)
            new_sta = c7.selectbox("Statut", ["OK", "En attente", "Refusé", "Terminé"], 
                                   index=0 if "OK" in str(ligne['Statut']).upper() else 1)
            new_pay = c8.selectbox("Paiement", ["À payer", "Payé"], 
                                   index=1 if "PAY" in str(ligne['Paiement']).upper() else 0)
            new_per = c9.number_input("Nb Pers", value=int(float(ligne.get('NbrePers', 1))))

            if st.form_submit_button("💾 ENREGISTRER"):
                df_c.at[idx, 'Nom'] = new_nom
                df_c.at[idx, 'Prénom'] = new_pre
                df_c.at[idx, 'Société'] = new_soc
                df_c.at[idx, 'Téléphone'] = new_tel
                df_c.at[idx, 'Email'] = new_mai
                df_c.at[idx, 'DateNav'] = new_dat
                df_c.at[idx, 'Prix'] = new_pri
                df_c.at[idx, 'Statut'] = new_sta
                df_c.at[idx, 'Paiement'] = new_pay
                df_c.at[idx, 'NbrePers'] = new_per
                sauvegarder_data(df_c, "contacts.json")
                st.success("Modifié !")
                st.session_state.page = "CONTACTS"
                st.rerun()
        if st.button("⬅️ Retour"):
            st.session_state.page = "CONTACTS"
            st.rerun()

# --- PAGE : CONTACTS (LISTE & RECHERCHE) ---
elif st.session_state.page == "CONTACTS":
    st.markdown('<div class="main-header">📇 RÉPERTOIRE & PLANNING</div>', unsafe_allow_html=True)

    # --- RECHERCHE ---
    with st.expander("🔍 FILTRER LES CONTACTS", expanded=False):
        cs1, cs2 = st.columns(2)
        search_nom = cs1.text_input("👤 Nom", value="")
        search_soc = cs2.text_input("🏢 Société", value="")
        if st.button("🔄 RÉINITIALISER", use_container_width=True):
            st.rerun()

    # --- PRÉPARATION & TRI CHRONOLOGIQUE ---
    df_view = df_c.copy()
    # Conversion date pour le tri (format JJ/MM/AAAA)
    df_view['DateSort'] = pd.to_datetime(df_view['DateNav'], dayfirst=True, errors='coerce')
    df_view = df_view.sort_values(by='DateSort', ascending=True)

    # Filtrage
    if search_nom:
        df_view = df_view[df_view['Nom'].str.contains(search_nom, case=False, na=False) | 
                         df_view['Prénom'].str.contains(search_nom, case=False, na=False)]
    if search_soc:
        df_view = df_view[df_view['Société'].str.contains(search_soc, case=False, na=False)]

    # --- AFFICHAGE ---
    for i, r in df_view.iterrows():
        # Variables propres
        nom_complet = f"{str(r.get('Prénom','')).capitalize()} {str(r.get('Nom','')).upper()}"
        soc = str(r.get('Société','PARTICULIER')).upper()
        tel = str(r.get('Téléphone','')).strip().replace(' ', '').replace('.','')
        mail = str(r.get('Email','')).strip()
        
        # Statut & Couleurs
        statut = str(r.get('Statut','En attente')).upper()
        st_col = "#2ecc71" if ("OK" in statut or "TERM" in statut) else "#f1c40f" if "ATTENTE" in statut else "#e74c3c" if "REFUS" in statut else "#95a5a6"
        
        paiement = str(r.get('Paiement','À PAYER')).upper()
        pay_col = "#2ecc71" if "PAY" in paiement and "NON" not in paiement else "#e67e22"
        pay_lab = "✅ PAYÉ" if "PAY" in paiement and "NON" not in paiement else "⏳ À PAYER"

        # --- FICHE HTML ---
        card_html = f"""
        <div style="border: 1px solid #ddd; border-left: 12px solid {'#0056b3' if 'CMN' in soc else '#1a2a6c'}; 
                    padding: 15px; border-radius: 15px; background: white; margin-bottom: 5px; box-shadow: 0px 4px 8px rgba(0,0,0,0.1); color: black;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="color: #666; font-weight: bold; font-size: 0.75rem;">🏢 {soc}</div>
                <div style="text-align: right;">
                    <div style="background: {pay_col}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.6rem; font-weight: bold; margin-bottom: 4px;">{pay_lab}</div>
                    <div style="background: {st_col}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.6rem; font-weight: bold;">{statut}</div>
                </div>
            </div>
            <div style="font-size: 1.2rem; font-weight: bold; margin-bottom: 12px; color: #1a2a6c;">{nom_complet}</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background: #f8f9fa; padding: 10px; border-radius: 10px; font-size: 0.85rem;">
                <div>📅 <b>{r.get('DateNav','-')}</b></div>
                <div>💰 <b>{r.get('Prix','0')} €</b></div>
                <div>⛵ <b>{int(float(r.get('NbreJours',1)))} j.</b></div>
                <div>👥 <b>{r.get('NbrePers','-')} pers.</b></div>
            </div>
            <div style="margin-top: 10px; font-size: 0.85rem; color: #444;">
                📞 {r.get('Téléphone','-')} | ✉️ {mail if mail not in ['nan','','None'] else '-'}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # --- ACTIONS ---
        c1, c2, c3 = st.columns(3)
        if len(tel) > 5:
            c1.markdown(f'<a href="tel:{tel}" style="text-decoration:none;"><div style="background:#2ecc71; color:white; padding:10px 2px; border-radius:8px; text-align:center; font-weight:bold; font-size:0.65rem;">📞 APPEL</div></a>', unsafe_allow_html=True)
            wa_n = tel if not tel.startswith('0') else "33" + tel[1:]
            c2.markdown(f'<a href="https://wa.me/{wa_n}" style="text-decoration:none;"><div style="background:#25D366; color:white; padding:10px 2px; border-radius:8px; text-align:center; font-weight:bold; font-size:0.65rem;">💬 WA</div></a>', unsafe_allow_html=True)
        if mail not in ['nan','','None']:
            c3.markdown(f'<a href="mailto:{mail}" style="text-decoration:none;"><div style="background:#3498db; color:white; padding:10px 2px; border-radius:8px; text-align:center; font-weight:bold; font-size:0.65rem;">✉️ EMAIL</div></a>', unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        if g1.button(f"📝 Modifier", key=f"ed_{i}", use_container_width=True):
            st.session_state.id_a_modifier = i
            st.session_state.page = "MODIFIER_CONTACT"
            st.rerun()
        if g2.button(f"🗑️ Supprimer", key=f"dl_{i}", use_container_width=True):
            st.session_state[f"confirm_{i}"] = True

        if st.session_state.get(f"confirm_{i}"):
            st.error("Confirmer ?")
            cf1, cf2 = st.columns(2)
            if cf1.button("OUI", key=f"y_{i}", use_container_width=True):
                df_c = df_c.drop(i)
                sauvegarder_data(df_c, 'contacts.json')
                st.rerun()
            if cf2.button("NON", key=f"n_{i}", use_container_width=True):
                del st.session_state[f"confirm_{i}"]
                st.rerun()
        st.write("---")


# =================================================================
# --- 6. PAGE PLANNING (VERSION OPTIMISÉE IPHONE) ---
# =================================================================
elif st.session_state.page == "PLANNING":
    st.markdown('<div class="main-header">🗓️ PLANNING VESTA 2026</div>', unsafe_allow_html=True)
    
    # RÉCUPÉRATION DE LA DATE DU JOUR
    maintenant = datetime.now()
    aujourdhui = date(maintenant.year, maintenant.month, maintenant.day)
    
    # 2. SÉLECTION MOIS/ANNÉE
    col_m, col_y = st.columns(2)
    with col_m:
        m_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        sel_m = m_noms.index(st.selectbox("Mois", m_noms, index=aujourdhui.month - 1)) + 1
    with col_y:
        sel_y = st.selectbox("Année", [2026, 2027, 2028], index=0)

    # 3. LOGIQUE DE CALCUL DES COULEURS
    jours_occ = {}
    for _, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' not in d_str: continue
            parts = d_str.split('/')
            dv, mv, yv = int(parts[0]), int(parts[1]), int(parts[2])
            if yv < 100: yv += 2000
            
            if mv == sel_m and yv == sel_y:
                s_val = str(r.get('Statut', '')).strip().lower()
                if s_val in ["", "archivé", "archive", "supprimé", "refusé"]: continue
                
                this_date = date(yv, mv, dv)
                p_val = str(r.get('Paiement', '')).strip().lower()
                is_paye = ("pay" in p_val or "paid" in p_val) and not any(x in p_val for x in ["un", "pas", "non"])
                
                # Couleur du rond
                if this_date < aujourdhui:
                    current_c = "#3498db" if is_paye else "#e74c3c"
                elif "ok" in s_val:
                    current_c = "#2ecc71"
                elif "attente" in s_val:
                    current_c = "#f1c40f"
                else:
                    current_c = "transparent"
                
                n_j = int(r.get('NbreJours', 1))
                for j in range(dv, dv + n_j):
                    if j in jours_occ:
                        old_c = jours_occ[j]["c"]
                        final_c = "#e74c3c" if "#e74c3c" in [current_c, old_c] else current_c
                        jours_occ[j] = {"c": final_c}
                    else:
                        jours_occ[j] = {"c": current_c}
        except: continue

    # 4. AFFICHAGE DU CALENDRIER HTML (FORCÉ 100% LARGEUR)
    jours_semaine = ["L", "M", "M", "J", "V", "S", "D"]
    
    # CSS crucial : table-layout fixed pour iPhone
    h_cal = '<table style="width:100%; table-layout:fixed; border-collapse: collapse; text-align: center; background: white; color: black; border: 1px solid #eee;">'
    
    h_cal += '<tr style="background: #f8f9fa; font-weight: bold;">'
    for js in jours_semaine:
        h_cal += f'<td style="padding: 8px 0; border: 0.5px solid #eee; font-size: 11px; color: #666;">{js}</td>'
    h_cal += '</tr>'
    
    import calendar as cal_mod
    cal_mat = cal_mod.monthcalendar(sel_y, sel_m)
    for sem in cal_mat:
        h_cal += '<tr>'
        for jour in sem:
            if jour == 0:
                h_cal += '<td style="height:45px; border:0.5px solid #eee;"></td>'
            else:
                bg = jours_occ.get(jour, {}).get("c", "transparent")
                txt_c = "white" if bg != "transparent" else "black"
                
                if bg != "transparent":
                    # Rond légèrement plus petit (28px) pour tenir sur iPhone SE/12/13
                    circle = f'<div style="background:{bg}; color:{txt_c}; border-radius:50%; width:28px; height:28px; line-height:28px; margin:auto; font-weight:bold; font-size:12px;">{jour}</div>'
                else:
                    circle = f'<span style="color:black; font-size:13px;">{jour}</span>'
                
                h_cal += f'<td style="border:0.5px solid #eee; height:45px;">{circle}</td>'
        h_cal += '</tr>'
    h_cal += '</table>'
    
    st.markdown(h_cal, unsafe_allow_html=True)
    st.caption("🔴 Impayé | 🔵 Payé | 🟢 OK | 🟡 Attente")

    # 5. DÉTAILS DES RÉSERVATIONS
    st.markdown(f"#### 📋 Sorties - {m_noms[sel_m-1]}")
    
    res_list = []
    ca_encaisse = 0.0
    ca_attente = 0.0

    for _, r in df_c.iterrows():
        try:
            d_str = str(r.get('DateNav', '')).strip()
            if '/' in d_str:
                parts = d_str.split('/')
                if int(parts[1]) == sel_m and (int(parts[2]) == sel_y or int(parts[2])+2000 == sel_y):
                    if str(r.get('Statut','')).lower() not in ["refusé", "archivé"]:
                        res_list.append(r)
                        prix = float(str(r.get('Prix', '0')).replace('€','').strip() or 0)
                        p_val = str(r.get('Paiement', '')).lower()
                        if ("pay" in p_val) and not any(x in p_val for x in ["un", "non"]):
                            ca_encaisse += prix
                        else:
                            ca_attente += prix
        except: continue

    if not res_list:
        st.info("Aucune navigation prévue.")
    else:
        res_list.sort(key=lambda x: int(str(x.get('DateNav')).split('/')[0]))
        
        for res in res_list:
            p_v = str(res.get('Paiement', '')).lower()
            is_p = ("pay" in p_v) and not any(x in p_v for x in ["un", "non"])
            p_color = "#27ae60" if is_p else "#e67e22"
            
            s_v = str(res.get('Statut', 'En attente'))
            s_color = "#2ecc71" if s_v == "OK" else "#f1c40f" if s_v == "En attente" else "#e74c3c"
            
            nom_c = f"{res.get('Prénom')} {res.get('Nom','').upper()}"
            nom_famille = res.get('Nom','')
            unique_key = f"btn_{nom_famille}_{str(res.get('DateNav')).replace('/','')}"

            st.markdown(f"""
            <div style="padding: 12px; border-left: 6px solid {p_color}; background: white; color: black; border-radius: 8px; margin-bottom: 8px; box-shadow: 0px 1px 3px rgba(0,0,0,0.1); border: 1px solid #eee;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="font-size: 0.95rem; font-weight: bold;">{nom_c}</div>
                    <div style="text-align: right;">
                        <span style="background:{s_color}; color:white; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:bold;">{s_v}</span>
                    </div>
                </div>
                <div style="margin-top: 5px; font-size: 0.85rem;">
                    📅 <b>{res.get('DateNav')}</b> | 💰 <b>{res.get('Prix')} €</b><br>
                    <small style="color: #666;">🏢 {res.get('Société','-')}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"🔎 FICHE {nom_famille.upper()}", key=unique_key, use_container_width=True):
                st.session_state.search_contact = nom_famille
                st.session_state.page = "CONTACTS"
                st.rerun()

    # 6. RÉCAPITULATIF FINANCIER
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Missions", len(res_list))
    c2.metric("Payé", f"{ca_encaisse:.0f}€")
    c3.metric("Dû", f"{ca_attente:.0f}€")

# =================================================================
# --- 7. PAGE STATS (VERSION PILOTAGE PRO) ---
# =================================================================
if st.session_state.page == "STATS":
    st.title("📊 Vesta - Pilotage & Performance")

    # --- 1. PRÉPARATION ET NETTOYAGE ---
    df_st = df_c.copy()
    if 'Société' in df_st.columns:
        df_st['Société'] = df_st['Société'].astype(str).str.strip().str.upper()
        df_st['Société'] = df_st['Société'].replace(['NAN', '', 'NONE', 'PERSO'], 'PARTICULIER')

    if not df_st.empty and 'Prix' in df_st.columns:
        df_st['PrixNum'] = df_st['Prix'].apply(clean_val)
        month_data = df_st['DateNav'].apply(get_month_info)
        df_st['M_Sort'] = [x[0] for x in month_data]
        df_st['Mois'] = [x[1] for x in month_data]
        
        # Filtres de paiement
        mask_paye = df_st['Paiement'].astype(str).str.upper().str.strip() == "PAYÉ"
        mask_ok = df_st['Statut'].astype(str).str.upper() == "OK"
        df_st['CA_Calcul'] = df_st.apply(lambda x: x['PrixNum'] if (mask_paye[x.name] or mask_ok[x.name]) else 0.0, axis=1)
    
    # Récupération Frais
    df_maint_stats = charger_data('maintenance.json')
    if not df_maint_stats.empty and 'Date' in df_maint_stats.columns:
        m_data_f = df_maint_stats['Date'].apply(get_month_info)
        df_maint_stats['M_Sort'] = [x[0] for x in m_data_f]
        df_maint_stats['Mois'] = [x[1] for x in m_data_f]
        df_maint_stats['FraisNum'] = df_maint_stats['Montant'].apply(clean_val)
    else:
        df_maint_stats = pd.DataFrame(columns=['M_Sort', 'Mois', 'FraisNum'])

    # --- 2. RÉPARTITION DU CA (SUGGESTION PRIORITAIRE) ---
    st.subheader("🎯 Origine des Revenus (CA)")
    if not df_st.empty:
        ca_par_soc = df_st.groupby('Société')['CA_Calcul'].sum().reset_index()
        import plotly.express as px
        fig_ca = px.pie(ca_par_soc, values='CA_Calcul', names='Société', 
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig_ca, use_container_width=True)
    
    st.divider()

    # --- 3. PANIER MOYEN PAR CLIENT ---
    st.subheader("📈 Rentabilité par Client")
    if not df_st.empty:
        # Calcul : Somme des prix / Nombre de missions
        stats_renta = df_st.groupby('Société').agg({'PrixNum': ['sum', 'count']}).reset_index()
        stats_renta.columns = ['Société', 'Total_CA', 'Nb_Missions']
        stats_renta['Panier_Moyen'] = stats_renta['Total_CA'] / stats_renta['Nb_Missions']
        
        fig_renta = px.bar(stats_renta.sort_values('Panier_Moyen', ascending=False), 
                           x='Société', y='Panier_Moyen', text='Panier_Moyen',
                           labels={'Panier_Moyen': '€ / Mission'}, color='Société')
        fig_renta.update_traces(texttemplate='%{text:.0f} €', textposition='outside')
        st.plotly_chart(fig_renta, use_container_width=True)

    st.divider()

    # --- 4. MÉTÉO DE TRÉSORERIE ---
    st.subheader("🌤️ Météo de Trésorerie")
    col1, col2, col3 = st.columns(3)
    
    # Calculs Tréso
    tot_encaisse = df_st[mask_paye]['PrixNum'].sum()
    tot_attendu = df_st[mask_ok & ~mask_paye]['PrixNum'].sum()
    tot_frais = df_maint_stats['FraisNum'].sum() if not df_maint_stats.empty else 0
    
    col1.metric("✅ Encaissé", f"{tot_encaisse:,.0f}€")
    col2.metric("🕒 Attendu", f"{tot_attendu:,.0f}€")
    col3.metric("📉 Frais", f"{tot_frais:,.0f}€", delta=f"-{tot_frais:,.0f}€", delta_color="inverse")

    # Graphique Météo (Cascade/Barres)
    treso_data = pd.DataFrame({
        'Type': ['Déjà Encaissé', 'À Recevoir', 'Frais Engagés'],
        'Montant': [tot_encaisse, tot_attendu, tot_frais],
        'Couleur': ['#2ecc71', '#f1c40f', '#e74c3c']
    })
    fig_treso = px.bar(treso_data, x='Type', y='Montant', color='Type',
                       color_discrete_map={'Déjà Encaissé':'#2ecc71', 'À Recevoir':'#f1c40f', 'Frais Engagés':'#e74c3c'})
    st.plotly_chart(fig_treso, use_container_width=True)

    # --- 5. SYNTHÈSE MENSUELLE (TABLEAU) ---
    st.divider()
    st.subheader("📅 Synthèse Mensuelle")
    stats_ca = df_st.groupby(['M_Sort', 'Mois'])['CA_Calcul'].sum().reset_index()
    stats_fr = df_maint_stats.groupby(['M_Sort', 'Mois'])['FraisNum'].sum().reset_index()
    mensuel = pd.merge(stats_ca, stats_fr, on=['M_Sort', 'Mois'], how='outer').fillna(0)
    mensuel.columns = ['M_Sort', 'Mois', 'CA', 'Frais']
    mensuel = mensuel.sort_values('M_Sort')
    mensuel['Bénéfice'] = mensuel['CA'] - mensuel['Frais']
    
    if not mensuel.empty:
        st.table(mensuel[['Mois', 'CA', 'Frais', 'Bénéfice']].set_index('Mois').style.format("{:.0f} €"))

    # --- 6. MISSIONS À VENIR ---
    st.subheader("⏳ Détail des paiements attendus")
    df_avenir = df_st[mask_ok & ~mask_paye].copy()
    if not df_avenir.empty:
        tab_avenir = df_avenir[['DateNav', 'Nom', 'PrixNum']]
        tab_avenir.columns = ['Date', 'Client', 'Prix €']
        st.dataframe(tab_avenir.set_index('Date'), use_container_width=True)
    else:
        st.info("Tout est à jour !")
# =================================================================
# --- 8. PAGE MAINTENANCE (VERSION OPTIMISÉE IPHONE 2026) ---
# =================================================================
if st.session_state.page == "MAINT":
    st.title("🔧 Maintenance Vesta")

    # 1. CHARGEMENT DES DONNÉES
    file_path_m = 'maintenance.json'
    df_m = charger_data(file_path_m)
    
    if df_m.empty:
        df_m = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])

    # --- 2. INTERFACE DE SAISIE DYNAMIQUE ---
    
    # Initialisation de l'état du formulaire dans la mémoire de la session
    if 'show_maint_form' not in st.session_state:
        st.session_state.show_maint_form = False

    # Barre d'outils supérieure
    col_nav1, col_nav2 = st.columns([2, 1])
    
    if not st.session_state.show_maint_form:
        if col_nav1.button("➕ AJOUTER UNE DÉPENSE", use_container_width=True, type="primary"):
            st.session_state.show_maint_form = True
            st.rerun()
    else:
        if col_nav2.button("❌ FERMER", use_container_width=True):
            st.session_state.show_maint_form = False
            st.rerun()

    # Affichage du formulaire (uniquement si activé)
    if st.session_state.show_maint_form:
        with st.form("form_maint_new"):
            st.write("### 📝 Nouvelle Saisie")
            f_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            f_obj = st.text_input("Objet (ex: Taxes, Révision, Accastillage)")
            f_mt = st.number_input("Montant (€)", min_value=0.0, step=1.0)
            
            submit = st.form_submit_button("💾 ENREGISTRER SUR GITHUB", use_container_width=True)
            
            if submit:
                if f_obj:
                    # Création de la nouvelle ligne
                    nouvelle_ligne = pd.DataFrame([{
                        "Date": f_date,
                        "Objet": f_obj,
                        "Montant": float(f_mt),
                        "Statut": "OK"
                    }])
                    df_m = pd.concat([df_m, nouvelle_ligne], ignore_index=True)
                    
                    # Sauvegarde sur GitHub
                    sauvegarder_data(df_m, file_path_m)
                    
                    # Fermeture automatique du formulaire
                    st.session_state.show_maint_form = False
                    
                    st.balloons()
                    st.success(f"Enregistré : {f_obj}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un 'Objet'.")

    st.divider()

 # 3. AFFICHAGE DE L'HISTORIQUE ET TOTAL
    if not df_m.empty:
        df_m['Montant'] = pd.to_numeric(df_m['Montant'], errors='coerce').fillna(0)
        total_frais = df_m['Montant'].sum()
        st.metric("TOTAL CUMULÉ 2026", f"{total_frais:,.2f} €")

        st.write("### 📋 Historique des frais")
        
        # On parcourt l'historique (du plus récent au plus ancien)
        for index, item in df_m.iloc[::-1].iterrows():
            # Clé unique pour le mode édition de chaque ligne
            edit_key = f"edit_mode_{index}"
            if edit_key not in st.session_state:
                st.session_state[edit_key] = False

            with st.expander(f"📅 {item['Date']} - {item['Objet']} ({item['Montant']}€)"):
                
                if not st.session_state[edit_key]:
                    # --- AFFICHAGE CLASSIQUE ---
                    col_a, col_b = st.columns(2)
                    if col_a.button("✏️ Modifier", key=f"btn_edit_{index}", use_container_width=True):
                        st.session_state[edit_key] = True
                        st.rerun()
                    
                    if col_b.button("🗑️ Supprimer", key=f"btn_del_{index}", use_container_width=True):
                        df_m = df_m.drop(index).reset_index(drop=True)
                        sauvegarder_data(df_m, file_path_m)
                        st.rerun()
                else:
                    # --- MODE ÉDITION (DANS L'EXPANDER) ---
                    st.info("Mode modification activé")
                    new_date = st.text_input("Date", item['Date'], key=f"in_date_{index}")
                    new_obj = st.text_input("Objet", item['Objet'], key=f"in_obj_{index}")
                    new_mt = st.number_input("Montant (€)", value=float(item['Montant']), key=f"in_mt_{index}")
                    
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Sauver", key=f"save_{index}", use_container_width=True, type="primary"):
                        # Mise à jour des données
                        df_m.at[index, 'Date'] = new_date
                        df_m.at[index, 'Objet'] = new_obj
                        df_m.at[index, 'Montant'] = new_mt
                        sauvegarder_data(df_m, file_path_m)
                        st.session_state[edit_key] = False # On ferme le mode édition
                        st.success("Modifié !")
                        time.sleep(0.5)
                        st.rerun()
                        
                    if c2.button("🚫 Annuler", key=f"cancel_{index}", use_container_width=True):
                        st.session_state[edit_key] = False
                        st.rerun()
    else:
        st.info("Aucune dépense enregistrée.")

    # 4. ZONE DE DANGER
    st.write("---")
    with st.expander("⚠️ Zone de Danger"):
        st.write("Attention, cette action est irréversible.")
        if st.checkbox("Confirmer la suppression totale de l'historique"):
            if st.button("🔴 VIDER LE FICHIER MAINTENANCE", type="primary", use_container_width=True):
                df_vide = pd.DataFrame(columns=["Date", "Objet", "Montant", "Statut"])
                sauvegarder_data(df_vide, file_path_m)
                st.rerun()

# =================================================================
# --- 9. PAGE FACTURES (ANALYSE & ENVOI CMN OPTIMISÉ IPHONE) ---
# =================================================================
if st.session_state.page == "FACTURES":
    st.title("📑 Facturation & Rapports")

    # --- 1. SÉLECTION DU MOIS ---
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                 "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    maintenant = datetime.now()
    
    col_m, col_a = st.columns(2)
    sel_mois = col_m.selectbox("Choisir le mois", mois_noms, index=maintenant.month - 1)
    sel_annee = col_a.selectbox("Année", [2025, 2026, 2027], index=1)
    index_mois = mois_noms.index(sel_mois) + 1

    # --- 2. FILTRAGE ET CALCULS ---
    if not df_c.empty:
        df_fact = df_c.copy()
        df_fact['dt'] = pd.to_datetime(df_fact['DateNav'], format='%d/%m/%Y', errors='coerce')
        
        mask_cmn = (df_fact['Société'].astype(str).str.upper() == "CMN") & \
                   (df_fact['dt'].dt.month == index_mois) & \
                   (df_fact['dt'].dt.year == sel_annee)
        
        df_cmn_mois = df_fact[mask_cmn].copy()
        
        if not df_cmn_mois.empty:
            st.subheader(f"Missions CMN - {sel_mois} {sel_annee}")
            
            df_cmn_mois['PrixNum'] = df_cmn_mois['Prix'].apply(clean_val)
            total_cmn = df_cmn_mois['PrixNum'].sum()
            
            st.table(df_cmn_mois[['DateNav', 'Nom', 'Prix']].set_index('DateNav'))
            st.metric("Total à facturer", f"{total_cmn:.2f} €")
            
            # --- 3. PRÉPARATION DU TEXTE ---
            st.divider()
            st.subheader("✉️ Rapport pour le Trésorier")
            
            lignes_missions = []
            for _, row in df_cmn_mois.iterrows():
                d_str = str(row['DateNav']).ljust(10)
                n_str = str(row['Nom'])
                p_str = f"{row['PrixNum']:.2f} €"
                lignes_missions.append(f"{d_str}{' '*12}{n_str}{' '*3}{p_str}")
            
            texte_missions = "\n".join(lignes_missions)
            destinataire = "tresorier@cmn-asso.fr, aurelienfaucheux@gmail.com"
            objet = f"Facturation Missions Vesta - {sel_mois} {sel_annee}"
            
            corps_mail = f"Bonjour,\n\nVoici le récapitulatif CMN de {sel_mois} {sel_annee} :\n\n{texte_missions}\n\nTotal : {total_cmn:.2f} €.\n\nMerci,\nEric (Vesta)"

            st.text_area("Texte prêt à copier :", corps_mail, height=200)
            
            import urllib.parse
            mail_link = f"mailto:{destinataire}?subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            gmail_link = f"googlegmail:///co?to={destinataire}&subject={urllib.parse.quote(objet)}&body={urllib.parse.quote(corps_mail)}"
            
            c_b1, c_b2 = st.columns(2)
            c_b1.link_button("🚀 GMAIL", gmail_link, use_container_width=True)
            c_b2.link_button("✉️ MAIL", mail_link, use_container_width=True)
          # --- 4. SUIVI DES ENVOIS (LOGIQUE DYNAMIQUE) ---
            st.divider()
            df_suivi = charger_data('suivi_envois.json')
            if df_suivi.empty:
                df_suivi = pd.DataFrame(columns=["Mois", "Annee", "DateEnvoi", "Total"])

            # On vérifie si le mois sélectionné est déjà dans le fichier JSON
            deja_envoye = df_suivi[(df_suivi['Mois'] == sel_mois) & (df_suivi['Annee'] == sel_annee)]

            if not deja_envoye.empty:
                # SI DÉJÀ ENVOYÉ : On affiche le message de succès (et pas le bouton)
                dernier = deja_envoye.iloc[-1]
                st.success(f"✅ Envoyé le {dernier['DateEnvoi']}")
                
                # Optionnel : un bouton discret pour corriger en cas d'erreur
                if st.button("🔄 RE-VALIDER (Si erreur)", use_container_width=True):
                    st.info("Le bouton d'envoi va réapparaître.")
                    # Ici on pourrait supprimer la ligne, mais le plus simple est de laisser le rerun
                    st.rerun()
            
            else:
                # SI PAS ENCORE ENVOYÉ : On affiche le gros bouton rouge/bleu
                if st.button("✔️ MARQUER COMME ENVOYÉ", type="primary", use_container_width=True):
                    nouvelle_trace = pd.DataFrame([{
                        "Mois": sel_mois,
                        "Annee": sel_annee,
                        "DateEnvoi": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                        "Total": f"{total_cmn:.2f} €"
                    }])
                    df_suivi = pd.concat([df_suivi, nouvelle_trace], ignore_index=True)
                    sauvegarder_data(df_suivi, 'suivi_envois.json')
                    st.success("Enregistré !")
                    time.sleep(1)
                    st.rerun()

            # L'historique reste visible en bas dans tous les cas
            with st.expander("🕒 Historique des envois"):
                if not df_suivi.empty:
                    st.dataframe(df_suivi.iloc[::-1], use_container_width=True, hide_index=True)  

# =================================================================
# --- 11. PAGE NOTES (VERSION COMPLÈTE AVEC MODIFICATION) ---
# =================================================================
if st.session_state.page == "NOTES":
    st.title("📝 Notes & Commentaires")

    # 1. CHARGEMENT ET SÉCURISATION DES DONNÉES
    file_path_notes = 'notes.json'
    df_n = charger_data(file_path_notes)
    
    # Force la structure pour éviter les KeyError
    if df_n.empty or 'Date' not in df_n.columns:
        df_n = pd.DataFrame(columns=["Date", "Sujet", "Commentaires", "Statut"])

    # --- 2. INTERFACE D'AJOUT DYNAMIQUE ---
    if 'show_notes_form' not in st.session_state:
        st.session_state.show_notes_form = False

    col_n1, col_n2 = st.columns([2, 1])
    
    if not st.session_state.show_notes_form:
        if col_n1.button("➕ NOUVELLE NOTE", use_container_width=True, type="primary"):
            st.session_state.show_notes_form = True
            st.rerun()
    else:
        if col_n2.button("❌ FERMER", key="close_notes_form", use_container_width=True):
            st.session_state.show_notes_form = False
            st.rerun()

    if st.session_state.show_notes_form:
        with st.form("form_notes_new"):
            st.write("### ✍️ Rédiger une note")
            fn_date = st.text_input("Date", datetime.now().strftime("%d/%m/%Y"))
            fn_sujet = st.text_input("Sujet (ex: Moteur, Amarrage, Électricité)")
            fn_comm = st.text_area("Commentaires")
            
            submit_n = st.form_submit_button("💾 ENREGISTRER LA NOTE", use_container_width=True)
            
            if submit_n:
                if fn_sujet:
                    nouvelle_note = pd.DataFrame([{
                        "Date": fn_date,
                        "Sujet": fn_sujet,
                        "Commentaires": fn_comm,
                        "Statut": "OK"
                    }])
                    df_n = pd.concat([df_n, nouvelle_note], ignore_index=True)
                    sauvegarder_data(df_n, file_path_notes)
                    st.session_state.show_notes_form = False
                    st.success("Note enregistrée !")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Veuillez entrer un sujet.")

    st.divider()

    # --- 3. AFFICHAGE & MODIFICATION DE L'HISTORIQUE ---
    if not df_n.empty:
        st.write(f"### 📋 Carnet de bord ({len(df_n)} notes)")
        
        for index, item in df_n.iloc[::-1].iterrows():
            # Clé d'édition unique pour cette note
            n_edit_key = f"note_edit_mode_{index}"
            if n_edit_key not in st.session_state:
                st.session_state[n_edit_key] = False

            with st.expander(f"📌 {item['Date']} - {item['Sujet']}"):
                
                if not st.session_state[n_edit_key]:
                    # --- VUE LECTURE ---
                    st.write(f"**Commentaire :**\n{item['Commentaires']}")
                    
                    c_na, c_nb = st.columns(2)
                    if c_na.button("✏️ Modifier", key=f"n_btn_edit_{index}", use_container_width=True):
                        st.session_state[n_edit_key] = True
                        st.rerun()
                    
                    if c_nb.button("🗑️ Supprimer", key=f"n_btn_del_{index}", use_container_width=True):
                        df_n = df_n.drop(index).reset_index(drop=True)
                        sauvegarder_data(df_n, file_path_notes)
                        st.rerun()
                else:
                    # --- VUE ÉDITION ---
                    st.info("Modification en cours...")
                    ed_n_date = st.text_input("Date", item['Date'], key=f"ed_n_d_{index}")
                    ed_n_sujet = st.text_input("Sujet", item['Sujet'], key=f"ed_n_s_{index}")
                    ed_n_comm = st.text_area("Commentaires", item['Commentaires'], key=f"ed_n_c_{index}")
                    
                    cn1, cn2 = st.columns(2)
                    if cn1.button("💾 Sauver", key=f"n_save_mod_{index}", use_container_width=True, type="primary"):
                        df_n.at[index, 'Date'] = ed_n_date
                        df_n.at[index, 'Sujet'] = ed_n_sujet
                        df_n.at[index, 'Commentaires'] = ed_n_comm
                        sauvegarder_data(df_n, file_path_notes)
                        st.session_state[n_edit_key] = False
                        st.success("C'est fait !")
                        time.sleep(0.5)
                        st.rerun()
                        
                    if cn2.button("🚫 Annuler", key=f"n_cancel_mod_{index}", use_container_width=True):
                        st.session_state[n_edit_key] = False
                        st.rerun()
    else:
        st.info("Aucune note enregistrée.")
# =================================================================
# --- 10. PAGE LOG (CONSULTATION DES ARCHIVES) ---
# =================================================================
elif st.session_state.page == "LOG":
    st.title("📂 Archives & Logs")
    
    annee_actuelle = datetime.now().year
    nom_archive = f"archives_{annee_actuelle}.json"
    
    df_arch = charger_data(nom_archive)
    
    if not df_arch.empty:
        st.write(f"### 📋 Missions Archivées {annee_actuelle}")
        st.dataframe(df_arch, use_container_width=True)
    else:
        st.info("Aucune archive trouvée pour cette saison.")

# --- FIN DU FICHIER ---
        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        








































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































        




































































































































































































































































































































































































































































































































































































































































































































































































































































































































































