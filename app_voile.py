elif st.session_state.page == "BUDGET":
    st.markdown('<div class="page-title">💰 STATS & BILAN</div>', unsafe_allow_html=True)
    
    # 1. Sélection de l'année (3 ans)
    annee_actuelle = 2026 # Référence selon tes instructions
    s_y = st.selectbox("Année", [annee_actuelle - 1, annee_actuelle, annee_actuelle + 1], index=1)
    obj = st.number_input("Cible annuelle (€)", value=15000)

    df['dt'] = df['DateNav'].apply(parse_d)
    df_f['dt'] = df_f['Date'].apply(parse_d)

    # Calcul global pour la barre de progression (Somme des OK de l'année)
    ca_total_ok = sum(df[(df['dt'].dt.year == s_y) & 
                         (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
    
    st.write(f"📈 **Réalisé (OK) : {int(ca_total_ok)} / {int(obj)}**")
    st.progress(min(ca_total_ok/obj, 1.0))
    
    st.markdown("---")
    
    # 2. Tableau de Bord Mensuel
    res = []
    t_rev, t_fra, t_net, t_pre = 0, 0, 0, 0

    for i in range(1, 13):
        # Revenu = Uniquement les sorties terminées/validées (Statut OK) pour ce mois
        rev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & 
                     (df['Statut'].str.contains("OK|🟢", na=False))]['PrixJour'].apply(to_f))
        
        # Frais = Maintenance enregistrée ce mois
        fr = sum(df_f[(df_f['dt'].dt.year == s_y) & (df_f['dt'].dt.month == i)]['Montant'].apply(to_f))
        
        # Prévisionnel = TOUT (OK + Attente 🟡)
        prev = sum(df[(df['dt'].dt.year == s_y) & (df['dt'].dt.month == i) & 
                      (df['Statut'].str.contains("OK|🟢|🟡|Attente", na=False))]['PrixJour'].apply(to_f))
        
        net = rev - fr
        
        # Cumul pour la ligne Total
        t_rev += rev; t_fra += fr; t_net += net; t_pre += prev

        res.append({
            "M": i, 
            "Rev": int(rev), 
            "Frais": int(fr), 
            "Net": int(net),
            "Prév": int(prev)
        })

    # Affichage du tableau
    df_stats = pd.DataFrame(res)
    
    # Ligne de TOTAL
    total_row = pd.DataFrame([{"M": "TOT", "Rev": int(t_rev), "Frais": int(t_fra), "Net": int(t_net), "Prév": int(t_pre)}])
    df_stats = pd.concat([df_stats, total_row], ignore_index=True)

    # Style pour forcer l'affichage compact
    st.table(df_stats.set_index('M'))

    st.markdown("---")
    # [Reste du code pour la Facture CMN...]





















































































































































































































































