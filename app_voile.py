elif st.session_state.page == "PLANNING":
    st.markdown('<div class="page-title">🗓️ PLANNING</div>', unsafe_allow_html=True)
    cp, cm, cn = st.columns([1,2,1])
    if cp.button("◀️"): st.session_state.cal_month -= 1; st.rerun()
    cm.markdown(f"<center><b>{st.session_state.cal_month:02d}/{st.session_state.cal_year}</b></center>", unsafe_allow_html=True)
    if cn.button("▶️"): st.session_state.cal_month += 1; st.rerun()

    occu = {}
    for _, r in df.iterrows():
        d_o = parse_date(r['DateNav'])
        for j in range(to_int(r.get('NbJours', 1))):
            d_c = (d_o + timedelta(days=j)).strftime('%d/%m/%Y')
            if d_c not in occu: occu[d_c] = []
            occu[d_c].append(r)

    # 1. Calendrier visuel
    cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
    h_c = '<table class="cal-table"><tr><th>L</th><th>M</th><th>M</th><th>J</th><th>V</th><th>S</th><th>D</th></tr>'
    for w in cal:
        h_c += '<tr>'
        for d in w:
            if d == 0: h_c += '<td></td>'
            else:
                ds = f"{d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
                bg = "#3498db" if any("CMN" in str(x.get('Société','')).upper() for x in occu.get(ds,[])) else ("#2ecc71" if ds in occu else "white")
                h_c += f'<td style="background:{bg}; color:{"white" if bg!="white" else "black"};">{d}</td>'
        h_c += '</tr>'
    st.markdown(h_c + '</table>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 2. Sélection SANS CLAVIER (Boutons Radio horizontaux)
    jours_nav = sorted([int(k.split('/')[0]) for k in occu.keys() if f"/{st.session_state.cal_month:02d}" in k])
    
    if jours_nav:
        st.write("📍 **Choisir un jour de navigation :**")
        # Le mode "segment" crée des boutons côte à côte très pratiques sur mobile
        sel_d = st.radio(
            "Jours occupés :", 
            jours_nav, 
            horizontal=True, 
            label_visibility="collapsed"
        )
        
        if sel_d:
            ds_sel = f"{sel_d:02d}/{st.session_state.cal_month:02d}/{st.session_state.cal_year}"
            st.markdown(f"**Détails pour le {ds_sel} :**")
            for res in occu.get(ds_sel, []):
                st.info(f"👤 **{res.get('Prénom')} {res.get('Nom')}**\n🏢 {res.get('Société')}\n⏱️ {res.get('HeuresMoteur')}h | ⚓ {res.get('Milles')} NM")
    else:
        st.write("Aucune navigation ce mois-ci.")



















































































































































