import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');

test('homepage contains four disclosed banner slides and excludes TTBET', () => {
  const slides = html.match(/<a class="ts-slide"[^>]+>/g) || [];
  assert.equal(slides.length, 4);
  assert.ok(slides.some((slide) => /bcb88j\.com\/RFAA8723385/.test(slide)));
  assert.doesNotMatch(html, /ttbet|RFAA9570A03/i);
  assert.ok(slides.every((slide) => slide.includes('rel="noopener sponsored"')));
});

test('carousel can start with every banner and produces all 24 intact permutations', () => {
  const script = html.match(/<script>\s*(\(function\(\)\{\s*var box = document\.getElementById\("topslider"\);[\s\S]*?\}\)\(\);)\s*<\/script>/)[1];
  const permutations = new Set();
  for (let a = 0; a < 4; a++) for (let b = 0; b < 3; b++) for (let c = 0; c < 2; c++) {
    const originals = ['bcb', 'bvbx', 'v12', 'x44'].map(brand => ({brand, image: brand + '.jpg', href: brand + '-referral'}));
    const track = {children: [...originals], style: {}, addEventListener() {}, appendChild(slide) {
      this.children.splice(this.children.indexOf(slide), 1);
      this.children.push(slide);
    }};
    const dots = {children: [], appendChild(button) { this.children.push(button); }};
    const control = {addEventListener() {}};
    const box = {querySelector(selector) { return selector === '.ts-track' ? track : selector === '.ts-dots' ? dots : control; }, addEventListener() {}};
    const randoms = [(a + 0.5) / 4, (b + 0.5) / 3, (c + 0.5) / 2];
    const math = Object.create(Math);
    math.random = () => randoms.shift();
    vm.runInNewContext(script, {Math: math, document: {getElementById: () => box, createElement: () => ({setAttribute() {}, addEventListener() {}, classList: {toggle() {}}})}, clearInterval() {}, setInterval() { return 1; }});
    assert.equal(new Set(track.children).size, 4);
    assert.ok(track.children.every(slide => originals.includes(slide)));
    assert.equal(dots.children.length, 4);
    assert.equal(track.style.transform, 'translateX(-0%)');
    permutations.add(track.children.map(slide => slide.brand).join(','));
  }
  assert.equal(permutations.size, 24);
  assert.deepEqual([...new Set([...permutations].map(order => order.split(',')[0]))].sort(), ['bcb', 'bvbx', 'v12', 'x44']);
});

test('TTBET banner assets are absent', () => {
  for (const filename of ['ttbet-wide.jpg', 'ttbet-mobile.jpg']) {
    assert.equal(fs.existsSync(path.join(root, filename)), false, `${filename} should not remain in MY4D`);
  }
});
