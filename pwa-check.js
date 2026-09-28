'use strict';
// Static check that the Doclets PWA pieces are present and consistent.
//
// DEV-ONLY diagnostic (same spirit as smoke-check.js): no browser, no
// network, no dependencies. It reads manifest.json, sw.js, index.html and
// deploy.sh and cross-checks them, so a rename or a forgotten file shows up
// here instead of as a silently non-installable site.
//
//   node pwa-check.js [root]      # root defaults to the script's directory
//
// Exit status is 0 when everything checks out, 1 otherwise.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(process.argv[2] || __dirname);
const problems = [];
const said = new Set();

function read(rel) {
  try {
    return fs.readFileSync(path.join(ROOT, rel), 'utf8');
  } catch (err) {
    problems.push(`missing file: ${rel}`);
    return null;
  }
}

function check(ok, message) {
  if (!ok && !said.has(message)) {
    said.add(message);
    problems.push(message);
  }
  return ok;
}

const exists = (rel) => fs.existsSync(path.join(ROOT, rel));

// Pixel size out of a PNG's IHDR chunk; null if it is not a PNG at all.
function pngSize(rel) {
  const buf = fs.readFileSync(path.join(ROOT, rel));
  if (buf.length < 24 || buf.toString('latin1', 1, 4) !== 'PNG') return null;
  return `${buf.readUInt32BE(16)}x${buf.readUInt32BE(20)}`;
}

// --- sw.js ------------------------------------------------------------
const sw = read('sw.js');
let runtimeHosts = [];
if (sw !== null) {
  try {
    new vm.Script(sw, { filename: 'sw.js' }); // parse only, never run
  } catch (err) {
    problems.push(`sw.js does not parse: ${err.message}`);
  }

  const version = /const VERSION = ['"]([^'"]+)['"]/.exec(sw);
  check(version !== null, 'sw.js has no VERSION constant');
  if (version) console.log(`  service worker cache version: ${version[1]}`);

  const hosts = (/const RUNTIME_HOSTS = \[([^\]]*)\]/.exec(sw) || [])[1] || '';
  runtimeHosts = (hosts.match(/['"]([^'"]+)['"]/g) || []).map((s) => s.slice(1, -1));

  const shell = (/const SHELL = \[([\s\S]*?)\]/.exec(sw) || [])[1] || '';
  const entries = (shell.match(/['"]([^'"]+)['"]/g) || []).map((s) => s.slice(1, -1));
  check(entries.length > 0, 'sw.js precaches nothing (SHELL is empty)');
  for (const entry of entries) {
    if (entry === './') continue; // the directory itself, not a file
    check(exists(entry), `sw.js precaches ${entry}, which is not in the repo`);
  }
}

// --- manifest.json ----------------------------------------------------
const manifestSrc = read('manifest.json');
let manifest = null;
if (manifestSrc !== null) {
  try {
    manifest = JSON.parse(manifestSrc);
  } catch (err) {
    problems.push(`manifest.json is not valid JSON: ${err.message}`);
  }
}

if (manifest) {
  for (const field of ['name', 'short_name', 'start_url', 'display']) {
    check(manifest[field] !== undefined, `manifest.json has no "${field}"`);
  }
  check(
    ['standalone', 'fullscreen', 'minimal-ui'].includes(manifest.display),
    `manifest display "${manifest.display}" is not an app-like mode`
  );

  const icons = Array.isArray(manifest.icons) ? manifest.icons : [];
  check(icons.length > 0, 'manifest.json lists no icons');
  const has = (purpose, size) =>
    icons.some(
      (icon) =>
        String(icon.purpose || 'any').split(/\s+/).includes(purpose) && icon.sizes === size
    );
  check(has('any', '192x192'), 'manifest has no 192x192 "any" icon');
  check(has('any', '512x512'), 'manifest has no 512x512 "any" icon');
  check(has('maskable', '512x512'), 'manifest has no 512x512 "maskable" icon');

  for (const icon of icons) {
    if (!check(exists(icon.src), `manifest icon not found: ${icon.src}`)) continue;
    const size = pngSize(icon.src);
    if (!check(size !== null, `manifest icon is not a PNG: ${icon.src}`)) continue;
    check(
      size === icon.sizes,
      `${icon.src} is ${size} but the manifest says ${icon.sizes}`
    );
  }
}

// --- index.html -------------------------------------------------------
const index = read('index.html');
if (index !== null) {
  const link = index.match(/<link[^>]+rel=["']manifest["'][^>]*>/i);
  if (check(link !== null, 'index.html has no <link rel="manifest">')) {
    const href = (link[0].match(/href=["']([^"']+)["']/) || [])[1];
    check(href && exists(href), `index.html links a manifest that is not in the repo: ${href}`);
  }

  check(
    /<meta[^>]+name=["']theme-color["'][^>]*>/i.test(index),
    'index.html has no <meta name="theme-color">'
  );
  check(
    /<link[^>]+rel=["']apple-touch-icon["'][^>]*>/i.test(index),
    'index.html has no <link rel="apple-touch-icon"> (iOS installs need one)'
  );

  const register = index.match(/serviceWorker\.register\(\s*['"]([^'"]+)['"]/);
  if (check(register !== null, 'index.html never registers a service worker')) {
    check(
      exists(register[1]),
      `index.html registers "${register[1]}", which is not in the repo`
    );
  }

  // Every third-party script index.html loads must be one sw.js caches, or
  // an offline load is missing it.
  for (const tag of index.match(/<script[^>]+src=["'][^"']+["'][^>]*>/gi) || []) {
    const url = (tag.match(/src=["']([^"']+)["']/) || [])[1] || '';
    if (!/^https?:\/\//i.test(url)) continue;
    const host = new URL(url).hostname;
    check(
      runtimeHosts.includes(host),
      `index.html loads ${host}, which sw.js does not cache (RUNTIME_HOSTS)`
    );
  }
}

// --- deploy.sh --------------------------------------------------------
const deploy = read('deploy.sh');
if (deploy !== null) {
  const client = (/CLIENT_FILES=\(([^)]*)\)/.exec(deploy) || [])[1] || '';
  const shipped = [
    'manifest.json',
    'sw.js',
    'apple-touch-icon.png',
    ...(manifest && manifest.icons ? manifest.icons.map((icon) => icon.src) : []),
  ];
  for (const file of shipped) {
    check(client.includes(file), `deploy.sh does not ship ${file}`);
  }
}

// --- report -----------------------------------------------------------
if (problems.length === 0) {
  console.log('PWA check: OK');
  process.exit(0);
}
console.log(`PWA check: ${problems.length} problem(s)`);
for (const problem of problems) console.log(`  - ${problem}`);
process.exit(1);
