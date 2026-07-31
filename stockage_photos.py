"""
stockage_photos.py
===================
Compression et stockage des photos de contacts sur GitHub.

Réutilise EXACTEMENT le même mécanisme d'authentification que
charger_data / sauvegarder_data dans app_voile1.py (st.secrets, API
Contents de GitHub). On ne réinvente pas une deuxième façon de parler à
GitHub : un seul token, un seul point de vérité.

Fonctionne même si le dépôt est privé, car on passe toujours par l'API
authentifiée (jamais par une URL "raw.githubusercontent.com" publique).
"""
import base64
import io

import requests
import streamlit as st
from PIL import Image

# Même casse que dans app_voile1.py (charger_data / sauvegarder_data)
REPO = "rico56-web/gestion-voile"
LARGEUR_MAX_PX = 400
QUALITE_JPEG = 80


def _token():
    """Récupère le token GitHub depuis st.secrets. Affiche une erreur
    Streamlit si absent (même message que dans app_voile1.py, pour ne
    pas dérouter Eric avec un message différent selon l'endroit)."""
    token = st.secrets.get("github", {}).get("token")
    if not token:
        st.error("Token GitHub manquant : configure-le dans .streamlit/secrets.toml (voir README).")
    return token


def compresser_image(fichier_upload):
    """Prend un fichier reçu via st.file_uploader et renvoie des bytes
    JPEG compressés, prêts à être envoyés sur GitHub.

    - Largeur ramenée à 400px MAX (on ne réduit pas si l'image est déjà
      plus petite, pour ne pas dégrader une petite photo)
    - Qualité JPEG 80 (bon compromis poids/qualité)
    - Conversion RGB obligatoire si le fichier d'origine est un PNG
      transparent (RGBA), car le format JPEG ne gère pas la transparence
    """
    image = Image.open(fichier_upload)

    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    if image.width > LARGEUR_MAX_PX:
        ratio = LARGEUR_MAX_PX / image.width
        nouvelle_hauteur = round(image.height * ratio)
        image = image.resize((LARGEUR_MAX_PX, nouvelle_hauteur), Image.LANCZOS)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=QUALITE_JPEG)
    return buffer.getvalue()


def uploader_photo(chemin_repo, contenu_bytes):
    """Envoie des bytes déjà compressés vers GitHub à l'emplacement
    chemin_repo (ex: 'photos/c-4f3a9b21_1.jpg').

    Même logique que sauvegarder_data() dans app_voile1.py :
    1. On regarde si le fichier existe déjà (pour récupérer son 'sha' —
       obligatoire pour REMPLACER un fichier existant, sinon GitHub refuse)
    2. On envoie le contenu encodé en base64 via PUT

    Renvoie True si succès, False sinon (avec message d'erreur affiché).
    """
    token = _token()
    if not token:
        return False

    url = f"https://api.github.com/repos/{REPO}/contents/{chemin_repo}"
    headers = {"Authorization": f"token {token}"}

    res_get = requests.get(url, headers=headers)
    sha = res_get.json().get("sha") if res_get.status_code == 200 else None

    payload = {
        "message": f"Ajout/MAJ photo {chemin_repo}",
        "content": base64.b64encode(contenu_bytes).decode("utf-8"),
    }
    if sha:
        payload["sha"] = sha

    res_put = requests.put(url, headers=headers, json=payload)
    if res_put.status_code not in (200, 201):
        st.error(
            f"Échec de l'envoi de la photo (code {res_put.status_code}) : "
            f"{res_put.json().get('message', res_put.text)}"
        )
        return False
    return True


def supprimer_photo(chemin_repo):
    """Supprime une photo sur GitHub. Si le fichier n'existe déjà plus,
    on considère que c'est un succès (rien à faire) plutôt qu'une erreur
    — utile quand on remplace une photo par une autre."""
    token = _token()
    if not token:
        return False

    url = f"https://api.github.com/repos/{REPO}/contents/{chemin_repo}"
    headers = {"Authorization": f"token {token}"}

    res_get = requests.get(url, headers=headers)
    if res_get.status_code != 200:
        return True

    sha = res_get.json().get("sha")
    res_del = requests.delete(
        url, headers=headers,
        json={"message": f"Suppression photo {chemin_repo}", "sha": sha},
    )
    if res_del.status_code != 200:
        st.error(
            f"Échec de la suppression de la photo (code {res_del.status_code}) : "
            f"{res_del.json().get('message', res_del.text)}"
        )
        return False
    return True


def telecharger_photo(chemin_repo):
    """Récupère les octets d'une photo directement depuis l'API GitHub
    (sans dépendre du disque local de l'app). Renvoie None si absente.

    Pas utilisé par page_contacts.py aujourd'hui (qui utilise le chemin
    local), mais disponible si on veut un jour un affichage instantané
    après upload, sans attendre le redéploiement Streamlit Cloud."""
    token = _token()
    if not token:
        return None

    url = f"https://api.github.com/repos/{REPO}/contents/{chemin_repo}"
    headers = {"Authorization": f"token {token}"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        return None
    return base64.b64decode(res.json().get("content", ""))
