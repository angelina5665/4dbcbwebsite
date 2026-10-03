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
  assert.equal(urls.length, 24);
  for (const url of urls) {
    const html = readFileSync(new URL(localPath(url), import.meta.url), 'utf8');
    assert.match(html, /href="\/assets\/theme\.css\?v=20261003"/);
    assert.match(html, /src="\/assets\/theme\.js\?v=20261003"/);
  }
});

test('theme defaults to system and offers system, light, and dark choices', () => {
  const js = readFileSync(new URL('../assets/theme.js', import.meta.url), 'utf8');
  assert.match(js, /return VALID\.has\(value\) \? value : 'auto'/);
  for (const value of ['auto', 'light', 'dark']) assert.match(js, new RegExp(`value="${value}"`));
  assert.match(js, /prefers-color-scheme: dark/);
});

test('theme loads the site-wide language system', () => {
  const js = readFileSync(new URL('../assets/theme.js', import.meta.url), 'utf8');
  const locale = readFileSync(new URL('../assets/site-locale.js', import.meta.url), 'utf8');
  const pages = readFileSync(new URL('../assets/site-pages-locale.js', import.meta.url), 'utf8');
  assert.match(js, /site-locale\.js\?v=20261003/);
  assert.match(locale, /site-pages-locale\.js\?v=20261003/);
  for (const language of ['English', 'Bahasa Melayu', '中文']) assert.match(locale, new RegExp(language));
  for (const path of ['about.html', 'privacy.html', 'disclaimer.html', 'methodology.html', 'affiliate-disclosure.html']) assert.match(pages, new RegExp(path.replace('.', '\\.')));
});
