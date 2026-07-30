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
from datetime import datetime, date


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

def tri_alphabetique(contacts):
    def cle(c):
        nom = (c.get("nom") or "").strip().upper()
        prenom = (c.get("prenom") or "").strip().upper()
        # Si le nom de famille est vide, on trie sur le prénom à la place
        # (évite que les fiches incomplètes se retrouvent toutes en tête)
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
