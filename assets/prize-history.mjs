const INDEX_BASE = '/assets/history';
const PAGE_SIZE = 36;
const tierKeys = {first:'historyFirst',second:'historySecond',third:'historyThird',special:'historySpecial',consolation:'historyConsolation'};
const t = (key, vars) => window.SiteLocale?.t(key, vars) || key;
const operators = {
  magnum:{name:'Magnum 4D',logo:'/logos/magnum.png'}, toto:{name:'Sports Toto 4D',logo:'/logos/toto.png'},
  damacai:{name:'Da Ma Cai 4D',logo:'/logos/damacai.png'}, sabah88:{name:'Sabah 88 4D',logo:'/logos/sabah88.png'},
  sandakan:{name:'Sandakan STC 4D',logo:'/logos/stc.png'}, cashsweep:{name:'Sarawak Cash Sweep 4D',logo:'/logos/cashsweep.png'}
};

export function filterHistory(records, {number='',date='all',operator='all',tier='all'} = {}, otherProviderReferences = []) {
  const query = String(number).trim();
  if (query && !/^\d{4}$/.test(query)) return {invalid:true,records:[]};
  if (tier === 'jackpot') return {unsupportedJackpot:true,records:[]};
  const matched = records.filter(item => (!query || item.number === query) && (date === 'all' || item.date === date) && (operator === 'all' || item.operator === operator) && (tier === 'all' || item.tier === tier));
  const references = matched.length || !query || operator !== 'all' ? [] : otherProviderReferences.filter(item => item.number === query && (date === 'all' || item.date === date) && (tier === 'all' || item.tier === tier));
  return {records:matched,references};
}
export function filterHistoricalRecords(records, {number='',date='',operator='all',tier='all'} = {}) {
  const query=String(number).trim();
  if (query && !/^\d{4}$/.test(query)) return {invalid:true,records:[]};
  if (tier==='jackpot') return {unsupportedJackpot:true,records:[]};
  return {records:records.filter(item=>(!query||item.number===query)&&(!date||item.date===date)&&(operator==='all'||item.operator===operator)&&(tier==='all'||item.tier===tier))};
}

function el(tag,className,text) { const node=document.createElement(tag); if(className) node.className=className; if(text!==undefined) node.textContent=text; return node; }
function unpack(tuple,coverage) {
  const [number,date,operator,drawNo,tier]=tuple;
  const archiveUrl=['2026-09-05','2026-09-06'].includes(date) ? `/results/${date}/` : null;
  return {number,date,operator,drawNo:/^\d+$/.test(drawNo)?`${drawNo}/${date.slice(2,4)}`:drawNo,tier,archiveUrl,sourceUrl:coverage[operator]?.sourceUrl};
}
function start() {
  const form=document.getElementById('history-search'); if(!form) return;
  const number=document.getElementById('history-number'),date=document.getElementById('history-date'),operator=document.getElementById('history-operator'),tier=document.getElementById('history-tier');
  const results=document.getElementById('history-results'),status=document.getElementById('history-status'),more=document.getElementById('history-more');
  let coverage=null,matches=[],shown=0,recent=false,request=0;
  const cache=new Map();
  async function load(url){if(!cache.has(url)) cache.set(url,fetch(url,{credentials:'same-origin'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}));return cache.get(url);}
  function card(record) {
    const company=operators[record.operator];
    const article=el('article','history-card');
    const head=el('header'); const logo=el('img','operator-logo'); logo.src=company.logo; logo.alt=`${company.name} logo`; logo.width=60; logo.height=42; head.append(logo,el('h3','',company.name));
    const body=el('div','history-body'); body.append(el('strong','history-number',record.number),el('span','history-tier',t(tierKeys[record.tier])));
    body.append(el('p','history-meta',`${t('historyDraw')}: ${record.date} · ${t('historyDrawNo')}: ${record.drawNo}`));
    const source=el('a','',t(record.archiveUrl?'historyArchive':'historyDataset')); source.href=record.archiveUrl||record.sourceUrl; source.rel='noopener noreferrer'; if(!record.archiveUrl)source.target='_blank'; body.append(source);
    article.append(head,body); return article;
  }
  function showNext() {
    const fragment=document.createDocumentFragment(); const end=Math.min(matches.length,shown+PAGE_SIZE);
    for(let i=shown;i<end;i++) fragment.append(card(matches[i])); results.append(fragment); shown=end; more.hidden=shown>=matches.length;
    status.textContent=t(recent?'historyRecentCount':'historyCount',{shown:shown.toLocaleString(),total:matches.length.toLocaleString()});
  }
  async function search() {
    const current=++request;
    results.replaceChildren(); more.hidden=true; shown=0;
    const criteria={number:number.value,date:date.value,operator:operator.value,tier:tier.value};
    const preliminary=filterHistoricalRecords([],criteria);
    if(preliminary.invalid){status.textContent=t('historyInvalid');return;}
    if(preliminary.unsupportedJackpot){status.textContent=t('historyJackpotNotice');return;}
    if(!coverage){status.textContent=t('historyLoading');return;}
    status.textContent=t('historyLoading');
    try {
      let tuples;
      recent=!criteria.number&&!criteria.date;
      if(criteria.number){const bucket=await load(`${INDEX_BASE}/by-prefix/${criteria.number.slice(0,2)}.json`);tuples=(bucket[criteria.number]||[]).map(([day,key,drawNo,prizeTier])=>[criteria.number,day,key,drawNo,prizeTier]);}
      else {const year=criteria.date.slice(0,4)||coverage.latestYear;tuples=await load(`${INDEX_BASE}/by-year/${year}.json`);}
      if(current!==request)return;
      const normalized=tuples.map(item=>unpack(item,coverage.operators));
      matches=filterHistoricalRecords(normalized,criteria).records;
      if(!matches.length){status.textContent=t('historyNoMatch');return;}
      showNext();
    } catch (_) {if(current===request)status.textContent=t('historyLoadError');}
  }
  form.addEventListener('submit',e=>{e.preventDefault();search();});
  form.addEventListener('reset',e=>{e.preventDefault();number.value='';date.value='';operator.value='all';tier.value='all';search();});
  [date,operator,tier].forEach(input=>input.addEventListener('change',search));
  more.addEventListener('click',showNext);
  document.addEventListener('site-language-change',()=>{if(coverage)search();else status.textContent=t('historyLoading');});
  load(`${INDEX_BASE}/coverage.json`).then(payload=>{
    if(payload.schemaVersion!==1||!payload.coverage||!payload.pinnedRevision)throw new Error('Invalid coverage');
    const keys=Object.keys(payload.coverage);
    if(keys.some(key=>!operators[key]))throw new Error('Unmapped operator');
    coverage={...payload,operators:payload.coverage,latestYear:Math.max(...keys.map(key=>Number(payload.coverage[key].end.slice(0,4)))).toString()};
    search();
  }).catch(()=>{status.textContent=t('historyLoadError');});
}
if(typeof document!=='undefined') start();
