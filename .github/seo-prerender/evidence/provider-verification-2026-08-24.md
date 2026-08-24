# Dated provider verification: 23 August 2026 snapshot

**Checked:** 2026-08-24 14:57-15:03 MYT

**Scope:** the exact provider objects referenced by `results.json`

**Outcome:** zero result mismatches

**Release boundary:** staging evidence only; no live-release approval

This record supplements the automated `4d4d.co` versus `4dmoon` comparison.
Each manual verification is bound to the exact provider object by date, draw
number (where available) and a canonical SHA-256 digest. It cannot validate a
later draw or changed result object.

## Special Cash Sweep

- Staged draw: 23-08-2026, draw 5334-26.
- Result: 9359 / 3532 / 4082; all 10 Special and all 10 Consolation values
  matched. The provider API's numeric `85` was normalised to the displayed
  four-digit value `0085`.
- Provider-owned evidence:
  `https://www.cashsweep.my/api/results/draw/number/5334`
- Separate publisher evidence:
  `https://www.4d2u.com.my/live.php?lang=E`
- Bound digest:
  `sha256:9146efcd529730736285f9abe307ba56605eee37bdd6ab23258cd0824061a1da`

## Sabah 88

- Staged draw: 23-08-2026, draw 4241-26.
- Result: 3355 / 2289 / 4324; all 10 Special, all 10 Consolation and Sabah 3D
  020 / 042 / 229 matched.
- Provider-owned evidence:
  `https://www.diriwan88.com/App88/Result/ResultPrint.asp?DataAction=Apply&strID=13971%3A13970%3A13969%3A13968%3A13967`
- Separate publisher evidence: `https://4dnow.app/`
- Bound digest:
  `sha256:09a6e57e2242aa45da60362580f3ccbadf39abf35097e3891642f36b66528037`

The provider page sorts some lower-tier values; the separate publisher also
confirmed the staged positional layout. The slash-to-hyphen draw-number
difference is formatting only.

## Sandakan Turf Club

- Staged draw: 23-08-2026, draw 106-26.
- Result: 4342 / 4630 / 9065; all 10 Special and all 10 Consolation values
  matched.
- Provider-owned evidence: `https://stc4d.com/results`
- Separate publisher evidence: `https://4dnow.app/`
- Bound digest:
  `sha256:2b5dc60329b3c72b34d3d7ff6ae372d724188ab4abad03a634d5df0595cac946`

The slash-to-hyphen draw-number difference is formatting only.

## Singapore Pools

- Staged draw: 23-08-2026, draw 5526.
- Result: 9675 / 0618 / 6753; all 10 Starter and all 10 Consolation values
  matched.
- Provider-owned data-file evidence:
  `https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/fourd_result_top_draws_en.html?v=%24`
- Stable separate publisher evidence:
  `https://www.check4dresult.com/singapore-result/23-08-2026`
- Additional draw-number corroboration:
  `https://www.cupin.net/draw/singapore-pools/5526/`
- Bound digest:
  `sha256:e7275777abccc5e5d36572f576ecec5505b1f0b4e9dd21f78a16402312b2aa1d`

The provider domain was restricted by the local Malaysian client route during
one direct check. Its current provider-owned data record was nevertheless
available to the read-only web crawl, and the two dated independent pages
matched the complete record.

## Grand Dragon

- Staged draw date: 23-08-2026. No operator-corroborated draw number was found,
  so the staged draw number remains absent.
- Result: 9870 / 9445 / 3927; all meaningful Special values and all 10
  Consolation values matched. Empty A-M positions remain presentation
  separators, not extra winning numbers.
- Operator-family surfaces:
  `https://www.gdlotto.net/results/prize-calculator/` and
  `https://gdlotto.com/jackpot/index.aspx`
- Dated separate publisher evidence:
  `https://www.check4dresult.com/zh/grand-dragon-lotto/23-08-2026`
- Additional separate publisher evidence:
  `https://4d2ulive.com/lotto-4d/page/31/`
- Bound digest:
  `sha256:8db23433d5f50f9672cd1cf709d7b942d783e9f68efeb3c7e58ae57d23c5bdba`

The `.com` and `.net` pages are treated as one operator family. The two other
domains are different publishers and are not the staged `4dmoon` feed, but
their undisclosed upstream lineage cannot be proven from public pages alone.
This is therefore a dated operator-family plus multi-domain check, not a claim
of repeatable independent automation.

## Carry-forward control

`scrape.py` writes only the repeatable automated cross-check record. It does
not copy `snapshotVerificationIds`. Removing the two dated IDs is a material
semantic change, so the next accepted scrape drops these manual checks and live
publication becomes fail-closed until the new snapshot is reviewed.
