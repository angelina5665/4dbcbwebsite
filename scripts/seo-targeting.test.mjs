import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

test("homepage targets current Malaysia result intent with useful internal links", async () => {
  const html = await fs.readFile(path.join(repo, "index.html"), "utf8");
  assert.match(html, /<title>4D Result Today Malaysia \| 4DVIP88<\/title>/);
  assert.match(html, /<h1><a href="\/">4D RESULT TODAY MALAYSIA<\/a><\/h1>/);
  assert.match(html, /MY4D at my4d\.co/);
  for (const href of [
    "/magnum-4d-results/", "/sports-toto-4d-results/", "/da-ma-cai-results/",
    "/east-malaysia-4d-results/", "/past-results/", "/prize-history/",
    "/4d-prize-guide/", "/dictionary.html", "/play-guide/", "/methodology.html",
  ]) {
    const escaped = href.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    assert.match(html, new RegExp(`href="${escaped}"`));
  }
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
  assert.doesNotMatch(html, /updated in real time|shortly after release/i);
});

test("Malay result page targets hari ini with provider links", async () => {
  const html = await fs.readFile(path.join(repo, "ms", "index.html"), "utf8");
  assert.match(html, /<title>Keputusan 4D Hari Ini Malaysia \| 4DVIP88<\/title>/);
  assert.match(html, /<h1>Keputusan 4D Hari Ini Malaysia<\/h1>/);
  for (const href of ["/magnum-4d-results/", "/sports-toto-4d-results/", "/da-ma-cai-results/", "/east-malaysia-4d-results/"]) {
    assert.match(html, new RegExp(`href="${href}"`));
  }
  assert.equal((html.match(/<h1\b/g) || []).length, 1);
});

test("brand identity and freshness distinctions are explicit", async () => {
  const about = await fs.readFile(path.join(repo, "about.html"), "utf8");
  const methodology = await fs.readFile(path.join(repo, "methodology.html"), "utf8");
  assert.match(about, /MY4D.*my4d\.co.*4DVIP88/s);
  assert.match(methodology, /Draw schedules and result update times/);
  assert.match(methodology, /provider's own draw date/);
  assert.match(methodology, /does not invent or label an upstream release timestamp/);
});

test("generated footers reinforce important discovered pages", async () => {
  for (const relative of ["magnum-4d-results/index.html", "sports-toto-4d-results/index.html", "east-malaysia-4d-results/index.html"]) {
    const html = await fs.readFile(path.join(repo, relative), "utf8");
    for (const href of ["/past-results/", "/4d-prize-guide/", "/dictionary.html", "/play-guide/"]) {
      assert.match(html, new RegExp(`href="${href}"`), `${relative} lacks ${href}`);
    }
  }
});
