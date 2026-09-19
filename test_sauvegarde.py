"""
test_sauvegarde.py — teste sauvegarde.py SANS internet et SANS toucher à
GitHub (on remplace les appels réseau par de faux). Lancer :
    python test_sauvegarde.py
"""
import io
import zipfile
from datetime import datetime

import sauvegarde


class FausseReponse:
    def __init__(self, code, json_data=None, contenu=b""):
        self.status_code, self._json, self.content = code, json_data, contenu
    def json(self):
        return self._json


def faux_get(url, headers=None, timeout=None):
    if url.endswith("/contents/"):
        return FausseReponse(200, [
            {"name": "contacts_v2.json", "type": "file"},
            {"name": "carburant.json", "type": "file"},
            {"name": "app_voile1.py", "type": "file"},        # pas un json
            {"name": "photos", "type": "dir"},                 # dossier
            {"name": "casse.json", "type": "file"},            # va échouer
        ])
    nom = url.rsplit("/", 1)[1]
    if nom == "casse.json":
        return FausseReponse(500)
    return FausseReponse(200, contenu=f'[{{"fichier": "{nom}"}}]'.encode("utf-8"))


sauvegarde.requests.get = faux_get

zip_octets, noms, erreurs = sauvegarde.preparer_sauvegarde("depot/test", "token")

assert noms == ["carburant.json", "contacts_v2.json"], noms
print("OK  seuls les .json sont pris (pas .py, pas les dossiers)")

assert len(erreurs) == 1 and "casse.json" in erreurs[0]
print("OK  un fichier en échec est signalé sans bloquer les autres")

with zipfile.ZipFile(io.BytesIO(zip_octets)) as z:
    assert sorted(z.namelist()) == noms
    assert z.read("contacts_v2.json") == b'[{"fichier": "contacts_v2.json"}]'
print("OK  le zip contient les copies exactes")

assert sauvegarde.nom_fichier_zip(datetime(2026, 9, 21, 16, 30)) == "sauvegarde_vesta_2026-09-21_16h30.zip"
print("OK  nom du zip daté")

print("\nTOUS LES TESTS PASSENT")
