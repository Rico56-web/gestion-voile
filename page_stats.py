"""
page_stats.py
==============
Tableau de bord statistiques et financier — PARTIE A (indicateurs clés,
répartition par société, graphique chronologique + seuil de rentabilité).

La PARTIE B (tableaux détaillés ligne par ligne, éditeur des charges
fixes) sera ajoutée dans une prochaine étape.

Sources de données :
- croisieres_v2.json / etapes_v2.json (nouveau modèle, migré)
- maintenance.json (ANCIEN format, PAS migré — la page MAINT n'existe pas
  encore dans le nouveau modèle, donc on lit ce fichier tel quel, sans le
  toucher, exactement comme le faisait l'ancien code)
- params.json (charges fixes annuelles, seuil de vidange — inchangé)

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, MAINT, LOG, MEMOS, FACT, ARCHIVES.
"""
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from modele_voile import (
    bilan_financier_annee, repartition_par_societe, bilan_navigation_annee,
    recettes_par_mois, derniere_lecture_compteur,
)

ORDRE_MOIS = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


def _depenses_maintenance_par_mois(df_maintenance, annee):
    """Reprend la logique de l'ancien code (inchangée, car maintenance.json
    n'est pas encore migré) : total des dépenses par mois pour l'année,
    et total des charges fixes réelles relevées dans le journal (Port,
    Assurance) séparé de la maintenance technique pure."""
    montants = [0.0] * 12
    total_pure_maint = 0.0
    total_reels_fixes = 0.0

    if df_maintenance is None or df_maintenance.empty:
        return montants, total_pure_maint, total_reels_fixes

    df = df_maintenance.copy()
    df["dt_maint"] = pd.to_datetime(df.get("Date"), dayfirst=True, errors="coerce")
    df["M_Num"] = pd.to_numeric(df.get("M_Num"), errors="coerce").fillna(0.0)
    df_y = df[df["dt_maint"].dt.year == annee]

    if df_y.empty:
        return montants, total_pure_maint, total_reels_fixes

    for _, row in df_y.iterrows():
        mois = row["dt_maint"].month
        montants[mois - 1] += row["M_Num"]

    mask_fixes = df_y.get("Type", pd.Series(dtype=str)).fillna("").str.lower().str.contains("port|assur", na=False)
    total_pure_maint = df_y[~mask_fixes]["M_Num"].sum()
    total_reels_fixes = df_y[mask_fixes]["M_Num"].sum()

    return montants, total_pure_maint, total_reels_fixes


def afficher_page_stats(charger_croisieres, charger_etapes, charger_maintenance, charger_params):
    """Point d'entrée de la page. Fonctions de chargement injectées
    depuis app_voile1.py."""

    st.markdown('<h2 style="text-align:center;">📊 Dashboard Intégral Vesta</h2>', unsafe_allow_html=True)

    croisieres = charger_croisieres()
    etapes = charger_etapes()
    df_maintenance = charger_maintenance()
    params = charger_params()

    frais_defaut = {"Port Arzon": 3800, "Assurance": 1200, "Entretien": 1500, "Divers": 500}
    if "frais_fixes" not in params or not isinstance(params["frais_fixes"], dict) or not params["frais_fixes"]:
        params["frais_fixes"] = frais_defaut
    frais_params = params["frais_fixes"]

    total_frais_fixes = 0.0
    for v in frais_params.values():
        try:
            total_frais_fixes += float(str(v).replace("€", "").replace(" ", "").replace(",", ".").strip())
        except (ValueError, TypeError):
            continue

    c_sel1, c_sel2 = st.columns([3, 1])
    mode_bilan = c_sel1.radio("Mode de calcul :", ["Réel (Encaissé)", "Prévisionnel (Saison)"], horizontal=True)
    sel_y = c_sel2.selectbox("Saison :", [2025, 2026, 2027], index=1)
    mode = "reel" if mode_bilan == "Réel (Encaissé)" else "previsionnel"

    bilan = bilan_financier_annee(croisieres, sel_y, mode)
    nav = bilan_navigation_annee(etapes, sel_y)
    h_moteur_abs = derniere_lecture_compteur(etapes)

    total_ca_display = bilan["total_encaisse"] if mode == "reel" else bilan["total_ca"]

    montants_maint_mois, total_pure_maint, total_reels_fixes = _depenses_maintenance_par_mois(df_maintenance, sel_y)
    total_dep = total_pure_maint + total_reels_fixes
    solde_net = total_ca_display - total_dep

    st.divider()

    # --- Activité & Navigation ---
    st.markdown("##### ⚓ Activité & Navigation")
    t1, t2, t3, t4 = st.columns(4)
    t1.metric("⛵ Sorties", f"{bilan['nb_sorties']}")
    t2.metric("⚙️ Heures Mot.", f"{nav['total_h_moteur']:.1f} h")
    t3.metric("🌊 Milles", f"{nav['total_milles']:,.0f} NM".replace(",", " "))
    t4.metric("⛵ Part voile", f"{nav['ratio_voile']:.0f} %")

    st.write("")

    # --- Recettes ---
    st.markdown("##### 💰 Recettes de la Saison")
    f1, f2, f3 = st.columns(3)
    f1.metric("🎯 CA Prévu", f"{bilan['total_ca']:,.0f} €".replace(",", " "))
    f2.metric("📥 Sommes Perçues", f"{bilan['total_encaisse']:,.0f} €".replace(",", " "))
    f3.metric("📩 Reste à percevoir", f"{bilan['reste_a_percevoir']:,.0f} €".replace(",", " "))

    st.write("")

    # --- Dépenses (maintenance.json, non migré) ---
    st.markdown("##### 💸 Sommes Dépensées")
    d1, d2, d3 = st.columns(3)
    d1.metric("🔧 Dépenses Maint.", f"{total_pure_maint:,.0f} €".replace(",", " "))
    d2.metric("📋 Charges Fixes Réelles", f"{total_reels_fixes:,.0f} €".replace(",", " "))
    d3.metric("📊 Total Dépenses", f"{total_dep:,.0f} €".replace(",", " "))

    st.write("")

    # --- Bilan net & vidange ---
    st.markdown("##### 📈 Bilan Net & Maintenance")
    m_col1, m_col2 = st.columns([1, 3])
    m_col1.metric("📊 Solde Net", f"{solde_net:,.0f} €".replace(",", " "))
    h_rest = params.get("prochaine_vidange", 2500.0) - h_moteur_abs
    with m_col2:
        st.write(f"**🔧 Vidange dans : {max(0, h_rest):.1f} h**")
        if h_rest <= 0:
            st.error(f"🚨 Échéance de vidange dépassée de {abs(h_rest):.1f} heures !")
        elif h_rest <= 20:
            st.warning(f"⚠️ Échéance de vidange proche ({h_rest:.1f} h restantes).")
        else:
            st.caption(f"Compteur absolu : {h_moteur_abs:.1f} h. Échéance : {params.get('prochaine_vidange', 2500.0):.1f} h.")

    # --- Répartition par société ---
    st.divider()
    st.markdown("### 🏢 Répartition par Société")
    repartition = repartition_par_societe(bilan["participations_retenues"], mode)
    if repartition:
        df_rep = pd.DataFrame(repartition, columns=["Société", "Montant (€)"])
        st.dataframe(
            df_rep.style.format({"Montant (€)": "{:,.2f} €"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Aucune donnée pour cette sélection.")

    # --- Graphique chronologique + seuil de rentabilité ---
    st.divider()
    st.markdown(f"### 📈 Chronologie des Recettes ({mode_bilan}) & Seuil de Rentabilité")

    recettes_mois = recettes_par_mois(croisieres, sel_y, mode)
    df_graph = pd.DataFrame({
        "Mois": range(1, 13), "NomMois": ORDRE_MOIS,
        "Recettes": recettes_mois, "Dépenses": montants_maint_mois,
    })
    df_graph["Recettes_Cumulees"] = df_graph["Recettes"].cumsum()

    maintenant = datetime.now()
    if sel_y == maintenant.year:
        df_graph["Recettes_Cumulees_Visuel"] = df_graph.apply(
            lambda x: x["Recettes_Cumulees"] if x["Mois"] <= maintenant.month else None, axis=1
        )
    else:
        df_graph["Recettes_Cumulees_Visuel"] = df_graph["Recettes_Cumulees"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df_graph["NomMois"], y=df_graph["Recettes"], name="Recettes du Mois (€)",
                          marker_color="#a3e4d7", opacity=0.5), secondary_y=False)
    fig.add_trace(go.Bar(x=df_graph["NomMois"], y=df_graph["Dépenses"], name="Dépenses du Mois (€)",
                          marker_color="#f5b7b1", opacity=0.5), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df_graph["NomMois"], y=df_graph["Recettes_Cumulees_Visuel"], name="Cumul de la Saison (€)",
        line=dict(color="#2ecc71", width=4, shape="spline"), mode="lines+markers+text",
        text=[f"{v:,.0f}€" if (v is not None and v > 0) else "" for v in df_graph["Recettes_Cumulees_Visuel"]],
        textposition="top center",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df_graph["NomMois"], y=[total_frais_fixes] * 12, name="Seuil de Rentabilité",
        line=dict(color="#e74c3c", width=2, dash="dash"), mode="lines",
    ), secondary_y=False)

    fig.update_layout(
        height=400, barmode="group", margin=dict(l=0, r=0, t=20, b=0),
        legend=dict(orientation="h", y=1.2, x=0),
        yaxis=dict(title="Montants (€)", gridcolor="#eee"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Seuil de rentabilité (résumé) ---
    st.divider()
    st.markdown("### ⚓ Seuil de Rentabilité (Point Mort Annuel)")
    ca_actuel = bilan["total_encaisse"]
    progression = min(1.0, ca_actuel / total_frais_fixes) if total_frais_fixes > 0 else 0
    manque_a_gagner = max(0.0, total_frais_fixes - ca_actuel)

    c_pm1, c_pm2 = st.columns([2, 1])
    with c_pm1:
        st.write(f"**Objectif : Couvrir les charges prévisionnelles de l'année ({int(total_frais_fixes):,} €)**".replace(",", " "))
        st.progress(progression)
        if progression >= 1:
            st.success(f"🎉 **Seuil de rentabilité atteint !** pour {sel_y}.")
        else:
            st.info(f"Il manque encore **{int(manque_a_gagner):,} €** pour équilibrer le budget annuel théorique.".replace(",", " "))
    with c_pm2:
        with st.expander("Détail des charges de référence"):
            for poste, montant in frais_params.items():
                st.write(f"{poste} : {int(montant):,} €".replace(",", " "))
            st.write("---")
            st.write(f"**TOTAL : {int(total_frais_fixes):,} €**".replace(",", " "))

    st.caption("📌 Tableaux détaillés (sommes perçues/à percevoir ligne par ligne, détail maintenance) et éditeur des charges fixes : à venir dans une prochaine étape.")
