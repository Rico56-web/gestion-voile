# --- LOGIQUE DU PLANNING AVEC PRIORITÉ JAUNE ---
elif st.session_state.page == "PLAN":
    m_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    c1, c2, c3 = st.columns([1,2,1])
    if c1.button("◀️"): st.session_state.m_idx = 12 if st.session_state.m_idx == 1 else st.session_state.m_idx - 1; st.rerun()
    c2.markdown(f"<h3 style='text-align:center;'>{m_fr[st.session_state.m_idx-1]} 2026</h3>", unsafe_allow_html=True)
    if c3.button("▶️"): st.session_state.m_idx = 1 if st.session_state.m_idx == 12 else st.session_state.m_idx + 1; st.rerun()

    # On prépare le dictionnaire des occupations
    occu = {}
    for _, r in df.iterrows():
        d_obj = parse_date(r['DateNav'])
        if d_obj.year == 2026:
            for j in range(to_int(r.get('NbJours', 1))):
                d_c = (d_obj + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)

    # Affichage du calendrier
    cal = calendar.monthcalendar(2026, st.session_state.m_idx)
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day != 0:
                d_s = f"{day:02d}/{st.session_state.m_idx:02d}/2026"
                label = str(day)
                
                if d_s in occu:
                    # RÈGLE DE COULEUR :
                    # Si l'un des dossiers est "🟢 OK" -> Vert
                    if any("🟢" in str(x['Statut']) for x in occu[d_s]):
                        label = "🟢"
                    # Sinon (donc que des "🟡 Attente") -> Jaune
                    else:
                        label = "🟡"
                
                if cols[i].button(label, key=f"p_{d_s}", use_container_width=True):
                    if d_s in occu:
                        for x in occu[d_s]: 
                            st.info(f"{x['Statut']} {x['Prénom']} {x['Nom']} ({x['Passagers']}p)")



























































