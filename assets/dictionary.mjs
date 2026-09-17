const DATA_URL = '/dictionary-data.json';
const PAGE_SIZE = 36;
const DREAM_IMAGE_BASE = 'https://prddmccms1.blob.core.windows.net/number-dictionary/';
const ZODIAC_IMAGES = Object.freeze({rat:'/media/1469/rat.png',ox:'/media/1471/ox.png',tiger:'/media/1472/tiger.png',rabbit:'/media/1473/rabbit.png',dragon:'/media/1474/dragon.png',snake:'/media/1475/snake.png',horse:'/media/1476/horse.png',goat:'/media/1477/goat.png',monkey:'/media/1478/monkey.png',rooster:'/media/1479/rooster.png',dog:'/media/1027/dog.png',boar:'/media/1085/pig.png'});

export function normalize(value) {
  return String(value ?? '').normalize('NFKC').toLocaleLowerCase('en').trim();
}

export function imageUrlFor(entry) {
  if (!entry || !/^\d{3,4}$/.test(entry.number)) return null;
  if (entry.category === 'Dream Numbers') return `${DREAM_IMAGE_BASE}${entry.number}.jpg`;
  if (entry.category === 'Zodiac Numbers') {
    const path = ZODIAC_IMAGES[normalize(entry.english)];
    return path ? `https://www.damacai.com.my${path}` : null;
  }
  return null;
}

export function searchEntries(entries, rawQuery, category = 'all', length = 'all') {
  const query = normalize(rawQuery);
  const numeric = /^\d{1,4}$/.test(query);
  const completeCode = numeric && query.length >= 3;
  return entries.map((entry, index) => {
    if (category !== 'all' && entry.category !== category) return null;
    if (length !== 'all' && entry.number.length !== Number(length)) return null;
    let score = 1;
    if (query && numeric) score = completeCode ? (entry.number === query ? 100 : 0) : (entry.number.startsWith(query) ? 50 : 0);
    else if (query) {
      const names = [normalize(entry.english), normalize(entry.chinese)];
      const subnames = [normalize(entry.subcategory_en), normalize(entry.subcategory_zh)];
      score = names.some(name => name === query) ? 100 : names.some(name => name.startsWith(query)) ? 80 : names.some(name => name.includes(query)) ? 60 : subnames.some(name => name.includes(query)) ? 30 : 0;
    }
    return score ? {entry, index, score} : null;
  }).filter(Boolean).sort((a,b) => b.score-a.score || a.index-b.index).map(item => item.entry);
}

function sourceLabel(value) {
  const key = ({'bilingual feed':'bilingual',both:'bothPages',en:'englishPage',zh:'chinesePage'})[value] || 'sourceEntry';
  return window.SiteLocale?.t(key) || key;
}
function t(key, vars) { return window.SiteLocale?.t(key, vars) || key; }

function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && ['www.damacai.com.my','damacai.com.my'].includes(url.hostname) ? url.href : null;
  } catch { return null; }
}

function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function card(entry) {
  const article = element('article','entry');
  const head = element('div','entry-head');
  const categoryKey = {'Dream Numbers':'dictDream','Zodiac Numbers':'dictZodiac','Festive Numbers':'dictFestive'}[entry.category];
  head.append(element('strong','entry-code',entry.number),element('span','entry-meta',`${t(categoryKey)} · ${entry.number.length}D`));
  const picture = element('div','entry-picture');
  const imageUrl = imageUrlFor(entry);
  if (imageUrl) {
    const img = element('img');
    img.src = imageUrl;
    img.alt = `Da Ma Cai — ${entry.english}`;
    img.loading = 'lazy';
    img.decoding = 'async';
    img.referrerPolicy = 'no-referrer';
    img.width = 290;
    img.height = 288;
    const fallback = element('span','no-picture',t('imageUnavailable'));
    fallback.hidden = true;
    img.addEventListener('error',() => { img.hidden = true; fallback.hidden = false; },{once:true});
    picture.append(img,fallback);
  } else picture.append(element('span','no-picture',t('noImage')));
  const body = element('div','entry-body');
  body.append(element('h3','',entry.english));
  const chinese = element('p','entry-zh',entry.chinese);
  chinese.lang = 'zh-Hans';
  body.append(chinese);
  if (entry.category !== 'Dream Numbers') body.append(element('p','entry-sub',`${entry.subcategory_en} · ${entry.subcategory_zh}`));
  const source = element('div','entry-source');
  const sourceUrl = safeSourceUrl(entry.source_url);
  if (sourceUrl) {
    const link = element('a','', t('sourceLink'));
    link.href = sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    source.append(link);
  }
  source.append(element('span','',sourceLabel(entry.source_language)));
  body.append(source);
  article.append(head,picture,body);
  return article;
}

function validEntry(entry) {
  return entry && typeof entry.number === 'string' && /^\d{3,4}$/.test(entry.number) && ['Dream Numbers','Zodiac Numbers','Festive Numbers'].includes(entry.category)
    && ['english','chinese','subcategory_en','subcategory_zh','source_url'].every(key => typeof entry[key] === 'string');
}

function start() {
  const form = document.getElementById('dictionary-search');
  if (!form) return;
  const query = document.getElementById('dictionary-query');
  const category = document.getElementById('dictionary-category');
  const length = document.getElementById('dictionary-length');
  const status = document.getElementById('dictionary-status');
  const results = document.getElementById('dictionary-results');
  const more = document.getElementById('dictionary-more');
  let entries = [], matches = [], shown = 0, debounce;

  function showNext() {
    const fragment = document.createDocumentFragment();
    const end = Math.min(shown + PAGE_SIZE, matches.length);
    for (let i = shown; i < end; i += 1) fragment.append(card(matches[i]));
    results.append(fragment);
    shown = end;
    more.hidden = shown >= matches.length;
    status.textContent = t('showing',{shown:shown.toLocaleString(),total:matches.length.toLocaleString()});
  }
  function search() {
    clearTimeout(debounce);
    results.replaceChildren();
    more.hidden = true;
    shown = 0;
    if (!entries.length) return;
    matches = searchEntries(entries, query.value, category.value, length.value);
    if (!matches.length) {
      status.textContent = t('noMatches');
      results.append(element('p','empty',t('noResults')));
      return;
    }
    showNext();
  }
  form.addEventListener('submit',event => { event.preventDefault(); search(); });
  form.addEventListener('reset',event => { event.preventDefault(); query.value=''; category.value='all'; length.value='all'; search(); query.focus(); });
  query.addEventListener('input',() => { clearTimeout(debounce); debounce=setTimeout(search,140); });
  category.addEventListener('change',search);
  length.addEventListener('change',search);
  more.addEventListener('click',showNext);
  document.addEventListener('site-language-change', () => { if (entries.length) search(); else status.textContent = t('loading'); });
  fetch(DATA_URL,{credentials:'same-origin'}).then(response => {
    if (!response.ok) throw new Error('Dataset unavailable');
    return response.json();
  }).then(payload => {
    if (!Array.isArray(payload) || payload.length !== 11824 || !payload.every(validEntry)) throw new Error('Unexpected dataset');
    entries = payload;
    search();
  }).catch(() => { status.textContent = t('loadError'); });
}

if (typeof document !== 'undefined') start();
