<?php
// Occupation de la salle de formation — partie serveur.
// Lecture libre du planning ; toute modification exige la connexion de l'administrateur.
// Les données vivent dans donnees/ (fichiers JSON), fermé au public par donnees/.htaccess.
declare(strict_types=1);

const DOSSIER    = __DIR__ . '/donnees';
const FICHIER    = DOSSIER . '/occupation.json';
const ADMIN      = DOSSIER . '/admin.json';
const TENTATIVES = DOSSIER . '/tentatives.json';
const SAUVEGARDES = DOSSIER . '/sauvegardes';
const SESSIONS   = DOSSIER . '/sessions';
const CRENEAUX   = ['journee', 'matin', 'apm', 'soir'];
const GARDER_SAUVEGARDES = 200;
const DUREE_SESSION = 60 * 60 * 24 * 60; // 60 jours

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function repondre(int $code, array $corps): void {
    http_response_code($code);
    echo json_encode($corps, JSON_UNESCAPED_UNICODE);
    exit;
}

function preparer_dossiers(): void {
    foreach ([DOSSIER, SAUVEGARDES, SESSIONS] as $d) {
        if (!is_dir($d) && !mkdir($d, 0700, true)) repondre(500, ['erreur' => 'Dossier de données impossible à créer.']);
    }
    $ht = DOSSIER . '/.htaccess';
    if (!file_exists($ht)) file_put_contents($ht, "Require all denied\nDeny from all\n");
}

function lire_json(string $f, $defaut) {
    if (!file_exists($f)) return $defaut;
    $v = json_decode((string)file_get_contents($f), true);
    return is_array($v) ? $v : $defaut;
}

function ecrire_json(string $f, array $v): void {
    $tmp = $f . '.' . bin2hex(random_bytes(4)) . '.tmp';
    if (file_put_contents($tmp, json_encode($v, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT)) === false || !rename($tmp, $f)) {
        @unlink($tmp);
        repondre(500, ['erreur' => "Écriture impossible sur le serveur."]);
    }
}

// Verrou exclusif pour qu'une écriture ne se mélange jamais avec une autre.
function avec_verrou(callable $fn) {
    $h = fopen(DOSSIER . '/.verrou', 'c');
    flock($h, LOCK_EX);
    try { return $fn(); } finally { flock($h, LOCK_UN); fclose($h); }
}

function donnees_vides(): array { return ['version' => 0, 'orgs' => [], 'formations' => []]; }

function texte($v, int $max): string {
    $s = trim(is_string($v) ? $v : '');
    return mb_substr($s, 0, $max);
}

// Reconstruit des données propres à partir de ce que la page envoie ; refuse le reste.
function valider(array $d): array {
    $orgs = []; $ids = [];
    foreach (array_slice((array)($d['orgs'] ?? []), 0, 100) as $o) {
        if (!is_array($o)) continue;
        $id = texte($o['id'] ?? '', 40);
        $nom = texte($o['nom'] ?? '', 80);
        $coul = texte($o['couleur'] ?? '', 7);
        if ($id === '' || $nom === '' || isset($ids[$id]) || !preg_match('/^#[0-9a-fA-F]{6}$/', $coul)) {
            repondre(400, ['erreur' => 'Organisme invalide.']);
        }
        $titres = [];
        foreach (array_slice((array)($o['titres'] ?? []), 0, 500) as $t) {
            $t = texte($t, 150);
            if ($t !== '' && !in_array($t, $titres, true)) $titres[] = $t;
        }
        $ids[$id] = true;
        $orgs[] = ['id' => $id, 'nom' => $nom, 'couleur' => strtolower($coul), 'titres' => $titres];
    }
    $formations = []; $fids = [];
    foreach (array_slice((array)($d['formations'] ?? []), 0, 5000) as $f) {
        if (!is_array($f)) continue;
        $id = texte($f['id'] ?? '', 40);
        $org = texte($f['org'] ?? '', 40);
        $titre = texte($f['titre'] ?? '', 150);
        $cr = texte($f['creneau'] ?? '', 10);
        $jours = [];
        foreach (array_slice((array)($f['jours'] ?? []), 0, 366) as $j) {
            $j = texte($j, 10);
            if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $j) && checkdate((int)substr($j, 5, 2), (int)substr($j, 8, 2), (int)substr($j, 0, 4))) {
                if (!in_array($j, $jours, true)) $jours[] = $j;
            }
        }
        sort($jours);
        if ($id === '' || isset($fids[$id]) || !isset($ids[$org]) || $titre === '' || !in_array($cr, CRENEAUX, true) || !$jours) {
            repondre(400, ['erreur' => 'Formation invalide : ' . ($titre ?: 'sans titre') . '.']);
        }
        $fids[$id] = true;
        $formations[] = ['id' => $id, 'org' => $org, 'titre' => $titre, 'creneau' => $cr, 'jours' => $jours, 'note' => texte($f['note'] ?? '', 1000)];
    }
    return ['orgs' => $orgs, 'formations' => $formations];
}

function ip(): string { return $_SERVER['REMOTE_ADDR'] ?? '?'; }

// Au-delà de 10 essais ratés en 15 minutes depuis une même adresse, on refuse un moment.
function trop_de_tentatives(): bool {
    $t = lire_json(TENTATIVES, []);
    $recents = array_filter($t[ip()] ?? [], fn($x) => $x > time() - 900);
    return count($recents) >= 10;
}
function noter_echec(): void {
    $t = lire_json(TENTATIVES, []);
    foreach ($t as $k => $l) { $t[$k] = array_values(array_filter($l, fn($x) => $x > time() - 900)); if (!$t[$k]) unset($t[$k]); }
    $t[ip()][] = time();
    ecrire_json(TENTATIVES, $t);
}

preparer_dossiers();
session_save_path(SESSIONS);
ini_set('session.gc_maxlifetime', (string)DUREE_SESSION);
session_name('occupation');
session_set_cookie_params([
    'lifetime' => DUREE_SESSION, 'path' => '/',
    'secure' => !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off',
    'httponly' => true, 'samesite' => 'Strict',
]);
session_start();
$admin = !empty($_SESSION['admin']);
$action = $_GET['a'] ?? '';

if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    session_write_close();
    if ($action === 'etat') repondre(200, ['admin' => $admin, 'initialise' => file_exists(ADMIN)]);
    if ($action === 'donnees') repondre(200, lire_json(FICHIER, donnees_vides()));
    repondre(404, ['erreur' => 'Action inconnue.']);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') repondre(405, ['erreur' => 'Méthode refusée.']);
// Les écritures ne viennent que de la page elle-même (en-tête qu'un autre site ne peut pas ajouter).
if (($_SERVER['HTTP_X_OCCUPATION'] ?? '') !== '1') repondre(403, ['erreur' => 'Requête refusée.']);
$corps = json_decode((string)file_get_contents('php://input'), true);
if (!is_array($corps)) $corps = [];

switch ($action) {
    case 'initialiser':
        $mdp = (string)($corps['motdepasse'] ?? '');
        if (mb_strlen($mdp) < 10) repondre(400, ['erreur' => 'Le mot de passe doit faire au moins 10 caractères.']);
        avec_verrou(function () use ($mdp) {
            if (file_exists(ADMIN)) repondre(409, ['erreur' => 'Le mot de passe administrateur existe déjà.']);
            ecrire_json(ADMIN, ['hash' => password_hash($mdp, PASSWORD_DEFAULT)]);
        });
        session_regenerate_id(true);
        $_SESSION['admin'] = true;
        repondre(200, ['admin' => true]);

    case 'connexion':
        $a = lire_json(ADMIN, []);
        if (!isset($a['hash'])) repondre(409, ['erreur' => "Aucun mot de passe n'a encore été créé."]);
        if (avec_verrou('trop_de_tentatives')) repondre(429, ['erreur' => 'Trop d’essais. Réessayez dans un quart d’heure.']);
        if (!password_verify((string)($corps['motdepasse'] ?? ''), $a['hash'])) {
            avec_verrou('noter_echec');
            sleep(2);
            repondre(401, ['erreur' => 'Mot de passe incorrect.']);
        }
        session_regenerate_id(true);
        $_SESSION['admin'] = true;
        repondre(200, ['admin' => true]);

    case 'deconnexion':
        $_SESSION = [];
        session_destroy();
        repondre(200, ['admin' => false]);

    case 'changer_mdp':
        if (!$admin) repondre(401, ['erreur' => 'Connexion requise.']);
        $a = lire_json(ADMIN, []);
        if (!password_verify((string)($corps['ancien'] ?? ''), $a['hash'] ?? '')) { sleep(2); repondre(401, ['erreur' => 'Ancien mot de passe incorrect.']); }
        $n = (string)($corps['nouveau'] ?? '');
        if (mb_strlen($n) < 10) repondre(400, ['erreur' => 'Le mot de passe doit faire au moins 10 caractères.']);
        avec_verrou(fn() => ecrire_json(ADMIN, ['hash' => password_hash($n, PASSWORD_DEFAULT)]));
        repondre(200, ['ok' => true]);

    case 'enregistrer':
        if (!$admin) repondre(401, ['erreur' => 'Votre connexion a expiré. Reconnectez-vous.']);
        session_write_close();
        $propre = valider((array)($corps['donnees'] ?? []));
        $version = avec_verrou(function () use ($propre, $corps) {
            $actuel = lire_json(FICHIER, donnees_vides());
            if ((int)($corps['version'] ?? -1) !== (int)$actuel['version']) {
                repondre(409, ['erreur' => 'Le planning a été modifié ailleurs entre-temps. La page va se recharger.']);
            }
            if (file_exists(FICHIER)) {
                copy(FICHIER, SAUVEGARDES . '/occupation-' . date('Ymd-His') . '-v' . $actuel['version'] . '.json');
                $vieilles = glob(SAUVEGARDES . '/occupation-*.json') ?: [];
                sort($vieilles);
                foreach (array_slice($vieilles, 0, max(0, count($vieilles) - GARDER_SAUVEGARDES)) as $v) @unlink($v);
            }
            $propre = ['version' => (int)$actuel['version'] + 1, 'modifie' => date('c')] + $propre;
            ecrire_json(FICHIER, $propre);
            return $propre['version'];
        });
        repondre(200, ['version' => $version]);
}
repondre(404, ['erreur' => 'Action inconnue.']);
