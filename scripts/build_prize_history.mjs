import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const retained = path.join(root, '.github', 'seo-prerender', 'retained-results');
const manifest = JSON.parse(fs.readFileSync(path.join(retained, 'manifest.json'), 'utf8'));
const operators = [
  { key:'magnum', name:'Magnum 4D', logo:'/logos/magnum.png', official:'https://www.magnum4d.my/results/winning-history' },
  { key:'toto', name:'Sports Toto 4D', logo:'/logos/toto.png', official:'https://www.sportstoto.com.my/results_past.asp' },
  { key:'damacai', name:'Da Ma Cai 4D', logo:'/logos/damacai.png', official:'https://www.damacai.com.my/draw-winning-history' }
];
const days = ['2026-09-05', '2026-09-06'];
const tiers = [['first','first'],['second','second'],['third','third'],['special','special'],['consolation','consolation']];
const records = [];
for (const day of [...days].reverse()) {
  const data = JSON.parse(fs.readFileSync(path.join(retained, `${day}.json`), 'utf8'));
  if (data.drawDate !== day.slice(8,10)+'-'+day.slice(5,7)+'-'+day.slice(0,4)) throw new Error(`Draw date mismatch: ${day}`);
  const manifestEntry = manifest.archives[day];
  if (!manifestEntry || !manifestEntry.historicalSourceComparison.includes('All nine displayed provider objects matched')) throw new Error(`Unreviewed archive: ${day}`);
  for (const operator of operators) {
    const provider = data.providers[operator.key];
    if (!provider || provider.drawDate !== data.drawDate) throw new Error(`Provider date mismatch: ${day}/${operator.key}`);
    for (const [field,tier] of tiers) {
      const values = Array.isArray(provider[field]) ? provider[field] : [provider[field]];
      for (const number of values) {
        if (!/^\d{4}$/.test(number || '')) continue;
        records.push({date:day,operator:operator.key,drawNo:provider.drawNo,tier,number,archiveUrl:`/results/${day}/`});
      }
    }
  }
}
const output = {schemaVersion:1,coverageStart:days[0],coverageEnd:days.at(-1),sourceName:'4d4d.co',sourceCheckedOn:'2026-09-08',permission:'Site-owner-reported approval to republish result information; no public licence text provided.',jackpotVerified:false,operators,records};
const destination = path.join(root, 'assets', 'prize-history-data.json');
const content = JSON.stringify(output, null, 2)+'\n';
if (process.argv.includes('--check')) {
  if (!fs.existsSync(destination) || fs.readFileSync(destination,'utf8').replace(/\r\n/g,'\n') !== content) throw new Error('Prize history data is stale');
  console.log(`Prize history check passed: ${records.length} standard-tier records`);
} else {
  fs.writeFileSync(destination,content);
  console.log(`Built ${records.length} standard-tier records for ${days.join(' and ')}`);
}
