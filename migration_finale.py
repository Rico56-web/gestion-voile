"""
migration_finale.py
====================
Migre les anciens fichiers (contacts.json mélangé + logbook.json) vers le
nouveau modèle à 4 fichiers : contacts_v2.json, croisieres_v2.json,
interets_v2.json, etapes_v2.json.

Reconstruit le 31/07/2026 (le script d'origine avait été perdu), à partir
des vraies données et des corrections déjà documentées dans le récap de
session. Reproductible : mêmes IDs à chaque exécution (dérivés d'un hash),
contrairement à generer_id_contact() dans modele_voile.py qui utilise des
IDs aléatoires pour les contacts créés depuis l'app.

Corrections appliquées (toutes documentées ci-dessous, aucune décision
silencieuse) :
  1. 3 inversions jour/mois dans le livre de bord (étapes n°5, 19, 25)
  2. Étape n°12 : date corrigée en 06/02/2026
  3. Réservation CMN du 05/02/2026 : durée corrigée à 2 jours
  4. Fusion Benoît Couronne + Pedro Bandim Faustino (14/03/2026) en une
     seule croisière à 2 participants
  5. Ligne "Sophie Younes" (25/04/2026) ignorée : doublon de saisie de la
     réservation CMN confirmée ce même jour
"""
import hashlib
import json
from datetime import datetime, timedelta

FICHIER_CONTACTS_SOURCE = "contacts.json"
FICHIER_LOGBOOK_SOURCE = "logbook.json"


# ---------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------

def id_stable(*parts):
    """ID reproductible dérivé d'un hash (contrairement aux IDs aléatoires
    utilisés pour les contacts créés depuis l'app). Permet de relancer la
    migration plusieurs fois et d'obtenir toujours les mêmes IDs."""
    texte = "|".join(str(p) for p in parts)
    return hashlib.md5(texte.encode("utf-8")).hexdigest()[:8]


def normaliser_date(date_brute):
    """Convertit les différents formats rencontrés dans contacts.json
    ('JJ/MM/AAAA', 'AAAA-MM-JJ', vide, None) vers 'JJ/MM/AAAA' uniforme."""
    if not date_brute:
        return ""
    s = str(date_brute).strip()
    if not s:
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return s  # format inconnu : on garde tel quel, signalé séparément


def decoder_date_logbook(valeur):
    """Le livre de bord stocke les dates en millisecondes epoch (sauf la
    toute dernière ligne, déjà en texte JJ/MM/AAAA)."""
    if isinstance(valeur, (int, float)):
        return datetime.utcfromtimestamp(valeur / 1000).strftime("%d/%m/%Y")
    return str(valeur) if valeur else ""


def jours_entre(date_debut_str, date_fin_str):
    d1 = datetime.strptime(date_debut_str, "%d/%m/%Y").date()
    d2 = datetime.strptime(date_fin_str, "%d/%m/%Y").date()
    return (d2 - d1).days


def to_float(v, defaut=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return defaut


def to_int(v, defaut=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return defaut


# ---------------------------------------------------------------------
# Étape 1 : charger les sources
# ---------------------------------------------------------------------

def charger_sources():
    with open(FICHIER_CONTACTS_SOURCE, encoding="utf-8") as f:
        contacts_bruts = json.load(f)
    with open(FICHIER_LOGBOOK_SOURCE, encoding="utf-8") as f:
        logbook_brut = json.load(f)
    return contacts_bruts, logbook_brut


# ---------------------------------------------------------------------
# Étape 2 : corriger le livre de bord AVANT toute conversion
# ---------------------------------------------------------------------

CORRECTIONS_DATES_LOGBOOK = {
    5: "12/04/2026",
    19: "12/06/2026",
    25: "12/07/2026",
    12: "06/02/2026",
}


def corriger_logbook(logbook_brut):
    logbook_corrige = []
    for i, e in enumerate(logbook_brut):
        e = dict(e)  # copie, pour ne jamais modifier l'original en mémoire
        if i in CORRECTIONS_DATES_LOGBOOK:
            e["_date_corrigee"] = CORRECTIONS_DATES_LOGBOOK[i]
        else:
            e["_date_corrigee"] = decoder_date_logbook(e.get("Date"))
        logbook_corrige.append(e)
    return logbook_corrige


# ---------------------------------------------------------------------
# Étape 3 : construire les contacts (identité pure, dédupliquée)
# ---------------------------------------------------------------------

ALIAS_CONTACTS = {
    # Correction manuelle du 31/07/2026 : "AURELIEN" (sans nom) et
    # "AURELIEN FAUCHEUX" sont la même personne. On force le premier vers
    # l'identité du second dès le calcul de la clé, pour qu'ils partagent
    # le même contact_id partout (contacts, croisières, prospects).
    ("AURELIEN", ""): ("AURELIEN", "FAUCHEUX"),
}


def cle_contact(prenom, nom):
    p, n = (prenom or "").strip(), (nom or "").strip()
    p_maj, n_maj = p.upper(), n.upper()
    for (alias_p, alias_n), (vrai_p, vrai_n) in ALIAS_CONTACTS.items():
        if p_maj == alias_p and n_maj == alias_n:
            return vrai_p, vrai_n
    return p, n


def construire_contacts(contacts_bruts):
    """Un contact = une paire (Prénom, Nom) unique. On garde le
    téléphone/email de la première ligne rencontrée qui en a un (certaines
    lignes du même client ont ces champs vides sur les réservations
    suivantes)."""
    contacts = {}
    for c in contacts_bruts:
        prenom, nom = cle_contact(c.get("Prénom"), c.get("Nom"))
        if not prenom and not nom:
            continue
        # Correction #5 : Sophie Younes n'existe que sur une ligne, qui est
        # un doublon de saisie de la résa CMN du même jour (25/04/2026).
        # On l'exclut donc aussi de la liste des contacts, pas seulement
        # de ses croisières.
        if prenom.upper() == "SOPHIE" and nom.upper() == "YOUNES":
            continue
        cid = "c-" + id_stable(prenom, nom)
        if cid not in contacts:
            contacts[cid] = {
                "id": cid, "prenom": prenom, "nom": nom,
                "telephone": "", "email": "", "adresse": "",
                "notes": "", "habitue": "Non", "photos": [],
            }
        # Complète téléphone/email/notes si vides jusque là
        if not contacts[cid]["telephone"] and c.get("Téléphone"):
            contacts[cid]["telephone"] = str(c["Téléphone"]).strip()
        if not contacts[cid]["email"] and c.get("Email"):
            contacts[cid]["email"] = str(c["Email"]).strip()
        if not contacts[cid]["notes"] and c.get("Notes"):
            contacts[cid]["notes"] = str(c["Notes"]).strip()
    return contacts


# ---------------------------------------------------------------------
# Étape 4 : construire les croisières (hors prospects), avec les
# corrections/fusions/exclusions documentées
# ---------------------------------------------------------------------

def construire_croisieres(contacts_bruts, contacts_par_cle):
    croisieres = []
    fusion_faite = False

    for i, c in enumerate(contacts_bruts):
        if c.get("Statut") == "Liste d'attente":
            continue  # traité séparément (prospects)

        prenom, nom = cle_contact(c.get("Prénom"), c.get("Nom"))

        # Correction #5 : ignorer Sophie Younes (doublon de la résa CMN)
        if prenom.upper() == "SOPHIE" and nom.upper() == "YOUNES":
            continue

        # Correction #4 : Pedro Bandim Faustino est fusionné avec la
        # croisière de Benoît Couronne (traité au même moment que Benoît)
        if prenom.upper() == "PEDRO" and "BANDIM" in nom.upper():
            continue

        date_debut = normaliser_date(c.get("DateNav"))
        jours = to_int(c.get("Jours"), 1) or 1

        # Correction #3 : réservation CMN du 05/02/2026, durée 1 -> 2
        if date_debut == "05/02/2026" and prenom.upper() == "CMN":
            jours = 2

        participant = {
            "contact_id": contacts_par_cle[(prenom, nom)],
            "societe": (c.get("Société") or "").strip(),
            "prix": to_float(c.get("Prix")),
            "terminee": c.get("Statut") == "Terminé",
            "payee": c.get("Paiement") == "Paid",
            "annulee": c.get("Statut") == "Annulé",
            "accompagnants": [],
        }
        participants = [participant]

        # Correction #4 (suite) : quand on traite Benoît Couronne, on
        # rajoute Pedro comme second participant de LA MÊME croisière
        if prenom.upper() == "BENOIT" and "COURONNE" in nom.upper():
            pedro = next(
                (x for x in contacts_bruts
                 if cle_contact(x.get("Prénom"), x.get("Nom"))[0].upper() == "PEDRO"
                 and "BANDIM" in cle_contact(x.get("Prénom"), x.get("Nom"))[1].upper()),
                None,
            )
            if pedro:
                p_prenom, p_nom = cle_contact(pedro.get("Prénom"), pedro.get("Nom"))
                participants.append({
                    "contact_id": contacts_par_cle[(p_prenom, p_nom)],
                    "societe": (pedro.get("Société") or "").strip(),
                    "prix": to_float(pedro.get("Prix")),
                    "terminee": pedro.get("Statut") == "Terminé",
                    "payee": pedro.get("Paiement") == "Paid",
                    "annulee": pedro.get("Statut") == "Annulé",
                    "accompagnants": [],
                })
                jours = max(jours, to_int(pedro.get("Jours"), 1) or 1)
                fusion_faite = True

        croisieres.append({
            "id": "cr-" + id_stable(prenom, nom, date_debut, i),
            "nom_croisiere": "",  # rempli à l'étape 6, à partir du livre de bord si possible
            "date_debut": date_debut,
            "jours": jours,
            "notes": (c.get("Notes") or "").strip(),
            "participants": participants,
        })

    assert fusion_faite, "La fusion Couronne/Bandim ne s'est pas déclenchée : vérifier les données sources"
    return croisieres


# ---------------------------------------------------------------------
# Étape 5 : construire les prospects (interets_v2)
# ---------------------------------------------------------------------

def construire_interets(contacts_bruts, contacts_par_cle):
    interets = []
    for i, c in enumerate(contacts_bruts):
        if c.get("Statut") != "Liste d'attente":
            continue
        prenom, nom = cle_contact(c.get("Prénom"), c.get("Nom"))
        date_demande = normaliser_date(c.get("DateNav"))
        prochaine_relance = ""
        if date_demande:
            try:
                d = datetime.strptime(date_demande, "%d/%m/%Y").date()
                prochaine_relance = (d + timedelta(days=15)).strftime("%d/%m/%Y")
            except ValueError:
                pass
        interets.append({
            "id": "i-" + id_stable(prenom, nom, date_demande, i),
            "contact_id": contacts_par_cle[(prenom, nom)],
            "societe": (c.get("Société") or "").strip(),
            "date_demande": date_demande,
            "prochaine_relance": prochaine_relance,
            "sans_suite": False,  # champ 100% manuel : jamais déduit automatiquement
            "notes": (c.get("Notes") or "").strip(),
        })
    return interets


# ---------------------------------------------------------------------
# Étape 6 : construire les étapes (livre de bord) + les relier aux
# croisières par plage de dates, et compléter nom_croisiere
# ---------------------------------------------------------------------

def construire_etapes_et_relier(logbook_corrige, croisieres):
    # Pré-calcule la plage de dates de chaque croisière
    plages = []
    for cr in croisieres:
        if not cr["date_debut"]:
            continue
        d_debut = datetime.strptime(cr["date_debut"], "%d/%m/%Y").date()
        d_fin = d_debut + timedelta(days=max(cr["jours"] - 1, 0))
        plages.append((cr["id"], d_debut, d_fin))

    etapes = []
    for i, e in enumerate(logbook_corrige):
        date_str = e["_date_corrigee"]
        croisiere_id = None
        if date_str:
            d = datetime.strptime(date_str, "%d/%m/%Y").date()
            for cr_id, d_debut, d_fin in plages:
                if d_debut <= d <= d_fin:
                    croisiere_id = cr_id
                    break

        etapes.append({
            "id": "e-" + id_stable(date_str, i),
            "croisiere_id": croisiere_id,
            "date": date_str,
            "navigation": (e.get("Navigation") or "").strip(),
            "port_depart": (e.get("PortDep") or "").strip(),
            "port_arrivee": (e.get("PortArr") or "").strip(),
            "milles": to_float(e.get("TotalMil")),
            "heures_moteur": to_float(e.get("TotalMot")),
            "heures_voile": to_float(e.get("H_Voile")),
            "compteur_moteur": to_float(e.get("MotArr")),
            "meteo": (e.get("Meteo") or "").strip(),
            "coequipiers_texte": (e.get("Coéquipiers") or "").strip(),
            "carburant": None,
            "notes": (e.get("Notes") or "").strip(),
        })

    # Complète nom_croisiere à partir de la 1ère étape trouvée pour
    # chaque croisière ; sinon on retombe sur le nom du 1er participant
    etapes_par_croisiere = {}
    for e in etapes:
        if e["croisiere_id"]:
            etapes_par_croisiere.setdefault(e["croisiere_id"], []).append(e)

    for cr in croisieres:
        if cr["id"] in etapes_par_croisiere:
            cr["nom_croisiere"] = etapes_par_croisiere[cr["id"]][0]["navigation"] or "(sans nom)"
        else:
            cr["nom_croisiere"] = "(à définir)"

    return etapes


# ---------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------

def main():
    contacts_bruts, logbook_brut = charger_sources()
    logbook_corrige = corriger_logbook(logbook_brut)

    contacts = construire_contacts(contacts_bruts)
    contacts_par_cle = {(c["prenom"], c["nom"]): c["id"] for c in contacts.values()}

    croisieres = construire_croisieres(contacts_bruts, contacts_par_cle)
    interets = construire_interets(contacts_bruts, contacts_par_cle)
    etapes = construire_etapes_et_relier(logbook_corrige, croisieres)

    with open("contacts_v2.json", "w", encoding="utf-8") as f:
        json.dump(list(contacts.values()), f, ensure_ascii=False, indent=2)
    with open("croisieres_v2.json", "w", encoding="utf-8") as f:
        json.dump(croisieres, f, ensure_ascii=False, indent=2)
    with open("interets_v2.json", "w", encoding="utf-8") as f:
        json.dump(interets, f, ensure_ascii=False, indent=2)
    with open("etapes_v2.json", "w", encoding="utf-8") as f:
        json.dump(etapes, f, ensure_ascii=False, indent=2)

    print(f"Contacts   : {len(contacts)}")
    print(f"Croisières : {len(croisieres)}")
    print(f"Prospects  : {len(interets)}")
    print(f"Étapes     : {len(etapes)}")

    etapes_liees = sum(1 for e in etapes if e["croisiere_id"])
    print(f"  dont étapes liées à une croisière : {etapes_liees}")
    print(f"  dont étapes 'sorties perso' (non liées) : {len(etapes) - etapes_liees}")

    croisieres_sans_etape = [cr["id"] for cr in croisieres if cr["nom_croisiere"] == "(à définir)"]
    print(f"  croisières sans étape de journal (normal pour les résas futures) : {len(croisieres_sans_etape)}")


if __name__ == "__main__":
    main()
