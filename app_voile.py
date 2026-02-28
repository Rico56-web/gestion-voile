elif st.session_state.page == "PLANNING":
    st.markdown('<div class="section-confirm">🗓️ PLANNING DES SORTIES</div>', unsafe_allow_html=True)
    
    # --- NAVIGATION PAR BOUTONS (Évite le clavier iPhone) ---
    if "cal_month" not in st.session_state: st.session_state.cal_month = datetime.now().month
    if "cal_year" not in st.session_state: st.session_state.cal_year = datetime.now().year
    
    col_prev, col_m, col_next = st.columns([1, 3, 1])
    
    with col_prev:
        if st.button("◀️", use_container_width=True):
            st.session_state.cal_month -= 1
            if st.session_state.cal_month < 1:
                st.session_state.cal_month = 12
                st.session_state.cal_year -= 1
            st.rerun()
            
    with col_m:
        mois_nom = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        st.markdown(f"<h3 style='text-align:center; margin:0; color:#1a2a6c;'>{mois_nom[st.session_state.cal_month-1]} {st.session_state.cal_year}</h3>", unsafe_allow_html=True)
        
    with col_next:
        if st.button("▶️", use_container_width=True):
            st.session_state.cal_month += 1
            if st.session_state.cal_month > 12:
                st.session_state.cal_month = 1
                st.session_state.cal_year += 1
            st.rerun()

    # --- LOGIQUE DU CALENDRIER ---
    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        if d_o.year == st.session_state.cal_year:
            for j in range(to_int(r['NbJours'])):
                d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
                if d_c not in occu: occu[d_c] = []
                occu[d_c].append(r)
                
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><thead><tr><th>LU</th><th>MA</th><th>ME</th><th>JE</th><th>VE</th><th>SA</th><th>DI</th></tr></thead><tbody>'
    
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0:
                h_c += '<td style="background:#f9f9f9;"></td>'
            else:
                ds = f"{d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                dat = occu.get(ds, [])
                bg, color = "white", "black"
                if dat:
                    # On prend la couleur de la première résa trouvée pour ce jour
                    first = dat[0]
                    if "CMN" in str(first['Société']).upper(): bg, color = "#3498db", "white"
                    elif "🟢" in str(first['Statut']): bg, color = "#2ecc71", "white"
                    else: bg, color = "#f1c40f", "black"
                h_c += f'<td style="background:{bg}; color:{color};">{d}</td>'
        h_c += '</tr>'
    
    st.markdown(h_c + '</tbody></table>', unsafe_allow_html=True)
    
    # Légende rapide
    st.markdown("""
        <div style="display:flex; justify-content:space-around; font-size:0.7rem; margin-top:10px;">
            <span>🔵 CMN</span><span>🟢 OK</span><span>🟡 Attente</span>
        </div>
    """, unsafe_allow_html=True)




































































































































