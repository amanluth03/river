# Apex Ridge peer benchmark

Pulls competitor filings from SEC EDGAR, extracts benchmark metrics, checks every number against the filing it came from, and shows the comparison with Apex Ridge's own data on one review page, with an Excel export.

**Rule one: a gap beats a wrong number.** A value appears only if its source text was found verbatim in the cached filing and the number was read back out of that text. Otherwise the cell shows "—" and the reason.

## Status (milestone 1, for Window 2)

| Metric | Apex Ridge | CCLFX | TAKIX | GBDC | KREF |
|---|---|---|---|---|---|
| NAV per share (latest + 8-quarter trend) | client CSV | done | done | done | done (book value) |
| Returns, fees, leverage, distribution yield | client CSV | pending | pending | pending | pending |

Pending cells say "pending" in the app. They are never filled with estimates.

## Run it

You need [uv](https://docs.astral.sh/uv/) (one-line install: `curl -LsSf https://astral.sh/uv/install.sh | sh`). It installs the right Python and all dependencies on its own.

```bash
git clone <repo-url> && cd rivertakehome
cp .env.example .env        # then set SEC_USER_AGENT to your name and email (the SEC requires it)
uv run benchmark            # opens http://127.0.0.1:8000
```

The first run downloads about 300 MB of filings into `data/cache/` (a minute or two). Later runs read the cache and take seconds.

Tests: `uv run pytest` (offline; uses small excerpts of real filings in `tests/fixtures/`).

## The analyst's workflow

1. Open the app.
2. Pick the quarter-end (default Dec 31, 2025) and press **Run**.
3. **Table:** scan the dots (green High, amber Medium, red Low). Click any value to see the filing, accession number, section, the exact source text, and the check that was run.
4. **Exceptions:** read every line. These are lags, filing conflicts, data-quality problems, client-data questions and peer-set questions. Nothing is resolved silently.
5. **Export to Excel:** the deck-layout table plus Provenance (one row per value), Exceptions and NAV Trend sheets.

## How a number earns its place

```
EDGAR ──> cache (by accession, SHA-256) ──> extract candidates ──> verification gate ──> resolve ──> confidence ──> page / Excel
          (XBRL tags first, then table rows)   (hash, verbatim quote,     (conflicts:
                                                value in quote, XBRL id)    later filing wins, both shown)
```

- **Sources:** inline-XBRL tags where the filing has them (GBDC NAV), otherwise the labeled table row (interval-fund Class I financial highlights, KREF book value table). Period dates come from each filing, not EDGAR's company metadata.
- **Confidence:** High = verified, plus a second independent check (another filing shows the same value, or a reconciliation holds, such as the NAV bridge or equity ÷ shares). Medium = verified, single source. Low = conflict, failed reconciliation, narrative-only or computed with an assumption.
- **Apex Ridge data** is shown as given and cited as client data. Its checks (for example, quarterly returns compounding to 22 to 28 bps above the reported 1Y) appear under Exceptions.

## Layout

```
benchmark/
  config.py        funds, as-of window, paths
  records.py       ValueRecord / Citation / Candidate / Issue / RunBundle
  edgar.py         EDGAR client (User-Agent, pacing, retries)
  cache.py         filing cache + SHA-256 manifest
  filings.py       which filings exist and the period each covers
  textnorm.py      one HTML-to-text routine shared by extractors and the verifier
  extract/         ixbrl.py (tagged facts), tables.py (labeled table rows)
  metrics/nav.py   NAV per share candidates + reconciliations
  verify.py        the verification gate
  conflicts.py     choosing between sources, never silently
  confidence.py    High / Medium / Low with a reason
  apex.py          client CSV loader + checks
  pipeline.py      one run, end to end
  export_excel.py  Excel workbook
  app.py, static/  the review page
context/           build log, decision log, client notes
docs/              spec and plan (technical approach and solution brief to follow)
```

## Known limitations (milestone 1)

- Only NAV per share is extracted for competitors so far.
- HTML filings have no fixed page numbers. Citations give the section, row, column, character offset and a link that opens the filing at that row (works in Chrome, Edge and Safari).
- Table parsing is tuned to these four funds' layouts. When a layout doesn't match, the value shows as missing, never mis-mapped.
- Only filings whose period falls in the 8-quarter window are read, so a value from the latest filing can't yet be cross-checked against a later one (GBDC 12/31/25 is Medium for that reason).
