# --- REMPLACE LA SECTION "PAGE LISTE" PAR CELLE-CI ---

if st.session_state.page == "LISTE":
    st.markdown('<div class="page-title">📋 MES NAVIGATIONS</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    if c1.button("🚀 FUTURES", key="v_fut", use_container_width=True, type="primary" if st.session_state.view_mode == "FUTURES" else "secondary"):
        st.session_state.view_mode = "FUTURES"; st.rerun()
    if c2.button("📂 PASSÉES", key="v_pas", use_container_width=True, type="primary" if st.session_state.view_mode == "PASSÉES" else "secondary"):
        st.session_state.view_mode = "PASSÉES"; st.rerun()
    st.markdown("---")
    
    if st.button("➕ NOUVELLE FICHE", use_container_width=True):
        st.session_state.edit_idx = "NEW"; st.session_state.page = "FORM"; st.rerun()

    if not df.empty:
        df['dt'] = df['DateNav'].apply(parse_d)
        now = datetime.now().replace(hour=0, minute=0, second=0)
        data = df[df['dt'] >= now] if st.session_state.view_mode == "FUTURES" else df[df['dt'] < now]
        data = data.sort_values('dt', ascending=(st.session_state.view_mode == "FUTURES"))

        for i, r in data.iterrows():
            st_txt = str(r.get('Statut','🟡'))
            col_s = "#2ecc71" if "OK" in st_txt.upper() or "🟢" in st_txt else ("#e74c3c" if "🔴" in st_txt else "#f1c40f")
            
            # Nettoyage du numéro pour WhatsApp (enlève espaces, points, +, etc.)
            tel_brut = str(r.get('Téléphone',''))
            tel_clean = "".join(filter(str.isdigit, tel_brut))
            
            eml = str(r.get('Email',''))
            
            st.markdown(f'''
                <div class="client-card" style="border-left: 12px solid {col_s};">
                    <div style="float:right; font-weight:bold;">{fmt_p(r.get("PrixJour",0))}</div>
                    <b>{r.get("Prénom","")} {r.get("Nom","").upper()}</b><br>
                    📅 <b>{r.get("DateNav","")}</b> — ⏱️ <b>{r.get("NbJours","1")} jours</b><br>
                    📞 <a href="tel:{tel_brut}" class="contact-link">{tel_brut}</a><br>
                    <div style="margin-top:8px; margin-bottom:8px;">
                        <a href="https://wa.me/{tel_clean}" target="_blank" 
                           style="background-color:#25D366; color:white; padding:5px 10px; border-radius:5px; text-decoration:none; font-weight:bold; font-size:0.8rem;">
                           💬 WHATSAPP
                        </a>
                    </div>
                    ✉️ <a href="mailto:{eml}" class="contact-link">{eml}</a><br>
                    <span style="color:{col_s}; font-weight:bold;">{st_txt}</span>
                </div>
            ''', unsafe_allow_html=True)
            if st.button("✏️ Modifier", key=f"ed_nav_{i}"):
                st.session_state.edit_idx = i; st.session_state.page = "FORM"; st.rerun()

































































































































































































