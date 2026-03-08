<?php
declare(strict_types=1);

$name = $_GET['name'] ?? trim($_SERVER['PATH_INFO'] ?? '', '/');
if (!in_array($name, ['token', 'key'], true)) {
    http_response_code(404);
    exit('Not found');
}

$path = dirname(__DIR__) . '/' . $name; // one level above web root
if (!is_readable($path)) {
    http_response_code(404);
    exit('Not found');
}

header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');
readfile($path);