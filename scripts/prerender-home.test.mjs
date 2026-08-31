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
  assert.equal(websiteSchema.name, "4DVIP88");
  assert.deepEqual(websiteSchema.alternateName, ["4D VIP", "4D VIP 88"]);
  assert.equal(websiteSchema.url, "https://4dvip88.com/");
  assert.ok(html.includes(`data-results-updated="${results.updated}"`));
  assert.equal(results.drawDate, latestProvider.drawDate);
  assert.equal(results.drawDay, latestProvider.drawDay);
  assert.equal(results.recentDates[0], `${results.drawDate} (${results.drawDay})`);
  assert.equal(results.providers.cashsweep.name, "Special Cash Sweep 4D");
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  assert.match(html, /<h1><a href="\/west-malaysia-4d-results\/">4D RESULT MALAYSIA<\/a><\/h1>/);
  assert.equal((rawResults.match(/class="outerbox"/g) || []).length, Object.keys(results.providers).length);
  assert.match(rawResults, /Special Cash Sweep 4D/);
  assert.doesNotMatch(rawResults, /Cashsweep 4D|Cashweep 4D/);
  for (const provider of Object.values(results.providers)) {
    for (const value of [provider.first, provider.second, provider.third].filter(Boolean)) {
      assert.ok(rawResults.includes(String(value)), `missing raw-HTML result ${value}`);
    }
  }
  assert.match(sitemap, new RegExp(`<loc>https://4dvip88\\.com/</loc>\\s*<lastmod>${results.updated.slice(0, 10)}</lastmod>`));
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

test("runtime preserves prerendered cards when the refresh request fails", async () => {
  const html = await fs.readFile(path.join(repo, "index.html"), "utf8");
  assert.match(html, /if \(first && !document\.querySelector\("#app \.outerbox"\)\) showError\(\);/);
  assert.match(html, /app\.dataset\.resultsUpdated !== snapshot/);
});
