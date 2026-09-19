"""
calendrier_ics.py
==================
Génère le calendrier des croisières au format .ics (le format standard
lu par Outlook, l'iPhone, Google Agenda...) et le publie dans un "Gist"
GitHub secret, dont l'adresse peut être ajoutée à Outlook comme
calendrier auquel on s'abonne (mise à jour automatique côté Outlook).

CONFIDENTIALITÉ : le fichier publié ne contient PAS les noms des
participants ni les prix. Uniquement : la date, la durée et la (ou les)
société(s), par exemple "⛵ Vesta – CMN". Le Gist est "secret" : il
n'apparaît dans aucune recherche, mais toute personne qui connaît son
adresse peut le lire. Ne partage donc pas cette adresse.

Ce module ne dépend pas de Streamlit : il est testable seul.
"""
from datetime import datetime, timedelta, timezone

import requests

from modele_voile import parse_date_eu

NOM_FICHIER_GIST = "vesta.ics"


# ---------------------------------------------------------------------
# 1. Fabrication du texte .ics
# ---------------------------------------------------------------------

def _echapper(texte):
    """Dans un .ics, certains caractères ont un sens spécial et doivent
    être précédés d'un antislash : \\ ; , et le retour à la ligne."""
    return (texte.replace("\\", "\\\\").replace(";", "\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _plier_ligne(ligne):
    """Le format .ics limite une ligne à 75 octets. Au-delà, on coupe et
    on continue sur la ligne suivante en commençant par une espace."""
    octets = ligne.encode("utf-8")
    if len(octets) <= 75:
        return ligne
    morceaux, debut = [], 0
    while debut < len(octets):
        taille = 75 if debut == 0 else 74  # 1 octet réservé à l'espace initiale
        fin = min(debut + taille, len(octets))
        # ne jamais couper au milieu d'un caractère accentué/emoji
        while fin < len(octets) and (octets[fin] & 0xC0) == 0x80:
            fin -= 1
        morceaux.append(octets[debut:fin].decode("utf-8"))
        debut = fin
    return "\r\n ".join(morceaux)


def _titre_evenement(croisiere):
    societes = []
    for p in croisiere.get("participants", []):
        s = p.get("societe")
        if s and s not in societes and not p.get("annulee"):
            societes.append(s)
    return "⛵ Vesta – " + "/".join(societes) if societes else "⛵ Vesta"


def croisieres_pour_calendrier(croisieres):
    """Garde les croisières qui ont une date valide et au moins un
    participant non annulé. Une croisière annulée n'apparaît pas."""
    retenues = []
    for cr in croisieres:
        if not parse_date_eu(cr.get("date_debut")):
            continue
        participants = cr.get("participants") or []
        if participants and all(p.get("annulee") for p in participants):
            continue
        retenues.append(cr)
    return retenues


def generer_ics(croisieres, maintenant=None):
    """Renvoie le contenu complet du fichier .ics (texte)."""
    maintenant = maintenant or datetime.now(timezone.utc)
    horodatage = maintenant.strftime("%Y%m%dT%H%M%SZ")
    lignes = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vesta Skipper//Croisieres//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Vesta",
        # Indications de fréquence de rafraîchissement (Outlook en tient
        # compte à sa façon, il décide finalement lui-même)
        "REFRESH-INTERVAL;VALUE=DURATION:PT1H",
        "X-PUBLISHED-TTL:PT1H",
    ]
    for cr in croisieres_pour_calendrier(croisieres):
        debut = parse_date_eu(cr["date_debut"])
        jours = max(int(cr.get("jours") or 1), 1)
        # Événement "journée entière" : la date de fin est EXCLUE dans le
        # format .ics, donc début + nombre de jours.
        fin = debut + timedelta(days=jours)
        lignes += [
            "BEGIN:VEVENT",
            f"UID:{cr['id']}@vesta",  # identifiant stable : une mise à jour remplace, sans doublon
            f"DTSTAMP:{horodatage}",
            f"DTSTART;VALUE=DATE:{debut.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{fin.strftime('%Y%m%d')}",
            f"SUMMARY:{_echapper(_titre_evenement(cr))}",
            f"DESCRIPTION:{_echapper(str(jours) + ' jour(s)')}",
            "TRANSP:OPAQUE",
            "END:VEVENT",
        ]
    lignes.append("END:VCALENDAR")
    # Le format exige des fins de ligne "\r\n"
    return "\r\n".join(_plier_ligne(l) for l in lignes) + "\r\n"


# ---------------------------------------------------------------------
# 2. Publication dans un Gist GitHub secret
# ---------------------------------------------------------------------

def url_abonnement(utilisateur, gist_id):
    """Adresse à donner à Outlook ("S'abonner à partir du web")."""
    return f"https://gist.githubusercontent.com/{utilisateur}/{gist_id}/raw/{NOM_FICHIER_GIST}"


def publier_dans_gist(contenu_ics, gist_id, token):
    """Remplace le contenu de vesta.ics dans le Gist. Lève une erreur
    claire si GitHub refuse (mauvais token, mauvais identifiant...)."""
    reponse = requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"token {token}"},
        json={"files": {NOM_FICHIER_GIST: {"content": contenu_ics}}},
        timeout=30,
    )
    if reponse.status_code != 200:
        raise RuntimeError(f"GitHub a répondu {reponse.status_code} : {reponse.text[:200]}")
