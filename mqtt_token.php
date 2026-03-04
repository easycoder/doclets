<?php

declare(strict_types=1);

/*
 * MQTT token utility
 *
 * Purpose:
 * - Encrypt and store token outside web root (above index.html)
 * - Decrypt token for server-side use
 *
 * Usage (CLI):
 *   export MQTT_TOKEN_KEY='your-strong-secret-passphrase'
 *
 *   php mqtt_token.php encrypt 'YOUR_MQTT_TOKEN'
 *   php mqtt_token.php decrypt
 *
 * Optional env overrides:
 *   MQTT_TOKEN_FILE=/custom/path/mqtt.token.enc
 *
 * Notes:
 * - This protects token at rest.
 * - Do not expose decrypted token to browser clients.
 */

const CIPHER = 'aes-256-gcm';

function tokenFilePath(): string
{
    $custom = getenv('MQTT_TOKEN_FILE');
    if ($custom !== false && trim($custom) !== '') {
        return $custom;
    }

    // File sits one level above this project ("above index.html")
    return dirname(__DIR__) . '/mqtt.token.enc';
}

function keyFromEnv(): string
{
    $key = getenv('MQTT_TOKEN_KEY');
    if ($key === false || trim($key) === '') {
        fwrite(STDERR, "Error: MQTT_TOKEN_KEY is not set.\n");
        exit(1);
    }

    // Normalize key size to 32 bytes for AES-256 using SHA-256 digest
    return hash('sha256', $key, true);
}

function encryptToken(string $plainToken, string $path): void
{
    $key = keyFromEnv();
    $iv = random_bytes(12); // recommended length for GCM
    $tag = '';

    $ciphertext = openssl_encrypt(
        $plainToken,
        CIPHER,
        $key,
        OPENSSL_RAW_DATA,
        $iv,
        $tag
    );

    if ($ciphertext === false) {
        fwrite(STDERR, "Error: encryption failed.\n");
        exit(1);
    }

    $payload = [
        'v' => 1,
        'c' => CIPHER,
        'iv' => base64_encode($iv),
        'tag' => base64_encode($tag),
        'ct' => base64_encode($ciphertext),
    ];

    $dir = dirname($path);
    if (!is_dir($dir) && !mkdir($dir, 0700, true) && !is_dir($dir)) {
        fwrite(STDERR, "Error: cannot create directory: {$dir}\n");
        exit(1);
    }

    $json = json_encode($payload, JSON_UNESCAPED_SLASHES);
    if ($json === false) {
        fwrite(STDERR, "Error: cannot encode payload.\n");
        exit(1);
    }

    if (file_put_contents($path, $json . PHP_EOL, LOCK_EX) === false) {
        fwrite(STDERR, "Error: cannot write token file: {$path}\n");
        exit(1);
    }

    @chmod($path, 0600);
    fwrite(STDOUT, "Encrypted token saved to: {$path}\n");
}

function decryptToken(string $path): string
{
    if (!is_file($path)) {
        fwrite(STDERR, "Error: token file not found: {$path}\n");
        exit(1);
    }

    $json = file_get_contents($path);
    if ($json === false) {
        fwrite(STDERR, "Error: cannot read token file: {$path}\n");
        exit(1);
    }

    $payload = json_decode($json, true);
    if (!is_array($payload)) {
        fwrite(STDERR, "Error: invalid token file format.\n");
        exit(1);
    }

    foreach (['iv', 'tag', 'ct'] as $field) {
        if (!isset($payload[$field]) || !is_string($payload[$field])) {
            fwrite(STDERR, "Error: missing field '{$field}' in token file.\n");
            exit(1);
        }
    }

    $iv = base64_decode($payload['iv'], true);
    $tag = base64_decode($payload['tag'], true);
    $ciphertext = base64_decode($payload['ct'], true);

    if ($iv === false || $tag === false || $ciphertext === false) {
        fwrite(STDERR, "Error: invalid base64 in token file.\n");
        exit(1);
    }

    $key = keyFromEnv();

    $plain = openssl_decrypt(
        $ciphertext,
        CIPHER,
        $key,
        OPENSSL_RAW_DATA,
        $iv,
        $tag
    );

    if ($plain === false) {
        fwrite(STDERR, "Error: decryption failed (wrong key or corrupted file).\n");
        exit(1);
    }

    return $plain;
}

function usage(): void
{
    $script = basename(__FILE__);
    $path = tokenFilePath();

    $message = <<<TXT
Usage:
  export MQTT_TOKEN_KEY='your-secret-passphrase'

  php {$script} encrypt 'YOUR_MQTT_TOKEN'
  php {$script} decrypt

Optional:
  export MQTT_TOKEN_FILE='{$path}'
TXT;

    fwrite(STDOUT, $message . PHP_EOL);
}

if (PHP_SAPI !== 'cli') {
    http_response_code(403);
    header('Content-Type: text/plain; charset=utf-8');
    echo "CLI only.";
    exit;
}

$argv = $_SERVER['argv'] ?? [];
$argc = $_SERVER['argc'] ?? 0;

if ($argc < 2) {
    usage();
    exit(1);
}

$command = strtolower((string)$argv[1]);
$path = tokenFilePath();

switch ($command) {
    case 'encrypt':
        if ($argc < 3) {
            fwrite(STDERR, "Error: token value required for encrypt.\n");
            usage();
            exit(1);
        }
        $token = (string)$argv[2];
        encryptToken($token, $path);
        break;

    case 'decrypt':
        $token = decryptToken($path);
        fwrite(STDOUT, $token . PHP_EOL);
        break;

    default:
        fwrite(STDERR, "Error: unknown command '{$command}'.\n");
        usage();
        exit(1);
}
