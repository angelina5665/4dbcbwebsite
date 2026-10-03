import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { uniquePermutationCount } from '../assets/play-guide.mjs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const hub = read('../play-guide/index.html');
const payout = read('../payout/index.html');
const bet = read('../bet/index.html');
const home = read('../index.html');
const sitemap = read('../sitemap.xml');

test('homepage and sitemap expose separate payout and bet routes', () => {
  for (const route of ['/payout/', '/bet/']) {
    assert.ok(home.includes(`href="${route}"`));
    assert.ok(sitemap.includes(`https://my4d.co${route}`));
  }
});

test('old play-guide route is a hub, not a merged guide', () => {
  assert.match(hub, /href="\/payout\/"/);
  assert.match(hub, /href="\/bet\/"/);
  assert.doesNotMatch(hub, /id="practice-form"/);
  assert.doesNotMatch(hub, /<table/);
});

test('payout page contains the exact BCB88 reference matrices', () => {
  assert.match(payout, /https:\/\/bcb88e\.com\/4d-payout/);
  const expectedRows = [
    ['3,600','5,100','8,500','840','280','18,000','120,000'],
    ['1,100','2,250','280','6,000','3,600'], ['550','1,100','280','3,600','360'],
    ['240','600','36'], ['70','24','4.80'],
    ['3,045','4,095','7,140','740.25','246.75','157,500'],
    ['1,050','2,100','246.75','5,250'], ['525','1,050','246.75','525'],
    ['210','52.50'], ['63','5.25'],
    ['3,150','4,200','7,350','756','252','105,000'],
    ['1,050','2,100','252','3,150'], ['525','1,050','252','315'],
    ['210','31.50'], ['63','4.20']
  ];
  expectedRows.flat().forEach(value => assert.ok(payout.includes(`>${value}<`), `missing ${value}`));
  assert.doesNotMatch(payout, /id="practice-form"/);
});

test('bet page is separate and remains practice-only', () => {
  assert.match(bet, /https:\/\/bcb88e\.com\/4d-how-to-bet/);
  assert.match(bet, /id="practice-form"/);
  for (const label of ['Normal','RV / Reverse','BOX','IBOX','BIG','SMALL','3A','3ABC','4A']) assert.ok(bet.includes(label));
  assert.match(bet, /sends nothing, stores nothing and cannot submit a bet/);
  assert.doesNotMatch(bet, /<table/);
});

test('permutation counts are correct for common digit patterns', () => {
  assert.equal(uniquePermutationCount('1234'), 24);
  assert.equal(uniquePermutationCount('1123'), 12);
  assert.equal(uniquePermutationCount('1122'), 6);
  assert.equal(uniquePermutationCount('1112'), 4);
  assert.equal(uniquePermutationCount('1111'), 1);
});
