# Planning de la salle de formation — Fichier maître

Planning partagé de la salle de formation, utilisée par plusieurs organismes de formation.
But : retrouver d'un coup d'œil qui occupe la salle, quand, et pour quelle formation.
Porteur : Dr Franck Moyal.

Dossier : `~/Desktop/Claude-Projects/PLANNING-FORMATION`.
Dépôt : à créer (`git@github.com:drfranckmoyal-cloud/<NOM>.git`, privé).

**À lire en premier par toute conversation qui reprend le projet.** À tenir à jour à chaque étape,
puis commit et push dans la foulée.

## Tableau de bord

| Étape | Contenu | État |
|---|---|---|
| 0 | Fichier maître, dépôt git local | Fait (02/10/2026) |
| 1 | Cadrage : qui saisit, qui consulte, où ça vit | En cours |
| 2 | Maquette visuelle (vue mois, vue année) validée par Franck | À faire |
| 3 | Construction de l'outil | À faire |
| 4 | Mise en service, partage aux organismes | À faire |

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

## Questions ouvertes

| # | Question | Qui tranche | Réponse |
|---|---|---|---|
| Q1 | Qui saisit les réservations : Franck seul, ou chaque organisme ? | Franck | Franck seul (D1) |
| Q2 | Qui consulte, et sur quoi (ordinateur, téléphone) ? | Franck | |
| Q3 | Où vit l'outil (page web en ligne, Google Sheet, fichier sur le Mac…) ? | Franck, sur proposition de Claude | Page web partagée (D2) |
| Q4 | Combien d'organismes, lesquels, quelles couleurs ? | Franck | |
| Q5 | Que faire si deux formations tombent sur le même créneau (blocage ou simple alerte) ? | Franck | Alerte seulement (D3) |
| Q6 | Les jours d'une formation sur plusieurs jours sont-ils toujours consécutifs ? Week-ends inclus ? | Franck | Dates libres (D4) |
| Q7 | Une seule salle, ou plusieurs à terme ? | Franck | |
| Q8 | Faut-il d'autres infos (formateur, nombre de participants, contact) ? | Franck | |

## Journal

- **02/10/2026** — Lancement. Franck pose le cahier des charges (ci-dessus). Création du dossier,
  du dépôt git local et de ce fichier. Début du cadrage.
  Premières réponses de Franck : D1 à D4.

## Garde-fous

- Aucune donnée personnelle de stagiaires dans le planning ni dans le dépôt.
- Rien de secret (mot de passe, clé) dans le dépôt.
