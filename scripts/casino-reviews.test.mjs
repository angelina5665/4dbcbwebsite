import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const page = readFileSync(new URL('../casino-reviews/index.html', import.meta.url), 'utf8');
const home = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const sitemap = readFileSync(new URL('../sitemap.xml', import.meta.url), 'utf8');

test('casino review guide is canonical, indexable, and internally linked', () => {
  assert.match(page, /<link rel="canonical" href="https:\/\/my4d\.co\/casino-reviews\/">/);
  assert.doesNotMatch(page, /noindex|nofollow/i);
  assert.match(home, /href="\/casino-reviews\/">Casino Reviews<\/a>/);
  assert.match(sitemap, /<loc>https:\/\/my4d\.co\/casino-reviews\/<\/loc>/);
});

test('BK8 and SureWin use disclosed non-affiliate destinations', () => {
  assert.match(page, /BK8 and SureWin use non-affiliate destination links/);
  assert.match(page, /href="https:\/\/www\.bk8sports\.com\/en"/);
  assert.match(page, /href="https:\/\/www\.surewinmyr\.com\/en-my\/home"/);
  assert.doesNotMatch(page, /bk8[^"\s]*RFA|surewin[^"\s]*RFA/i);
});

test('every outbound commercial link is marked sponsored', () => {
  const links = [...page.matchAll(/<a class="out"[^>]+>/g)].map(match => match[0]);
  assert.equal(links.length, 7);
  for (const link of links) assert.match(link, /rel="noopener sponsored"/);
});

test('guide avoids ratings and unsupported winning or safety claims', () => {
  assert.doesNotMatch(page, /AggregateRating|ratingValue|guaranteed winnings|safest casino|best casino/i);
  assert.match(page, /It is not a ranking/);
  assert.match(page, /Gambling involves financial risk/);
});
