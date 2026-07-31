'use strict';
// Headless smoke-test of doclets.as under the AllSpeak JS runtime.
// DEV-ONLY diagnostic tool — not part of the deployed app. The credentials in
// the prompt mock below are the localhost dev values from credentials-local /
// doclets.eclecity.net.txt (already committed in this repo).
// Loads the vendored allspeak-js sources in bundle order into a browser shim,
// then runs doclets.as for real: localhost credentials path, Webson render,
// attach, storage, prompts, and MQTT connect (stubbed - captures the URL).
// Dumps logs / alerts / the MQTT connection attempt / runtime errors.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = process.argv[2];
const HOST = process.argv[3] || 'localhost';   // 'localhost' → storage/prompt path; anything else → rest-get credentials path
const FILES = ['Core.js','Browser.js','MarkdownRenderer.js','Webson.js','JSON.js','MQTT.js','REST.js','Compare.js','Condition.js','Value.js','Run.js','Opcodes.js','Language.js','LanguagePack_en.js','Compile.js','Main.js','AllSpeak.js'];

// location is fixed before the runtime boots; it drives the hostname check
const pageURL = HOST === 'localhost' ? 'http://localhost:8080/' : 'https://' + HOST + '/';

// ---------- browser shim ----------
function makeElement(tag) {
  const el = {
    tagName: (tag || 'div').toUpperCase(),
    style: { setProperty(p, v) { this[p] = v; }, removeProperty(p) { delete this[p]; } },
    attrs: {}, children: [],
    offsetWidth: 100, offsetHeight: 100, clientWidth: 100, clientHeight: 100,
    parentElement: null,
    value: '', checked: false, disabled: false,
    innerHTML: '', textContent: '', className: '', id: '',
    scrollTop: 0, scrollHeight: 0,
    setAttribute(k, v) { this.attrs[k] = String(v); },
    removeAttribute(k) { delete this.attrs[k]; },
    getAttribute(k) { return this.attrs[k] ?? null; },
    appendChild(c) { this.children.push(c); if (c) c.parentElement = this; return c; },
    removeChild() {}, addEventListener() {}, removeEventListener() {},
    focus() {}, click() {}, blur() {},
    getBoundingClientRect() { return { left: 0, top: 0, width: 0, height: 0 }; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    closest() { return null; }, contains() { return false; },
    insertBefore() {}, replaceChild() {}, cloneNode() { return makeElement(tag); },
    getContext() { return null; }, play() {}, pause() {}, load() {},
    requestFullscreen() {}, exitFullscreen() {},
  };
  // Real DOM elements serialize to {} (props live on the prototype); mimic that
  // so JSON.parse(JSON.stringify(...)) inside the runtime doesn't see our graph.
  for (const k of Object.keys(el)) {
    Object.defineProperty(el, k, { value: el[k], writable: true, enumerable: false, configurable: true });
  }
  return el;
}

const elements = {};
const document = {
  getElementById(id) { if (!elements[id]) elements[id] = makeElement('div'); return elements[id]; },
  createElement(tag) { return makeElement(tag); },
  createTextNode(t) { return { nodeType: 3, textContent: String(t) }; },
  createDocumentFragment() { return { children: [], appendChild(c) { this.children.push(c); return c; } }; },
  body: makeElement('body'), documentElement: makeElement('html'), head: makeElement('head'),
  querySelector() { return null; }, addEventListener() {}, removeEventListener() {},
  title: '', cookie: '', readyState: 'complete',
  hidden: false, visibilityState: 'visible',
};
document.location = { hostname: HOST, href: pageURL, protocol: HOST === 'localhost' ? 'http:' : 'https:' };

const localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = String(v); }, removeItem(k) { delete this._d[k]; }, clear() { this._d = {}; } };

const prompts = [];
const promptFn = (msg) => {
  prompts.push(msg);
  const vals = ['rbrheating.duckdns.org', 'rbr', 'Ev5nt-H0r1zon', 'a8:41:f4:d3:19:dd/request'];
  return prompts.length <= vals.length ? vals[prompts.length - 1] : '';
};
const alerts = [];
const alertFn = (m) => { alerts.push(String(m)); };
const confirms = [];
const confirmFn = (m) => { confirms.push(String(m)); return true; };

const fetchMock = (url) => {
  const clean = String(url).split('?')[0].split('#')[0];
  const serve = (file) => Promise.resolve({ ok: true, status: 200, text: () => Promise.resolve(fs.readFileSync(path.join(ROOT, file), 'utf8')) });
  if (clean.endsWith('doclets.json')) return serve('doclets.json');
  if (clean.endsWith('doclets.as')) return serve('doclets.as');
  if (clean.endsWith('credentials.php')) return serve('doclets.eclecity.net.txt');
  return Promise.reject(new Error('fetch mock: no route for ' + url));
};

const mqttConnections = [];
const mqttStub = {
  connect(url, options) {
    mqttConnections.push({ url: String(url), options });
    const handlers = {};
    const client = {
      on(ev, cb) { handlers[ev] = cb; },
      end() {}, subscribe() {}, publish() {}, connected: false,
      _fire(ev, ...args) { if (handlers[ev]) handlers[ev](...args); }
    };
    // Simulate a successful broker connection shortly after connect()
    setTimeout(() => { client.connected = true; client._fire('connect'); }, 100);
    return client;
  }
};

const logs = [];
const consoleShim = {
  log: (...a) => logs.push('console.log: ' + a.join(' ')),
  warn: (...a) => logs.push('console.warn: ' + a.join(' ')),
  error: (...a) => logs.push('console.error: ' + a.join(' ')),
};

const webcrypto = (() => { try { return require('crypto').webcrypto; } catch (e) { return undefined; } })();

const window = {
  onload: null, localStorage, AllSpeak: undefined, mqtt: mqttStub,
  WebSocket: class {}, fetch: fetchMock,
  location: document.location,
  URLSearchParams: class { has() { return false; } get() { return null; } },
  addEventListener() {}, removeEventListener() {},
  alert: alertFn, prompt: promptFn, confirm: confirmFn,
  setTimeout: global.setTimeout, clearTimeout: global.clearTimeout,
  setInterval: global.setInterval, clearInterval: global.clearInterval,
  Date: global.Date, Math: global.Math,
  parseInt: global.parseInt, parseFloat: global.parseFloat, isNaN: global.isNaN,
  encodeURIComponent: global.encodeURIComponent, decodeURIComponent: global.decodeURIComponent,
  JSON: global.JSON, console: consoleShim, crypto: webcrypto,
  navigator: { userAgent: 'node-shim', language: 'en', onLine: true },
  screen: { width: 1280, height: 800 }, devicePixelRatio: 1,
  requestAnimationFrame() {}, cancelAnimationFrame() {},
  open() {}, close() {},
};

const sandbox = {
  window, document, localStorage,
  alert: alertFn, prompt: promptFn, confirm: confirmFn,
  fetch: fetchMock, mqtt: mqttStub, WebSocket: window.WebSocket,
  location: window.location,
  console: consoleShim, crypto: webcrypto,
  Date: global.Date, Math: global.Math,
  parseInt: global.parseInt, parseFloat: global.parseFloat, isNaN: global.isNaN,
  encodeURIComponent: global.encodeURIComponent, decodeURIComponent: global.decodeURIComponent,
  JSON: global.JSON, URLSearchParams: window.URLSearchParams,
  setTimeout: global.setTimeout, clearTimeout: global.clearTimeout,
  setInterval: global.setInterval, clearInterval: global.clearInterval,
  navigator: window.navigator, screen: window.screen,
  TextEncoder: global.TextEncoder, TextDecoder: global.TextDecoder,
  atob: global.atob, btoa: global.btoa,
  requestAnimationFrame() {}, cancelAnimationFrame() {},
  print: (m) => logs.push('print: ' + m),
};

const ctx = vm.createContext(sandbox);
for (const f of FILES) {
  const code = fs.readFileSync(path.join(ROOT, 'allspeak-js', f), 'utf8');
  try { vm.runInContext(code + '\n;', ctx, { filename: f }); }
  catch (e) { console.error('LOAD FAIL ' + f + ': ' + e.message); process.exit(1); }
}
const EC = vm.runInContext('AllSpeak', ctx);
EC.writeToDebugConsole = (m) => logs.push('trace: ' + m);
EC.scripts = {};
window.AllSpeak = EC;
vm.runInContext('if (!AllSpeak_Language.pack && typeof AllSpeak_LanguagePack_en !== `undefined`) AllSpeak_Language.init(AllSpeak_LanguagePack_en);', ctx);

const source = fs.readFileSync(path.join(ROOT, 'doclets.as'), 'utf8');
try { EC.start(source); } catch (e) { logs.push('EXCEPTION: ' + (e.stack || e.message)); }

// Let the event loop run (real timers) for a while, then dump.
setTimeout(() => {
  console.log('\n===== RESULT =====');
  console.log('logs: ' + logs.length);
  logs.slice(0, 60).forEach((l) => console.log('  ' + l));
  if (logs.length > 60) console.log('  ... (' + (logs.length - 60) + ' more)');
  console.log('prompts: ' + JSON.stringify(prompts));
  console.log('alerts: ' + JSON.stringify(alerts));
  console.log('confirms: ' + JSON.stringify(confirms));
  console.log('mqtt connections: ' + mqttConnections.length);
  mqttConnections.forEach((c, i) => console.log('  [' + i + '] url=' + c.url + ' clientId=' + c.options.clientId + ' user=' + c.options.username + ' pass=' + c.options.password));
  const errLines = logs.filter((l) => /error|exception|unknown|failed/i.test(l));
  console.log('potential errors: ' + (errLines.length ? '' : 'none'));
  errLines.forEach((l) => console.log('  ' + l));
  process.exit(0);
}, 5000);
