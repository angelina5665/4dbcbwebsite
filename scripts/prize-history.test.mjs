import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {filterHistory} from '../assets/prize-history.mjs';

const data = JSON.parse(fs.readFileSync(new URL('../assets/prize-history-data.json', import.meta.url), 'utf8'));

test('the retained archive has three operators, two dated draws, and no inferred Jackpot records', () => {
  assert.equal(data.records.length, 138);
  assert.deepEqual(new Set(data.records.map(r => r.date)), new Set(['2026-09-05', '2026-09-06']));
  assert.deepEqual(new Set(data.records.map(r => r.operator)), new Set(['magnum', 'toto', 'damacai']));
  assert.equal(data.jackpotVerified, false);
  assert.ok(data.records.every(r => /^\d{4}$/.test(r.number) && r.tier !== 'jackpot'));
  assert.ok(data.operators.every(o => o.logo.startsWith('/logos/')));
});

test('exact four-digit search preserves leading zeros and combines date and operator', () => {
  const result = filterHistory(data.records, {number:'0063',date:'2026-09-06',operator:'magnum'});
  assert.equal(result.records.length, 1);
  assert.deepEqual(result.records[0], {
    date:'2026-09-06',operator:'magnum',drawNo:'419-26',tier:'first',number:'0063',archiveUrl:'/results/2026-09-06/'
  });
  assert.equal(filterHistory(data.records, {number:'063'}).invalid, true);
  assert.equal(filterHistory(data.records, {number:'0063',operator:'toto'}).records.length, 0);
});

test('Jackpot filter never relabels ordinary first-prize records', () => {
  const result = filterHistory(data.records, {number:'0063',tier:'jackpot'});
  assert.equal(result.unsupportedJackpot, true);
  assert.deepEqual(result.records, []);
  assert.equal(filterHistory(data.records, {tier:'first'}).records.every(r => r.tier === 'first'), true);
});
