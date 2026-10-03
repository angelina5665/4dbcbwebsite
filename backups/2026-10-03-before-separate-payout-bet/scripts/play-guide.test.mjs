import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { uniquePermutationCount } from '../assets/play-guide.mjs';

const html = readFileSync(new URL('../play-guide/index.html', import.meta.url), 'utf8');
const home = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sitemap = readFileSync(new URL('../sitemap.xml', import.meta.url), 'utf8');

test('play guide is linked from the homepage and sitemap', () => {
  assert.match(home, /href="\/play-guide\/"/);
  assert.match(sitemap, /https:\/\/my4d\.co\/play-guide\//);
});

test('play guide exposes both requested sections and official sources', () => {
  assert.match(html, /id="payout-table"/);
  assert.match(html, /id="how-to-bet"/);
  assert.match(html, /magnum4d\.my/);
  assert.match(html, /sportstoto\.com\.my/);
  assert.match(html, /damacai\.com\.my/);
  assert.match(html, /No bet is placed/);
});

test('permutation counts are correct for common digit patterns', () => {
  assert.equal(uniquePermutationCount('1234'), 24);
  assert.equal(uniquePermutationCount('1123'), 12);
  assert.equal(uniquePermutationCount('1122'), 6);
  assert.equal(uniquePermutationCount('1112'), 4);
  assert.equal(uniquePermutationCount('1111'), 1);
});
