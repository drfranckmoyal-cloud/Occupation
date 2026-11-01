# Planéo sur le serveur du portail (163.172.8.49) — en service depuis le 02/10/2026

- Adresse : https://163-172-8-49.nip.io/planeo/ — même connexion que DFM et OPCO Watch.
- Code : `/home/dfm/Planeo/` (`app.py`, `index.html`), venv propre (`flask`, `waitress`).
- Données : `/home/dfm/Planeo/donnees/occupation.json` + `sauvegardes/` (200 dernières).
- Service : `planeo.service` (port 5003, utilisateur `dfm`), copie dans ce dossier.
- nginx (`/etc/nginx/sites-available/dfm`, ancienne version : `/root/nginx-dfm.avant-planeo`) :
  `location /planeo/` vers 127.0.0.1:5003 avec `X-Forwarded-Prefix /planeo` ; la page
  `/portail` est fermée par `auth_request /_planeo_verif` (sans session : connexion DFM).
- Mot de passe : celui de DFM (`/home/dfm/DFM/acces.json`), lu seulement, jamais écrit.

Mettre à jour le code : copier `planeo/app.py`, `planeo/groupes.py`, `planeo/releve.py` et `planeo/index.html` dans `/home/dfm/Planeo/`,
puis `systemctl restart planeo`.

## Groupes (demandes d'inscription)

- Données personnelles : `/home/dfm/Planeo/donnees/groupes.json` (lisible du seul service) et
  `donnees/sauvegardes-groupes/` (50 dernières copies). Jamais dans le dépôt.
- Relevé du matin : `planeo-releve.timer` (6 h) lance `releve.py`.
- Accès Google : clé du compte de service dans `/home/dfm/Planeo/compte-google.json` (droits 600, jamais dans
  le dépôt). Franck partage chaque classeur en lecture avec l'adresse de ce compte.
- Dépendances du venv : `flask waitress google-auth requests`.
