# How it works, and how to defend it

Milestone 1 (NAV per share end to end). For each module: what it does, what can go wrong, and why this approach over the alternatives. Decision numbers (D#) refer to `context/decisions.md`.

## The chain of trust in one line

EDGAR file → saved once by accession number with a SHA-256 fingerprint → a candidate value with its exact source text → the **verification gate** re-reads the saved file and proves the text and number are there → conflicts resolved by rule, never silently → confidence with a stated reason → page and Excel.

A number that fails any step is not shown. Its cell says "—" and why (P1).

## Modules

### `config.py`: funds, window, paths
- Reads the client's `competitor_cik_list.csv` and adds per-fund settings: fund type (interval / BDC / REIT), share class (I), and which forms to read.
- `window_quarters(as_of)` gives the 8 quarter-ends ending at the as-of date. `quarters_between` gives the lag.
- **Can go wrong:** a new peer needs a settings entry. **Why:** the client's file stays the source for who the peers are.

### `records.py`: the data model
- `Citation` (where), `Candidate` (one value seen in one place), `ValueRecord` (what we show), `Issue` (one Exceptions line), `RunBundle` (one whole run).
- A validator enforces the core rule in the type itself: status "ok" must have a value **and** a citation, and a missing value must not carry a number.
- **Why Pydantic:** one schema, validated on every write, and it serializes straight to the bundle JSON.

### `edgar.py` + `cache.py`: getting filings politely and provably
- The User-Agent comes from `SEC_USER_AGENT`. Requests are 0.2 s apart (at most 5 per second; the SEC limit is 10). It retries on 429/5xx. A 403 raises a plain message ("usually a missing or invalid User-Agent").
- Each file is downloaded once to `data/cache/{cik}/{accession}/` and its SHA-256 is recorded in `manifest.json`.
- **Can go wrong:** EDGAR down → that fund shows "fetch failed" and the others continue. **Why hash:** a citation is only as good as the bytes it points to; the gate refuses a file that changed.

### `filings.py`: which filings, which period
- Lists a fund's filings of the right forms, including `/A` amendments.
- Takes the period from **each filing**, never EDGAR's company-level `fiscalYearEnd`, which is stale for Cliffwater (it says Dec 31; the filings say Mar 31). The mismatch is reported, not hidden (D18).
- Cross-checks the index period against the document's own cover tag (`dei:DocumentPeriodEndDate`).

### `textnorm.py`: one way to read HTML
- Extractors and the gate must see identical text, or a correct quote could fail just because of spacing. Everything goes through one routine that puts a space between table cells, maps odd characters (non-breaking spaces, dashes, curly quotes) to plain ones, and collapses whitespace.
- **Found in testing:** filings declare no character encoding, so lxml assumed Latin-1 and produced "Â". We detect UTF-8 ourselves.

### `extract/tables.py`: reading a labeled table row
- Finds the row ("Net asset value, end of period", "Book value per share") and its table.
- Works out the share class from a "CLASS I" header row (TAKIX) or the heading just above the table (CCLFX).
- Maps each number to its column's period end. It understands three header shapes: a full date per column; bare years under "Year Ended December 31,"; and "Six Months Ended June 30, 2025" followed by that year group, in that exact order only.
- **Fails safe:** if the column count and the values don't line up, or the order is ambiguous (TAKIX Class M), it returns nothing. A missing value is safe; a value attributed to the wrong period is not.

### `extract/ixbrl.py`: reading tagged numbers
- Reads inline-XBRL facts directly from the filing with lxml: concept, period, share-class dimensions, scale, sign, element id, and the row it sits in.
- **Why not the SEC company-facts API:** it drops dimensional facts, so it can't see per-class tags. **Why not Arelle:** a heavy dependency for a handful of tags (D21).

### `metrics/nav.py`: NAV candidates and their checks
- **Interval funds:** Class I financial highlights, checked with the **NAV bridge** (beginning NAV + total from operations + distributions = ending NAV, within $0.01).
- **KREF:** the book value table, checked as common equity ($ thousands) ÷ total shares. Labeled "KREF does not report NAV" (D14).
- **GBDC:** the `us-gaap:NetAssetValuePerShare` tag.
- Only periods inside the 8-quarter window are kept.

### `verify.py`: the gate (P1, P2)
A candidate is shown only if all of these pass:
1. The saved file's SHA-256 still matches.
2. The quote is found verbatim in the filing text, and its character offset is recorded.
3. The value is the right number in that quote (the right column for tables). The number parser ignores footnote digits glued to words ("income1", "%5"), reads "(0.54 )" as negative, and reads a standalone "—" as zero.
4. For tagged values, the XBRL element with that id and concept exists and shows that number.

Extractor and gate share one number parser, so they can't disagree about which number is in which column.

### `conflicts.py` + `confidence.py`: choosing, out loud
- Equal values from several filings agree, which raises confidence.
- Different values from different filings: the latest filing wins (an amendment is always later than its original). Both values and the rule are recorded and listed in Exceptions; confidence is Low.
- Two values in **one** filing: no rule applies, so it is flagged for the PM.
- **High:** verified, plus a second independent check (another filing agrees, or a reconciliation holds). **Medium:** verified, single source. **Low:** conflict, failed check, narrative-only or computed. The reason text names the rule that fired.

### `apex.py`: client data
- Loads `apex_ridge_fund_data.csv` as cited client data, unchanged.
- Checks that four quarterly returns compound to the reported 1Y. They don't: +22 to +28 bps every checkable quarter. Reported as a client question, not fixed (D11). Also checks that fee terms are constant.

### `pipeline.py`: one run
- For each fund: filing index → keep filings in the window and on or before the as-of date → download → candidates → gate → resolve per period.
- Then builds the deck table (latest verified NAV, with lag), the 8-quarter trend, and Exceptions.
- A date with a filing we read but no value says "not found in <accession>". A date with no filing at all (semi-annual funds) says "not reported". These are not the same, so we never blur them.
- Writes `runs/<timestamp>/bundle.json`, which includes every filing read with its hash and the code version.

### `export_excel.py` + `app.py` + `static/`: what people see
- Excel: Benchmark (deck layout with confidence letters), Provenance (one row per value), Exceptions, NAV Trend.
- The page has three tabs; a click opens the source panel. Run is in the background with a progress line. Every dynamic string is HTML-escaped before display.
- **Why FastAPI and plain JavaScript:** small, explainable, nothing to install beyond `uv`.

## Questions you'll likely get

- **"How do you know a number is right without an answer key?"** It's verbatim in a hashed copy of the filing, it's in the right column, and for High it's confirmed by an accounting identity or a second filing. 31 of 32 competitor NAV points are High.
- **"What if the parser hits a new layout?"** It returns nothing, and the cell says "not found in <accession>". It never shifts a column.
- **"Why not an LLM for everything?"** It isn't reproducible and can't prove which of two genuine figures it picked. LLM use is reserved for narrative fee terms (milestone 2), and its quote must still pass the same gate.
- **"Why is GBDC 12/31/25 only Medium?"** Only the Dec 2025 10-Q reports it within the as-of scope; we don't read later filings yet.
