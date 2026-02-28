# --- DANS LA BOUCLE D'AFFICHAGE DES FICHES (PAGE LISTE) ---

for i, r in data.iterrows():
    # 1. On définit la couleur du bandeau (Priorité au bleu si CMN)
    soc_nom = str(r.get('Société', '')).upper()
    statut_val = str(r.get('Statut', ''))
    
    if "CMN" in soc_nom:
        cl = "cmn-style"  # Bandeau Bleu Ciel
    elif "🟢" in statut_val:
        cl = "status-ok"   # Bandeau Vert
    else:
        cl = "status-attente" # Bandeau Jaune

    # Affichage de la carte
    st.markdown(f"""
        <div class="client-card {cl}">
            <div style="float:right; font-weight:bold; color:#1a2a6c;">{r['PrixJour']}€</div>
            <b style="font-size:1.1rem;">{r["Prénom"]} {r["Nom"]}</b><br>
            <span style="color:#d35400; font-weight:bold; font-size:0.9rem;">🏢 {r["Société"]}</span>
            <div class="contact-bar" style="margin-top:8px;">
                <a href="tel:{r["Téléphone"]}">📞 Appeler</a> 
                <a href="mailto:{r["Email"]}">✉️ Mail</a>
            </div>
            <div style="margin-top:8px; font-size:0.8rem; color:#7f8c8d;">
                📅 <b>{r["DateNav"]}</b> | ⚓ {r["Milles"]} NM | ⏱️ {r["HeuresMoteur"]}h
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Bouton de gestion
    st.markdown('<div class="btn-marine">', unsafe_allow_html=True)
    if st.button(f"✏️ Gérer {r['Prénom']}", key=f"btn_{i}", use_container_width=True):
        st.session_state.edit_idx = i
        st.session_state.page = "FORM"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)







































































































































