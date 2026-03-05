# --- PAGE LISTE (ORDRE CHRONOLOGIQUE POUR FUTURES) ---
if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", use_container_width=True): st.session_state.view_mode = "FUTURES"
    if c2.button("📂 ARCHIVES", use_container_width=True): st.session_state.view_mode = "ARCHIVES"
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = None; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        
        if st.session_state.view_mode == "FUTURES":
            # Filtre les dates à venir et trie de la plus proche à la plus lointaine
            data = df[df['dt'] >= now].sort_values('dt', ascending=True)
        else:
            # Filtre les archives et trie de la plus récente à la plus ancienne
            data = df[df['dt'] < now].sort_values('dt', ascending=False)

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            tel, eml = str(r.get('Téléphone','')), str(r.get('Email',''))
            
            st.markdown(f'''
                <div class="client-card" style="border-left-color:{col};">
                    <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                    📅 <b>{r.get("DateNav","")}</b> — ⏱️ {r.get("NbJours","1")} j<br>
                    📞 <a href="tel:{tel}" class="contact-link">{tel if tel else "Non renseigné"}</a> | ✉️ <a href="mailto:{eml}" class="contact-link">{eml if eml else "Pas de mail"}</a><br>
                    <span style="color:{col}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            
            c_edit, c_del = st.columns(2)
            if c_edit.button("✏️ Modifier", key=f"ed_{i}"): 
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()
            
            if st.session_state.del_idx == i:
                st.warning("Supprimer ?")
                cy, cn = st.columns(2)
                if cy.button("OUI", key=f"cy_{i}"): 
                    df.drop(i).pipe(sauvegarder_data)
                    st.session_state.del_idx = None
                    st.rerun()
                if cn.button("NON", key=f"cn_{i}"): 
                    st.session_state.del_idx = None
                    st.rerun()
            else:
                if c_del.button("🗑️ Supprimer", key=f"dl_{i}"): 
                    st.session_state.del_idx = i
                    st.rerun()




















































































































































































