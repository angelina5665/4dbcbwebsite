import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('homepage contains five disclosed banner slides including TTBET', () => {
  const slides = html.match(/<a class="ts-slide"[^>]+>/g) || [];
  assert.equal(slides.length, 5);
  assert.match(slides[0], /bcb88j\.com\/RFAA8723385/);
  assert.match(slides[1], /ttbet\.fun\/RFAA9570A03/);
  assert.match(html, /href="https:\/\/ttbet\.fun\/RFAA9570A03"/);
  assert.match(html, /srcset="ttbet-mobile\.jpg\?v=1"/);
  assert.match(html, /src="ttbet-wide\.jpg\?v=1"/);
  assert.ok(slides.every((slide) => slide.includes('rel="noopener sponsored"')));
});

test('TTBET banner assets are present and non-empty', () => {
  for (const filename of ['ttbet-wide.jpg', 'ttbet-mobile.jpg']) {
    const stats = fs.statSync(path.join(root, filename));
    assert.ok(stats.size > 50_000, `${filename} is unexpectedly small`);
  }
});
