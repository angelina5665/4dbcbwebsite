import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const generator = path.join(repo, "scripts", "prerender-home.mjs");

function runGenerator(target, ...args) {
  return spawnSync(process.execPath, [generator, "--repo", target, ...args], { encoding: "utf8" });
}

function hash(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}

function drawTime(value) {
  assert.match(value, /^\d{2}-\d{2}-\d{4}$/);
  const [day, month, year] = value.split("-").map(Number);
  return Date.UTC(year, month - 1, day);
}

function stripGenerated(html) {
  return html
    .replace(/(data-results-updated=")[^"]*(")/, "$1__GENERATED_SNAPSHOT__$2")
    .replace(
      /(<!-- PRERENDERED_RESULTS_START -->)[\s\S]*?(<!-- PRERENDERED_RESULTS_END -->)/,
      "$1__GENERATED_RESULTS__$2"
    );
}

function generatedRegion(html) {
  const match = html.match(/<!-- PRERENDERED_RESULTS_START -->([\s\S]*?)<!-- PRERENDERED_RESULTS_END -->/);
  assert.ok(match, "generated result markers are missing");
  return match[1];
}

async function makeFixture(t) {
  const target = await fs.mkdtemp(path.join(os.tmpdir(), "4dvip88-prerender-"));
  t.after(() => fs.rm(target, { recursive: true, force: true }));
  for (const name of ["index.html", "results.json", "sitemap.xml"]) {
    await fs.copyFile(path.join(repo, name), path.join(target, name));
  }
  return target;
}

test("checked-in prerender is synchronized and exposes the result facts", async () => {
  const check = runGenerator(repo, "--check");
  assert.equal(check.status, 0, check.stderr || check.stdout);

  const [html, resultsText, sitemap] = await Promise.all([
    fs.readFile(path.join(repo, "index.html"), "utf8"),
    fs.readFile(path.join(repo, "results.json"), "utf8"),
    fs.readFile(path.join(repo, "sitemap.xml"), "utf8"),
  ]);
  const results = JSON.parse(resultsText);
  const rawResults = generatedRegion(html);
  const websiteSchemaMatch = html.match(/<script type="application\/ld\+json">\s*({[^<]+})\s*<\/script>/);
  assert.ok(websiteSchemaMatch, "homepage WebSite schema is missing");
  const websiteSchema = JSON.parse(websiteSchemaMatch[1]);
  const latestProvider = Object.values(results.providers)
    .reduce((latest, provider) => drawTime(provider.drawDate) > drawTime(latest.drawDate) ? provider : latest);
  assert.match(html, /<title>Malaysia 4D Results \| 4DVIP88<\/title>/);
  assert.match(html, /<meta name="description" content="[^"]*4DVIP88[^"]*">/);
  assert.match(html, /<meta property="og:site_name" content="4DVIP88">/);
  assert.match(html, /<link rel="alternate" hreflang="en-MY" href="https:\/\/4dvip88\.com\/">/);
  assert.match(html, /<link rel="alternate" hreflang="ms-MY" href="https:\/\/4dvip88\.com\/ms\/">/);
  assert.match(html, /<link rel="alternate" hreflang="x-default" href="https:\/\/4dvip88\.com\/">/);
  assert.equal((html.match(/<link rel="alternate" hreflang=/g) || []).length, 3);
  assert.equal(websiteSchema.name, "4DVIP88");
  assert.deepEqual(websiteSchema.alternateName, ["4D VIP", "4D VIP 88"]);
  assert.equal(websiteSchema.url, "https://4dvip88.com/");
  assert.ok(html.includes(`data-results-updated="${results.updated}"`));
  assert.equal(results.drawDate, latestProvider.drawDate);
  assert.equal(results.drawDay, latestProvider.drawDay);
  assert.equal(results.recentDates[0], `${results.drawDate} (${results.drawDay})`);
  assert.equal(results.providers.cashsweep.name, "Special Cash Sweep 4D");
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  assert.match(html, /<h1><a href="\/">4D RESULT MALAYSIA<\/a><\/h1>/);
  assert.equal((rawResults.match(/class="outerbox"/g) || []).length, Object.keys(results.providers).length);
  assert.match(rawResults, /Cashsweep 4D/);
  assert.doesNotMatch(rawResults, /Special Cash Sweep 4D|Cashweep 4D/);
  const providerLinks = [
    ["Damacai 4D", "/da-ma-cai-results/"],
    ["Da Ma Cai 1+3D", "/da-ma-cai-results/"],
    ["Magnum 4D", "/magnum-4d-results/"],
    ["Toto 4D", "/sports-toto-4d-results/"],
    ["SportsToto 5D, 6D, Lotto", "/sports-toto-4d-results/"],
    ["Sabah88 4D", "/sabah-88-4d-results/"],
    ["Sandakan 4D", "/sandakan-stc-4d-results/"],
    ["Cashsweep 4D", "/special-cash-sweep-results/"],
  ];
  for (const [name, href] of providerLinks) {
    const anchor = `<a class="providerlink" href="${href}">${name}</a>`;
    assert.equal(rawResults.split(anchor).length - 1, 1, `missing or duplicated provider link ${name}`);
  }
  assert.doesNotMatch(rawResults, /<a class="providerlink"[^>]*>Grand Dragon 4D<\/a>/);
  assert.doesNotMatch(rawResults, /<a class="providerlink"[^>]*>Singapore 4D<\/a>/);
  for (const provider of Object.values(results.providers)) {
    for (const value of [provider.first, provider.second, provider.third].filter(Boolean)) {
      assert.ok(rawResults.includes(String(value)), `missing raw-HTML result ${value}`);
    }
  }
  assert.match(sitemap, new RegExp(`<loc>https://4dvip88\\.com/</loc>\\s*<lastmod>${results.updated.slice(0, 10)}</lastmod>`));
});

test("homepage retains the current brand icon tags and valid icon assets", async () => {
  const html = await fs.readFile(path.join(repo, "index.html"), "utf8");
  assert.match(html, /<link rel="icon" type="image\/png" sizes="64x64" href="favicon\.png\?v=1">/);
  assert.match(html, /<link rel="apple-touch-icon" href="apple-touch-icon\.png\?v=1">/);
  for (const [name, dimension] of [["favicon.png", 64], ["apple-touch-icon.png", 180]]) {
    const icon = await fs.readFile(path.join(repo, name));
    assert.deepEqual(icon.subarray(0, 8), Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), `${name} is not a PNG`);
    assert.equal(icon.toString("ascii", 12, 16), "IHDR", `${name} is missing its PNG header`);
    assert.equal(icon.readUInt32BE(16), dimension, `${name} width changed`);
    assert.equal(icon.readUInt32BE(20), dimension, `${name} height changed`);
  }
});

test("generated category headings link to existing pages or a real in-page section", async () => {
  const html = await fs.readFile(path.join(repo, "index.html"), "utf8");
  const rawResults = generatedRegion(html);
  const sections = [
    ["4D RESULT MALAYSIA", "/"],
    ["4D RESULT SINGAPORE", "#singapore-results"],
    ["4D RESULT SABAH SARAWAK", "/east-malaysia-4d-results/"],
  ];
  for (const [title, href] of sections) {
    const anchor = `<a href="${href}">${title}</a>`;
    assert.equal(rawResults.split(anchor).length - 1, 1, `missing or duplicated section link ${title}`);
    if (href.startsWith("#")) {
      assert.equal(rawResults.split(`id="${href.slice(1)}"`).length - 1, 1, `missing section target ${href}`);
    } else {
      await fs.access(path.join(repo, href.slice(1), "index.html"));
    }
  }
  assert.doesNotMatch(rawResults, /href="\/?(?:malaysia|singapore|sarawak)-4d-result\.html"/);
});

test("raw cards retain each provider's draw date and day rather than the overall date", async (t) => {
  const target = await makeFixture(t);
  const resultsPath = path.join(target, "results.json");
  const results = JSON.parse(await fs.readFile(resultsPath, "utf8"));
  // Deliberately different from every provider date: the overall label must not
  // replace the dates attached to the individual result records.
  results.drawDate = "31-12-2099";
  results.drawDay = "Thu";
  await fs.writeFile(resultsPath, JSON.stringify(results), "utf8");
  const run = runGenerator(target);
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const rawResults = generatedRegion(await fs.readFile(path.join(target, "index.html"), "utf8"));
  const cards = new Map(
    rawResults.split('<div class="outerbox" id="card-').slice(1)
      .map((card) => [card.slice(0, card.indexOf('"')), card.split('<td class="resultdrawdate" style="text-align:right">')[0]])
  );
  for (const [key, provider] of Object.entries(results.providers)) {
    const card = cards.get(key);
    assert.ok(card, `missing raw card ${key}`);
    assert.ok(card.includes(`Date: ${provider.drawDate} (${provider.drawDay})`), `wrong provider date/day in ${key}`);
    assert.ok(!card.includes(results.drawDate), `overall draw date leaked into ${key}`);
  }
});

test("generation changes only bounded regions and is idempotent", async (t) => {
  const target = await makeFixture(t);
  const indexPath = path.join(target, "index.html");
  const sitemapPath = path.join(target, "sitemap.xml");
  const initial = await fs.readFile(indexPath, "utf8");
  const stale = initial.replace(
    /(<!-- PRERENDERED_RESULTS_START -->)[\s\S]*?(<!-- PRERENDERED_RESULTS_END -->)/,
    "$1$2"
  );
  await fs.writeFile(indexPath, stale, "utf8");

  const staleCheck = runGenerator(target, "--check");
  assert.notEqual(staleCheck.status, 0);
  const first = runGenerator(target);
  assert.equal(first.status, 0, first.stderr || first.stdout);

  const generated = await fs.readFile(indexPath, "utf8");
  assert.equal(stripGenerated(generated), stripGenerated(stale));
  const firstHashes = [hash(generated), hash(await fs.readFile(sitemapPath))];

  const second = runGenerator(target);
  assert.equal(second.status, 0, second.stderr || second.stdout);
  const secondHashes = [hash(await fs.readFile(indexPath)), hash(await fs.readFile(sitemapPath))];
  assert.deepEqual(secondHashes, firstHashes);
});

test("an incomplete provider set fails before generated files are written", async (t) => {
  const target = await makeFixture(t);
  const resultsPath = path.join(target, "results.json");
  const results = JSON.parse(await fs.readFile(resultsPath, "utf8"));
  delete results.providers.damacai;
  await fs.writeFile(resultsPath, JSON.stringify(results), "utf8");

  const guarded = ["index.html", "sitemap.xml"];
  const before = await Promise.all(guarded.map((name) => fs.readFile(path.join(target, name))));
  const run = runGenerator(target);
  assert.notEqual(run.status, 0);
  const after = await Promise.all(guarded.map((name) => fs.readFile(path.join(target, name))));
  assert.deepEqual(after.map(hash), before.map(hash));
});

for (const marker of ["/* PRERENDER_CORE_START */", "/* PRERENDER_CORE_END */"]) {
  test(`missing ${marker} fails before generated files are written`, async (t) => {
    const target = await makeFixture(t);
    const indexPath = path.join(target, "index.html");
    const source = await fs.readFile(indexPath, "utf8");
    assert.ok(source.includes(marker), `fixture has no ${marker} to remove`);
    await fs.writeFile(indexPath, source.replace(marker, ""), "utf8");
    const guarded = ["index.html", "sitemap.xml"];
    const before = await Promise.all(guarded.map((name) => fs.readFile(path.join(target, name))));
    const run = runGenerator(target);
    assert.notEqual(run.status, 0);
    assert.ok(run.stderr.includes(`Expected exactly one ${marker} marker`), run.stderr);
    const after = await Promise.all(guarded.map((name) => fs.readFile(path.join(target, name))));
    assert.deepEqual(after.map(hash), before.map(hash));
    assert.deepEqual((await fs.readdir(target)).sort(), ["index.html", "results.json", "sitemap.xml"]);
  });
}

test("runtime preserves prerendered cards when the refresh request fails", async () => {
  const html = await fs.readFile(path.join(repo, "index.html"), "utf8");
  assert.match(html, /if \(first && !document\.querySelector\("#app \.outerbox"\)\) showError\(\);/);
  assert.match(html, /app\.dataset\.resultsUpdated !== snapshot/);
});
