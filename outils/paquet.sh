#!/bin/sh
# Fabrique l'archive à déposer dans le dossier du sous-domaine sur Hostinger.
# Ne contient jamais de données : donnees/ n'y figure qu'avec sa protection (.htaccess).
set -e
cd "$(dirname "$0")/../site"
mkdir -p ../livrables
rm -f ../livrables/occupation-site.zip
zip -q -X ../livrables/occupation-site.zip index.html api.php robots.txt .htaccess donnees/.htaccess
unzip -l ../livrables/occupation-site.zip
