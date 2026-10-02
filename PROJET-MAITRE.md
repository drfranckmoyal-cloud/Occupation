# Planéo — planning de la salle de formation — Fichier maître

Planning partagé de la salle de formation, utilisée par plusieurs organismes de formation.
But : retrouver d'un coup d'œil qui occupe la salle, quand, et pour quelle formation.
Porteur : Dr Franck Moyal.

Dossier : `~/Desktop/Claude-Projects/PLANNING-FORMATION`.
Dépôt : `git@github.com:drfranckmoyal-cloud/Occupation.git` (privé).

**À lire en premier par toute conversation qui reprend le projet.** À tenir à jour à chaque étape,
puis commit et push dans la foulée.

## Tableau de bord

| Étape | Contenu | État |
|---|---|---|
| 0 | Fichier maître, dépôt git, GitHub | Fait (02/10/2026) |
| 1 | Cadrage : qui saisit, qui consulte, où ça vit | Fait (02/10/2026) |
| 2 | Maquette visuelle (vue mois, vue année) | Faite ; Franck demande la construction complète |
| 3 | Construction de l'outil (`site/`) | Fait, essayé sur le Mac (02/10/2026) |
| 4 | Mise en ligne sur planning.drfranckmoyal.fr | **En service** sur le portail CEMEDIS (`/planeo/`, mot de passe DFM) depuis le 02/10/2026 |

## Cahier des charges initial (Franck, 02/10/2026)

1. Un calendrier en vue **mois** et en vue **année**.
2. On voit très facilement l'aperçu des formations sur le mois / l'année.
3. **Une couleur par organisme de formation.**
4. Pour chaque formation, on choisit le **créneau** : journée entière / matin / après-midi / soirée,
   et le **nombre de jours**.
5. On saisit le **titre de la formation** ; les titres sont **gardés en mémoire par organisme**
   (on les retrouve dans une liste au lieu de les retaper).

## Verrous (décisions de Franck, non renégociables)

- V1. Outil très simple : un calendrier, pas un logiciel de gestion.
- V2. Une couleur par organisme.
- V3. Créneaux : journée entière, matin, après-midi, soirée.
- V4. Titres de formation mémorisés par organisme.

## Décisions

- D1 (02/10) **Franck seul saisit** les réservations. Les organismes consultent, sans pouvoir modifier.
- D2 (02/10) **Page web partagée** : un lien, lisible sur ordinateur et téléphone, la même version pour tous.
- D3 (02/10) **Chevauchement = simple alerte** : l'outil prévient, mais laisse enregistrer.
- D4 (02/10) **Dates libres** pour une formation de plusieurs jours : on choisit les jours un par un
  (le « nombre de jours » du cahier des charges se déduit des jours cochés).
- D5 (02/10) **Organismes créés par Franck dans l'application** (nom + couleur), pas de liste figée dans le code.
- D6 (02/10) **Une seule salle.**
- D7 (02/10) Par formation : organisme, titre, créneau, jours, **et une note libre**.
- D8 (02/10) **Hébergement sur le compte Hostinger de Franck** (sous-domaine type `planning.drfranckmoyal.fr`
  : consultation publique par lien, saisie derrière le mot de passe de Franck.
- D9 (02/10) **Pas d'horaires** affichés : seulement Journée / Matin / Après-midi / Soirée.
- D10 (02/10) **Visible par toute personne qui a le lien**, sans mot de passe. Page non indexée par Google.
- D11 (02/10) Adresse : **planning.drfranckmoyal.fr**.
- D12 (02/10) Technique : une page (`site/index.html`) + un petit programme PHP (`site/api.php`) chez
  Hostinger ; données dans un fichier `donnees/occupation.json` (pas de base MySQL à gérer), fermé au
  public. Copie automatique avant chaque modification (`donnees/sauvegardes/`, 200 dernières gardées).
- D13 (02/10) Le mot de passe administrateur est **créé par Franck lui-même** à la première visite de
  `planning.drfranckmoyal.fr/?admin` ; seule son empreinte est gardée sur le serveur, jamais en clair,
  jamais dans le dépôt. 10 essais ratés en 15 min bloquent l'accès un quart d'heure.
- D15 (02/10) Franck gère seul tous les organismes : aucun accès à créer pour eux. Le lien public
  reste disponible, le partager ou non est à sa main.
- D16 (02/10) **Nom : Planéo** (choisi par Franck). Dépôt et dossier gardent leur nom (`Occupation`,
  `PLANNING-FORMATION`).
- D17 (02/10) **Intégration au portail CEMEDIS Formations** (https://163-172-8-49.nip.io/portail, page
  statique `/var/www/portail/index.html` sur le serveur Scaleway de DFM) : une 3e carte « Planéo » qui
  ouvre planning.drfranckmoyal.fr. Planéo reste chez Hostinger avec son mot de passe propre (choix de
  Franck, contre un déménagement sur le serveur DFM). Lien « Portail CEMEDIS » en bas de Planéo, pour
  l'administrateur seulement.
- D18 (02/10) **Un seul mot de passe pour tout le portail** (demande de Franck) : Planéo déménage
  sur le serveur du portail, sous https://163-172-8-49.nip.io/planeo/, et utilise la connexion de DFM
  (même cookie, même hôte). Plus de mot de passe propre à Planéo. La page du portail elle-même est
  fermée derrière cette connexion. La connexion dure une journée de travail (réglage DFM).
  L'ancienne adresse planning.drfranckmoyal.fr renvoie vers la nouvelle. Version PHP (`site/`)
  gardée en archive. Notice serveur : `deploiement/LISEZ-MOI.md`.
- D19 (02/10) **L'annexe planning.drfranckmoyal.fr est retirée** (DNS OVH, sous-domaine et dossier
  Hostinger) : rien de Planéo ne reste sur drfranckmoyal.fr. Planéo vit uniquement sur le portail.
- D20 (02/10, revu le même jour à la demande de Franck) **Superpositions** : quand plusieurs formations
  partagent un créneau, la bande se partage côte à côte, chaque formation garde sa couleur et son titre et
  s'ouvre d'un clic ; un cadre rouge signale la superposition (vue année : bande rayée aux couleurs).
- D21 (02/10) **Fermetures** (bouton « Fermetures ») : deux types, **Congés** (salle fermée, hachuré gris)
  et **Fermeture possible** (à confirmer, hachuré orange), jours au choix, note. Les **jours fériés**
  français sont calculés et affichés d'office. Alerte si une formation tombe un jour fermé ou férié.
- D22 (02/10) **Choix des jours par un petit calendrier cliquable** dans la saisie (un clic ajoute ou
  retire un jour, flèches pour changer de mois, pastilles des formations déjà prévues, fermetures et
  fériés visibles), au lieu du champ date + bouton « Ajouter ».
- D14 (02/10) Un chevauchement apparaît en deux couleurs, entouré de rouge.

## Questions ouvertes

Toutes tranchées au 02/10/2026 (Q1→D1, Q2→D10, Q3→D2, Q4→D5, Q5→D3, Q6→D4, Q7→D6, Q8→D7, Q9→D9, Q10→D11).

## Ce que fait l'outil

- **Tout le monde (lien)** : vue mois (chaque jour en trois bandes matin / après-midi / soirée, couleur de
  l'organisme, titre), vue année (12 petits calendriers), clic sur un jour = détail (titre, organisme,
  créneau, jours, note). Flèches ← → du clavier pour changer de mois/année. Imprimable.
- **Franck connecté** (« Accès administrateur » en bas de page, ou adresse terminée par `?admin`) :
  bouton « Organismes » (créer, renommer, changer la couleur, supprimer s'il n'a aucune formation,
  oublier un titre mémorisé) ; « + Formation » ou clic sur un jour libre (organisme, titre proposé parmi
  ceux de l'organisme, créneau, jours ajoutés un par un, note libre visible par tous) ; clic sur une
  formation pour la modifier ou la supprimer ; alerte si la salle est déjà prise ; « Changer le mot de passe ».
- La connexion reste ouverte 60 jours sur le même navigateur.

## Mise en ligne

Fait le 02/10/2026 (avec l'accord de Franck, dans son Chrome) :
1. hPanel → site drfranckmoyal.fr → Domaines → Sous-domaines : créer `planning` (dossier
   `public_html/planning`).
2. Si besoin, chez OVH (où est réservé le domaine) : enregistrement A `planning` → `91.108.101.161`.
3. Attendre le certificat https (hPanel → Sécurité → SSL).
4. Déposer l'archive (ci-dessous) dans le dossier du sous-domaine.
5. Franck ouvre `https://planning.drfranckmoyal.fr/?admin` et **crée lui-même son mot de passe**.

Mettre à jour la page plus tard : `outils/paquet.sh` fabrique `livrables/occupation-site.zip` (jamais de
données dedans) ; dans le gestionnaire de fichiers d'Hostinger, le déposer dans le dossier du
sous-domaine, « Extract » avec `.` et « Overwrite existing files », puis mettre le zip à la corbeille
(décocher « Skip trash bin »). Le dossier `donnees/` en ligne n'est jamais écrasé.

## Informations techniques

- `site/` : ce qui part en ligne (`index.html`, `api.php`, `.htaccess`, `robots.txt`, `donnees/.htaccess`).
- `maquette/` : la maquette du 02/10 (données fictives, sans serveur).
- `outils/serveur_essai.py` : imite `api.php` en Python pour essayer la page sur le Mac (PHP n'est pas
  installé sur le Mac) ; aperçu `occupation-essai`, port 8791. Données d'essai dans un dossier temporaire.
- `outils/paquet.sh` : fabrique l'archive à déposer.
- Sauvegarde en ligne : `donnees/occupation.json` + `donnees/sauvegardes/`. Pour récupérer un état
  ancien, remplacer `occupation.json` par une copie de `sauvegardes/` dans le gestionnaire de fichiers.

## Journal

- **02/10/2026** — Lancement. Franck pose le cahier des charges (ci-dessus). Création du dossier,
  du dépôt git local et de ce fichier. Début du cadrage.
  Premières réponses de Franck : D1 à D4, puis D5 à D8. Dépôt GitHub `Occupation` créé par Franck.
  Maquette `maquette/index.html` (données fictives, fonctionne sans serveur, mémoire du navigateur) :
  vue mois où chaque jour a trois bandes matin / après-midi / soirée colorées par organisme ; vue année
  en 12 petits calendriers, chaque jour coupé en trois bandes ; fenêtre de saisie (organisme, titre
  proposé parmi ceux déjà utilisés par l'organisme, créneau, jours un par un, note, alerte de
  chevauchement) ; fenêtre Organismes (ajout, couleur modifiable). Vérifiée dans le navigateur.
- **02/10/2026** — Franck tranche : pas d'horaires, visible par lien, adresse planning.drfranckmoyal.fr,
  « construis tout ». Construction de `site/` (page + `api.php`), essai complet sur le Mac avec le
  serveur d'essai : création du mot de passe, organismes, formations, mémoire des titres, alerte de
  chevauchement, refus d'écrire sans connexion, vue visiteur sans boutons de saisie. Archive prête.
  Reste la mise en ligne (sous-domaine, DNS, dépôt, mot de passe).
- **02/10/2026** — Mise en ligne, accord de Franck : sous-domaine `planning` créé dans hPanel (dossier
  `/home/u272950422/domains/drfranckmoyal.fr/public_html/planning`) ; chez OVH, enregistrement A
  `planning` → `91.108.101.161` ajouté (rien d'autre touché) ; certificat https Lifetime SSL posé
  automatiquement ; archive déposée et décompressée, archive et page d'attente `default.php` mises
  à la corbeille. Vérifié en ligne : page 200, `donnees/` et `.htaccess` refusés (403), écriture sans
  connexion refusée (401), en-tête manquant refusé (403), mot de passe trop court refusé, page non
  indexable. Reste : Franck crée son mot de passe (`/?admin`), puis premier enregistrement à vérifier.
- **02/10/2026** — Franck crée son mot de passe, 3 organismes et 2 premières formations. Vérifié côté
  serveur : version 6, données bien enregistrées, mot de passe en place. Mise en service terminée.
- **02/10/2026** — Intégration au portail CEMEDIS Formations (D17) et nom Planéo (D16). Carte préparée,
  copie d'essai déposée à `/portail/essai-salle.html` sur le serveur DFM. Mise en ligne de la carte et
  de la nouvelle version de Planéo en attente de l'accord explicite de Franck.
- **02/10/2026** — Accord de Franck (« oui pour les deux ») : portail mis à jour sur le serveur DFM
  (ancienne page gardée en `/var/www/portail/index.html.avant-planeo`, copie d'essai supprimée) ;
  Planéo redéposé chez Hostinger (archive mise à la corbeille). Vérifié en ligne : carte Planéo
  présente sur le portail, titre « Planéo » et lien « Portail CEMEDIS » sur le planning, données
  intactes (3 organismes, 2 formations).

## Garde-fous

- Aucune donnée personnelle de stagiaires dans le planning ni dans le dépôt.
- Rien de secret (mot de passe, clé) dans le dépôt.
- Le contenu en ligne de `donnees/` (planning, empreinte du mot de passe) n'est ni copié dans le dépôt ni écrasé.

- **02/10/2026** — D18 : Planéo installé sur le serveur du portail (service `planeo`, port 5003),
  données reprises (version 6, identiques à Hostinger), nginx réglé (copie de l'ancien réglage gardée),
  portail fermé derrière la connexion DFM, carte Planéo pointant vers `/planeo/`. Vérifié sans
  connexion : `/portail`, `/planeo/`, `/` et `/opco/` renvoient vers la connexion, l'API refuse (401).
  Reste : redirection de planning.drfranckmoyal.fr chez Hostinger.
- **02/10/2026** — Franck préfère retirer l'annexe plutôt que rediriger (D19). Il a lui-même supprimé
  la ligne A `planning` chez OVH, le sous-domaine dans hPanel et mis le dossier `public_html/planning`
  à la corbeille. Vérifié : `planning` n'existe plus chez OVH ; messagerie (MX, SPF), vérification
  Google, site et www intacts. drfranckmoyal.fr est revenu à son état du matin.
- **02/10/2026** — Retours de Franck : superposition illisible (18 novembre), fermetures/congés, choix des
  jours peu pratique. D20 à D22 faits, essayés sur le Mac avec une copie des vraies données, puis mis en
  ligne (anciens fichiers gardés dans `/home/dfm/Planeo/anciennes/`). Données intactes.
