import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('homepage contains six disclosed banner slides and excludes TTBET', () => {
  const slides = html.match(/<a class="ts-slide"[^>]+>/g) || [];
  assert.equal(slides.length, 6);
  assert.ok(slides[0].includes('data-first-banner') && slides[0].includes('https://12boss.net/RFA60227383'));
  assert.equal(slides.filter(slide => slide.includes('data-first-banner')).length, 1);
  assert.match(html, /srcset="12boss-mobile-v2\.jpg"/);
  assert.match(html, /src="12boss-desktop-v2\.jpg"/);
  for (const image of ['12boss-mobile-v2.jpg', '12boss-desktop-v2.jpg']) {
    assert.ok(fs.existsSync(path.join(root, image)));
  }
  assert.ok(slides.some((slide) => slide.includes('http://laicibet.net/RFA5635588A')));
  assert.match(html, /srcset="laicibet-mobile-v2\.png"/);
  assert.match(html, /src="laicibet-wide-v2\.png"/);
  assert.ok(slides.some((slide) => /bcb88j\.com\/RFAA8723385/.test(slide)));
  assert.doesNotMatch(html, /ttbet|RFAA9570A03/i);
  assert.ok(slides.every((slide) => slide.includes('rel="noopener sponsored"')));
});

test('12BOSS stays first while the other five cover all 120 intact orders equally', () => {
  const script = html.match(/<script>\s*(\(function\(\)\{\s*var box = document\.getElementById\("topslider"\);[\s\S]*?\}\)\(\);)\s*<\/script>/)[1];
  const permutations = new Set();
  const otherBrands = ['bcb', 'bvbx', 'v12', 'x44', 'laicibet'];
  for (let a = 0; a < 5; a++) for (let b = 0; b < 4; b++) for (let c = 0; c < 3; c++) for (let d = 0; d < 2; d++) {
    const originals = [...otherBrands, '12boss'].map(brand => ({brand, image: brand + '.jpg', href: brand + '-referral', hasAttribute: name => name === 'data-first-banner' && brand === '12boss'}));
    const track = {children: [...originals], style: {}, addEventListener() {}, appendChild(slide) {
      this.children.splice(this.children.indexOf(slide), 1);
      this.children.push(slide);
    }};
    const dots = {children: [], appendChild(button) { this.children.push(button); }};
    const control = {addEventListener() {}};
    const box = {querySelector(selector) { return selector === '.ts-track' ? track : selector === '.ts-dots' ? dots : control; }, addEventListener() {}};
    const randoms = [(a + 0.5) / 5, (b + 0.5) / 4, (c + 0.5) / 3, (d + 0.5) / 2];
    const math = Object.create(Math);
    math.random = () => randoms.shift();
    vm.runInNewContext(script, {Math: math, document: {getElementById: () => box, createElement: () => ({setAttribute() {}, addEventListener() {}, classList: {toggle() {}}})}, clearInterval() {}, setInterval() { return 1; }});
    assert.equal(new Set(track.children).size, 6);
    assert.equal(track.children[0].brand, '12boss');
    assert.ok(track.children.every(slide => originals.includes(slide)));
    assert.equal(dots.children.length, 6);
    assert.equal(track.style.transform, 'translateX(-0%)');
    permutations.add(track.children.map(slide => slide.brand).join(','));
  }
  assert.equal(permutations.size, 120);
  for (const brand of otherBrands) {
    assert.equal([...permutations].filter(order => order.split(',')[1] === brand).length, 24);
  }
});

test('TTBET banner assets are absent', () => {
  for (const filename of ['ttbet-wide.jpg', 'ttbet-mobile.jpg']) {
    assert.equal(fs.existsSync(path.join(root, filename)), false, `${filename} should not remain in MY4D`);
  }
});
