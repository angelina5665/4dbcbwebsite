import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../assets/history');
const coverage=JSON.parse(fs.readFileSync(path.join(root,'coverage.json'),'utf8'));

test('number and year shards contain the same labelled prize records',()=>{
  const numbered=new Map();
  for(const file of fs.readdirSync(path.join(root,'by-prefix'))){
    const bucket=JSON.parse(fs.readFileSync(path.join(root,'by-prefix',file),'utf8'));
    for(const [number,rows] of Object.entries(bucket)){
      assert.match(number,/^\d{4}$/);
      assert.equal(number.slice(0,2),file.slice(0,2));
      for(const [date,operator,drawNo,tier] of rows){
        assert.match(date,/^\d{4}-\d{2}-\d{2}$/);
        assert.ok(coverage.coverage[operator],operator);
        assert.ok(['first','second','third','special','consolation'].includes(tier));
        const id=[number,date,operator,drawNo,tier].join('|');
        numbered.set(id,(numbered.get(id)||0)+1);
      }
    }
  }
  const dated=new Map();
  for(const file of fs.readdirSync(path.join(root,'by-year'))){
    const rows=JSON.parse(fs.readFileSync(path.join(root,'by-year',file),'utf8'));
    for(const row of rows){
      assert.equal(row[1].slice(0,4),file.slice(0,4));
      const id=row.join('|');
      dated.set(id,(dated.get(id)||0)+1);
    }
  }
  assert.equal([...numbered.values()].reduce((a,b)=>a+b,0),coverage.totalPrizeRecords);
  assert.deepEqual(dated,numbered);
});

test('limited regional coverage and missing older Toto consolation data are explicit',()=>{
  assert.equal(coverage.coverage.sabah88.draws,2);
  assert.equal(coverage.coverage.sandakan.draws,2);
  assert.equal(coverage.coverage.cashsweep.draws,2);
  assert.ok(coverage.coverage.toto.missingPrizes>30000);
  assert.ok(fs.readFileSync(path.join(root,'SOURCE-LICENSE.txt'),'utf8').includes('Copyright (c) 2026 deadboy18'));
});
