import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const sitemap = readFileSync(new URL('../sitemap.xml', import.meta.url), 'utf8');

function localPath(url) {
  const pathname = new URL(url).pathname;
  if (pathname === '/') return '../index.html';
  if (pathname.endsWith('/')) return `..${pathname}index.html`;
  return `..${pathname}`;
}

test('every sitemap page loads the shared theme assets', () => {
  const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(match => match[1]);
  assert.equal(urls.length, 23);
  for (const url of urls) {
    const html = readFileSync(new URL(localPath(url), import.meta.url), 'utf8');
    assert.match(html, /href="\/assets\/theme\.css\?v=20261001"/);
    assert.match(html, /src="\/assets\/theme\.js\?v=20261001"/);
  }
});

test('theme defaults to system and offers system, light, and dark choices', () => {
  const js = readFileSync(new URL('../assets/theme.js', import.meta.url), 'utf8');
  assert.match(js, /return VALID\.has\(value\) \? value : 'auto'/);
  for (const value of ['auto', 'light', 'dark']) assert.match(js, new RegExp(`value="${value}"`));
  assert.match(js, /prefers-color-scheme: dark/);
});
