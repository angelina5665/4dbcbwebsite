import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/guide-referral.js', import.meta.url), 'utf8');
const links = [
  'https://bcb88j.com/RFAA8723385',
  'https://2bvbx.com/RFMY4D.BVBX',
  'https://v12luck.com/RFMY4D.V12',
  'https://3x44my.com/RFMY4D.X44',
  'https://ttbet.fun/RFAA9570A03'
];

function loadPage(randomValues) {
  let ready;
  let handler;
  const redirects = [];
  const button = { addEventListener(type, callback) { if (type === 'click') handler = callback; } };
  const notice = { textContent: '' };
  const document = {
    readyState: 'loading', documentElement: { lang: 'en-MY' },
    addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready = callback; },
    querySelectorAll(selector) { return selector === '[data-guide-referral]' ? [button] : selector === '[data-guide-referral-notice]' ? [notice] : []; }
  };
  const math = Object.create(Math);
  const queue = [...randomValues];
  math.random = () => queue.shift();
  vm.runInNewContext(source, { document, window: { location: { assign(url) { redirects.push(url); } } }, Math: math });
  ready();
  const click = overrides => {
    let prevented = false;
    handler({ isTrusted: true, defaultPrevented: false, button: 0, ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, preventDefault() { prevented = true; }, ...overrides });
    return prevented;
  };
  return { click, redirects, notice };
}

test('eligible clicks redirect on values below the 50% threshold', () => {
  const page = loadPage([0.499999, 0]);
  assert.equal(page.click(), true);
  assert.deepEqual(page.redirects, [links[0]]);
});

test('eligible clicks follow MY4D normally at and above the threshold', () => {
  const page = loadPage([0.50]);
  assert.equal(page.click(), false);
  assert.deepEqual(page.redirects, []);
});

test('a triggered click selects exactly one sponsor from the full approved list', () => {
  for (let index = 0; index < links.length; index += 1) {
    const page = loadPage([0, (index + 0.1) / links.length]);
    page.click();
    assert.deepEqual(page.redirects, [links[index]]);
  }
});

test('every eligible click gets a fresh independent chance', () => {
  const page = loadPage([0.7, 0.1, 0.99]);
  assert.equal(page.click(), false);
  assert.equal(page.click(), true);
  assert.deepEqual(page.redirects, [links[4]]);
});

test('modified, cancelled, middle, and untrusted clicks never redirect', () => {
  const page = loadPage([0, 0]);
  for (const event of [{ ctrlKey: true }, { defaultPrevented: true }, { button: 1 }, { isTrusted: false }]) assert.equal(page.click(event), false);
  assert.deepEqual(page.redirects, []);
});

test('both page surfaces disclose and mark the 50% referral behavior', () => {
  for (const path of ['../index.html', '../play-guide/index.html']) {
    const html = readFileSync(new URL(path, import.meta.url), 'utf8');
    assert.equal((html.match(/data-guide-referral(?=\s|>)/g) ?? []).length, 2);
    assert.match(html, /data-guide-referral-notice/);
    assert.match(html, /guide-referral\.js\?v=20261003r1/);
  }
});
