"""
page_archives.py
==================
Consultation par période (année ou plage de dates personnalisée) des
croisières, du livre de bord et des dépenses de maintenance, avec export
Excel multi-onglets.

Principe (décidé le 03/08/2026, en remplacement de l'ancien module qui
déplaçait physiquement les données) : RIEN N'EST JAMAIS DÉPLACÉ NI
SUPPRIMÉ. "Archiver" = simplement filtrer par période pour consulter ou
exporter — les données restent à leur place, dans les mêmes fichiers,
pour toujours. Zéro risque de perte de données.

Les CONTACTS ne sont jamais filtrés ici : ce sont des identités
permanentes, pas des éléments d'une saison particulière.

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, FACT, RELANCES, MAINT, LOG, MEMOS.
"""
import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from modele_voile import croisieres_entre_dates, etapes_entre_dates, noms_participants, parser_date_flexible


def _construire_excel(df_croisieres, df_etapes, df_maintenance):
    """Construit un fichier Excel en mémoire avec un onglet par type de
    donnée (seuls les onglets non vides sont inclus)."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        if not df_croisieres.empty:
            df_croisieres.to_excel(writer, sheet_name="Croisières", index=False)
        if not df_etapes.empty:
            df_etapes.to_excel(writer, sheet_name="Livre de bord", index=False)
        if not df_maintenance.empty:
            df_maintenance.to_excel(writer, sheet_name="Maintenance", index=False)
    return buffer.getvalue()


def afficher_page_archives(charger_croisieres, charger_etapes, charger_maintenance, charger_contacts):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    st.markdown("<h2 style='text-align: center;'>📂 Archives & Consultation par période</h2>", unsafe_allow_html=True)
    st.caption("Rien n'est jamais déplacé ni supprimé ici — juste filtré pour consulter ou exporter.")

    if st.button("⬅️ Retour au Planning", use_container_width=True):
        st.session_state.page = "PLANNING"
        st.rerun()

    st.divider()

    croisieres = charger_croisieres()
    etapes = charger_etapes()
    contacts = charger_contacts()
    df_maintenance = charger_maintenance()
    contacts_par_id = {c["id"]: c for c in contacts}

    # --- Choix de la période ---
    mode = st.radio("Consulter :", ["📅 Par année", "🗓️ Par plage de dates personnalisée"], horizontal=True)

    if mode == "📅 Par année":
        annee = st.selectbox("Année :", [2025, 2026, 2027, 2028], index=1)
        date_min = date(annee, 1, 1)
        date_max = date(annee, 12, 31)
        libelle_periode = f"année {annee}"
    else:
        c1, c2 = st.columns(2)
        date_min = c1.date_input("Du", value=date(date.today().year, 1, 1), format="DD/MM/YYYY")
        date_max = c2.date_input("Au", value=date.today(), format="DD/MM/YYYY")
        if date_min > date_max:
            st.error("La date de début doit être avant la date de fin.")
            return
        libelle_periode = f"du {date_min.strftime('%d/%m/%Y')} au {date_max.strftime('%d/%m/%Y')}"

    st.divider()

    # --- Filtrage ---
    croisieres_periode = croisieres_entre_dates(croisieres, date_min, date_max)
    etapes_periode = etapes_entre_dates(etapes, date_min, date_max)

    if not df_maintenance.empty:
        df_maint_copy = df_maintenance.copy()
        df_maint_copy["_dt"] = df_maint_copy["Date"].apply(parser_date_flexible)
        df_maint_periode = df_maint_copy[
            df_maint_copy["_dt"].apply(lambda d: d is not None and date_min <= d <= date_max)
        ].sort_values("_dt", ascending=False, key=lambda col: col.map(lambda d: d or date.min))
        df_maint_periode = df_maint_periode.assign(Date=df_maint_periode["_dt"].apply(lambda d: d.strftime("%d/%m/%Y"))).drop(columns=["_dt"])
    else:
        df_maint_periode = pd.DataFrame()

    # --- Indicateurs ---
    c1, c2, c3 = st.columns(3)
    c1.metric("⛵ Croisières", len(croisieres_periode))
    c2.metric("📖 Étapes livre de bord", len(etapes_periode))
    c3.metric("🛠️ Dépenses maintenance", f"{len(df_maint_periode)} fiche(s)")

    st.divider()

    # --- Construction des tableaux lisibles (avec nom du contact) ---
    lignes_croisieres = []
    for cr in croisieres_periode:
        prix_total = sum(p.get("prix", 0) or 0 for p in cr.get("participants", []))
        lignes_croisieres.append({
            "Date": cr.get("date_debut", ""),
            "Nom": cr.get("nom_croisiere") or "(sans nom)",
            "Participants": noms_participants(cr, contacts_par_id),
            "Jours": cr.get("jours", 1),
            "Prix total (€)": prix_total,
        })
    df_croisieres_aff = pd.DataFrame(lignes_croisieres)

    lignes_etapes = []
    for e in etapes_periode:
        lignes_etapes.append({
            "Date": e.get("date", ""),
            "Navigation": e.get("navigation", ""),
            "Milles": e.get("milles", 0),
            "H. Moteur": e.get("heures_moteur", 0),
            "H. Voile": e.get("heures_voile", 0),
            "Météo": e.get("meteo", ""),
            "Notes": e.get("notes", ""),
        })
    df_etapes_aff = pd.DataFrame(lignes_etapes)

    # --- Affichage en onglets ---
    t1, t2, t3 = st.tabs(["⛵ Croisières", "📖 Livre de bord", "🛠️ Maintenance"])
    with t1:
        if df_croisieres_aff.empty:
            st.info(f"Aucune croisière pour {libelle_periode}.")
        else:
            st.dataframe(df_croisieres_aff, use_container_width=True, hide_index=True)
    with t2:
        if df_etapes_aff.empty:
            st.info(f"Aucune étape de livre de bord pour {libelle_periode}.")
        else:
            st.dataframe(df_etapes_aff, use_container_width=True, hide_index=True)
    with t3:
        if df_maint_periode.empty:
            st.info(f"Aucune dépense de maintenance pour {libelle_periode}.")
        else:
            st.dataframe(df_maint_periode, use_container_width=True, hide_index=True)

    st.divider()

    # --- Export Excel ---
    st.markdown("### 📥 Export Excel de cette période")
    if df_croisieres_aff.empty and df_etapes_aff.empty and df_maint_periode.empty:
        st.caption("Rien à exporter pour cette période.")
    else:
        excel_bytes = _construire_excel(df_croisieres_aff, df_etapes_aff, df_maint_periode)
        nom_fichier = f"Vesta_Archives_{date_min.strftime('%Y%m%d')}_{date_max.strftime('%Y%m%d')}.xlsx"
        st.download_button(
            "📥 Télécharger cette période en Excel (croisières + livre de bord + maintenance)",
            data=excel_bytes, file_name=nom_fichier,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
