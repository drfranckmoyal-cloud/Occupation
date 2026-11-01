"""Constitution des groupes : les demandes d'inscription aux formations CEMEDIS.

Le circuit : un classeur Google Sheets reçoit les réponses d'un formulaire → Planéo
le relit (chaque matin, ou sur demande) → les demandes sont rangées par formation →
Franck coche les praticiens retenus, confirme, peut rouvrir.

LE RANGEMENT N'EST JAMAIS STOCKÉ, IL EST RECALCULÉ. Une demande garde les choix tels
que le formulaire les a écrits ; la formation correspondante se déduit à chaque
lecture. Une formation créée plus tard dans Planéo récupère donc toute seule les
demandes restées « À trier ».

DONNÉES PERSONNELLES. Noms, téléphones et e-mails vivent dans donnees/groupes.json,
lisible par le seul service, jamais dans le dépôt ni dans les journaux.

    PLANEO_GOOGLE_CLE=/home/dfm/Planeo/compte-google.json   le compte de service
"""
import csv
import fcntl
import json
import os
import re
import secrets
import tempfile
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

ecran = Blueprint("groupes", __name__)

JOURS_NOUVEAU = 3     # une demande reste marquée « Nouveau » trois jours
GARDER_COPIES = 50
MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
        "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}


class Erreur(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.message, self.code = message, code


def _dossier():
    return (os.environ.get("PLANEO_DONNEES") or "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "donnees")


def _fichier():
    return os.path.join(_dossier(), "groupes.json")


def _cle_google():
    return (os.environ.get("PLANEO_GOOGLE_CLE") or "").strip() or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "compte-google.json")


def adresse_robot():
    """L'adresse avec laquelle Franck partage ses classeurs ; vide si pas encore posée."""
    try:
        with open(_cle_google(), encoding="utf-8") as f:
            return json.load(f).get("client_email") or ""
    except Exception:
        return ""


# ---------------------------------------------------------------- stockage


def _vide():
    return {"formulaires": [], "demandes": [], "correspondance": {}, "groupes": {}}


def _lire():
    try:
        with open(_fichier(), encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        return _vide()
    for k, v in _vide().items():
        d.setdefault(k, v)
    return d


def _ecrire(d):
    dossier = _dossier()
    os.makedirs(dossier, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dossier, prefix=".groupes-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o600)
    if os.path.exists(_fichier()):
        copies = os.path.join(dossier, "sauvegardes-groupes")
        os.makedirs(copies, mode=0o700, exist_ok=True)
        nom = f"groupes-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
        with open(_fichier(), "rb") as a, open(os.path.join(copies, nom), "wb") as b:
            b.write(a.read())
        os.chmod(os.path.join(copies, nom), 0o600)
        vieilles = sorted(x for x in os.listdir(copies) if x.startswith("groupes-"))
        for x in vieilles[:max(0, len(vieilles) - GARDER_COPIES)]:
            os.remove(os.path.join(copies, x))
    os.replace(tmp, _fichier())


@contextmanager
def _verrou():
    """Le relevé du matin est un autre processus que le site : un verrou de fichier
    les empêche d'écrire en même temps, ce qu'un verrou en mémoire ne ferait pas."""
    os.makedirs(_dossier(), exist_ok=True)
    with open(os.path.join(_dossier(), ".groupes.verrou"), "w") as h:
        fcntl.flock(h, fcntl.LOCK_EX)
        yield


# ---------------------------------------------------------------- lecture du formulaire


def sans_accents(t):
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn").casefold()


def _sans_complet(t):
    """Retire « /////COMPLET////// » que Franck met devant une formation pleine."""
    return re.sub(r"^\s*/+\s*complet\s*/+\s*", "", t or "", flags=re.I).strip()


def cle_choix(t):
    """Un même choix, qu'il soit marqué COMPLET ou non, a la même clé."""
    return " ".join(sans_accents(_sans_complet(t)).split())


_NOMS_MOIS = "|".join(MOIS)
_DATE = re.compile(rf"\b(\d{{1,2}})(?:er)?(?:\s*(?:et|-|au|,)\s*\d{{1,2}})*\s+({_NOMS_MOIS})\s+(\d{{4}})\b")
# Une virgule ne sépare deux cases cochées que si ce qui suit commence un nouveau choix :
# « Lundi 9 novembre 2026, de 14 h à 19 h : … » contient une virgule à l'intérieur.
_DEBUT = r"(?:/+\s*complet\s*/+\s*)?(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b|\d{1,2}(?:er)?\s+[a-zéû]+\s+\d{4})"


def separer_choix(cellule):
    morceaux = re.split(rf",\s+(?={_DEBUT})", (cellule or "").strip(), flags=re.I)
    return [m.strip() for m in morceaux if m.strip()]


def date_du_choix(t):
    """La date écrite dans le choix, ou None si elle est absente ou impossible (31 novembre)."""
    m = _DATE.search(sans_accents(t))
    if not m:
        return None
    try:
        return date(int(m.group(3)), MOIS[m.group(2)], int(m.group(1))).isoformat()
    except ValueError:
        return None


def normaliser_tel(t):
    """Rend (numéro lisible, chiffres), ou (texte d'origine, "") si le numéro est douteux."""
    brut = (t or "").strip()
    c = re.sub(r"\D", "", brut)
    if c.startswith("0033"):
        c = c[4:]
    elif c.startswith("33") and len(c) == 11:
        c = c[2:]
    if len(c) == 9:
        c = "0" + c
    if len(c) == 10 and c.startswith("0"):
        return " ".join(c[i:i + 2] for i in range(0, 10, 2)), c
    return brut, ""


def _colonnes(entetes):
    """Retrouve les colonnes par leur sens : les libellés changent d'un formulaire à l'autre."""
    col = {}
    for i, e in enumerate(entetes):
        n = sans_accents(e)
        if "prenom" in n:
            col.setdefault("prenom", i)
        elif "horodat" in n or "timestamp" in n:
            col.setdefault("date", i)
        elif "mail" in n:
            col.setdefault("mail", i)
        elif "tel" in n or "portable" in n:
            col.setdefault("tel", i)
        elif "demande" in n or "inscription" in n or "formation" in n:
            col.setdefault("choix", i)
        elif re.search(r"\bnom\b", n):
            col.setdefault("nom", i)
    manque = [k for k, lib in (("nom", "le nom"), ("prenom", "le prénom"), ("tel", "le téléphone"),
                               ("choix", "la demande d'inscription")) if k not in col]
    if manque:
        noms = {"nom": "nom", "prenom": "prénom", "tel": "téléphone", "choix": "demande d'inscription"}
        raise Erreur("Colonne introuvable dans le classeur : " + ", ".join(noms[k] for k in manque) + ".")
    return col


def _date_reponse(t):
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", t or "")
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            pass
    return ""


def integrer(d, form, lignes, aujourdhui=None):
    """Range les lignes du classeur dans les demandes. Rend le nombre de personnes nouvelles.

    Une même personne qui répond deux fois reste une seule demande : ses choix s'additionnent
    et ses coordonnées les plus récentes l'emportent. Ce qui a disparu du classeur n'est jamais
    effacé ici : Franck a pu retenir cette personne.
    """
    if not lignes:
        raise Erreur("Le classeur est vide.")
    col = _colonnes(lignes[0])
    auj = aujourdhui or date.today().isoformat()
    existantes = {x["cle"]: x for x in d["demandes"]}
    nouvelles = 0
    for ligne in lignes[1:]:
        lire = lambda k: (ligne[col[k]] if k in col and col[k] < len(ligne) else "").strip()
        nom, prenom = lire("nom"), lire("prenom")
        if not (nom or prenom):
            continue
        tel, chiffres = normaliser_tel(lire("tel"))
        mail = lire("mail").lower()
        cle = chiffres or mail or sans_accents(f"{nom} {prenom}")
        x = existantes.get(cle)
        if x is None:
            x = {"id": secrets.token_hex(6), "cle": cle, "formulaire": form["id"], "choix": [],
                 "date": _date_reponse(lire("date")), "premiere_vue": auj}
            d["demandes"].append(x)
            existantes[cle] = x
            nouvelles += 1
        x.update(nom=nom.upper(), prenom=_prenom(prenom), tel=tel, tel_valide=bool(chiffres), mail=mail)
        connus = {cle_choix(c) for c in x["choix"]}
        for c in separer_choix(lire("choix")):
            if cle_choix(c) not in connus:
                x["choix"].append(_sans_complet(c))
                connus.add(cle_choix(c))
    return nouvelles


def _prenom(t):
    return "-".join(" ".join(m.capitalize() for m in p.split()) for p in (t or "").strip().split("-"))


# ---------------------------------------------------------------- lecture de Google Sheets


def id_classeur(lien):
    m = re.match(r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]{20,})", (lien or "").strip())
    if not m:
        raise Erreur("Ce lien n'est pas celui d'un classeur Google Sheets (docs.google.com/spreadsheets/d/…).")
    return m.group(1)


def lire_classeur(identifiant):
    """Les lignes du premier onglet du classeur. Un fichier CSV d'essai peut la remplacer."""
    essai = (os.environ.get("PLANEO_CLASSEUR_ESSAI") or "").strip()
    if essai:
        with open(essai, encoding="utf-8", newline="") as f:
            return list(csv.reader(f))
    robot = adresse_robot()
    if not robot:
        raise Erreur("L'accès à Google n'est pas encore installé sur le serveur.", 503)
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    cred = service_account.Credentials.from_service_account_file(
        _cle_google(), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    try:
        r = AuthorizedSession(cred).get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{identifiant}/values/A:Z", timeout=30)
    except Exception:
        raise Erreur("Google ne répond pas. Réessayez dans un instant.", 502)
    if r.status_code in (401, 403):
        raise Erreur(f"Planéo n'a pas accès à ce classeur : partagez-le en lecture avec {robot}.", 403)
    if r.status_code == 404:
        raise Erreur("Classeur introuvable : vérifiez le lien.", 404)
    if r.status_code != 200:
        raise Erreur(f"Google a refusé la lecture (code {r.status_code}).", 502)
    return r.json().get("values") or []


def relever(d, form):
    """Relit un classeur et note le résultat sur le formulaire, succès comme échec."""
    form["dernier_essai"] = datetime.now().astimezone().isoformat(timespec="minutes")
    try:
        lignes = lire_classeur(form["classeur"])
        n = integrer(d, form, lignes)
    except Erreur as e:
        form["erreur"] = e.message
        return False
    form.update(erreur="", releve=form["dernier_essai"], recues=max(0, len(lignes) - 1), nouvelles=n)
    return True


def releve_tous():
    """Le relevé du matin (appelé par releve.py)."""
    with _verrou():
        d = _lire()
        resultats = [relever(d, f) for f in d["formulaires"]]
        if d["formulaires"]:
            _ecrire(d)
    return resultats


# ---------------------------------------------------------------- rangement par formation


def formations_cemedis(planning):
    orgs = {o["id"] for o in planning.get("orgs", []) if sans_accents(o.get("nom", "")).startswith("cemedis")}
    return [f for f in planning.get("formations", []) if f.get("org") in orgs]


def rattacher(choix, formations, correspondance):
    """L'id de la formation d'un choix, ou None : à trier."""
    ids = {f["id"] for f in formations}
    memo = correspondance.get(cle_choix(choix))
    if memo in ids:
        return memo
    jour = date_du_choix(choix)
    if not jour:
        return None
    trouvees = [f["id"] for f in formations if jour in f.get("jours", [])]
    return trouvees[0] if len(trouvees) == 1 else None      # deux formations ce jour-là : à trier


def vue_complete(d, planning, aujourdhui=None):
    """Ce que la page affiche : chaque demande avec ses formations, et ce qui reste à trier."""
    formations = formations_cemedis(planning)
    auj = aujourdhui or date.today().isoformat()
    limite = (date.fromisoformat(auj) - timedelta(days=JOURS_NOUVEAU)).isoformat()
    demandes, a_trier = [], []
    for x in d["demandes"]:
        voeux = []
        for c in x["choix"]:
            fid = rattacher(c, formations, d["correspondance"])
            if fid:
                if fid not in voeux:
                    voeux.append(fid)
            else:
                a_trier.append({"demande": x["id"], "choix": c})
        demandes.append({k: x.get(k, "") for k in ("id", "nom", "prenom", "tel", "tel_valide", "mail", "date")}
                        | {"voeux": voeux, "nouveau": x.get("premiere_vue", "") > limite})
    avec_demandes = {v for x in demandes for v in x["voeux"]}
    liste = sorted((f for f in formations if max(f["jours"]) >= auj or f["id"] in avec_demandes),
                   key=lambda f: min(f["jours"]))
    return {"robot": adresse_robot(), "formulaires": d["formulaires"], "formations": liste,
            "demandes": demandes, "a_trier": a_trier,
            "groupes": {f["id"]: d["groupes"].get(f["id"], {"etat": "ouvert", "retenus": []}) for f in liste}}


# ---------------------------------------------------------------- routes


def _planning():
    from app import _lire as lire_planning
    return lire_planning()


@ecran.errorhandler(Erreur)
def _erreur(e):
    return jsonify({"erreur": e.message}), e.code


@ecran.get("/api/groupes")
def voir():
    with _verrou():
        d = _lire()
    return jsonify(vue_complete(d, _planning()))


def _formation_connue(fid):
    if fid not in {f["id"] for f in formations_cemedis(_planning())}:
        raise Erreur("Formation inconnue, ou qui n'est pas une formation CEMEDIS.", 404)


@ecran.post("/api/groupes/formulaire")
def ajouter_formulaire():
    corps = request.get_json(silent=True) or {}
    nom = (corps.get("nom") or "").strip()[:120]
    lien = (corps.get("lien") or "").strip()[:500]
    if not nom:
        raise Erreur("Donnez un nom à ce formulaire.")
    classeur = id_classeur(lien)
    with _verrou():
        d = _lire()
        if any(f["classeur"] == classeur for f in d["formulaires"]):
            raise Erreur("Ce classeur est déjà exploité.", 409)
        form = {"id": secrets.token_hex(5), "nom": nom, "lien": lien, "classeur": classeur}
        d["formulaires"].append(form)
        relever(d, form)        # un échec reste affiché : Franck n'a qu'à partager puis rafraîchir
        _ecrire(d)
    return jsonify(vue_complete(d, _planning()))


@ecran.post("/api/groupes/formulaire/retirer")
def retirer_formulaire():
    fid = (request.get_json(silent=True) or {}).get("id")
    with _verrou():
        d = _lire()
        d["formulaires"] = [f for f in d["formulaires"] if f["id"] != fid]
        _ecrire(d)      # les demandes déjà relevées restent : des praticiens ont pu être retenus
    return jsonify(vue_complete(d, _planning()))


@ecran.post("/api/groupes/rafraichir")
def rafraichir():
    with _verrou():
        d = _lire()
        for f in d["formulaires"]:
            relever(d, f)
        _ecrire(d)
    return jsonify(vue_complete(d, _planning()))


@ecran.post("/api/groupes/ranger")
def ranger():
    """Range un choix sous une formation, et s'en souvient pour toutes les réponses à venir."""
    corps = request.get_json(silent=True) or {}
    choix, fid = corps.get("choix") or "", corps.get("formation") or ""
    _formation_connue(fid)
    with _verrou():
        d = _lire()
        d["correspondance"][cle_choix(choix)] = fid
        _ecrire(d)
    return jsonify(vue_complete(d, _planning()))


@ecran.post("/api/groupes/retenir")
def retenir():
    corps = request.get_json(silent=True) or {}
    fid, did, oui = corps.get("formation") or "", corps.get("demande") or "", bool(corps.get("retenu"))
    _formation_connue(fid)
    with _verrou():
        d = _lire()
        if did not in {x["id"] for x in d["demandes"]}:
            raise Erreur("Demande inconnue.", 404)
        g = d["groupes"].setdefault(fid, {"etat": "ouvert", "retenus": []})
        if g["etat"] == "confirme":
            raise Erreur("Ce groupe est confirmé : rouvrez-le pour le modifier.", 409)
        g["retenus"] = [r for r in g["retenus"] if r != did] + ([did] if oui else [])
        _ecrire(d)
    return jsonify(vue_complete(d, _planning()))


@ecran.post("/api/groupes/etat")
def changer_etat():
    corps = request.get_json(silent=True) or {}
    fid, etat = corps.get("formation") or "", corps.get("etat")
    if etat not in ("confirme", "ouvert"):
        raise Erreur("État inconnu.")
    _formation_connue(fid)
    with _verrou():
        d = _lire()
        g = d["groupes"].setdefault(fid, {"etat": "ouvert", "retenus": []})
        if etat == "confirme" and not g["retenus"]:
            raise Erreur("Cochez au moins un praticien avant de confirmer.")
        g["etat"] = etat
        _ecrire(d)
    return jsonify(vue_complete(d, _planning()))
