"""Essais de la constitution des groupes, avec des praticiens fictifs.

    PYTHONPATH=planeo python planeo/test_groupes.py
"""
import csv
import json
import os
import tempfile

essai = tempfile.mkdtemp()
os.environ["PLANEO_DONNEES"] = essai
os.environ["PLANEO_ACCES"] = os.path.join(essai, "acces.json")
os.environ["PLANEO_CLASSEUR_ESSAI"] = os.path.join(essai, "classeur.csv")
json.dump({"secret": "secret-essai"}, open(os.environ["PLANEO_ACCES"], "w"))

import app as A          # noqa: E402
import groupes as G      # noqa: E402

ENTETES = ["Horodateur", "NOM (majuscules)", "Prénom", "@adresse mail", "Numéro téléphone", "Demande d'inscription"]
STRAT = "Lundi 9 novembre 2030, de 14 h à 19 h : Stratification — niveau 1."
INLAY = "/////COMPLET //////Lundi 23 novembre 2030, de 14 h à 19 h : Inlays, onlays et overlays."
ICON = "Lundi 31 novembre 2030, de 19h30 à 21h : Eclaircissement et ICON."
LIGNES = [
    ENTETES,
    ["28/10/2030 10:00:00", "exemple", "alice", "Alice@Exemple.fr", "06 00 00 00 01", f"{STRAT}, {INLAY}"],
    ["29/10/2030 11:00:00", "FICTIF", "jean-marc", "b@exemple.fr", "+33 6 00 00 00 02", ICON],
    ["30/10/2030 12:00:00", "MODELE", "Claire", "c@exemple.fr", "6.00.00.00.03", "Une formation sans date"],
    ["31/10/2030 12:00:00", "EXEMPLE", "Alice", "autre@exemple.fr", "0033600000001", STRAT],
    ["31/10/2030 13:00:00", "COURT", "Numéro", "d@exemple.fr", "1234", STRAT],
    ["", "", "", "", "", ""],
]


def classeur(lignes):
    with open(os.environ["PLANEO_CLASSEUR_ESSAI"], "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(lignes)


def verifie(nom, obtenu, attendu):
    assert obtenu == attendu, f"{nom} : obtenu {obtenu!r}, attendu {attendu!r}"
    print("ok  ", nom)


verifie("virgule interne : deux choix seulement", G.separer_choix(f"{STRAT}, {INLAY}"), [STRAT, INLAY])
verifie("une date dans un seul choix", G.separer_choix(STRAT), [STRAT])
verifie("date lue", G.date_du_choix(STRAT), "2030-11-09")
verifie("date lue malgré COMPLET", G.date_du_choix(INLAY), "2030-11-23")
verifie("31 novembre refusé", G.date_du_choix(ICON), None)
verifie("plusieurs jours : le premier", G.date_du_choix("9 et 10 décembre 2030 : Usures"), "2030-12-09")
verifie("COMPLET ne change pas la clé", G.cle_choix(INLAY), G.cle_choix(INLAY.replace("/////COMPLET //////", "")))
verifie("téléphone international", G.normaliser_tel("+33 6 00 00 00 02")[0], "06 00 00 00 02")
verifie("téléphone sans zéro", G.normaliser_tel("6.00.00.00.03")[0], "06 00 00 00 03")
verifie("téléphone douteux gardé tel quel", G.normaliser_tel("1234"), ("1234", ""))


def refus(fn):
    try:
        fn()
    except G.Erreur:
        return True
    return False


verifie("lien de formulaire refusé", refus(lambda: G.id_classeur("https://docs.google.com/forms/d/abc/edit")), True)
verifie("colonne manquante signalée", refus(lambda: G._colonnes(["Nom", "Prénom"])), True)
verifie("colonnes trouvées", G._colonnes(ENTETES),
        {"date": 0, "nom": 1, "prenom": 2, "mail": 3, "tel": 4, "choix": 5})

# --- Le planning : deux formations CEMEDIS, une d'un autre organisme le même jour qu'ICON
planning = {"version": 1, "orgs": [
    {"id": "o1", "nom": "CEMEDIS", "couleur": "#1f77b4", "titres": []},
    {"id": "o2", "nom": "SMILECLUB", "couleur": "#d6731c", "titres": []}],
    "formations": [
    {"id": "f1", "org": "o1", "titre": "Stratification Niveau 1", "creneau": "apm", "jours": ["2030-11-09"], "note": "", "places": 1},
    {"id": "f2", "org": "o1", "titre": "Inlay - Onlay - Overlay", "creneau": "apm", "jours": ["2030-11-23"], "note": ""},
    {"id": "f3", "org": "o1", "titre": "Eclaircissement + ICON", "creneau": "soir", "jours": ["2030-11-30"], "note": ""},
    {"id": "f4", "org": "o2", "titre": "Autre organisme", "creneau": "matin", "jours": ["2030-11-09"], "note": ""}],
    "fermetures": []}
A._ecrire(planning)

c = A.app.test_client()
verifie("sans connexion : refus", c.get("/api/groupes").status_code, 401)
verifie("sans connexion : écriture refusée", c.post("/api/groupes/rafraichir").status_code, 401)
with c.session_transaction() as s:
    s["ouvert"] = True

classeur(LIGNES)
LIEN = "https://docs.google.com/spreadsheets/d/" + "a" * 30 + "/edit#gid=0"
r = c.post("/api/groupes/formulaire", json={"nom": "Essai", "lien": LIEN}).get_json()
verifie("formulaire enregistré sans erreur", r["formulaires"][0].get("erreur"), "")
verifie("réponses comptées", r["formulaires"][0]["recues"], 6)
verifie("seules les formations CEMEDIS", [f["id"] for f in r["formations"]], ["f1", "f2", "f3"])
verifie("doublon de personne fusionné : 4 personnes", len(r["demandes"]), 4)
alice = next(x for x in r["demandes"] if x["prenom"] == "Alice")
verifie("Alice sous deux formations", sorted(alice["voeux"]), ["f1", "f2"])
verifie("coordonnées les plus récentes", alice["mail"], "autre@exemple.fr")
verifie("nom en majuscules", alice["nom"], "EXEMPLE")
jm = next(x for x in r["demandes"] if x["nom"] == "FICTIF")
verifie("prénom composé", jm["prenom"], "Jean-Marc")
verifie("à trier : 31 novembre et sans date", sorted(t["choix"] for t in r["a_trier"]),
        sorted([ICON, "Une formation sans date"]))
verifie("numéro douteux signalé", next(x for x in r["demandes"] if x["nom"] == "COURT")["tel_valide"], False)
verifie("même classeur refusé", c.post("/api/groupes/formulaire", json={"nom": "Bis", "lien": LIEN}).status_code, 409)
verifie("lien invalide refusé", c.post("/api/groupes/formulaire", json={"nom": "X", "lien": "https://exemple.fr"}).status_code, 400)

# --- Le rangement manuel est mémorisé
verifie("autre organisme refusé au rangement", c.post("/api/groupes/ranger", json={"choix": ICON, "formation": "f4"}).status_code, 404)
r = c.post("/api/groupes/ranger", json={"choix": ICON, "formation": "f3"}).get_json()
verifie("rangé : il reste une réponse à trier", [t["choix"] for t in r["a_trier"]], ["Une formation sans date"])
verifie("Jean-Marc sous ICON", next(x for x in r["demandes"] if x["nom"] == "FICTIF")["voeux"], ["f3"])

# --- Rafraîchir : une nouvelle réponse, et le rangement tient
classeur(LIGNES + [["01/11/2030 09:00:00", "NOUVELLE", "Hélène", "h@exemple.fr", "0600000008", ICON.replace("Lundi", "/////COMPLET //////Lundi")]])
r = c.post("/api/groupes/rafraichir").get_json()
verifie("une nouvelle personne", r["formulaires"][0]["nouvelles"], 1)
h = next(x for x in r["demandes"] if x["nom"] == "NOUVELLE")
verifie("rangement mémorisé, même marqué COMPLET", h["voeux"], ["f3"])
verifie("rien en double après relecture", len(r["demandes"]), 5)

# --- Cocher, confirmer, rouvrir
verifie("confirmer sans personne : refus", c.post("/api/groupes/etat", json={"formation": "f1", "etat": "confirme"}).status_code, 400)
aid = alice["id"]
r = c.post("/api/groupes/retenir", json={"formation": "f1", "demande": aid, "retenu": True}).get_json()
verifie("Alice retenue", r["groupes"]["f1"]["retenus"], [aid])
bid = next(x["id"] for x in r["demandes"] if x["nom"] == "COURT")
r = c.post("/api/groupes/retenir", json={"formation": "f1", "demande": bid, "retenu": True}).get_json()
verifie("dépassement des places accepté", len(r["groupes"]["f1"]["retenus"]), 2)
r = c.post("/api/groupes/etat", json={"formation": "f1", "etat": "confirme"}).get_json()
verifie("confirmé", r["groupes"]["f1"]["etat"], "confirme")
verifie("confirmé : plus de coche", c.post("/api/groupes/retenir", json={"formation": "f1", "demande": aid, "retenu": False}).status_code, 409)
r = c.post("/api/groupes/rafraichir").get_json()
verifie("un relevé ne touche pas aux retenus", len(r["groupes"]["f1"]["retenus"]), 2)
r = c.post("/api/groupes/etat", json={"formation": "f1", "etat": "ouvert"}).get_json()
verifie("rouvert", r["groupes"]["f1"]["etat"], "ouvert")
r = c.post("/api/groupes/retenir", json={"formation": "f1", "demande": aid, "retenu": False}).get_json()
verifie("décochée", r["groupes"]["f1"]["retenus"], [bid])
verifie("autre site refusé", c.post("/api/groupes/rafraichir", headers={"Origin": "https://mechant.example"}).status_code, 403)

# --- Classeur illisible : l'erreur s'affiche, rien n'est perdu
classeur([["Colonne", "Inconnue"]])
r = c.post("/api/groupes/rafraichir").get_json()
assert "introuvable" in r["formulaires"][0]["erreur"], r["formulaires"][0]
verifie("rien de perdu après une erreur", len(r["demandes"]), 5)

# --- Le nombre de places traverse l'enregistrement du planning
d = c.get("/api/donnees").get_json()
d["formations"][0]["places"] = 12
d["formations"][1]["places"] = "n'importe quoi"
r = c.post("/api/enregistrer", json={"version": d["version"], "donnees": d})
verifie("planning enregistré", r.status_code, 200)
d = c.get("/api/donnees").get_json()
verifie("places gardées", d["formations"][0].get("places"), 12)
verifie("places invalides ignorées", d["formations"][1].get("places"), None)

verifie("fichier lisible du seul service", oct(os.stat(G._fichier()).st_mode & 0o777), "0o600")
print("\nTout est bon.")
