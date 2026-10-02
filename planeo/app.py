"""Planéo sur le serveur du portail CEMEDIS Formations, sous /planeo/.

AUCUN MOT DE PASSE PROPRE. Planéo lit le fichier d'accès de DFM (PLANEO_ACCES) et
n'en garde que le secret qui signe les sessions : le cookie ouvert par la
connexion DFM l'ouvre aussi. Planéo n'écrit JAMAIS ce fichier — il ne pose ni ne
change aucun mot de passe. Sans session ouverte, on renvoie vers /connexion de DFM.

    PLANEO_ACCES=/home/dfm/DFM/acces.json   le fichier d'accès partagé
    PLANEO_DONNEES=/home/dfm/Planeo/donnees  le planning et ses copies
    PLANEO_PORT=5003

/verif sert à nginx (auth_request) pour fermer la page du portail elle-même
derrière le même mot de passe.
"""
import json
import os
import re
import tempfile
import threading
from datetime import date, datetime
from urllib.parse import urlparse

from flask import Flask, jsonify, redirect, request, send_file, session

DOSSIER = os.path.dirname(os.path.abspath(__file__))
ACCES = (os.environ.get("PLANEO_ACCES") or "").strip() or os.path.join(DOSSIER, "acces.json")
DONNEES = (os.environ.get("PLANEO_DONNEES") or "").strip() or os.path.join(DOSSIER, "donnees")
FICHIER = os.path.join(DONNEES, "occupation.json")
SAUVEGARDES = os.path.join(DONNEES, "sauvegardes")
GARDER_SAUVEGARDES = 200
CRENEAUX = {"journee", "matin", "apm", "soir"}
TYPES_FERMETURE = {"conges", "fermeture"}   # congés = salle fermée ; fermeture = possible, à confirmer
VERROU = threading.Lock()


def _secret():
    try:
        with open(ACCES, encoding="utf-8") as f:
            return (json.load(f) or {}).get("secret") or ""
    except Exception:
        return ""


app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
    SESSION_COOKIE_SECURE=(os.environ.get("PLANEO_PROXY") or "").strip() == "1",
    # Planéo lit la session, il ne la prolonge ni ne la réécrit : c'est DFM qui la gère.
    SESSION_REFRESH_EACH_REQUEST=False,
    MAX_CONTENT_LENGTH=4 * 1024 * 1024,
)


class _Prefixe:
    """nginx annonce /planeo dans X-Forwarded-Prefix ; Flask ne le lit pas seul."""
    def __init__(self, suite):
        self.suite = suite

    def __call__(self, environ, start_response):
        # La clé est relue AVANT que Flask ouvre la session : si le mot de passe a
        # changé dans DFM (nouveau secret), les anciennes sessions tombent ici aussi.
        app.secret_key = _secret() or None
        prefixe = environ.get("HTTP_X_FORWARDED_PREFIX", "")
        if prefixe.startswith("/") and "//" not in prefixe:
            environ["SCRIPT_NAME"] = prefixe.rstrip("/")
        return self.suite(environ, start_response)


app.wsgi_app = _Prefixe(app.wsgi_app)


@app.before_request
def _garde():
    if not app.secret_key:
        return jsonify({"erreur": "Accès non configuré sur le serveur."}), 503
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        origine = request.headers.get("Origin") or request.headers.get("Referer") or ""
        if origine and urlparse(origine).netloc != request.host:
            return jsonify({"erreur": "Requête refusée."}), 403
    if session.get("ouvert"):
        return None
    if request.path == "/verif" or request.path.startswith("/api/"):
        return jsonify({"erreur": "Session expirée. Reconnectez-vous."}), 401
    return redirect("/connexion?suite=" + request.script_root + "/")


@app.after_request
def _entetes(r):
    r.headers["Cache-Control"] = "no-store"
    return r


@app.get("/verif")
def verif():
    return "", 204


@app.get("/")
def page():
    return send_file(os.path.join(DOSSIER, "index.html"), mimetype="text/html")


def _lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            return d
    except FileNotFoundError:
        pass
    return {"version": 0, "orgs": [], "formations": []}


def _ecrire(d):
    os.makedirs(SAUVEGARDES, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DONNEES, prefix=".occupation-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


class Invalide(Exception):
    pass


def _texte(v, n):
    return (v.strip() if isinstance(v, str) else "")[:n]


def valider(d):
    """Reconstruit des données propres ; refuse le reste (mêmes règles qu'api.php)."""
    orgs, ids = [], set()
    for o in (d.get("orgs") or [])[:100]:
        if not isinstance(o, dict):
            continue
        i, nom, c = _texte(o.get("id"), 40), _texte(o.get("nom"), 80), _texte(o.get("couleur"), 7)
        if not i or not nom or i in ids or not re.fullmatch(r"#[0-9a-fA-F]{6}", c):
            raise Invalide("Organisme invalide.")
        titres = []
        for t in (o.get("titres") or [])[:500]:
            t = _texte(t, 150)
            if t and t not in titres:
                titres.append(t)
        ids.add(i)
        orgs.append({"id": i, "nom": nom, "couleur": c.lower(), "titres": titres})
    forms, fids = [], set()
    for f in (d.get("formations") or [])[:5000]:
        if not isinstance(f, dict):
            continue
        jours = []
        for j in (f.get("jours") or [])[:366]:
            j = _texte(j, 10)
            try:
                date.fromisoformat(j)
            except ValueError:
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", j) and j not in jours:
                jours.append(j)
        jours.sort()
        i, org, titre, cr = (_texte(f.get("id"), 40), _texte(f.get("org"), 40),
                             _texte(f.get("titre"), 150), _texte(f.get("creneau"), 10))
        if not i or i in fids or org not in ids or not titre or cr not in CRENEAUX or not jours:
            raise Invalide("Formation invalide : " + (titre or "sans titre") + ".")
        fids.add(i)
        forms.append({"id": i, "org": org, "titre": titre, "creneau": cr,
                      "jours": jours, "note": _texte(f.get("note"), 1000)})
    ferms, cids = [], set()
    for f in (d.get("fermetures") or [])[:1000]:
        if not isinstance(f, dict):
            continue
        jours = []
        for j in (f.get("jours") or [])[:366]:
            j = _texte(j, 10)
            try:
                date.fromisoformat(j)
            except ValueError:
                continue
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", j) and j not in jours:
                jours.append(j)
        jours.sort()
        i, t = _texte(f.get("id"), 40), _texte(f.get("type"), 12)
        if not i or i in cids or t not in TYPES_FERMETURE or not jours:
            raise Invalide("Fermeture invalide.")
        cids.add(i)
        ferms.append({"id": i, "type": t, "jours": jours, "note": _texte(f.get("note"), 200)})
    return {"orgs": orgs, "formations": forms, "fermetures": ferms}


@app.get("/api/donnees")
def donnees():
    return jsonify(_lire())


@app.post("/api/enregistrer")
def enregistrer():
    corps = request.get_json(silent=True) or {}
    try:
        propre = valider(corps.get("donnees") or {})
    except Invalide as e:
        return jsonify({"erreur": str(e)}), 400
    with VERROU:
        actuel = _lire()
        if corps.get("version") != actuel.get("version"):
            return jsonify({"erreur": "Le planning a été modifié ailleurs entre-temps. La page va se recharger."}), 409
        if os.path.exists(FICHIER):
            os.makedirs(SAUVEGARDES, exist_ok=True)
            nom = f"occupation-{datetime.now():%Y%m%d-%H%M%S}-v{actuel.get('version', 0)}.json"
            with open(FICHIER, "rb") as a, open(os.path.join(SAUVEGARDES, nom), "wb") as b:
                b.write(a.read())
            vieilles = sorted(x for x in os.listdir(SAUVEGARDES) if x.startswith("occupation-"))
            for x in vieilles[:max(0, len(vieilles) - GARDER_SAUVEGARDES)]:
                os.remove(os.path.join(SAUVEGARDES, x))
        v = int(actuel.get("version", 0)) + 1
        _ecrire({"version": v, "modifie": datetime.now().astimezone().isoformat(), **propre})
    return jsonify({"version": v})


if __name__ == "__main__":
    from waitress import serve
    os.makedirs(DONNEES, exist_ok=True)
    serve(app, host="127.0.0.1", port=int(os.environ.get("PLANEO_PORT") or 5003), threads=4)
