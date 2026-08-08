"""
page_log.py
============
Livre de bord (LOG) : saisie/modification/suppression d'étapes, vue
synthétique par navigation avec "zoom" pour le détail, export CSV.

Différences par rapport à l'ancien code :
- Lit/écrit etapes_v2.json (au lieu de logbook.json)
- Le compteur moteur (comme avant) reste en Départ/Arrivée ; les MILLES
  sont simplifiés en un seul champ "Milles parcourus" (décision du
  03/08/2026 — etapes_v2 ne garde qu'une durée, pas de compteur cumulé
  pour les milles)
- Chaque étape est reliée automatiquement à une croisière existante si sa
  date tombe dans la plage [date_debut, date_fin] d'une croisière
  (même logique que la migration d'origine)
- Le nom de navigation suggéré par défaut reprend la dernière étape
  PASSÉE si elle date de moins de 5 jours (continuité probable)
- NOUVEAU (07/08/2026) : la liste des navigations est maintenant affichée
  sous forme de TABLEAU SYNTHÉTIQUE (date, équipage, site, nb de jours).
  Cliquer sur une ligne "zoome" et affiche le détail jour par jour
  (météo, milles, moteur, etc.) juste en dessous.

NE TOUCHE PAS à CONTACTS, MODIFIER_CONTACT, PLANNING, CROISIERES,
MODIFIER_CROISIERE, STATS, FACT, RELANCES, MAINT, MEMOS, ARCHIVES.
"""
from datetime import date, datetime
import io

import pandas as pd
import streamlit as st
from openpyxl.utils import get_column_letter

from modele_voile import (
    generer_id_etape, trouver_croisiere_id_pour_date, suggestion_nom_navigation,
    ajouter_etape, modifier_etape, supprimer_etape, etapes_groupees_par_navigation,
    derniere_lecture_compteur, parse_date_eu, fond_clair,
)

PALETTE_NAVIGATION = ["#2980B9", "#27AE60", "#8E44AD", "#D35400", "#16A085", "#C0392B", "#2C3E50", "#E67E22"]


def _couleur_navigation(nom_nav):
    """Couleur stable par nom de navigation (même principe que pour les
    contacts), pour distinguer visuellement chaque voyage d'un coup d'œil."""
    return PALETTE_NAVIGATION[hash(nom_nav) % len(PALETTE_NAVIGATION)]


def _site_croisiere(croisieres, croisiere_id):
    """Retrouve le 'site' (plateforme de contact : CMN, CLICK, VOG, PERSO...)
    d'une croisière à partir de son id. Ce champ s'appelle 'societe' et se
    trouve sur chaque participant (une croisière peut avoir plusieurs
    participants) — on prend celui du premier participant."""
    if not croisiere_id:
        return "-"
    croisiere = next((c for c in croisieres if c.get("id") == croisiere_id), None)
    if not croisiere:
        return "-"
    participants = croisiere.get("participants") or []
    if participants:
        return participants[0].get("societe") or "-"
    return "-"


def _noms_equipage(liste_etapes):
    """Rassemble les noms d'équipage cités sur les étapes d'une navigation,
    sans doublons, dans l'ordre d'apparition."""
    noms_vus = []
    for e in liste_etapes:
        texte = (e.get("coequipiers_texte") or "").strip()
        if not texte:
            continue
        # Le texte peut contenir plusieurs noms séparés par des virgules
        for nom in texte.split(","):
            nom = nom.strip()
            if nom and nom not in noms_vus:
                noms_vus.append(nom)
    return ", ".join(noms_vus) if noms_vus else "-"


def _nb_jours_etape(e):
    """Nombre de jours couverts par UNE étape.
    - Cas normal (saisie quotidienne) : 1 jour.
    - Cas 'multi-jours' (une seule ligne pour toute une navigation) : on
      calcule la différence entre 'date' (départ) et 'date_fin' (arrivée),
      +1 pour compter le jour de départ lui-même.
    Si les dates sont incohérentes ou manquantes, on retombe sur 1 par
    sécurité (on ne veut jamais afficher 0 ou une valeur négative)."""
    date_fin_str = e.get("date_fin")
    if not date_fin_str:
        return 1
    d_debut = parse_date_eu(e.get("date", ""))
    d_fin = parse_date_eu(date_fin_str)
    if d_debut and d_fin and d_fin >= d_debut:
        return (d_fin - d_debut).days + 1
    return 1


def _construire_tableau_synthese(groupes, croisieres):
    """Construit le DataFrame résumé : 1 ligne par navigation.

    'groupes' est la liste (nom_navigation, liste_etapes) déjà triée par
    etapes_groupees_par_navigation. On calcule pour chaque navigation :
    - Date : la date de la première étape (début du voyage)
    - Navigation : le nom du voyage
    - Équipage : noms uniques trouvés sur les étapes
    - Site : déduit de la croisière liée (via croisiere_id)
    - Jours : somme des jours couverts par chaque étape (une étape
      'multi-jours' compte pour plusieurs jours d'un coup)
    """
    lignes = []
    for nom_nav, liste in groupes:
        # On trie les étapes par date réelle (pas par texte) pour trouver
        # la première de manière fiable, même si la saisie n'était pas
        # dans l'ordre chronologique.
        liste_triee = sorted(
            liste,
            key=lambda e: parse_date_eu(e.get("date", "")) or date.min,
        )
        premiere = liste_triee[0]
        croisiere_id = next((e.get("croisiere_id") for e in liste if e.get("croisiere_id")), None)

        # Ordre des colonnes = ordre d'affichage voulu : Date, Navigation,
        # Équipage en premier, puis le reste.
        lignes.append({
            "Date": premiere.get("date", "-"),
            "Navigation": nom_nav,
            "Équipage": _noms_equipage(liste),
            "Site": _site_croisiere(croisieres, croisiere_id),
            "Jours": sum(_nb_jours_etape(e) for e in liste),
            "Milles": sum(e.get("milles", 0) or 0 for e in liste),
        })
    return pd.DataFrame(lignes)


def _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="creation", etape_id=None):
    """Formulaire unique pour créer ou modifier une étape."""
    title = "➕ NOUVELLE ÉTAPE QUOTIDIENNE" if mode == "creation" else "📝 MODIFIER L'ÉTAPE"

    if mode == "edition" and etape_id is not None:
        e = next(x for x in etapes if x["id"] == etape_id)
        val_date = e.get("date", "")
        val_date_fin = e.get("date_fin", "") or val_date
        val_nav = e.get("navigation", "")
        val_equi = e.get("coequipiers_texte", "")
        val_meteo = e.get("meteo", "")
        val_notes = e.get("notes", "")
        val_mot_dep = float(e.get("compteur_moteur", 0.0)) - float(e.get("heures_moteur", 0.0))
        val_mot_arr = float(e.get("compteur_moteur", 0.0))
        val_milles = float(e.get("milles", 0.0))
        val_voile = float(e.get("heures_voile", 0.0))
        # Si l'étape en édition a déjà une date_fin, c'était une saisie
        # multi-jours : la case à cocher démarre donc pré-cochée.
        multi_jours_par_defaut = bool(e.get("date_fin"))
    else:
        aujourdhui = date.today()
        last_mot = derniere_lecture_compteur(etapes)
        val_date = datetime.now()
        val_date_fin = val_date
        val_nav = suggestion_nom_navigation(etapes, aujourdhui)
        val_equi = ""
        val_meteo = ""
        val_notes = ""
        val_mot_dep = last_mot
        val_mot_arr = last_mot
        val_milles = 0.0
        val_voile = 0.0
        multi_jours_par_defaut = False

    with st.expander(title, expanded=True):
        # La case à cocher est VOLONTAIREMENT en dehors du st.form : dans
        # Streamlit, les widgets à l'intérieur d'un formulaire ne
        # déclenchent pas de rafraîchissement immédiat de la page (il faut
        # attendre le bouton "Enregistrer"). Or on a besoin de savoir tout
        # de suite si on doit afficher UNE date ou DEUX (départ/arrivée)
        # pour construire le formulaire juste après.
        multi_jours = st.checkbox(
            "🗓️ Navigation de plusieurs jours (une seule ligne pour toute la période, "
            "avec les totaux météo/milles/moteur)",
            value=multi_jours_par_defaut,
            key=f"chk_multi_jours_{mode}_{etape_id}",
        )

        with st.form(key=f"form_log_{mode}"):
            f_nav = st.text_input("Nom du Voyage / Croisière", value=val_nav, placeholder="ex: Gijón 2026")

            # IMPORTANT : on donne une 'key' FIXE à chaque champ de date,
            # qui ne dépend PAS de multi_jours. Sans ça, comme le libellé
            # passe de "Date" à "Date de départ" selon la case cochée,
            # Streamlit considère qu'il s'agit d'un champ différent à
            # chaque bascule de la case — et donc oublie la date déjà
            # tapée, en revenant à sa valeur par défaut (aujourd'hui).
            # Avec une clé stable, la valeur saisie est conservée.
            key_date_debut = f"log_date_debut_{mode}_{etape_id}"
            key_date_fin = f"log_date_fin_{mode}_{etape_id}"

            if multi_jours:
                c1, c2 = st.columns(2)
                if mode == "creation":
                    f_date_debut_in = c1.date_input("Date de départ", val_date, format="DD/MM/YYYY", key=key_date_debut)
                    f_date_fin_in = c2.date_input("Date d'arrivée", val_date, format="DD/MM/YYYY", key=key_date_fin)
                else:
                    f_date_debut_in = c1.text_input("Date de départ", value=val_date, key=key_date_debut)
                    f_date_fin_in = c2.text_input("Date d'arrivée", value=val_date_fin, key=key_date_fin)
            else:
                if mode == "creation":
                    f_date_debut_in = st.date_input("Date", val_date, format="DD/MM/YYYY", key=key_date_debut)
                else:
                    f_date_debut_in = st.text_input("Date", value=val_date, key=key_date_debut)
                f_date_fin_in = None

            f_equipage = st.text_area("Équipage / Rôle", value=val_equi, height=60)

            cm1, cm2 = st.columns(2)
            f_meteo = cm1.text_input("Météo (Vent/Mer)", value=val_meteo)
            f_notes = cm2.text_area("Observations / Escale", value=val_notes, height=60)

            st.divider()
            col1, col2, col3 = st.columns(3)
            m_dep = col1.number_input("Moteur Départ (h)", value=val_mot_dep, format="%.1f", step=0.5)
            m_arr = col2.number_input("Moteur Arrivée (h)", value=val_mot_arr, format="%.1f", step=0.5)
            h_voile = col3.number_input("Heures Voile (h)", value=val_voile, format="%.1f", step=0.5)

            f_milles = st.number_input("Milles parcourus cette étape", value=val_milles, format="%.1f", step=1.0)

            b1, b2 = st.columns(2)
            if b1.form_submit_button("💾 ENREGISTRER L'ÉTAPE", use_container_width=True, type="primary"):
                # 'date' = toujours la date de DÉPART (utilisée pour le tri,
                # le regroupement par navigation, et pour retrouver la
                # croisière liée). 'date_fin' n'est renseignée qu'en mode
                # multi-jours ; sinon on la met à None pour bien indiquer
                # "étape d'un seul jour" (utile si on décoche la case en
                # modifiant une étape qui était multi-jours avant).
                date_str = f_date_debut_in.strftime("%d/%m/%Y") if mode == "creation" else f_date_debut_in
                if multi_jours:
                    date_fin_str = f_date_fin_in.strftime("%d/%m/%Y") if mode == "creation" else f_date_fin_in
                else:
                    date_fin_str = None

                d_obj = parse_date_eu(date_str)
                croisiere_id = trouver_croisiere_id_pour_date(croisieres, d_obj) if d_obj else None

                champs = {
                    "date": date_str,
                    "date_fin": date_fin_str,
                    "navigation": f_nav,
                    "coequipiers_texte": f_equipage,
                    "meteo": f_meteo,
                    "notes": f_notes,
                    "compteur_moteur": m_arr,
                    "heures_moteur": round(max(0.0, m_arr - m_dep), 2),
                    "heures_voile": h_voile,
                    "milles": f_milles,
                    "croisiere_id": croisiere_id,
                }

                if mode == "creation":
                    nouvelle = {"id": generer_id_etape(), "carburant": None, **champs}
                    etapes_maj = ajouter_etape(etapes, nouvelle)
                else:
                    etapes_maj = modifier_etape(etapes, etape_id, champs)
                    st.session_state.log_edit_id = None

                # On "oublie" volontairement les valeurs saisies pour la
                # date et la case multi-jours, sinon la prochaine ouverture
                # du formulaire "Nouvelle étape" réutiliserait par erreur
                # la dernière date tapée au lieu de repartir à zéro.
                for cle in (key_date_debut, key_date_fin, f"chk_multi_jours_{mode}_{etape_id}"):
                    st.session_state.pop(cle, None)

                sauvegarder_etapes(etapes_maj)
                st.session_state.log_saisie_ouverte = False
                st.rerun()

            if b2.form_submit_button("❌ ANNULER", use_container_width=True):
                for cle in (key_date_debut, key_date_fin, f"chk_multi_jours_{mode}_{etape_id}"):
                    st.session_state.pop(cle, None)
                st.session_state.log_saisie_ouverte = False
                st.session_state.log_edit_id = None
                st.rerun()


def _afficher_detail_navigation(nom_nav, liste, etapes, sauvegarder_etapes):
    """Affiche le détail jour par jour d'UNE navigation (le 'zoom').
    C'est exactement l'ancien affichage carte par carte, mais appelé
    uniquement pour la navigation sélectionnée dans le tableau."""
    couleur_nav = _couleur_navigation(nom_nav)
    fond_nav = fond_clair(couleur_nav)
    t_mil = sum(e.get("milles", 0) or 0 for e in liste)

    st.markdown(
        f"""
        <div style="background:{couleur_nav}; color:white; padding:10px 14px; border-radius:8px; margin-top:15px;">
            <b>🔍 Détail — {nom_nav}</b> &nbsp;|&nbsp; Distance Totale : {t_mil:.1f} NM &nbsp;|&nbsp; {len(liste)} étape(s)
        </div>
        """,
        unsafe_allow_html=True,
    )

    for e in liste:
        with st.container():
            c_txt, c_btn = st.columns([0.7, 0.3])
            with c_txt:
                # Si l'étape a une date_fin, on affiche la période complète
                # avec le nombre de jours couverts ; sinon, juste la date.
                if e.get("date_fin"):
                    nb_j = _nb_jours_etape(e)
                    label_date = f"📅 {e.get('date','')} → {e.get('date_fin','')} ({nb_j} j)"
                else:
                    label_date = f"📅 {e.get('date','')}"

                st.markdown(
                    f"""
                    <div style="background:{fond_nav}; border-left:6px solid {couleur_nav}; padding:8px 15px; border-radius:0 8px 8px 0; margin-bottom:2px; color: black;">
                        <b>{label_date}</b> | ⚙️ {e.get('heures_moteur',0):.1f}h Mot. | ⛵ {e.get('heures_voile',0):.1f}h Voile | <b>{e.get('milles',0):.1f} NM</b><br>
                        <small style="color:#34495e;">📍 Cond. Météo : {e.get('meteo') or '-'} | {e.get('notes') or ''}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_btn:
                ce, cd, cc = st.columns([1, 1, 2])
                if ce.button("✏️", key=f"e_{e['id']}"):
                    st.session_state.log_edit_id = e["id"]
                    st.rerun()

                confirm_key = f"confirm_del_log_{e['id']}"
                if not st.session_state.get(confirm_key, False):
                    if cd.button("🗑️", key=f"d_{e['id']}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    if cc.button("✅ OUI", key=f"ok_{e['id']}", type="primary"):
                        st.session_state[confirm_key] = False
                        sauvegarder_etapes(supprimer_etape(etapes, e["id"]))
                        st.toast("Étape supprimée", icon="🗑️")
                        st.rerun()
                    if cc.button("❌", key=f"no_{e['id']}"):
                        st.session_state[confirm_key] = False
                        st.rerun()


def afficher_page_log(charger_etapes, sauvegarder_etapes, charger_croisieres):
    """Point d'entrée de la page. Fonctions injectées depuis app_voile1.py."""

    st.markdown(
        '<div style="text-align:center; background-color:#2c3e50; color:white; padding:10px; border-radius:10px;">'
        "<h1>📖 Livre de Bord & Statistiques</h1></div>",
        unsafe_allow_html=True,
    )

    etapes = charger_etapes()
    croisieres = charger_croisieres()

    if "log_saisie_ouverte" not in st.session_state:
        st.session_state.log_saisie_ouverte = False
    if "log_edit_id" not in st.session_state:
        st.session_state.log_edit_id = None

    if st.session_state.log_edit_id is not None:
        _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="edition", etape_id=st.session_state.log_edit_id)
    elif st.session_state.log_saisie_ouverte:
        _formulaire_etape(etapes, croisieres, sauvegarder_etapes, mode="creation")
    else:
        if st.button("➕ NOUVELLE ÉTAPE QUOTIDIENNE", use_container_width=True):
            st.session_state.log_saisie_ouverte = True
            st.rerun()

    # --- Vue synthétique (1 ligne = 1 navigation) + zoom ---
    if etapes:
        st.divider()
        groupes = etapes_groupees_par_navigation(etapes)
        # dict pratique pour retrouver la liste d'étapes à partir du nom
        # de navigation (utilisé après la sélection dans le tableau)
        groupes_par_nom = dict(groupes)

        df_synthese = _construire_tableau_synthese(groupes, croisieres)

        st.markdown("#### 🗂️ Vue d'ensemble des navigations")
        st.caption("Clique sur une ligne du tableau pour afficher le détail jour par jour.")

        selection = st.dataframe(
            df_synthese,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            use_container_width=True,
            column_config={
                "Milles": st.column_config.NumberColumn(format="%.1f NM"),
            },
        )

        lignes_selectionnees = selection.selection.rows
        if lignes_selectionnees:
            idx = lignes_selectionnees[0]
            nom_nav_choisi = df_synthese.iloc[idx]["Navigation"]
            liste_choisie = groupes_par_nom[nom_nav_choisi]
            _afficher_detail_navigation(nom_nav_choisi, liste_choisie, etapes, sauvegarder_etapes)
        else:
            st.info("Aucune navigation sélectionnée — clique sur une ligne ci-dessus pour voir le détail.")

    # --- Export XLSX (Excel) ---
    if etapes:
        st.divider()
        df_export = pd.DataFrame(etapes)

        # On écrit le fichier Excel en mémoire (pas sur le disque), dans un
        # "buffer" — c'est l'équivalent d'un fichier temporaire mais qui
        # reste en RAM, plus simple à donner ensuite au bouton de
        # téléchargement de Streamlit.
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_export.to_excel(writer, index=False, sheet_name="Livre de bord")
            feuille = writer.sheets["Livre de bord"]

            # Auto-largeur : pour chaque colonne, on mesure la longueur du
            # texte le plus long (soit une valeur de la colonne, soit son
            # en-tête si les valeurs sont plus courtes), et on règle la
            # largeur en conséquence (+2 pour un peu de marge visuelle).
            for i, colonne in enumerate(df_export.columns, start=1):
                if df_export.empty:
                    longueur_max = len(str(colonne))
                else:
                    longueur_max = max(
                        df_export[colonne].astype(str).map(len).max(),
                        len(str(colonne)),
                    )
                feuille.column_dimensions[get_column_letter(i)].width = longueur_max + 2

        st.download_button(
            label="📥 Télécharger le Livre de Bord complet (.XLSX)",
            data=buffer.getvalue(),
            file_name="livre_de_bord_vesta.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
