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


def sommes_percues(croisieres_contact):
    """Total des sommes payées par ce contact, toutes croisières confondues.
    Jamais stocké : toujours recalculé à partir de croisieres.json."""
    return sum(
        c["ma_participation"].get("prix", 0) or 0
        for c in croisieres_contact
        if c["ma_participation"].get("payee")
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


def valider_croisiere(croisiere):
    """Vérifie qu'une croisière est valide avant sauvegarde. Renvoie une
    liste de messages d'erreur (vide = valide)."""
    erreurs = []
    if not croisiere.get("participants"):
        erreurs.append("Il faut au moins un participant.")
    for p in croisiere.get("participants", []):
        if not p.get("contact_id"):
            erreurs.append("Un participant n'a pas de contact associé.")
    if croisiere.get("date_debut") and not parse_date_eu(croisiere["date_debut"]):
        erreurs.append("La date de début n'est pas au format jj/mm/aaaa.")
    if not croisiere.get("jours") or croisiere["jours"] < 1:
        erreurs.append("Le nombre de jours doit être au moins 1.")
    return erreurs
