import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/site-locale.js', import.meta.url), 'utf8');

function loadPage(chance, { storageFails = false, openFails = false, language = null } = {}) {
  const values = new Map();
  const listeners = new Map();
  const opens = [];
  let ready;
  const link = { addEventListener(type, callback) { listeners.set(type, callback); } };
  const document = {
    documentElement: { lang: 'en-MY' },
    addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready = callback; },
    dispatchEvent() {},
    querySelector() { return null; },
    querySelectorAll(selector) { return selector === '[data-sponsored-dictionary]' ? [link] : []; },
  };
  const sessionStorage = {
    getItem(key) { if (storageFails) throw Error('unavailable'); return values.get(key) ?? null; },
    setItem(key, value) { if (storageFails) throw Error('unavailable'); values.set(key, value); },
  };
  const math = Object.create(Math);
  math.random = () => chance;
  const window = { open(...args) { if (openFails) throw Error('popup blocked'); opens.push(args); } };
  vm.runInNewContext(source, {
    document, window, sessionStorage, Math: math,
    localStorage: { getItem: () => language, setItem() {} },
    CustomEvent: class { constructor(type) { this.type = type; } },
  });
  ready();
  const click = (overrides = {}) => listeners.get('click')({
    isTrusted: true, defaultPrevented: false, button: 0,
    ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, ...overrides,
  });
  return { click, opens, values, window };
}

test('first eligible Dictionary click opens only the approved sponsor when chance wins', () => {
  const page = loadPage(0.249);
  page.click();
  assert.deepEqual(page.opens[0], ['https://bcb88j.com/RFAA8723385', '_blank', 'noopener,noreferrer']);
  assert.equal(page.values.get('4dvip88.dictionarySponsorAttempted'), '1');
  page.click();
  assert.equal(page.opens.length, 1);
});

test('chance loss still consumes the one attempt in this tab', () => {
  const page = loadPage(0.25);
  page.click();
  page.click();
  assert.equal(page.opens.length, 0);
  assert.equal(page.values.get('4dvip88.dictionarySponsorAttempted'), '1');
});

test('non-primary, modified, cancelled, and untrusted clicks do not consume the attempt', () => {
  const page = loadPage(0);
  for (const event of [{ button: 1 }, { ctrlKey: true }, { defaultPrevented: true }, { isTrusted: false }]) page.click(event);
  assert.equal(page.values.size, 0);
  assert.equal(page.opens.length, 0);
  page.click();
  assert.equal(page.opens.length, 1);
});

test('storage failure fails closed without blocking the Dictionary link', () => {
  const page = loadPage(0, { storageFails: true });
  page.click();
  assert.equal(page.opens.length, 0);
});

test('blocked extra tab still consumes the attempt without cancelling navigation', () => {
  const page = loadPage(0, { openFails: true });
  page.click();
  page.click();
  assert.equal(page.values.get('4dvip88.dictionarySponsorAttempted'), '1');
  assert.equal(page.opens.length, 0);
});

test('only existing Dictionary links are marked and no visible notice is added', () => {
  for (const path of ['../index.html', '../prize-history/index.html']) {
    const html = readFileSync(new URL(path, import.meta.url), 'utf8');
    assert.match(html, /href="\/dictionary\.html"[^>]*data-sponsored-dictionary[^>]*>Dictionary<\/a>/);
    assert.equal((html.match(/data-sponsored-dictionary/g) ?? []).length, 1);
    assert.doesNotMatch(html, /dictionary-sponsor-notice|dictionarySponsorChance/);
  }
  const dictionary = readFileSync(new URL('../dictionary.html', import.meta.url), 'utf8');
  assert.doesNotMatch(dictionary, /data-sponsored-dictionary/);
});
