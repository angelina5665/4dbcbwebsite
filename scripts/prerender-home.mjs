import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const scriptRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function parseArgs(args) {
  const options = { repo: scriptRoot, checkOnly: false };
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === "--check") {
      options.checkOnly = true;
    } else if (args[index] === "--repo") {
      index += 1;
      if (!args[index]) throw new Error("--repo requires a path");
      options.repo = path.resolve(args[index]);
    } else {
      throw new Error(`Unknown argument: ${args[index]}`);
    }
  }
  return options;
}

function requireOnce(text, marker) {
  const first = text.indexOf(marker);
  if (first < 0 || text.indexOf(marker, first + marker.length) >= 0) {
    throw new Error(`Expected exactly one ${marker} marker`);
  }
  return first;
}

function replaceBlock(text, startMarker, endMarker, value, eol) {
  const start = requireOnce(text, startMarker);
  const end = requireOnce(text, endMarker);
  if (end <= start) throw new Error(`${endMarker} must follow ${startMarker}`);
  const before = text.slice(0, start + startMarker.length);
  const after = text.slice(end);
  const normalized = value.replace(/\r?\n/g, eol);
  return `${before}${eol}${normalized}${eol}${after}`;
}

function replaceHomepageLastmod(sitemap, lastmod) {
  const pattern = /(<loc>https:\/\/4dvip88\.com\/<\/loc>\s*<lastmod>)[^<]+(<\/lastmod>)/g;
  const matches = [...sitemap.matchAll(pattern)];
  if (matches.length !== 1) {
    throw new Error(`Expected one homepage sitemap entry, found ${matches.length}`);
  }
  return sitemap.replace(pattern, (_match, prefix, suffix) => `${prefix}${lastmod}${suffix}`);
}

function replaceSnapshotAttribute(html, value) {
  const pattern = /(<main class="container" id="app" data-results-updated=")[^"]*(">)/g;
  const matches = [...html.matchAll(pattern)];
  if (matches.length !== 1) {
    throw new Error(`Expected one result snapshot attribute, found ${matches.length}`);
  }
  return html.replace(pattern, (_match, prefix, suffix) => `${prefix}${value}${suffix}`);
}

function writeIfChanged(filePath, before, after) {
  if (before === after) return false;
  const temporary = `${filePath}.tmp`;
  try {
    fs.writeFileSync(temporary, after, "utf8");
    fs.renameSync(temporary, filePath);
  } finally {
    if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
  }
  return true;
}

const options = parseArgs(process.argv.slice(2));
const indexPath = path.join(options.repo, "index.html");
const resultsPath = path.join(options.repo, "results.json");
const sitemapPath = path.join(options.repo, "sitemap.xml");

const source = fs.readFileSync(indexPath, "utf8");
const resultsText = fs.readFileSync(resultsPath, "utf8");
const sitemap = fs.readFileSync(sitemapPath, "utf8");
const data = JSON.parse(resultsText);
const eol = source.includes("\r\n") ? "\r\n" : "\n";

const coreStart = "/* PRERENDER_CORE_START */";
const coreEnd = "/* PRERENDER_CORE_END */";
const coreStartAt = requireOnce(source, coreStart) + coreStart.length;
const coreEndAt = requireOnce(source, coreEnd);
if (coreEndAt <= coreStartAt) throw new Error("Prerender core markers are out of order");

const context = vm.createContext({});
const core = source.slice(coreStartAt, coreEndAt);
vm.runInContext(
  `${core}\nthis.__resultsHTML = resultsHTML; this.__layout = LAYOUT; this.__escapeHTML = esc;`,
  context,
  { filename: "index-prerender-core.js", timeout: 1000 }
);

if (!data.providers || typeof data.providers !== "object") {
  throw new Error("results.json must contain a providers object");
}

const layoutProviders = [];
for (const section of context.__layout) {
  for (const item of section.items || []) {
    if (item.p) layoutProviders.push(item.p);
  }
}

const requiredProviders = layoutProviders.filter((provider) => provider !== "gd4d");
const providerKeys = Object.keys(data.providers);
const missing = requiredProviders.filter((provider) => !providerKeys.includes(provider));
const unexpected = providerKeys.filter((provider) => !layoutProviders.includes(provider));
if (missing.length) throw new Error(`Missing required providers: ${missing.join(", ")}`);
if (unexpected.length) throw new Error(`Providers are absent from homepage layout: ${unexpected.join(", ")}`);

const resultMarkup = context.__resultsHTML(data);
if (!resultMarkup || resultMarkup.includes("undefined")) {
  throw new Error("Generated result markup is incomplete");
}

for (const provider of providerKeys) {
  if (!resultMarkup.includes(`id="card-${provider}"`)) {
    throw new Error(`Generated markup is missing provider ${provider}`);
  }
}

const cardCount = (resultMarkup.match(/class="outerbox"/g) || []).length;
if (cardCount !== providerKeys.length) {
  throw new Error(`Expected ${providerKeys.length} result cards, generated ${cardCount}`);
}

let nextIndex = replaceBlock(
  source,
  "<!-- PRERENDERED_RESULTS_START -->",
  "<!-- PRERENDERED_RESULTS_END -->",
  resultMarkup,
  eol
);
nextIndex = replaceSnapshotAttribute(nextIndex, context.__escapeHTML(String(data.updated || "")));

const h1Count = (nextIndex.match(/<h1\b/gi) || []).length;
if (h1Count !== 1 || !nextIndex.includes("<h1><a href=\"/west-malaysia-4d-results/\">4D RESULT MALAYSIA</a></h1>")) {
  throw new Error("Expected the Malaysia section to be the single homepage H1");
}

const materialDate = String(data.updated || "").match(/^(\d{4}-\d{2}-\d{2})/);
if (!materialDate) throw new Error("results.updated must begin with YYYY-MM-DD");
const nextSitemap = replaceHomepageLastmod(sitemap, materialDate[1]);

const stale = [];
if (nextIndex !== source) stale.push("index.html");
if (nextSitemap !== sitemap) stale.push("sitemap.xml");

if (options.checkOnly) {
  if (stale.length) {
    console.error(`Generated files are stale: ${stale.join(", ")}`);
    process.exit(1);
  }
  console.log(`Prerender check passed for ${providerKeys.length} providers`);
} else {
  const changed = [];
  if (writeIfChanged(indexPath, source, nextIndex)) changed.push("index.html");
  if (writeIfChanged(sitemapPath, sitemap, nextSitemap)) changed.push("sitemap.xml");
  console.log(changed.length ? `Updated ${changed.join(", ")}` : "Homepage prerender is already current");
}
