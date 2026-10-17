# Apex Ridge peer benchmark

Pulls competitor filings from SEC EDGAR, extracts benchmark metrics, checks every number against the filing it came from, and shows the comparison with Apex Ridge's own data on one review page, with Excel and Word exports.

**Rule one: a gap beats a wrong number.** A value appears only if its source text was found verbatim in the cached filing and the number was read back out of that text. A computed value (leverage, distribution yield) appears only if every input passed that check. Otherwise the cell says what is missing and why.

**Validation strategy:** how each number is checked, reconciled and scored, cell by cell: [docs/technical_approach.md#validation-strategy](docs/technical_approach.md#validation-strategy).

## Status (after Window 3)

All nine deck rows are filled for every fund, from the filings, as of Dec 31, 2025:

| Row | CCLFX | TAKIX | GBDC | KREF |
|---|---|---|---|---|
| Net return 1Y / 3Y / 5Y | 1Y "Conflict: PM to choose" (11.78% performance table, 11.58% financial highlights); 3Y 10.69%, 5Y 10.98% (as of 3/31/25) | 6.27% / Not reported by fund / 8.21% | Return on average net assets 9.36% (FY to 9/30/25), "Not directly comparable"; 3Y/5Y not reported | Not applicable: no NAV-based return (REIT reports book value) |
| Management / incentive fee | "Not extracted in v1 · view fee terms ↗" (incentive: annual report states no incentive-fee terms) | Not extracted in v1 · view fee terms ↗ | same | same |
| NAV per share | $10.77 (9/30/25) | $8.32 | $14.84 | Book value per share $13.04 |
| Economic leverage (D/E) | 0.31x | 0.40x | 1.25x | 4.00x |
| Regulatory leverage (asset coverage) | Not reported by fund (note: 421.1% (computed, low confidence)) | 352.0% | 178.94% | Not applicable: not a 1940 Act fund |
| Distribution yield (TTM ÷ NAV) | 10.58% | 9.01% | 10.51% | 7.67% (on book value) |

Gaps are labeled with the reason (for example "Not reported by fund"), never blank, and every cell links to its filing. `context/build_log.md` has the hand-check link for each value; `docs/CODE_TOUR.md` traces each one through the code.

## Run it

You need [uv](https://docs.astral.sh/uv/) (one-line install: `curl -LsSf https://astral.sh/uv/install.sh | sh`). It installs the right Python and all dependencies on its own.

```bash
git clone https://github.com/amanluth03/river.git && cd river
cp .env.example .env        # then set SEC_USER_AGENT to your name and email (the SEC requires it)
uv run benchmark            # opens http://127.0.0.1:8000
```

The command opens your browser at the page; port 8000 must be free. On a fresh clone the page says "No run yet": press **Run** once (Q4 2025 is selected). The first run downloads about 400 MB of filings into `data/cache/` (under a minute on a fast connection). Later runs read the cache and take seconds. Stop the server with Ctrl+C.

No API key is needed: nothing in v1 calls a language model.

Tests: `uv run pytest` (offline; uses small excerpts of real filings in `tests/fixtures/`).

## The analyst's workflow

1. Open the app.
2. The page opens on Q4 2025 (Dec 31, 2025), the default as-of. Pick another quarter-end to see its latest run, or press **Run** to build or refresh it.
3. **Table:** scan the dots (green High, amber Medium, red Low). Click any value to see the filing, accession number, section, the exact source text, and the check that was run.
4. **Exceptions:** read every line. These are lags, filing conflicts, data-quality problems, client-data questions and peer-set questions. Nothing is resolved silently.
5. **Export to Excel:** the deck-layout table plus Provenance (one row per value), Exceptions and NAV Trend sheets, protected against accidental edits.
6. **Export to Word:** the same table (same cell text, same run), footnotes, exceptions and a provenance appendix, every cell linked to its filing. Labeled as a generated report with the run time and code version.

Every export is also saved in `exports/` and the page shows the path.

## How a number earns its place

```
EDGAR ──> cache (by accession, SHA-256) ──> extract candidates ──> verification gate ──> resolve ──> confidence ──> page / Excel
          (XBRL tags first, then table rows)   (hash, verbatim quote,     (conflicts:
                                                value in quote, XBRL id)    later filing wins, both shown)
```

- **Sources:** inline-XBRL tags where the filing has them (GBDC), otherwise the labeled table row (Class I financial highlights, balance sheets, performance tables, KREF's statements), and one narrative sentence (TAKIX asset coverage), always quoted verbatim. Period dates and period lengths come from each filing, not EDGAR's company metadata.
- **Computed values** (economic leverage, distribution yield, CCLFX asset coverage) list every input with its own citation; the formula is shown next to the value.
- **Amendments:** each run checks every fund's EDGAR index; a value whose filing was later amended is flagged "Superseded by amendment: re-check".
- **Confidence:** High = verified, plus a second independent check (another filing shows the same value, or a reconciliation holds, such as the NAV bridge or equity ÷ shares). Medium = verified, single source. Low = conflict, failed reconciliation, narrative-only or computed with an assumption.
- **Apex Ridge data** is shown as given and cited as client data. Its checks (for example, quarterly returns compounding to 22 to 28 bps above the reported 1Y) appear under Exceptions.

## Layout

```
benchmark/
  config.py        EVERY constant, each with its source (row labels, tags, tolerances, client wording)
  records.py       ValueRecord / Citation / Candidate / Issue / RunBundle
  edgar.py         EDGAR client (User-Agent, pacing, retries)
  cache.py         filing cache + SHA-256 manifest
  filings.py       which filings exist and the period each covers
  textnorm.py      one HTML-to-text routine shared by extractors and the verifier
  extract/         ixbrl.py (tagged facts), tables.py (labeled table rows)
  metrics/         nav, leverage, distributions, returns, fees (+ common helpers)
  amendments.py    amendment check against the EDGAR index
  verify.py        the verification gate
  conflicts.py     choosing between sources, never silently
  confidence.py    High / Medium / Low with a reason
  apex.py          client CSV loader + checks
  pipeline.py      one run, end to end
  export_excel.py  Excel workbook
  export_word.py   Word report (same run data and cell text as the Excel)
  app.py, static/  the review page
context/           build log, decision log, client notes
docs/              CODE_TOUR.md (pipeline map, value paths, constants, failure modes)
tests/             offline tests on fixtures cut from the real filings (tests/cut_fixtures.py)
```

## Known limitations (v1)

- Fee terms are not extracted; the cell links to the sentence that states them (decision 45).
- HTML filings have no fixed page numbers. Every cell's link (UI, Excel and Word) lands on its source text: the row label or quote start when it is unique in the filing, else the nearest unique text above the cited row, with a find hint ("search “Net asset value, end of period”: match 2 of 7", counted ignoring case like a browser's find). One citation (KREF "Cash and cash equivalents", an input to KREF's leverage check) has no unique text nearby and opens the filing with its hint. Text-fragment links need a current browser and a click.
- Table parsing is tuned to these four funds' layouts and row labels (all in `config.py`). When a layout or label changes, the value shows as missing, never mis-mapped.
- Only filings whose period falls in the 8-quarter window are read.
- Amendments are flagged, not re-pulled automatically.
