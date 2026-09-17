const DATA_URL = '/assets/prize-history-data.json';
const PAGE_SIZE = 36;
const tierKeys = {first:'historyFirst',second:'historySecond',third:'historyThird',special:'historySpecial',consolation:'historyConsolation'};
const t = (key, vars) => window.SiteLocale?.t(key, vars) || key;

export function filterHistory(records, {number='',date='all',operator='all',tier='all'} = {}) {
  const query = String(number).trim();
  if (query && !/^\d{4}$/.test(query)) return {invalid:true,records:[]};
  if (tier === 'jackpot') return {unsupportedJackpot:true,records:[]};
  return {records:records.filter(item => (!query || item.number === query) && (date === 'all' || item.date === date) && (operator === 'all' || item.operator === operator) && (tier === 'all' || item.tier === tier))};
}

function el(tag,className,text) { const node=document.createElement(tag); if(className) node.className=className; if(text!==undefined) node.textContent=text; return node; }
function validData(data) {
  return data && data.schemaVersion === 1 && data.jackpotVerified === false && Array.isArray(data.operators) && Array.isArray(data.records)
    && data.operators.length === 3 && data.records.every(r => /^\d{4}$/.test(r.number) && /^2026-09-0[56]$/.test(r.date) && tierKeys[r.tier] && data.operators.some(o=>o.key===r.operator));
}
function start() {
  const form=document.getElementById('history-search'); if(!form) return;
  const number=document.getElementById('history-number'),date=document.getElementById('history-date'),operator=document.getElementById('history-operator'),tier=document.getElementById('history-tier');
  const results=document.getElementById('history-results'),status=document.getElementById('history-status'),more=document.getElementById('history-more');
  let data=null,matches=[],shown=0;
  function card(record) {
    const company=data.operators.find(item=>item.key===record.operator);
    const article=el('article','history-card');
    const head=el('header'); const logo=el('img','operator-logo'); logo.src=company.logo; logo.alt=`${company.name} logo`; logo.width=60; logo.height=42; head.append(logo,el('h3','',company.name));
    const body=el('div','history-body'); body.append(el('strong','history-number',record.number),el('span','history-tier',t(tierKeys[record.tier])));
    body.append(el('p','history-meta',`${t('historyDraw')}: ${record.date} · ${t('historyDrawNo')}: ${record.drawNo}`));
    const archive=el('a','',t('historyArchive')); archive.href=record.archiveUrl; body.append(archive); article.append(head,body); return article;
  }
  function showNext() {
    const fragment=document.createDocumentFragment(); const end=Math.min(matches.length,shown+PAGE_SIZE);
    for(let i=shown;i<end;i++) fragment.append(card(matches[i])); results.append(fragment); shown=end; more.hidden=shown>=matches.length;
    status.textContent=t('historyCount',{shown:shown.toLocaleString(),total:matches.length.toLocaleString()});
  }
  function search() {
    if(!data) return; results.replaceChildren(); more.hidden=true; shown=0;
    const result=filterHistory(data.records,{number:number.value,date:date.value,operator:operator.value,tier:tier.value});
    if(result.invalid){status.textContent=t('historyInvalid');return;}
    if(result.unsupportedJackpot){status.textContent=t('historyJackpotNotice');return;}
    matches=result.records;
    if(!matches.length){status.textContent=t('historyNoMatch');return;}
    showNext();
  }
  form.addEventListener('submit',e=>{e.preventDefault();search();});
  form.addEventListener('reset',e=>{e.preventDefault();number.value='';date.value='all';operator.value='all';tier.value='all';search();});
  [date,operator,tier].forEach(input=>input.addEventListener('change',search));
  more.addEventListener('click',showNext);
  document.addEventListener('site-language-change',()=>{if(data) search(); else status.textContent=t('historyLoading');});
  fetch(DATA_URL,{credentials:'same-origin'}).then(r=>{if(!r.ok) throw new Error('History unavailable');return r.json();}).then(payload=>{
    if(!validData(payload)) throw new Error('Invalid history data'); data=payload; search();
  }).catch(()=>{status.textContent=t('historyLoadError');});
}
if(typeof document!=='undefined') start();
