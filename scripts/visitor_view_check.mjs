// Opens each site in a real browser, reads the first prize shown on every result card,
// and compares it with the live source. Exits non-zero when a visitor would see stale
// numbers, so the watchman can raise the alarm.
import { chromium } from 'playwright';

const SITES = ['https://my4d.co/', 'https://4dresult1.com/'];
const SOURCE = 'https://www.4dmoon.com/';

// card id -> [feed region, section, field]
const MAP = {
  gd4d: ['west', 'G', 'P1'],
  damacai: ['west', 'D', 'P1'],
  magnum: ['west', 'M', 'P1'],
  toto: ['west', 'T', 'P1'],
  totoextra: ['west', 'T', 'P5D1'],
  damacai13d: ['west', 'D6', 'P1'],
  singapore: ['sg', 'S', 'P1'],
  sabah88: ['east', 'B', 'P1'],
  sandakan: ['east', 'K', 'P1'],
  cashsweep: ['east', 'W', 'P1'],
};

const digits = (v) => String(v ?? '').replace(/\D/g, '');

async function sourceNumbers() {
  const get = async (f) => (await fetch(SOURCE + f + '.json', { headers: { 'User-Agent': 'Mozilla/5.0 (health-check)' } })).json();
  const feeds = { west: await get('feedwest'), east: await get('feedeast'), sg: await get('feedsg') };
  const out = {};
  for (const [card, [region, section, field]] of Object.entries(MAP)) {
    out[card] = digits(feeds[region]?.[section]?.[field]);
  }
  return out;
}

async function cardNumbers(page, url) {
  await page.goto(url + '?watchman=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60_000 });
  await page.waitForSelector('.outerbox[id^="card-"]', { timeout: 30_000 });
  await page.waitForTimeout(15_000); // give the live feed time to arrive and redraw
  return page.evaluate(() => {
    const out = {};
    document.querySelectorAll('.outerbox[id^="card-"]').forEach((card) => {
      const top = card.querySelector('.resulttop') || card.querySelector('.resultbottom');
      out[card.id.slice(5)] = top ? top.textContent.replace(/\D/g, '') : '';
    });
    return out;
  });
}

function compare(shown, expected) {
  const wrong = [];
  for (const card of Object.keys(MAP)) {
    if (!expected[card] || expected[card].length < 3) continue; // source mid-draw, nothing to compare yet
    if (!(card in shown)) wrong.push(`${card}: card missing`);
    else if (shown[card] !== expected[card]) wrong.push(`${card}: shows ${shown[card] || 'nothing'}, source has ${expected[card]}`);
  }
  return wrong;
}

const browser = await chromium.launch();
const page = await browser.newPage();
const problems = [];
try {
  for (const site of SITES) {
    let wrong = [];
    for (let attempt = 1; attempt <= 2; attempt++) {
      const expected = await sourceNumbers();
      const shown = await cardNumbers(page, site);
      wrong = compare(shown, expected);
      if (!wrong.length) break;
      if (attempt === 1) await page.waitForTimeout(75_000); // results may have just been released
    }
    if (wrong.length) problems.push(`${site} shows stale or wrong numbers -> ${wrong.join('; ')}`);
    else console.log(`${site} matches the live source on every card`);
  }
} catch (error) {
  problems.push(`Screen check could not run: ${error.message}`);
} finally {
  await browser.close();
}

if (problems.length) {
  for (const p of problems) console.log(' - ' + p);
  process.exit(1);
}
