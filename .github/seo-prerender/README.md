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

The checked-in third gate records the site owner's 24 August 2026 approval for
the reviewed live Batch 2-3 release. Each source's `publicationAllowed` value is
enabled for the fail-closed publication workflow. Merely having permission to
reuse results is not treated as publishing approval, and the dated manual
checks remain bound to the exact retained snapshot.

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
draw metadata and results between the two approved feeds. It writes atomically
only when semantic result data changes. A timestamp-only check leaves
`results.json` untouched.

Grand Dragon and the remaining regional records do not yet have repeatable
automated second-source coverage. The reviewed 23 August 2026 snapshot has
separate dated checks in `accuracyReview.snapshotVerifications`. Each provider
binding includes its date, draw number where available, source URLs and a
canonical result digest. `results.json` opts into those records through
`snapshotVerificationIds`.

The scraper deliberately does not carry those IDs into its next output. Their
removal is a semantic change, so a future snapshot cannot inherit a dated
manual check. Publication mode still requires a valid independent check for
every provider plus explicit live-release approval.

The scheduled workflow intentionally uses `--mode publication`. The reviewed
snapshot has live-release approval, but a future changed snapshot loses the
dated manual verification IDs and remains fail-closed until all required
provider checks are satisfied again.

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

## Tests

```powershell
python -m unittest discover -s .github/seo-prerender/tests -p "test_*.py" -v
```
