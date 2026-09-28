'use strict';
// Behavioural test for sw.js, run outside a browser.
//
// DEV-ONLY (same spirit as smoke-check.js): it loads sw.js into a Node
// context with a stub Cache Storage and fetch, then drives the real
// install/activate/fetch/message events and asserts what the worker did.
// That covers the decisions a browser would otherwise be needed to observe:
// which requests are intercepted, what gets cached under which key, and what
// is served when the network is down.
//
//   node sw-test.js [sw.js]
//
// Exit status is 0 when every assertion passes, 1 otherwise.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const SRC_PATH = path.resolve(process.argv[2] || path.join(__dirname, 'sw.js'));
const ORIGIN = 'https://doclets.example';

// --- stub Response / Cache / CacheStorage -----------------------------
class StubResponse {
  constructor(body, { status = 200, type = 'basic' } = {}) {
    this.body = body;
    this.status = status;
    this.type = type;
  }
  get ok() {
    return this.status >= 200 && this.status < 300;
  }
  clone() {
    return new StubResponse(this.body, { status: this.status, type: this.type });
  }
}

class StubCache {
  constructor() {
    this.entries = new Map();
  }
  async put(key, response) {
    if (response.status === 206) throw new TypeError('cannot cache a partial response');
    this.entries.set(typeof key === 'string' ? key : key.url, response);
  }
  async match(key) {
    return this.entries.get(typeof key === 'string' ? key : key.url);
  }
  async keys() {
    return [...this.entries.keys()].map((url) => ({ url }));
  }
}

class StubCacheStorage {
  constructor() {
    this.named = new Map();
  }
  async open(name) {
    if (!this.named.has(name)) this.named.set(name, new StubCache());
    return this.named.get(name);
  }
  async keys() {
    return [...this.named.keys()];
  }
  async delete(name) {
    return this.named.delete(name);
  }
}

// --- the world sw.js sees --------------------------------------------
const FILES = {
  '/': '<!doctype html>index',
  '/index.html': '<!doctype html>index',
  '/manifest.json': '{"name":"Doclets"}',
  '/doclets.json': '{"#doc":"layout"}',
  '/doclets.allspeak': '! the client',
  '/icon-192.png': 'png',
  '/icon-512.png': 'png',
  '/icon-maskable-512.png': 'png',
  '/apple-touch-icon.png': 'png',
  '/favicon.ico': 'ico',
  '/dist/allspeak-min.js': 'the runtime',
  '/npm/mqtt/dist/mqtt.min.js': 'the mqtt client',
  '/credentials.php': '{"broker":"secret"}',
  '/token': 'the token',
  '/key': 'the key',
};

const offline = new Set();
const fetched = [];
const caches = new StubCacheStorage();
const listeners = {};
let skippedWaiting = 0;
let claimed = 0;

const self = {
  registration: { scope: `${ORIGIN}/` },
  location: new URL(`${ORIGIN}/sw.js`),
  addEventListener: (type, fn) => {
    (listeners[type] = listeners[type] || []).push(fn);
  },
  skipWaiting: async () => {
    skippedWaiting++;
  },
  clients: { claim: async () => { claimed++; } },
};

globalThis.self = self;
globalThis.caches = caches;
globalThis.fetch = async (input) => {
  const url = new URL(typeof input === 'string' ? input : input.url, `${ORIGIN}/`);
  fetched.push(url.href);
  if (offline.has(url.pathname)) throw new Error('network is down');
  const body = FILES[url.pathname];
  if (body === undefined) return new StubResponse('not found', { status: 404 });
  return new StubResponse(body);
};

vm.runInThisContext(fs.readFileSync(SRC_PATH, 'utf8'), { filename: 'sw.js' });

function fire(type, event) {
  for (const fn of listeners[type] || []) fn(event);
}

async function install() {
  let done;
  fire('install', { waitUntil: (p) => { done = p; } });
  await done;
}

async function activate() {
  let done;
  fire('activate', { waitUntil: (p) => { done = p; } });
  await done;
}

// Returns {handled:false} when sw.js passed the request through to the network.
async function request(url, { mode = 'cors' } = {}) {
  const target = url.startsWith('http') ? url : ORIGIN + url;
  let pending;
  fire('fetch', {
    request: { url: target, method: 'GET', mode },
    respondWith: (p) => { pending = p; },
  });
  if (pending === undefined) return { handled: false };
  return { handled: true, response: await pending };
}

// --- assertions -------------------------------------------------------
const results = [];
function expect(name, ok, detail = '') {
  results.push({ name, ok, detail });
}

(async () => {
  await install();
  const cache = await caches.open('doclets-v1');
  const paths = (await cache.keys()).map((r) => new URL(r.url).pathname).sort();
  expect('install precaches the whole shell',
    ['/index.html', '/doclets.allspeak', '/doclets.json', '/manifest.json',
     '/icon-192.png', '/favicon.ico', '/'].every((p) => paths.includes(p)),
    paths.join(' '));
  expect('install calls skipWaiting', skippedWaiting === 1);

  // The loader fetches `doclets.allspeak?v=` cat now — one new URL per load.
  const before = (await cache.keys()).length;
  await request('/doclets.allspeak?v=111');
  await request('/doclets.allspeak?v=222');
  await request('/doclets.json?v=333');
  const after = (await cache.keys()).length;
  expect('cache-busted ?v= loads do not grow the cache', after === before, `${before} -> ${after}`);
  expect('a ?v= load is still cached under its plain URL',
    (await cache.keys()).some((r) => r.url.endsWith('/doclets.allspeak') && r.url === `${ORIGIN}/doclets.allspeak`));

  // Offline: the shell comes back from the cache.
  offline.add('/doclets.allspeak');
  const file = await request('/doclets.allspeak?v=444');
  expect('offline shell request falls back to the cached copy',
    file.handled && file.response && file.response.body === '! the client');
  offline.add('/');
  const nav = await request('/', { mode: 'navigate' });
  expect('offline navigation falls back to the cached index',
    nav.handled && String(nav.response && nav.response.body).includes('index'));

  // Last success wins, so a redeploy is picked up.
  offline.delete('/doclets.allspeak');
  FILES['/doclets.allspeak'] = '! the client, v2';
  await request('/doclets.allspeak?v=555');
  offline.add('/doclets.allspeak');
  const refreshed = await request('/doclets.allspeak?v=556');
  expect('a successful fetch replaces the cached copy',
    refreshed.response && refreshed.response.body === '! the client, v2');

  // Runtime libraries from the CDNs index.html loads.
  const runtime = await request('https://allspeak.ai/dist/allspeak-min.js');
  const mqtt = await request('https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js');
  const urls = (await cache.keys()).map((r) => r.url);
  expect('the allspeak.ai runtime is cached', runtime.handled && urls.includes('https://allspeak.ai/dist/allspeak-min.js'));
  expect('the jsdelivr mqtt client is cached', mqtt.handled && urls.includes('https://cdn.jsdelivr.net/npm/mqtt/dist/mqtt.min.js'));

  // Secrets must never be intercepted, let alone stored.
  const creds = await request('/credentials.php?v=1');
  const token = await request('/token', { mode: 'navigate' });
  const key = await request('/key');
  const secrets = await request('/secrets.php?name=token');
  const stored = (await cache.keys()).map((r) => r.url);
  expect('credentials.php is not intercepted', creds.handled === false);
  expect('/token (a navigation) is not intercepted', token.handled === false);
  expect('/key is not intercepted', key.handled === false);
  expect('/secrets.php is not intercepted', secrets.handled === false);
  expect('no secret endpoint is cached',
    !stored.some((u) => /\/(credentials\.php|token|key|secrets\.php)/.test(u)),
    stored.filter((u) => /credential|token|key|secret/.test(u)).join(' '));

  // Everything else is left to the browser.
  expect('third-party traffic is left alone',
    (await request('https://example.org/thing.js')).handled === false);
  expect('an unrelated same-origin file is left alone',
    (await request('/editor.html')).handled === false);
  expect('a GET for a shell file is handled',
    (await request('/doclets.json')).handled === true);
  let posted;
  fire('fetch', {
    request: { url: `${ORIGIN}/doclets.json`, method: 'POST', mode: 'cors' },
    respondWith: () => { posted = true; },
  });
  expect('a POST is left alone', posted === undefined);

  // Activation cleans up only our own stale caches.
  await caches.open('doclets-v0');
  await caches.open('some-other-app');
  await activate();
  const names = await caches.keys();
  expect('activate drops stale doclets-* caches', !names.includes('doclets-v0'), names.join(' '));
  expect('activate keeps the current cache', names.includes('doclets-v1'));
  expect('activate leaves other apps\' caches alone', names.includes('some-other-app'));
  expect('activate calls clients.claim', claimed === 1);

  const port = { postMessage: (msg) => { port.message = msg; } };
  fire('message', { data: { type: 'version' }, ports: [port] });
  expect('the message handler reports a version',
    port.message && /^doclets-/.test(port.message.version), JSON.stringify(port.message));

  for (const r of results) {
    console.log(`${r.ok ? 'ok  ' : 'FAIL'}  ${r.name}${r.detail ? `   (${r.detail})` : ''}`);
  }
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
})().catch((err) => {
  console.error(`harness error: ${err && err.stack ? err.stack : err}`);
  process.exit(2);
});
