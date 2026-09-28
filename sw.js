// Doclets service worker — makes the reader installable as a PWA and keeps
// the app shell available (and fast) without a round trip.
//
// Scope: the *shell* — index.html, the AllSpeak client, the Webson layout,
// the icons, and the two runtime libraries index.html pulls from CDNs.
// Doclet *content* is not here and cannot be: it arrives over MQTT from the
// doclet server, so the app still needs the network to show anything.
//
// Everything managed here is network-first, falling back to the cache, so a
// deployed change is picked up on the next load and only an offline load
// gets the previous copy. Requests for the app's own files are keyed
// without their query string, because the loader fetches
// `doclets.allspeak?v=` cat now — one new URL per page load would otherwise
// fill the cache with duplicates.

'use strict';

const VERSION = 'doclets-v1';
const CACHE_PREFIX = 'doclets-';

// App shell, relative to the service worker's scope (the web root).
const SHELL = [
  './',
  'index.html',
  'manifest.json',
  'doclets.json',
  'doclets.allspeak',
  'icon-192.png',
  'icon-512.png',
  'icon-maskable-512.png',
  'apple-touch-icon.png',
  'favicon.ico',
];

// Third-party runtime libraries loaded by index.html. Both are fetched
// through the browser's HTTP cache first, so this normally costs nothing.
const RUNTIME_HOSTS = ['allspeak.ai', 'cdn.jsdelivr.net'];

// Never touched: the MQTT credentials endpoint. A stale credential file
// breaks the connection, and it is a secret.
const PRIVATE_PATH = /\/credentials\.php$/;

const SCOPE = new URL(self.registration.scope);

function shellURL(path) {
  return new URL(path, SCOPE).href;
}

// Cache key: the URL without its query string or fragment.
function cacheKey(request) {
  const url = new URL(request.url);
  url.search = '';
  url.hash = '';
  return url.href;
}

const SHELL_PATHS = new Set(
  SHELL.map((path) => new URL(path, SCOPE).pathname).concat(SCOPE.pathname)
);

// Opaque (cross-origin, no-cors) responses have status 0 and are still fine
// to replay. Anything that failed, or is a partial response, is not.
function isCacheable(response) {
  return Boolean(response) && (response.ok || response.type === 'opaque');
}

async function store(cache, request, response) {
  try {
    await cache.put(cacheKey(request), response);
  } catch (err) {
    // e.g. a response with `Vary: *`. Losing a cache entry is not fatal.
  }
}

async function networkFirst(request, cache) {
  try {
    const response = await fetch(request);
    if (isCacheable(response)) await store(cache, request, response.clone());
    return response;
  } catch (err) {
    const cached = await cache.match(cacheKey(request));
    if (cached) return cached;
    if (request.mode === 'navigate') {
      const shell = await cache.match(shellURL('index.html'));
      if (shell) return shell;
    }
    throw err;
  }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(VERSION);
      // One at a time: cache.addAll would abandon the whole precache if a
      // single file were missing, and anything skipped here is cached by
      // networkFirst on first use anyway.
      await Promise.all(
        SHELL.map(async (path) => {
          const url = shellURL(path);
          try {
            const response = await fetch(url, { cache: 'reload' });
            if (isCacheable(response)) await cache.put(url, response);
          } catch (err) {
            // Offline during install — carry on.
          }
        })
      );
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key.startsWith(CACHE_PREFIX) && key !== VERSION)
          .map((key) => caches.delete(key))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  let url;
  try {
    url = new URL(request.url);
  } catch (err) {
    return;
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  if (PRIVATE_PATH.test(url.pathname)) return;

  // Only the known shell paths — which include the scope root, so opening
  // the app is covered. Intercepting *every* navigation would cache whatever
  // a same-origin URL returned, and `/token` and `/key` are rewrite rules
  // onto secrets.php.
  const isShell =
    url.origin === SCOPE.origin && SHELL_PATHS.has(url.pathname);
  if (!isShell && !RUNTIME_HOSTS.includes(url.hostname)) return;

  event.respondWith(caches.open(VERSION).then((cache) => networkFirst(request, cache)));
});

// Lets a page (or pwa-check) ask which copy is live.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'version' && event.ports[0]) {
    event.ports[0].postMessage({ version: VERSION });
  }
});
