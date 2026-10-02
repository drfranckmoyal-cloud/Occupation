# Planéo sur le serveur du portail (163.172.8.49) — en service depuis le 02/10/2026

- Adresse : https://163-172-8-49.nip.io/planeo/ — même connexion que DFM et OPCO Watch.
- Code : `/home/dfm/Planeo/` (`app.py`, `index.html`), venv propre (`flask`, `waitress`).
- Données : `/home/dfm/Planeo/donnees/occupation.json` + `sauvegardes/` (200 dernières).
- Service : `planeo.service` (port 5003, utilisateur `dfm`), copie dans ce dossier.
- nginx (`/etc/nginx/sites-available/dfm`, ancienne version : `/root/nginx-dfm.avant-planeo`) :
  `location /planeo/` vers 127.0.0.1:5003 avec `X-Forwarded-Prefix /planeo` ; la page
  `/portail` est fermée par `auth_request /_planeo_verif` (sans session : connexion DFM).
- Mot de passe : celui de DFM (`/home/dfm/DFM/acces.json`), lu seulement, jamais écrit.

Mettre à jour le code : copier `planeo/app.py` et `planeo/index.html` dans `/home/dfm/Planeo/`,
puis `systemctl restart planeo`.
