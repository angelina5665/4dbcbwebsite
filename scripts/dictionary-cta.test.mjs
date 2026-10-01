import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../assets/site-locale.js', import.meta.url), 'utf8');

function loadCta(chance) {
  let ready;
  let handler;
  const redirects = [];
  const cta = { addEventListener(type, callback) { if (type === 'click') handler = callback; } };
  const document = {
    documentElement: { lang: 'en-MY' },
    addEventListener(type, callback) { if (type === 'DOMContentLoaded') ready = callback; },
    dispatchEvent() {},
    querySelector() { return null; },
    querySelectorAll(selector) { return selector === '[data-dictionary-cta]' ? [cta] : []; },
  };
  const math = Object.create(Math);
  math.random = () => chance;
  vm.runInNewContext(source, {
    document,
    window: { location: { assign(url) { redirects.push(url); } }, open() {} },
    sessionStorage: { getItem() { return null; }, setItem() {} },
    localStorage: { getItem() { return null; }, setItem() {} },
    Math: math,
    CustomEvent: class { constructor(type) { this.type = type; } },
  });
  ready();
  const click = (overrides = {}) => {
    let prevented = false;
    handler({
      isTrusted: true, defaultPrevented: false, button: 0,
      ctrlKey: false, metaKey: false, shiftKey: false, altKey: false,
      preventDefault() { prevented = true; }, ...overrides,
    });
    return prevented;
  };
  return { click, redirects };
}

test('Dictionary CTA redirects to the disclosed sponsor below the 60% threshold', () => {
  const page = loadCta(0.599999);
  assert.equal(page.click(), true);
  assert.deepEqual(page.redirects, ['https://bcb88j.com/RFAA8723385']);
});

test('Dictionary CTA follows its normal dictionary href at and above the threshold', () => {
  const page = loadCta(0.60);
  assert.equal(page.click(), false);
  assert.deepEqual(page.redirects, []);
});

test('modified and untrusted Dictionary CTA clicks are never redirected', () => {
  const page = loadCta(0);
  for (const event of [{ ctrlKey: true }, { button: 1 }, { isTrusted: false }, { defaultPrevented: true }]) {
    assert.equal(page.click(event), false);
  }
  assert.deepEqual(page.redirects, []);
});

test('homepage CTA has a dictionary fallback and visible sponsor disclosure', () => {
  const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  assert.match(html, /href="\/dictionary\.html"[^>]*data-dictionary-cta/);
  assert.match(html, /id="dictionary-cta-note"[^>]*data-i18n="dictionaryCtaNotice"/);
});
