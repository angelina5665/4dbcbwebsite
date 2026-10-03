import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// The homepage gets draw-night numbers from the live feed in the browser, because the
// scheduled results robot can run hours late. These tests protect that path.

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

function extractFunction(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `${name}() not found in index.html`);
  let depth = 0;
  for (let i = source.indexOf('{', start); i < source.length; i++) {
    if (source[i] === '{') depth++;
    if (source[i] === '}' && --depth === 0) return source.slice(start, i + 1);
  }
  throw new Error(`could not find the end of ${name}()`);
}

test('homepage still polls the live results relay', () => {
  assert.match(html, /const LIVEFEED_URL = "https:\/\/livefeed\.angelina-bcb88\.workers\.dev\/"/);
  assert.match(extractFunction(html, 'pollLiveFeed'), /render\(/);
});

test('live feed covers every result card', () => {
  const apply = extractFunction(html, 'applyLiveFeed');
  for (const key of ['magnum', 'damacai', 'gd4d', 'toto', 'sandakan', 'sabah88', 'cashsweep', 'singapore']) {
    assert.match(html, new RegExp(`"${key}"`), `FEED_MAP lost ${key}`);
  }
  assert.match(apply, /providers\.totoextra/);
  assert.match(apply, /providers\.damacai13d/);
});

test('cards redraw when live-feed numbers change without a new results.json timestamp', () => {
  // Regression: 3 Oct 2026 the cards kept last draw's numbers all evening because the
  // redraw only happened when results.json's `updated` stamp changed.
  let draws = 0;
  const app = { dataset: {}, innerHTML: '', querySelector: () => (draws ? {} : null) };
  const context = {
    __data: null,
    document: { getElementById: (id) => (id === 'app' ? app : { textContent: '', innerHTML: '' }) },
    resultsHTML: () => { draws++; return '<div class="outerbox"></div>'; },
    homeLanguage: () => 'en',
    homeUI: (k) => k,
    renderChips() {}, renderCountdown() {}, runCheck() {},
    esc: (s) => String(s),
  };
  vm.createContext(context);
  vm.runInContext(extractFunction(html, 'render'), context);

  const data = {
    updated: '2026-10-03 14:45 MYT', drawDate: '30-09-2026', drawDay: 'Wed', recentDates: [],
    providers: { magnum: { first: '6859', drawDate: '30-09-2026' } },
  };
  context.render(data);
  assert.equal(draws, 1, 'first render should draw the cards');

  context.render(data);
  assert.equal(draws, 1, 'unchanged data should not redraw');

  data.providers.magnum = { first: '5313', drawDate: '03-10-2026' };
  context.render(data);
  assert.equal(draws, 2, 'new live numbers with the same timestamp must redraw the cards');
});
