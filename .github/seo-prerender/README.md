# Validated static-results pipeline

This directory validates result provenance and builds crawlable homepage,
provider, regional, Malay and genuine-date archive HTML from `results.json`.
JavaScript remains progressive enhancement; it is not the only copy of the
result numbers.

## Approval boundaries

`provenance-policy.json` separates three facts:

1. reuse rights confirmed by the site owner;
2. a dated accuracy cross-check for the current completed snapshot; and
3. live release approval.

The 24 August 2026 Batch 2-3 approval was consumed by production commit
`6ae25b05eef6efdeedc353fa81e823835a2b31a9`. The checked-in third gate is reset
to staging-only and each source's `publicationAllowed` value is false. Every
later result snapshot needs separate explicit live approval bound to its exact
snapshot digest. Permission to reuse results is not treated as publishing
approval, and dated manual checks remain bound to the exact retained snapshot.

## Local staging build

From the repository root:

```powershell
python .github/seo-prerender/build_site.py `
  --mode staging `
  --results results.json `
  --policy .github/seo-prerender/provenance-policy.json
```

Then verify deterministic parity without writing:

```powershell
python .github/seo-prerender/build_site.py `
  --mode staging `
  --results results.json `
  --policy .github/seo-prerender/provenance-policy.json `
  --check
```

## Result update behavior

`scrape.py` requires all reviewed providers, exact number formats and counts,
matching weekdays and related draw numbers, product-specific Sports Toto fields,
and a seven-day freshness limit. It compares Magnum, Da Ma Cai and Sports Toto
draw metadata and results between the two approved feeds. It writes a validated
candidate only to an explicitly supplied path outside the repository. Factual
comparison excludes volatile timestamps and approval metadata, so a
timestamp-only or verification-ID-only change is not a new candidate.
Each upstream response is capped at 2 MiB and only its SHA-256 digest is retained
with the candidate; raw responses are not included in the review artifact.

Grand Dragon and the remaining regional records do not yet have repeatable
automated second-source coverage. The reviewed 23 August 2026 snapshot has
separate dated checks in `accuracyReview.snapshotVerifications`. Each provider
binding includes its date, draw number where available, source URLs and a
canonical result digest. `results.json` opts into those records through
`snapshotVerificationIds`.

The scraper deliberately does not carry those IDs into its next output, so a
future snapshot cannot inherit a dated manual check. Publication mode still
requires a valid independent check for every provider plus explicit
live-release approval for the exact snapshot.

The scheduled workflow has read-only repository permission and disables
checkout credentials. It runs tests, writes candidates only under the runner's
temporary directory and, for a factual change, uploads a bounded staging-only
review artifact retained for seven days. Frequent checks do not upload; packaging
is limited to the post-draw and morning catch-up schedules, plus an explicit
manual run. The workflow does not build in publication mode, commit, push,
deploy, submit indexing or alter the checkout.

## Candidate review artifact

The artifact contains the candidate `results.json`, an exact unified diff,
publication blockers, a manifest, checksums, a `READY` marker and 14 static-page
previews. Its allowlist is capped at 25 files, 1 MiB per file and 5 MiB total.
The packer refuses a candidate with no factual change, any path inside the
repository, a symlink, an unexpected file or a candidate that fails staging
policy. It also rejects inherited snapshot-specific checks, missing source
payload hashes and any global or provider date regression. Files are assembled
and validated in a temporary directory, the `READY` marker is written last, and
the complete directory is atomically moved into place.

## Generated public routes

- homepage raw HTML result cards;
- Magnum, Sports Toto and Da Ma Cai pages;
- Sabah 88, Special Cash Sweep and Sandakan STC pages;
- West and East Malaysia comparison pages;
- a substantive prize-label guide;
- a Malay overview page with reciprocal language signals;
- `/past-results/` and one archive URL per completed snapshot actually retained;
  each dated archive includes only providers whose own draw date matches its URL.

No Chinese page, future-date archive, spelling doorway or provider/date page
permutation is generated.

## Archive sitemap dates

`archive-metadata.json` is the deterministic source for each retained archive's
sitemap `lastmod`. Historical archive records are mandatory and cannot predate
their draw date or point into the future. Staging may derive a missing current
candidate date from the candidate's update date so the read-only review
artifact still builds. Publication requires an explicit current record that
does not predate the frozen snapshot's update date. Bump a retained archive's
value only when that archived page receives a material content change.

## Tests

```powershell
python -m unittest discover -s .github/seo-prerender/tests -p "test_*.py" -v
```
