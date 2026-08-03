"""
modele_voile.py
================
Toute la logique liée aux contacts, croisières et prospects, séparée du
code d'affichage (Streamlit). Objectif : que app_voile1.py reste lisible,
et que cette logique soit testable sans lancer l'app.

Principe central (décidé le 30/07/2026) : `croisieres.json` est la seule
source de vérité pour tout ce qui concerne une navigation (statut, prix,
paiement). `contacts.json` ne stocke JAMAIS de somme perçue ni d'historique
— ces valeurs sont toujours calculées ici, à partir de croisieres.json.
"""
from datetime import datetime, date, timedelta
import uuid


# ---------------------------------------------------------------------
# 1. Dates (format européen partout : jj/mm/aaaa)
# ---------------------------------------------------------------------

def parse_date_eu(date_str):
    """Convertit 'jj/mm/aaaa' en objet date. Renvoie None si vide/invalide."""
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


# ---------------------------------------------------------------------
# 2. Règles sur une participation à une croisière
#    (une "participation" = une entrée de la liste participants[])
# ---------------------------------------------------------------------

def est_en_cours(participation):
    """Une navigation est 'en cours' tant qu'elle n'est ni terminée ni annulée."""
    return not participation.get("terminee") and not participation.get("annulee")


def est_classee(participation):
    """'Classée' = terminée ET (payée OU gratuite)."""
    prix = participation.get("prix", 0) or 0
    return bool(participation.get("terminee")) and (bool(participation.get("payee")) or prix == 0)


# ---------------------------------------------------------------------
# 3. Croisières liées à un contact
# ---------------------------------------------------------------------

def croisieres_du_contact(croisieres, contact_id):
    """Renvoie la liste des croisières où ce contact participe, chacune
    accompagnée de SA participation (ma_participation), triées de la plus
    récente à la plus ancienne (ordre chronologique inversé, comme demandé)."""
    resultat = []
    for c in croisieres:
        for p in c.get("participants", []):
            if p.get("contact_id") == contact_id:
                resultat.append({**c, "ma_participation": p})
                break  # un contact n'apparaît qu'une fois par croisière
    resultat.sort(key=lambda c: parse_date_eu(c.get("date_debut")) or date.min, reverse=True)
    return resultat


def montant_encaisse(participation):
    """Montant réellement encaissé pour UNE participation :
    - si payée intégralement : le prix en entier
    - sinon : l'acompte versé (0€ si aucun acompte)
    Centralisé ici pour que CONTACTS et STATS calculent ce montant de la
    MÊME façon (évite d'avoir deux logiques différentes qui divergent)."""
    if participation.get("payee"):
        return participation.get("prix", 0) or 0
    return participation.get("acompte", 0) or 0


def sommes_percues(croisieres_contact):
    """Total des sommes réellement encaissées par ce contact, toutes
    croisières confondues (prix si payée, sinon acompte versé).
    Jamais stocké : toujours recalculé à partir de croisieres.json."""
    return sum(
        montant_encaisse(c["ma_participation"])
        for c in croisieres_contact
    )


def nb_navigations_classees(croisieres_contact):
    return sum(1 for c in croisieres_contact if est_classee(c["ma_participation"]))


# ---------------------------------------------------------------------
# 4. Prospects (interets.json) liés à un contact
# ---------------------------------------------------------------------

def interets_du_contact(interets, contact_id):
    resultat = [i for i in interets if i.get("contact_id") == contact_id]
    resultat.sort(key=lambda i: parse_date_eu(i.get("date_demande")) or date.min, reverse=True)
    return resultat


# ---------------------------------------------------------------------
# 5. Filtres de la page Contacts (En cours / Habitué / Passé / Sans suite)
#    Ce sont des filtres COMBINABLES, pas des onglets exclusifs
#    (décision du 30/07/2026) : un contact peut cocher plusieurs cases.
# ---------------------------------------------------------------------

def filtres_contact(croisieres_contact, interets_contact):
    """Calcule, pour un contact donné, à quels filtres il correspond."""
    en_cours = any(est_en_cours(c["ma_participation"]) for c in croisieres_contact)
    habitue_auto = nb_navigations_classees(croisieres_contact) >= 2

    interets_actifs = [i for i in interets_contact if not i.get("sans_suite")]
    interets_sans_suite = [i for i in interets_contact if i.get("sans_suite")]

    a_navigue = len(croisieres_contact) > 0
    passe = a_navigue and not en_cours

    # "Sans suite" : uniquement des prospects, jamais devenu client, et
    # tous ses prospects ont été marqués sans suite à la main.
    sans_suite = (not a_navigue) and len(interets_contact) > 0 and len(interets_actifs) == 0

    return {
        "en_cours": en_cours,
        "habitue_auto": habitue_auto,
        "passe": passe,
        "sans_suite": sans_suite,
        "a_un_interet_actif": len(interets_actifs) > 0,
    }


# ---------------------------------------------------------------------
# 6. Tri alphabétique des fiches contact
# ---------------------------------------------------------------------

def tri_alphabetique(contacts, critere="nom"):
    """Trie les contacts par ordre alphabétique.

    critere="nom" (par défaut, comportement historique) : tri par nom de
    famille, prénom en critère secondaire en cas d'égalité. Si le nom est
    vide, on retombe sur le prénom pour ne pas perdre la fiche en tête de
    liste.

    critere="prenom" : même logique mais inversée (prénom en premier,
    nom en secondaire)."""
    def cle(c):
        nom = (c.get("nom") or "").strip().upper()
        prenom = (c.get("prenom") or "").strip().upper()
        if critere == "prenom":
            return (prenom or nom, nom)
        return (nom or prenom, prenom)
    return sorted(contacts, key=cle)


# ---------------------------------------------------------------------
# 7. Recherche (nom, prénom ou société d'une de ses croisières)
# ---------------------------------------------------------------------

def contact_correspond_recherche(contact, croisieres_contact, texte_recherche):
    if not texte_recherche:
        return True
    t = texte_recherche.strip().upper()
    if t in contact.get("nom", "").upper() or t in contact.get("prenom", "").upper():
        return True
    for c in croisieres_contact:
        if t in c["ma_participation"].get("societe", "").upper():
            return True
    return False


# ---------------------------------------------------------------------
# 8. Génération d'ID pour un NOUVEAU contact créé depuis l'app
#    (AJOUTÉ le 31/07/2026 — manquait par rapport au récap de session)
# ---------------------------------------------------------------------

def generer_id_contact():
    """Génère un identifiant unique pour un nouveau contact.

    Pourquoi un ID ALÉATOIRE et pas dérivé du nom (comme dans la
    migration) ? Parce que deux personnes différentes peuvent porter
    le même nom (ex: deux 'Martin Dupont'). Un ID basé sur le nom
    créerait un risque de collision. uuid4() génère un nombre quasi
    impossible à obtenir deux fois par hasard.

    Format : 'c-' + 8 caractères hexadécimaux, ex. 'c-4f3a9b21'.
    Le préfixe 'c-' garde la cohérence visuelle avec les IDs générés
    par le script de migration (voir contacts_v2.json).
    """
    return f"c-{uuid.uuid4().hex[:8]}"


def generer_nom_fichier_photo(contact_id, index):
    """Construit le nom de fichier d'une photo de contact.
    Ex: generer_nom_fichier_photo('c-4f3a9b21', 1) -> 'photos/c-4f3a9b21_1.jpg'
    Centralisé ici pour que stockage_photos.py et page_modifier_contact.py
    utilisent TOUJOURS la même convention de nommage (évite les bugs de
    photos "orphelines" ou introuvables)."""
    return f"photos/{contact_id}_{index}.jpg"


# ---------------------------------------------------------------------
# 9. Fonctions pour la page PLANNING (AJOUTÉ le 31/07/2026)
# ---------------------------------------------------------------------

def derniere_lecture_compteur(etapes):
    """Dernière lecture connue du compteur moteur cumulé (comme un
    compteur kilométrique), utilisée pour l'alerte vidange.

    IMPORTANT : on prend le MAX de 'compteur_moteur' sur toutes les
    étapes, jamais une somme. Une somme serait faussée par les anomalies
    de saisie du journal d'origine (ex: une étape avec une durée
    négative). Le compteur cumulé, lui, ne ment pas : c'est une lecture
    directe, pas un calcul."""
    valeurs = [e.get("compteur_moteur", 0) or 0 for e in etapes]
    return max(valeurs) if valeurs else 0.0


def date_fin_croisiere(croisiere):
    """Renvoie la date de fin (date object) d'une croisière, ou None si
    la date de début est manquante/invalide."""
    d_debut = parse_date_eu(croisiere.get("date_debut"))
    if not d_debut:
        return None
    jours = croisiere.get("jours") or 1
    return d_debut + timedelta(days=max(jours - 1, 0))


def croisieres_du_mois(croisieres, annee, mois):
    """Renvoie les croisières qui touchent le mois/année donnés (une
    croisière à cheval sur 2 mois apparaît dans les deux), triées par
    date de début."""
    resultat = []
    for cr in croisieres:
        d_debut = parse_date_eu(cr.get("date_debut"))
        if not d_debut:
            continue
        d_fin = date_fin_croisiere(cr)
        # Ce mois est concerné si l'intervalle [d_debut, d_fin] touche
        # le 1er ou le dernier jour du mois demandé
        premier_jour_mois = date(annee, mois, 1)
        dernier_jour_mois = date(annee, mois, calendar_dernier_jour(annee, mois))
        if d_debut <= dernier_jour_mois and d_fin >= premier_jour_mois:
            resultat.append(cr)
    resultat.sort(key=lambda cr: parse_date_eu(cr.get("date_debut")) or date.min)
    return resultat


def calendar_dernier_jour(annee, mois):
    """Nombre de jours dans le mois (évite d'importer le module calendar
    dans modele_voile.py juste pour ça)."""
    if mois == 12:
        return 31
    return (date(annee, mois + 1, 1) - timedelta(days=1)).day


def nb_participants_impayes(croisieres):
    """Nombre de participations non annulées et non payées, toutes
    croisières confondues (sert à l'alerte 'factures en attente')."""
    return sum(
        1 for cr in croisieres for p in cr.get("participants", [])
        if not p.get("annulee") and not p.get("payee")
    )


COULEURS_SOCIETE = {
    "CMN": "#3498db",
    "CLICK": "#27AE60",
    "VOG": "#8E44AD",
    "PERSO": "#F1C40F",
}


def couleur_croisiere(croisiere):
    """Couleur d'affichage d'une croisière dans le calendrier : grise si
    annulée, sinon couleur de la première société trouvée parmi les
    participants (ou gris par défaut si société inconnue)."""
    participants = croisiere.get("participants", [])
    if participants and all(p.get("annulee") for p in participants):
        return "#BDC3C7"
    societe = (participants[0].get("societe") if participants else "") or "PERSO"
    return COULEURS_SOCIETE.get(societe.upper(), "#7F8C8D")


def noms_participants(croisiere, contacts_par_id):
    """Construit un texte lisible des participants d'une croisière, ex.
    'BENOIT COURONNE + 1' pour l'afficher dans la liste des missions."""
    participants = croisiere.get("participants", [])
    if not participants:
        return "(sans participant)"
    premier = contacts_par_id.get(participants[0]["contact_id"])
    nom = f"{premier['prenom']} {premier['nom']}".strip() if premier else "?"
    if len(participants) > 1:
        nom += f" + {len(participants) - 1}"
    return nom


# ---------------------------------------------------------------------
# 10. Fonctions pour la page CROISIÈRE (AJOUTÉ le 31/07/2026)
# ---------------------------------------------------------------------

def generer_id_croisiere():
    """ID aléatoire pour une nouvelle croisière créée depuis l'app (même
    principe que generer_id_contact : pas de collision possible)."""
    return f"cr-{uuid.uuid4().hex[:8]}"


def rechercher_contacts(contacts, texte_recherche, max_resultats=8):
    """Recherche de contacts par nom/prénom, pour choisir un participant
    à la création d'une croisière. Renvoie une liste (courte, limitée à
    max_resultats) plutôt qu'un menu déroulant géant avec les 39+ noms."""
    if not texte_recherche or not texte_recherche.strip():
        return []
    t = texte_recherche.strip().upper()
    resultats = [
        c for c in contacts
        if t in (c.get("nom") or "").upper() or t in (c.get("prenom") or "").upper()
    ]
    return resultats[:max_resultats]


def croisieres_depuis(croisieres, date_min):
    """Filtre les croisières dont la date de début est >= date_min (objet
    date). Les croisières sans date valide sont exclues (pas de sens à
    les classer dans une plage de dates)."""
    resultat = []
    for cr in croisieres:
        d = parse_date_eu(cr.get("date_debut"))
        if d and d >= date_min:
            resultat.append(cr)
    resultat.sort(key=lambda cr: parse_date_eu(cr.get("date_debut")) or date.min, reverse=True)
    return resultat


CAPACITE_MAX_BATEAU = 6  # skipper compris


def nb_personnes_a_bord(croisiere):
    """Compte le nombre total de personnes prévues pour cette croisière,
    SKIPPER COMPRIS : toi + chaque participant + ses accompagnants."""
    total = 1  # le skipper
    for p in croisiere.get("participants", []):
        total += 1
        total += len(p.get("accompagnants", []) or [])
    return total


def valider_croisiere(croisiere):
    """Vérifie qu'une croisière est valide avant sauvegarde. Renvoie une
    liste de messages d'erreur (vide = valide)."""
    erreurs = []
    if not croisiere.get("participants"):
        erreurs.append("Il faut au moins un participant.")
    for p in croisiere.get("participants", []):
        if not p.get("contact_id"):
            erreurs.append("Un participant n'a pas de contact associé.")
        if (p.get("acompte", 0) or 0) > (p.get("prix", 0) or 0):
            erreurs.append("L'acompte d'un participant ne peut pas dépasser son prix.")
    if croisiere.get("date_debut") and not parse_date_eu(croisiere["date_debut"]):
        erreurs.append("La date de début n'est pas au format jj/mm/aaaa.")
    if not croisiere.get("jours") or croisiere["jours"] < 1:
        erreurs.append("Le nombre de jours doit être au moins 1.")
    nb_total = nb_personnes_a_bord(croisiere)
    if nb_total > CAPACITE_MAX_BATEAU:
        erreurs.append(
            f"Trop de monde à bord : {nb_total} personnes (skipper compris), "
            f"maximum {CAPACITE_MAX_BATEAU}."
        )
    return erreurs


def filtrer_temporel(croisieres, mode, aujourdhui):
    """Filtre les croisières selon leur position dans le temps.
    mode : 'toutes', 'passees' (déjà terminées à la date du jour) ou
    'futures' (à venir, y compris aujourd'hui même).
    Les croisières sans date valide sont exclues des filtres 'passees' et
    'futures' (impossible de savoir où les classer), mais gardées dans 'toutes'."""
    if mode == "toutes":
        return list(croisieres)
    resultat = []
    for cr in croisieres:
        d_fin = date_fin_croisiere(cr)
        if not d_fin:
            continue
        if mode == "passees" and d_fin < aujourdhui:
            resultat.append(cr)
        elif mode == "futures" and d_fin >= aujourdhui:
            resultat.append(cr)
    return resultat


def trier_croisieres(croisieres, contacts_par_id, critere="date_desc"):
    """Trie une liste de croisières.
    critere : 'date_desc' (plus récent d'abord, défaut), 'date_asc',
    'nom' (nom de famille du 1er participant), 'prenom' (idem, prénom)."""
    def cle_nom_prenom(cr, champ):
        participants = cr.get("participants", [])
        if not participants:
            return ""
        contact = contacts_par_id.get(participants[0].get("contact_id"))
        if not contact:
            return ""
        return (contact.get(champ) or "").strip().upper()

    if critere == "date_asc":
        return sorted(croisieres, key=lambda cr: parse_date_eu(cr.get("date_debut")) or date.min)
    if critere == "nom":
        return sorted(croisieres, key=lambda cr: cle_nom_prenom(cr, "nom"))
    if critere == "prenom":
        return sorted(croisieres, key=lambda cr: cle_nom_prenom(cr, "prenom"))
    # date_desc par défaut : plus récent en premier (ordre chronologique inversé, comme le reste de l'app)
    return sorted(croisieres, key=lambda cr: parse_date_eu(cr.get("date_debut")) or date.min, reverse=True)


# ---------------------------------------------------------------------
# 11. Fonctions pour la page STATS (AJOUTÉ le 01/08/2026)
# ---------------------------------------------------------------------

def participations_annee(croisieres, annee):
    """Renvoie une liste 'à plat' : une entrée par PARTICIPANT (pas par
    croisière), pour toutes les croisières qui démarrent dans l'année
    donnée. Les participations ANNULÉES sont exclues (comme l'ancien
    code qui excluait 'annule/refuse' du calcul financier)."""
    resultat = []
    for cr in croisieres:
        d = parse_date_eu(cr.get("date_debut"))
        if not d or d.year != annee:
            continue
        for p in cr.get("participants", []):
            if p.get("annulee"):
                continue
            resultat.append({
                **p,
                "date_debut": cr.get("date_debut"),
                "jours": cr.get("jours", 1),
                "nom_croisiere": cr.get("nom_croisiere"),
                "croisiere_id": cr["id"],
            })
    return resultat


def bilan_financier_annee(croisieres, annee, mode="reel"):
    """Calcule les indicateurs financiers de l'année.
    mode='reel' (Réel Encaissé) ou 'previsionnel' (CA prévu total)."""
    participations = participations_annee(croisieres, annee)
    total_ca = sum(p.get("prix", 0) or 0 for p in participations)
    total_encaisse = sum(montant_encaisse(p) for p in participations)
    reste = total_ca - total_encaisse
    nb_sorties = sum(1 for p in participations if (p.get("prix", 0) or 0) > 0)

    # Participations "retenues" pour la répartition par société : en mode
    # réel, uniquement celles avec un montant encaissé > 0 (comme l'ancien
    # code, qui ne comptait que Montant_Encaisse > 0)
    participations_retenues = (
        [p for p in participations if montant_encaisse(p) > 0]
        if mode == "reel" else participations
    )

    return {
        "total_ca": total_ca,
        "total_encaisse": total_encaisse,
        "reste_a_percevoir": reste,
        "nb_sorties": nb_sorties,
        "participations": participations,
        "participations_retenues": participations_retenues,
    }


def repartition_par_societe(participations, mode="reel"):
    """Regroupe le montant (encaissé en mode réel, prix en mode
    prévisionnel) par société. Renvoie une liste [(société, montant), ...]
    triée du plus gros au plus petit."""
    totaux = {}
    for p in participations:
        soc = (p.get("societe") or "PERSO").strip().upper()
        valeur = montant_encaisse(p) if mode == "reel" else (p.get("prix", 0) or 0)
        totaux[soc] = totaux.get(soc, 0) + valeur
    return sorted(totaux.items(), key=lambda x: x[1], reverse=True)


def etapes_annee(etapes, annee):
    """Étapes du livre de bord dont la date tombe dans l'année donnée."""
    resultat = []
    for e in etapes:
        d = parse_date_eu(e.get("date"))
        if d and d.year == annee:
            resultat.append(e)
    return resultat


def bilan_navigation_annee(etapes, annee):
    """Milles, heures moteur/voile et ratio voile/total pour l'année."""
    etapes_y = etapes_annee(etapes, annee)
    total_milles = sum(e.get("milles", 0) or 0 for e in etapes_y)
    total_h_moteur = sum(e.get("heures_moteur", 0) or 0 for e in etapes_y)
    total_h_voile = sum(e.get("heures_voile", 0) or 0 for e in etapes_y)
    total_heures_mer = total_h_moteur + total_h_voile
    ratio_voile = (total_h_voile / total_heures_mer * 100) if total_heures_mer > 0 else 0.0
    return {
        "total_milles": total_milles,
        "total_h_moteur": total_h_moteur,
        "total_h_voile": total_h_voile,
        "ratio_voile": ratio_voile,
    }


def recettes_par_mois(croisieres, annee, mode="reel"):
    """Renvoie une liste de 12 montants (janvier à décembre) : les
    recettes du mois, pour tracer le graphique chronologique."""
    montants = [0.0] * 12
    for cr in croisieres:
        d = parse_date_eu(cr.get("date_debut"))
        if not d or d.year != annee:
            continue
        for p in cr.get("participants", []):
            if p.get("annulee"):
                continue
            valeur = montant_encaisse(p) if mode == "reel" else (p.get("prix", 0) or 0)
            montants[d.month - 1] += valeur
    return montants


# ---------------------------------------------------------------------
# 12. Fonctions pour la page FACT (AJOUTÉ le 02/08/2026)
# ---------------------------------------------------------------------

def toutes_participations(croisieres, exclure_annulees=True):
    """Liste 'à plat' de toutes les participations, toutes croisières et
    toutes années confondues (contrairement à participations_annee, qui
    filtre sur une saison). Utile pour FACT : une facture impayée d'une
    année passée reste due, elle ne doit pas disparaître.
    Chaque entrée garde 'croisiere_id' et 'participant_index', pour
    pouvoir la retrouver et la modifier plus tard (marquer_participant_paye)."""
    resultat = []
    for cr in croisieres:
        for i, p in enumerate(cr.get("participants", [])):
            if exclure_annulees and p.get("annulee"):
                continue
            resultat.append({
                **p,
                "croisiere_id": cr["id"],
                "participant_index": i,
                "date_debut": cr.get("date_debut"),
                "nom_croisiere": cr.get("nom_croisiere"),
            })
    return resultat


def bilan_facturation(croisieres):
    """Bilan de facturation TOUTES ANNÉES CONFONDUES (une facture
    impayée ne doit pas disparaître au changement de saison). Les
    croisières annulées ne comptent pas (rien à facturer)."""
    participations = toutes_participations(croisieres, exclure_annulees=True)
    total_ca = sum(p.get("prix", 0) or 0 for p in participations)
    total_encaisse = sum(montant_encaisse(p) for p in participations)
    reste = total_ca - total_encaisse

    a_encaisser = [p for p in participations if not p.get("payee")]
    payees = [p for p in participations if p.get("payee")]

    # "À encaisser" : les plus anciennes en premier (les plus en retard
    # sont donc en tête, ce qui attire l'œil en premier)
    a_encaisser.sort(key=lambda p: parse_date_eu(p.get("date_debut")) or date.min)
    # "Payées" : ordre chronologique inversé, comme partout ailleurs
    payees.sort(key=lambda p: parse_date_eu(p.get("date_debut")) or date.min, reverse=True)

    return {
        "total_ca": total_ca,
        "total_encaisse": total_encaisse,
        "reste_a_percevoir": reste,
        "a_encaisser": a_encaisser,
        "payees": payees,
    }


def marquer_participant_paye(croisieres, croisiere_id, participant_index, payee):
    """Marque UN participant comme payé/non payé, en modifiant SEULEMENT
    la croisière concernée (aucune autre touchée). Cohérent avec l'ancien
    comportement de FACT : encaisser = acompte mis au niveau du prix ;
    annuler le paiement = acompte remis à 0."""
    resultat = []
    for cr in croisieres:
        if cr["id"] == croisiere_id:
            cr = dict(cr)
            cr["participants"] = [dict(p) for p in cr["participants"]]
            participant = cr["participants"][participant_index]
            participant["payee"] = payee
            participant["acompte"] = participant.get("prix", 0) if payee else 0.0
        resultat.append(cr)
    return resultat


def est_en_retard(participation, aujourdhui):
    """Une participation est en retard si sa date de début est passée et
    qu'elle n'est toujours pas payée."""
    d = parse_date_eu(participation.get("date_debut"))
    return bool(d and d < aujourdhui and not participation.get("payee"))


def participations_cmn_impayees(croisieres):
    """Participations CMN non payées (hors annulées), toutes années
    confondues — sert au module d'envoi groupé du relevé mensuel CMN."""
    return [
        p for p in toutes_participations(croisieres)
        if "CMN" in (p.get("societe") or "").upper() and not p.get("payee")
    ]


# ---------------------------------------------------------------------
# 13. Fonctions pour l'onglet "À relancer" (AJOUTÉ le 02/08/2026)
# ---------------------------------------------------------------------

def prospects_actifs(interets):
    """Prospects qui ne sont PAS marqués 'sans suite' (champ 100% manuel)."""
    return [i for i in interets if not i.get("sans_suite")]


def trier_relances(interets):
    """Trie les prospects actifs par date de relance croissante : les
    plus urgents (en retard, donc date la plus ancienne) en premier.
    Les prospects sans date de relance renseignée sont mis en toute fin."""
    actifs = prospects_actifs(interets)
    return sorted(actifs, key=lambda i: parse_date_eu(i.get("prochaine_relance")) or date.max)


def relance_en_retard(interet, aujourdhui):
    d = parse_date_eu(interet.get("prochaine_relance"))
    return bool(d and d < aujourdhui)


def relance_proche(interet, aujourdhui, fenetre_jours=7):
    """Relance prévue dans les prochains jours (mais pas encore en retard)."""
    d = parse_date_eu(interet.get("prochaine_relance"))
    if not d:
        return False
    return aujourdhui <= d <= aujourdhui + timedelta(days=fenetre_jours)


def marquer_sans_suite(interets, interet_id):
    """Marque un prospect comme 'sans suite'. Ne touche à aucun autre
    prospect (réécriture complète de interets.json à chaque fois)."""
    resultat = []
    for i in interets:
        i = dict(i)
        if i["id"] == interet_id:
            i["sans_suite"] = True
        resultat.append(i)
    return resultat


def reporter_relance(interets, interet_id, nouvelle_date_str):
    """Change la date de prochaine relance d'un prospect."""
    resultat = []
    for i in interets:
        i = dict(i)
        if i["id"] == interet_id:
            i["prochaine_relance"] = nouvelle_date_str
        resultat.append(i)
    return resultat


# ---------------------------------------------------------------------
# 14. Fonctions pour la page LOG (AJOUTÉ le 03/08/2026)
# ---------------------------------------------------------------------

def generer_id_etape():
    """ID aléatoire pour une nouvelle étape créée depuis l'app (même
    principe que generer_id_contact / generer_id_croisiere)."""
    return f"e-{uuid.uuid4().hex[:8]}"


def trouver_croisiere_id_pour_date(croisieres, d):
    """Cherche une croisière dont la plage [date_debut, date_fin] couvre
    la date donnée. Renvoie son id, ou None si aucune (= sortie perso,
    comme pour les étapes #0, #1, #15 de la migration d'origine)."""
    for cr in croisieres:
        d_debut = parse_date_eu(cr.get("date_debut"))
        if not d_debut:
            continue
        d_fin = date_fin_croisiere(cr)
        if d_fin and d_debut <= d <= d_fin:
            return cr["id"]
    return None


def suggestion_nom_navigation(etapes, aujourdhui, fenetre_jours=5):
    """Propose le nom de la dernière étape enregistrée SI elle date de
    moins de `fenetre_jours` jours (continuité probable de la même
    croisière). Renvoie une chaîne vide sinon."""
    if not etapes:
        return ""
    etapes_datees = [(parse_date_eu(e.get("date")), e) for e in etapes]
    etapes_datees = [(d, e) for d, e in etapes_datees if d and d <= aujourdhui]
    if not etapes_datees:
        return ""
    d_derniere, derniere = max(etapes_datees, key=lambda x: x[0])
    ecart = (aujourdhui - d_derniere).days
    if 0 <= ecart < fenetre_jours:
        return derniere.get("navigation", "")
    return ""


def ajouter_etape(etapes, nouvelle_etape):
    """Ajoute une étape à la liste (ne touche à aucune autre)."""
    return list(etapes) + [nouvelle_etape]


def modifier_etape(etapes, etape_id, champs_maj):
    """Met à jour UNE étape (par id) avec les champs fournis, sans
    toucher aux autres."""
    resultat = []
    for e in etapes:
        if e["id"] == etape_id:
            e = {**e, **champs_maj}
        resultat.append(e)
    return resultat


def supprimer_etape(etapes, etape_id):
    return [e for e in etapes if e["id"] != etape_id]


def etapes_groupees_par_navigation(etapes):
    """Groupe les étapes par nom de navigation, chaque groupe trié par
    date décroissante ; les groupes eux-mêmes triés par date de la plus
    récente étape du groupe (ordre chronologique inversé global)."""
    groupes = {}
    for e in etapes:
        nom = e.get("navigation") or "Navigation Hors-Croisière"
        groupes.setdefault(nom, []).append(e)

    resultat = []
    for nom, liste in groupes.items():
        liste_triee = sorted(liste, key=lambda e: parse_date_eu(e.get("date")) or date.min, reverse=True)
        date_max = max((parse_date_eu(e.get("date")) or date.min) for e in liste_triee)
        resultat.append((nom, liste_triee, date_max))

    resultat.sort(key=lambda x: x[2], reverse=True)
    return [(nom, liste) for nom, liste, _ in resultat]
