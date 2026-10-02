"""Serveur d'essai local : sert site/ et imite api.php (mêmes actions, mêmes réponses).

Sert seulement à essayer la page sur le Mac, sans PHP. Les données d'essai vont dans
le dossier donné par OCCUPATION_ESSAI (par défaut un dossier temporaire), jamais dans le dépôt.
Lancement : python3 outils/serveur_essai.py [port]
"""
import hashlib, http.server, json, os, re, secrets, sys, tempfile, time
from datetime import date, datetime
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')
DONNEES = os.environ.get('OCCUPATION_ESSAI') or os.path.join(tempfile.gettempdir(), 'occupation-essai')
os.makedirs(DONNEES, exist_ok=True)
FICHIER, ADMIN = os.path.join(DONNEES, 'occupation.json'), os.path.join(DONNEES, 'admin.json')
CRENEAUX = {'journee', 'matin', 'apm', 'soir'}
SESSIONS = set()


def lire(f, defaut):
    try:
        with open(f) as h: return json.load(h)
    except Exception: return defaut


def ecrire(f, v):
    with open(f, 'w') as h: json.dump(v, h, ensure_ascii=False, indent=1)


def hacher(mdp, sel=None):
    sel = sel or secrets.token_hex(8)
    return sel + '$' + hashlib.pbkdf2_hmac('sha256', mdp.encode(), sel.encode(), 100_000).hex()


class Erreur(Exception):
    def __init__(self, code, msg): self.code, self.msg = code, msg


def texte(v, n): return (v.strip() if isinstance(v, str) else '')[:n]


def valider(d):
    orgs, ids = [], set()
    for o in (d.get('orgs') or [])[:100]:
        i, nom, c = texte(o.get('id'), 40), texte(o.get('nom'), 80), texte(o.get('couleur'), 7)
        if not i or not nom or i in ids or not re.fullmatch(r'#[0-9a-fA-F]{6}', c): raise Erreur(400, 'Organisme invalide.')
        titres = []
        for t in (o.get('titres') or [])[:500]:
            t = texte(t, 150)
            if t and t not in titres: titres.append(t)
        ids.add(i); orgs.append({'id': i, 'nom': nom, 'couleur': c.lower(), 'titres': titres})
    forms, fids = [], set()
    for f in (d.get('formations') or [])[:5000]:
        jours = []
        for j in (f.get('jours') or [])[:366]:
            j = texte(j, 10)
            try: date.fromisoformat(j)
            except ValueError: continue
            if j not in jours: jours.append(j)
        jours.sort()
        i, org, titre, cr = texte(f.get('id'), 40), texte(f.get('org'), 40), texte(f.get('titre'), 150), texte(f.get('creneau'), 10)
        if not i or i in fids or org not in ids or not titre or cr not in CRENEAUX or not jours:
            raise Erreur(400, 'Formation invalide : ' + (titre or 'sans titre') + '.')
        fids.add(i); forms.append({'id': i, 'org': org, 'titre': titre, 'creneau': cr, 'jours': jours, 'note': texte(f.get('note'), 1000)})
    return {'orgs': orgs, 'formations': forms}


class Gestion(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=RACINE, **k)

    def session(self):
        c = SimpleCookie(self.headers.get('Cookie', ''))
        return c['occupation'].value if 'occupation' in c else None

    def repondre(self, code, corps, cookie=None):
        b = json.dumps(corps, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        if cookie is not None:
            self.send_header('Set-Cookie', f'occupation={cookie}; Path=/; HttpOnly; SameSite=Strict')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def api(self, methode):
        a = parse_qs(urlparse(self.path).query).get('a', [''])[0]
        admin = self.session() in SESSIONS
        vide = {'version': 0, 'orgs': [], 'formations': []}
        try:
            if methode == 'GET':
                if a == 'etat': return self.repondre(200, {'admin': admin, 'initialise': os.path.exists(ADMIN)})
                if a == 'donnees': return self.repondre(200, lire(FICHIER, vide))
                raise Erreur(404, 'Action inconnue.')
            if self.headers.get('X-Occupation') != '1': raise Erreur(403, 'Requête refusée.')
            n = int(self.headers.get('Content-Length') or 0)
            try: corps = json.loads(self.rfile.read(n) or b'{}')
            except ValueError: corps = {}
            if a in ('initialiser', 'connexion'):
                mdp = str(corps.get('motdepasse', ''))
                if a == 'initialiser':
                    if len(mdp) < 10: raise Erreur(400, 'Le mot de passe doit faire au moins 10 caractères.')
                    if os.path.exists(ADMIN): raise Erreur(409, 'Le mot de passe administrateur existe déjà.')
                    ecrire(ADMIN, {'hash': hacher(mdp)})
                else:
                    h = lire(ADMIN, {}).get('hash')
                    if not h: raise Erreur(409, "Aucun mot de passe n'a encore été créé.")
                    if hacher(mdp, h.split('$')[0]) != h: time.sleep(1); raise Erreur(401, 'Mot de passe incorrect.')
                jeton = secrets.token_hex(16); SESSIONS.add(jeton)
                return self.repondre(200, {'admin': True}, cookie=jeton)
            if a == 'deconnexion':
                SESSIONS.discard(self.session()); return self.repondre(200, {'admin': False}, cookie='')
            if a == 'changer_mdp':
                if not admin: raise Erreur(401, 'Connexion requise.')
                h = lire(ADMIN, {}).get('hash', '$')
                if hacher(str(corps.get('ancien', '')), h.split('$')[0]) != h: raise Erreur(401, 'Ancien mot de passe incorrect.')
                if len(str(corps.get('nouveau', ''))) < 10: raise Erreur(400, 'Le mot de passe doit faire au moins 10 caractères.')
                ecrire(ADMIN, {'hash': hacher(str(corps['nouveau']))}); return self.repondre(200, {'ok': True})
            if a == 'enregistrer':
                if not admin: raise Erreur(401, 'Votre connexion a expiré. Reconnectez-vous.')
                propre = valider(corps.get('donnees') or {})
                actuel = lire(FICHIER, vide)
                if corps.get('version') != actuel['version']:
                    raise Erreur(409, 'Le planning a été modifié ailleurs entre-temps. La page va se recharger.')
                v = actuel['version'] + 1
                ecrire(FICHIER, {'version': v, 'modifie': datetime.now().astimezone().isoformat(), **propre})
                return self.repondre(200, {'version': v})
            raise Erreur(404, 'Action inconnue.')
        except Erreur as e:
            self.repondre(e.code, {'erreur': e.msg})

    def do_GET(self):
        if urlparse(self.path).path.endswith('/api.php'): return self.api('GET')
        if urlparse(self.path).path.startswith('/donnees'): return self.repondre(403, {'erreur': 'interdit'})
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path.endswith('/api.php'): return self.api('POST')
        self.repondre(405, {'erreur': 'Méthode refusée.'})


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    print(f'Essai : http://localhost:{port}  (données : {DONNEES})', flush=True)
    http.server.ThreadingHTTPServer(('127.0.0.1', port), Gestion).serve_forever()
