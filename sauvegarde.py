"""
sauvegarde.py
==============
Sauvegarde groupée de tous les fichiers .json du dépôt GitHub dans un
seul fichier ZIP daté (ex: sauvegarde_vesta_2026-09-21_16h30.zip).

On récupère les fichiers BRUTS directement sur GitHub (donc les données
les plus récentes, même saisies depuis l'iPhone), sans les retravailler :
ce sont des copies exactes.

Cette sauvegarde ne modifie RIEN sur GitHub : elle ne fait que lire.

La liste des fichiers n'est pas écrite en dur : on prend tous les .json
présents à la racine du dépôt. Un futur fichier JSON sera donc
sauvegardé automatiquement.

Limite : les photos des contacts ne sont pas des .json, elles ne sont
pas incluses.
"""
import io
import zipfile
from datetime import datetime
from zoneinfo import ZoneInfo

import requests


def lister_json_depot(repo, token):
    """Renvoie la liste des noms de fichiers .json à la racine du dépôt."""
    reponse = requests.get(
        f"https://api.github.com/repos/{repo}/contents/",
        headers={"Authorization": f"token {token}"},
        timeout=30,
    )
    if reponse.status_code != 200:
        raise RuntimeError(f"GitHub a répondu {reponse.status_code} en listant le dépôt.")
    return sorted(
        f["name"] for f in reponse.json()
        if f.get("type") == "file" and f["name"].lower().endswith(".json")
    )


def telecharger_fichier_brut(repo, token, nom):
    """Télécharge le contenu exact (octets) d'un fichier du dépôt."""
    reponse = requests.get(
        f"https://api.github.com/repos/{repo}/contents/{nom}",
        # "raw" = on demande le fichier tel quel, sans emballage JSON/base64
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.raw"},
        timeout=30,
    )
    if reponse.status_code != 200:
        raise RuntimeError(f"GitHub a répondu {reponse.status_code} pour {nom}.")
    return reponse.content


def creer_zip(fichiers):
    """Assemble un ZIP en mémoire. `fichiers` = {nom: contenu en octets}."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, contenu in fichiers.items():
            z.writestr(nom, contenu)
    return tampon.getvalue()


def nom_fichier_zip(maintenant=None):
    """Nom daté, à l'heure de Paris (le serveur Streamlit est en heure UTC)."""
    if maintenant is None:
        try:
            maintenant = datetime.now(ZoneInfo("Europe/Paris"))
        except Exception:
            maintenant = datetime.now()  # secours : heure du serveur
    return f"sauvegarde_vesta_{maintenant.strftime('%Y-%m-%d_%Hh%M')}.zip"


def preparer_sauvegarde(repo, token):
    """Fait tout le travail. Renvoie (zip_en_octets, noms_ok, erreurs).
    Un fichier qui échoue n'empêche pas les autres : il est listé dans
    `erreurs` pour que tu saches que la sauvegarde est incomplète."""
    fichiers, erreurs = {}, []
    for nom in lister_json_depot(repo, token):
        try:
            fichiers[nom] = telecharger_fichier_brut(repo, token, nom)
        except Exception as e:
            erreurs.append(f"{nom} : {e}")
    return creer_zip(fichiers), sorted(fichiers), erreurs
