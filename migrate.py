import json
import uuid

def migrer_donnees(input_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    clients = {} # Utilisation d'un dict pour éviter les doublons par Nom+Prenom
    navigations = []

    for entry in data:
        # 1. Extraction et nettoyage des données Client
        nom = entry.get("Nom", "Inconnu")
        prenom = entry.get("Prénom", entry.get("Prenom", ""))
        cle_client = f"{nom}_{prenom}".lower()

        if cle_client not in clients:
            clients[cle_client] = {
                "id": str(uuid.uuid4()),
                "nom": nom,
                "prenom": prenom,
                "societe": entry.get("Société", entry.get("Societe", "")),
                "telephone": entry.get("Téléphone", entry.get("Telephone", "")),
                "email": entry.get("Email", "")
            }

        # 2. Extraction et nettoyage des données Navigation
        # On ne crée une navigation que si une date existe
        if entry.get("DateNav"):
            nav = {
                "client_id": clients[cle_client]["id"],
                "date": entry.get("DateNav"),
                "statut": entry.get("Statut", "Confirmé"),
                "paiement": entry.get("Paiement", "Unpaid"),
                "prix": entry.get("Prix", 0),
                "jours": entry.get("Jours", 0),
                "personnes": entry.get("Pers", 0),
                "notes": entry.get("Notes", "")
            }
            navigations.append(nav)

    # Sauvegarde des deux nouveaux fichiers
    with open('clients.json', 'w', encoding='utf-8') as f:
        json.dump(list(clients.values()), f, indent=4, ensure_ascii=False)

    with open('navigations.json', 'w', encoding='utf-8') as f:
        json.dump(navigations, f, indent=4, ensure_ascii=False)

    print(f"Migration terminée : {len(clients)} clients et {len(navigations)} navigations créés.")

# Lancer la migration
migrer_donnees('Contacts.json')
