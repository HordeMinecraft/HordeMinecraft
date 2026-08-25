<?php
declare(strict_types=1);

$configPath = __DIR__ . '/config.php';
$config = file_exists($configPath) ? require $configPath : require __DIR__ . '/config.example.php';

function send_cors(array $config): void {
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';
    if ($origin && in_array($origin, $config['cors_origins'], true)) {
        header('Access-Control-Allow-Origin: ' . $origin);
        header('Vary: Origin');
    }
    header('Access-Control-Allow-Credentials: true');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Authorization, Content-Type, X-Horde-Server-Secret');
}

function horde_starts_with(string $haystack, string $needle): bool {
    return $needle === '' || strncmp($haystack, $needle, strlen($needle)) === 0;
}

function json_response($data, int $status = 200): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function read_json(): array {
    $raw = file_get_contents('php://input') ?: '';
    $data = json_decode($raw, true);
    if (!is_array($data)) json_response(['detail' => 'Некорректный JSON.'], 400);
    return $data;
}

function pdo(array $config): PDO {
    static $pdo = null;
    if ($pdo) return $pdo;
    $dsn = 'mysql:host=' . $config['db_host'] . ';dbname=' . $config['db_name'] . ';charset=utf8mb4';
    $pdo = new PDO($dsn, $config['db_user'], $config['db_password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT => 5,
    ]);
    return $pdo;
}

function ensure_schema(PDO $db): void {
    static $done = false;
    if ($done) return;
    $sqls = [
        "CREATE TABLE IF NOT EXISTS users (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, minecraft_nick VARCHAR(32) NOT NULL, minecraft_uuid CHAR(36) NULL, email VARCHAR(255) NULL, password_hash VARCHAR(255) NULL, skin_model ENUM('classic','slim') NOT NULL DEFAULT 'classic', skin_data_url MEDIUMTEXT NULL, skin_updated_at TIMESTAMP NULL, role ENUM('player','moderator','admin') NOT NULL DEFAULT 'player', is_site_linked TINYINT(1) NOT NULL DEFAULT 0, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, last_login_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_users_minecraft_nick (minecraft_nick), UNIQUE KEY uq_users_minecraft_uuid (minecraft_uuid), KEY idx_users_email (email)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS sessions (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, user_id BIGINT UNSIGNED NOT NULL, session_token_hash CHAR(64) NOT NULL, user_agent VARCHAR(255) NULL, ip_hash CHAR(64) NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, revoked_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_sessions_token_hash (session_token_hash), KEY idx_sessions_user_id (user_id), KEY idx_sessions_expires_at (expires_at), CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS launcher_tokens (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, user_id BIGINT UNSIGNED NOT NULL, token_hash CHAR(64) NOT NULL, device_name VARCHAR(128) NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, revoked_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_launcher_tokens_token_hash (token_hash), KEY idx_launcher_tokens_user_id (user_id), KEY idx_launcher_tokens_expires_at (expires_at), CONSTRAINT fk_launcher_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS site_link_codes (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, minecraft_nick VARCHAR(32) NOT NULL, code_hash CHAR(64) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, used_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_site_link_codes_code_hash (code_hash), KEY idx_site_link_codes_nick (minecraft_nick), KEY idx_site_link_codes_expires_at (expires_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS donate_subscriptions (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, minecraft_nick VARCHAR(32) NOT NULL, tier ENUM('PRO','ELITE','PRIME','EMPEROR') NOT NULL, source VARCHAR(64) NOT NULL DEFAULT 'donationalerts', external_payment_id VARCHAR(128) NULL, started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, active TINYINT(1) NOT NULL DEFAULT 1, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (id), UNIQUE KEY uq_donate_external_payment (source, external_payment_id), KEY idx_donate_nick_active (minecraft_nick, active), KEY idx_donate_expires_at (expires_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS donate_pending_kits (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, minecraft_nick VARCHAR(32) NOT NULL, tier ENUM('PRO','ELITE','PRIME','EMPEROR') NOT NULL, source VARCHAR(64) NOT NULL DEFAULT 'donationalerts', external_payment_id VARCHAR(128) NULL, status VARCHAR(32) NOT NULL DEFAULT 'pending', queued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, claimed_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_pending_kit_external_payment (source, external_payment_id), KEY idx_pending_kit_nick_claimed (minecraft_nick, claimed_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS player_inventory_snapshots (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, minecraft_nick VARCHAR(32) NOT NULL, minecraft_uuid CHAR(36) NULL, inventory_json JSON NOT NULL, equipment_json JSON NULL, ender_chest_json JSON NULL, updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, PRIMARY KEY (id), UNIQUE KEY uq_inventory_nick (minecraft_nick), KEY idx_inventory_uuid (minecraft_uuid), KEY idx_inventory_updated_at (updated_at)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci",
        "CREATE TABLE IF NOT EXISTS password_reset_codes (id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT, user_id BIGINT UNSIGNED NOT NULL, code_hash CHAR(64) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, used_at TIMESTAMP NULL, PRIMARY KEY (id), UNIQUE KEY uq_password_reset_code_hash (code_hash), KEY idx_password_reset_user (user_id), KEY idx_password_reset_expires (expires_at), CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    ];
    foreach ($sqls as $sql) $db->exec($sql);
    $done = true;
}

function normalize_nick($nick): string {
    $nick = trim((string)$nick);
    if (strlen($nick) < 3 || strlen($nick) > 32 || !preg_match('/^[A-Za-z0-9_]+$/', $nick)) {
        json_response(['detail' => 'Ник должен быть 3-32 символа: латиница, цифры и подчёркивание.'], 400);
    }
    return $nick;
}

function token_hash(string $token, string $secret): string { return hash_hmac('sha256', $token, $secret); }
function new_token(): string { return rtrim(strtr(base64_encode(random_bytes(40)), '+/', '-_'), '='); }
function code_short(): string { $a='ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; $s=''; for($i=0;$i<8;$i++) $s.=$a[random_int(0, strlen($a)-1)]; return $s; }
function password_make(string $password): string { return password_hash($password, defined('PASSWORD_ARGON2ID') ? PASSWORD_ARGON2ID : PASSWORD_DEFAULT); }
function password_ok(?string $hash, string $password): bool { return $hash ? password_verify($password, $hash) : false; }
function public_user(array $u): array { return ['id'=>(int)$u['id'], 'minecraft_nick'=>$u['minecraft_nick'], 'email'=>$u['email'] ?? null, 'skin_model'=>$u['skin_model'] ?: 'classic', 'skin_data_url'=>$u['skin_data_url'] ?? null, 'skin_updated_at'=>$u['skin_updated_at'] ?? null]; }

function auth_user(PDO $db, array $config): array {
    $auth = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (!horde_starts_with($auth, 'Bearer ')) json_response(['detail'=>'Нет токена.'], 401);
    $digest = token_hash(substr($auth, 7), $config['server_secret']);
    $st=$db->prepare('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.session_token_hash=? AND s.revoked_at IS NULL AND s.expires_at > NOW()');
    $st->execute([$digest]);
    $u=$st->fetch();
    if (!$u) json_response(['detail'=>'Сессия истекла.'], 401);
    return $u;
}

function issue_tokens(PDO $db, array $config, int $userId): array {
    $session = new_token(); $launcher = new_token();
    $expires = (new DateTimeImmutable('now', new DateTimeZone('UTC')))->modify('+' . (int)$config['session_days'] . ' days')->format('Y-m-d H:i:s');
    $ua = substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 255);
    $ip = $_SERVER['REMOTE_ADDR'] ?? '';
    $ipHash = $ip ? token_hash($ip, $config['server_secret']) : null;
    $st=$db->prepare('INSERT INTO sessions (user_id, session_token_hash, user_agent, ip_hash, expires_at) VALUES (?,?,?,?,?)');
    $st->execute([$userId, token_hash($session, $config['server_secret']), $ua, $ipHash, $expires]);
    $st=$db->prepare('INSERT INTO launcher_tokens (user_id, token_hash, expires_at) VALUES (?,?,?)');
    $st->execute([$userId, token_hash($launcher, $config['server_secret']), $expires]);
    return ['session_token'=>$session, 'launcher_token'=>$launcher, 'expires_at'=>(new DateTimeImmutable($expires, new DateTimeZone('UTC')))->format(DATE_ATOM)];
}

send_cors($config);
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') exit;
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH) ?: '/';
$base = rtrim(dirname($_SERVER['SCRIPT_NAME']), '/');
if ($base && horde_starts_with($path, $base)) $path = substr($path, strlen($base));
$path = '/' . ltrim($path, '/');
$method = $_SERVER['REQUEST_METHOD'];

try {
    if ($path === '/health') json_response(['status'=>'ok']);
    $db = pdo($config);
    ensure_schema($db);
    if ($path === '/db-health') { $row=$db->query('SELECT 1 ok')->fetch(); json_response(['status'=>($row && (int)$row['ok']===1) ? 'ok':'db_error']); }

    if ($method === 'POST' && $path === '/auth/register') {
        $p=read_json(); $nick=normalize_nick($p['minecraft_nick'] ?? ''); $password=(string)($p['password'] ?? ''); if(strlen($password)<6) json_response(['detail'=>'Пароль должен быть не короче 6 символов.'],400);
        $email=isset($p['email']) && $p['email']!=='' ? trim((string)$p['email']) : null; $hash=password_make($password);
        $db->beginTransaction();
        $st=$db->prepare('SELECT * FROM users WHERE minecraft_nick=? FOR UPDATE'); $st->execute([$nick]); $u=$st->fetch();
        if($u && $u['password_hash']) { $db->rollBack(); json_response(['detail'=>'Этот ник уже зарегистрирован.'],409); }
        if($u){ $st=$db->prepare('UPDATE users SET password_hash=?, email=? WHERE id=?'); $st->execute([$hash,$email,$u['id']]); $uid=(int)$u['id']; }
        else { $st=$db->prepare('INSERT INTO users (minecraft_nick,email,password_hash) VALUES (?,?,?)'); $st->execute([$nick,$email,$hash]); $uid=(int)$db->lastInsertId(); }
        $st=$db->prepare('SELECT * FROM users WHERE id=?'); $st->execute([$uid]); $u=$st->fetch(); $tokens=issue_tokens($db,$config,$uid); $db->commit(); json_response(['user'=>public_user($u)] + $tokens);
    }

    if ($method === 'POST' && $path === '/auth/login') {
        $p=read_json(); $nick=normalize_nick($p['minecraft_nick'] ?? ''); $password=(string)($p['password'] ?? '');
        $st=$db->prepare('SELECT * FROM users WHERE minecraft_nick=?'); $st->execute([$nick]); $u=$st->fetch();
        if(!$u || !password_ok($u['password_hash'] ?? null, $password)) json_response(['detail'=>'Неверный ник или пароль.'],401);
        $tokens=issue_tokens($db,$config,(int)$u['id']); json_response(['user'=>public_user($u)] + $tokens);
    }

    if ($method === 'POST' && $path === '/auth/link') {
        $p=read_json(); $nick=normalize_nick($p['minecraft_nick'] ?? ''); $password=(string)($p['password'] ?? ''); if(strlen($password)<6) json_response(['detail'=>'Пароль должен быть не короче 6 символов.'],400);
        $digest=token_hash(trim((string)($p['code'] ?? '')), $config['server_secret']); $email=isset($p['email']) && $p['email']!=='' ? trim((string)$p['email']) : null;
        $db->beginTransaction();
        $st=$db->prepare('SELECT * FROM site_link_codes WHERE minecraft_nick=? AND code_hash=? AND used_at IS NULL AND expires_at > NOW() ORDER BY id DESC LIMIT 1'); $st->execute([$nick,$digest]); $code=$st->fetch();
        if(!$code){ $db->rollBack(); json_response(['detail'=>'Код привязки неверный или истёк.'],400); }
        $st=$db->prepare('SELECT * FROM users WHERE minecraft_nick=? FOR UPDATE'); $st->execute([$nick]); $u=$st->fetch();
        $hash=password_make($password);
        if($u){ $st=$db->prepare('UPDATE users SET password_hash=?, email=COALESCE(?, email), is_site_linked=1 WHERE id=?'); $st->execute([$hash,$email,$u['id']]); $uid=(int)$u['id']; }
        else { $st=$db->prepare('INSERT INTO users (minecraft_nick,email,password_hash,is_site_linked) VALUES (?,?,?,1)'); $st->execute([$nick,$email,$hash]); $uid=(int)$db->lastInsertId(); }
        $st=$db->prepare('UPDATE site_link_codes SET used_at=NOW() WHERE id=?'); $st->execute([$code['id']]);
        $st=$db->prepare('SELECT * FROM users WHERE id=?'); $st->execute([$uid]); $u=$st->fetch(); $tokens=issue_tokens($db,$config,$uid); $db->commit(); json_response(['user'=>public_user($u)] + $tokens);
    }

    if ($method === 'GET' && $path === '/auth/me') json_response(['user'=>public_user(auth_user($db,$config))]);
    if ($method === 'GET' && $path === '/auth/inventory') { $u=auth_user($db,$config); $st=$db->prepare('SELECT * FROM player_inventory_snapshots WHERE minecraft_nick=?'); $st->execute([$u['minecraft_nick']]); $r=$st->fetch(); if(!$r) json_response(['synced'=>false,'minecraft_nick'=>$u['minecraft_nick'],'inventory'=>[],'equipment'=>new stdClass(),'ender_chest'=>[]]); json_response(['synced'=>true,'minecraft_nick'=>$u['minecraft_nick'],'inventory'=>json_decode($r['inventory_json'],true) ?: [],'equipment'=>json_decode($r['equipment_json'] ?: '{}',true) ?: new stdClass(),'ender_chest'=>json_decode($r['ender_chest_json'] ?: '[]',true) ?: [],'updated_at'=>$r['updated_at']]); }
    if ($method === 'POST' && $path === '/auth/skin') { $u=auth_user($db,$config); $p=read_json(); $model=strtolower(trim((string)($p['skin_model'] ?? 'classic'))); if(!in_array($model,['classic','slim'],true)) json_response(['detail'=>'Модель скина должна быть classic или slim.'],400); $skin=(string)($p['skin_data_url'] ?? ''); if(!horde_starts_with($skin,'data:image/png;base64,')) json_response(['detail'=>'Загрузите PNG-скин Minecraft.'],400); $st=$db->prepare('UPDATE users SET skin_model=?, skin_data_url=?, skin_updated_at=NOW() WHERE id=?'); $st->execute([$model,$skin,$u['id']]); $st=$db->prepare('SELECT * FROM users WHERE id=?'); $st->execute([$u['id']]); json_response(['user'=>public_user($st->fetch())]); }

    if ($method === 'POST' && $path === '/server/link-code') { $secret=$_SERVER['HTTP_X_HORDE_SERVER_SECRET'] ?? ''; if(!hash_equals($config['server_secret'],$secret)) json_response(['detail'=>'Серверный доступ запрещён.'],403); $p=read_json(); $nick=normalize_nick($p['minecraft_nick'] ?? ''); $code=code_short(); $st=$db->prepare('INSERT INTO site_link_codes (minecraft_nick, code_hash, expires_at) VALUES (?,?,DATE_ADD(NOW(), INTERVAL 10 MINUTE))'); $st->execute([$nick,token_hash($code,$config['server_secret'])]); if(!empty($p['minecraft_uuid'])){ $st=$db->prepare('INSERT INTO users (minecraft_nick,minecraft_uuid,is_site_linked) VALUES (?,?,0) ON DUPLICATE KEY UPDATE minecraft_uuid=COALESCE(minecraft_uuid, VALUES(minecraft_uuid))'); $st->execute([$nick,$p['minecraft_uuid']]); } json_response(['minecraft_nick'=>$nick,'code'=>$code,'expires_in_seconds'=>600]); }
    if ($method === 'POST' && $path === '/server/inventory') { $secret=$_SERVER['HTTP_X_HORDE_SERVER_SECRET'] ?? ''; if(!hash_equals($config['server_secret'],$secret)) json_response(['detail'=>'Серверный доступ запрещён.'],403); $p=read_json(); $nick=normalize_nick($p['minecraft_nick'] ?? ''); $st=$db->prepare('INSERT INTO player_inventory_snapshots (minecraft_nick,minecraft_uuid,inventory_json,equipment_json,ender_chest_json) VALUES (?,?,?,?,?) ON DUPLICATE KEY UPDATE minecraft_uuid=VALUES(minecraft_uuid), inventory_json=VALUES(inventory_json), equipment_json=VALUES(equipment_json), ender_chest_json=VALUES(ender_chest_json), updated_at=CURRENT_TIMESTAMP'); $st->execute([$nick,$p['minecraft_uuid'] ?? null,json_encode($p['inventory'] ?? [],JSON_UNESCAPED_UNICODE),json_encode($p['equipment'] ?? new stdClass(),JSON_UNESCAPED_UNICODE),json_encode($p['ender_chest'] ?? [],JSON_UNESCAPED_UNICODE)]); json_response(['ok'=>true,'minecraft_nick'=>$nick]); }

    if ($method === 'GET' && preg_match('#^/donate/subscription/([A-Za-z0-9_]{3,32})$#', $path, $m)) { $nick=normalize_nick($m[1]); $st=$db->prepare('SELECT tier, expires_at FROM donate_subscriptions WHERE minecraft_nick=? AND active=1 AND expires_at > NOW() ORDER BY expires_at DESC LIMIT 1'); $st->execute([$nick]); $r=$st->fetch(); if(!$r) json_response(['active'=>false,'minecraft_nick'=>$nick]); json_response(['active'=>true,'minecraft_nick'=>$nick,'tier'=>$r['tier'],'expires_at'=>$r['expires_at']]); }

    if ($method === 'POST' && $path === '/auth/password-reset/request') json_response(['ok'=>true,'message'=>'Если почта совпала с аккаунтом, код восстановления будет отправлен.']);
    if ($method === 'POST' && $path === '/auth/password-reset/confirm') json_response(['detail'=>'Восстановление пароля на PHP API будет подключено после настройки почтового SMTP.'],501);
    json_response(['detail'=>'Маршрут не найден.'],404);
} catch (Throwable $e) {
    json_response(['detail'=>'Ошибка кабинета. Сообщи администрации.'],500);
}
