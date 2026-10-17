# Code tour

A script for walking someone through this code: what runs, where each number comes from, what is hard-coded and why, and what breaks when a filing changes. Every claim names a file and function, so you can open it and check.

---

## 1. Pipeline map (one page)

```
app.py  Runner.start ──► pipeline.run(as_of)
                           │
  apex.load ◄──────────────┤  Apex Ridge column from the client CSV (cited as client data, never modified)
                           │
                           ├─ for each competitor ─► pipeline._competitor
                           │     edgar.submissions ─► filings.list_filings ─► pipeline._filings_in_window
                           │     pipeline._fetcher ─► edgar.fetch ─► cache.store (SHA-256 in manifest.json)
                           │     metrics.nav.candidates ─► verify.check ─► conflicts.resolve ─► confidence.score
                           │     pipeline._nav_cell / _nav_trend
                           │     FundData (metrics/common.py) handed to:
                           │        metrics.leverage.records        (2 rows)
                           │        metrics.distributions.record    (1 row)
                           │        metrics.returns.records         (3 rows)
                           │        metrics.fees.records            (2 rows)
                           │     pipeline._apply_lag, _record_issues, amendments.flag / amended_filings
                           │
                           └─ RunBundle (records.py) ─► runs/<timestamp>/bundle.json
app.py  /api/bundle ─► static/app.js (Table · Exceptions · NAV trend, side panel per cell)
app.py  /api/export.{xlsx,docx} ─► export_excel.write (4 protected sheets) / export_word.write (same cell text)
```

| File | Job | Key functions |
|---|---|---|
| `config.py` | Every constant with its source; fund list | `load_funds`, `window_quarters`, `quarters_between` |
| `records.py` | Data model: `Citation`, `Candidate` (one value seen in one place), `ValueRecord` (one cell), `Issue`, `RunBundle` | `ValueRecord._status_matches_value` (no shown value without a citation; no computed value without verified inputs), `ValueRecord.gap` |
| `edgar.py` | EDGAR HTTP: User-Agent, 0.2 s pacing, retries, 403 message | `Edgar.get_bytes`, `submissions`, `fetch`, `archive_url` |
| `cache.py` | Files on disk by accession plus a SHA-256 manifest | `store`, `verify_hash` |
| `filings.py` | Which filings exist, each one's own period | `list_filings`, `fiscal_year_end_mismatch`, `document_period` |
| `textnorm.py` | One HTML-to-text routine shared by extractors and the verifier | `normalize`, `element_text`, `document_text` |
| `extract/tables.py` | Find a labeled table row; date each column from its header; read period length from the column title | `find_row`, `_column_dates` (4 cases), `row_in_same_table`, `period_months`, `find_named_columns_row` |
| `extract/ixbrl.py` | Inline-XBRL tagged numbers with period start and end | `facts`, `_contexts` |
| `verify.py` | The gate. Checks: the hash is unchanged; the quote is verbatim; the value is in the right column; the column header gives the period and sits above the row; the XBRL element exists | `check`, `_check`, `parse_numbers` |
| `conflicts.py` | One value per (fund, metric, period). Equal values agree; otherwise the later filing (or the amendment) wins and both are shown; two values in one filing go to the PM | `resolve` |
| `confidence.py` | High / Medium / Low, with the rule that fired | `score` |
| `metrics/common.py` | Shared builders: table/XBRL candidates, computed values, gaps with links | `table_candidate`, `ixbrl_candidates`, `computed`, `missing`, `searched_citation` |
| `metrics/*.py` | One module per deck row group (sections 2a to 2e) | `candidates` / `records` / `record` |
| `amendments.py` | Flags values whose filing was later amended | `flag`, `amended_filings` |
| `apex.py` | Client CSV loader; compounding-gap and fee-change checks | `load`, `_compounding_issues` |
| `export_excel.py`, `export_word.py`, `app.py`, `static/` | Output. `export_excel.cell_text` is the one function that turns a record into cell text (value, confidence, "(computed)", note, lag, amendment flag, conflict values); Word reuses it, so the two files can't differ | `cell_text`, `alert`, `write`; FastAPI routes; `app.js cellHtml/openPanel` |

**The invariant to say out loud:** nothing reaches the table unless `verify.check` passed on it, or (for computed values) on every input. `records.py` enforces this in the model validator, so code that tried otherwise would raise an error, not show a number.

---

## 2. The exact path of one value, per metric

The format of each walk: filing text → function → normalization → confidence → cell.

### 2a. NAV per share: TAKIX $8.32 (as of 12/31/25)
1. **Filing:** N-CSR 0001725472-26-000003, Class I Financial Highlights row `Net asset value, end of period $ 8.32 $ 8.55 …`.
2. **Extract:** `metrics/nav.candidates` → `_from_table` → `tables.find_row(path, config.NAV_END, "I")`. The class comes from `_share_class` (the "Class I" heading above the table). The column dates come from `_column_dates`: "Year Ended December 31," over a row of years.
3. **Check:** `nav._bridge`: beginning NAV + total from operations + distributions = ending NAV, within `config.PER_SHARE_TOLERANCE` ($0.01).
4. **Gate:** `verify.check` finds the quote verbatim and reads 8.32 back out of column 0. It re-derives 12/31/25 from the column header and confirms that header is above the row. It also records the find hint (match 2 of 7).
5. **Resolve and confidence:** `conflicts.resolve` → `confidence.score` gives High (verified, and the bridge reconciles).
6. **Cell:** `pipeline._nav_cell` takes the latest verified period. `app.js cellHtml` and `export_excel.cell_text` show "$8.32 [H]".

GBDC's NAV is the same path via `nav._from_ixbrl` (tag `us-gaap:NetAssetValuePerShare`), and the gate also checks the XBRL element. KREF's goes via the "Book value per share" row, checked as equity × the caption's scale ÷ shares. The label is exactly `config.KREF_BOOK_VALUE_LABEL`.

### 2b. Economic leverage: TAKIX 0.40x
1. **Filing:** the same N-CSR, Consolidated Statement of Assets and Liabilities. Rows: `Secured credit facilities $ 920,159`, `Mandatory redeemable preferred shares (…) 946,446`, `Note-on-note loans 27,686`, `Net Assets $ 4,782,841`.
2. **Extract:** `leverage._balance_sheet` finds the `config.LEVERAGE_ROWS["TAKIX"]["equity"]` row. It then requires every debt row **in the same table** (`tables.row_in_same_table`), so every input shares one scale.
3. **Gate:** `common.check_all` runs on all four inputs. If any fails, the cell shows "not found" with the failing row's reason.
4. **Normalization:** D/E = (920,159 + 946,446 + 27,686) ÷ 4,782,841 = 0.396 → 0.40x. The formula, with every number, is in `record.normalizations`.
5. **Check:** the asset coverage TAKIX reports (2c), 352.0%, implies 1 ÷ (3.52 − 1) = 0.397x (`leverage.implied_de`). This agrees within `config.LEVERAGE_TOLERANCE` (0.05x).
6. **Confidence:** `common.computed` gives High (verified inputs plus an independent check that agrees). If they disagree it gives Low with the "check_failed" flag (test: `tests/test_units.py::test_leverage_that_disagrees_with_reported_coverage_is_low`).
7. **Cell:** "0.40x [H]". The side panel lists all four inputs, each with its own link, quote and find hint. The Provenance "Inputs" column does the same in Excel.

The same path applies to GBDC (`Debt` ÷ `Total Net Assets`, checked against 178.94%), KREF (checked against its own 3.9x total leverage recomputed net of cash) and CCLFX (no independent figure, so Medium).

### 2c. Regulatory leverage
- **TAKIX 352.0%:** `leverage._takix_coverage` matches `config.TAKIX_COVERAGE_SENTENCE` in the Note 7 text. The sentence's date must equal the balance-sheet date. It becomes a `regex` candidate and goes through the gate. Confidence is Medium: narrative text confirmed by the balance sheet (`confidence.score`, decision 38).
- **GBDC 178.94%:** `leverage._gbdc_coverage` reads `config.COVERAGE_CONCEPT` facts that sit in a table row (`common.ixbrl_candidates` skips the "178.9%" in running text). It goes through the gate plus the XBRL element check, and comes out High after the same cross-check.
- **CCLFX:** the cell says "Not reported by fund" (client, W3: decision 57), because the fund reports coverage per facility only. The computed (net assets + debt) ÷ debt = 421.1% sits in the note as "computed, low confidence", with its verified inputs and formula in the panel.
- **KREF:** `missing(..., "not_applicable", config.KREF_NOT_1940_ACT)`. The note quotes KREF's own verified ratios.
- **Apex:** `config.NOT_IN_CLIENT_DATA` (`pipeline._apex_column`).

### 2d. Distribution yield: CCLFX 10.58% (as of 9/30/25)
1. **Filings:** N-CSRS 0001213900-25-118573, Class I `Total Distributions to shareholders (0.54) (0.90) …`, and N-CSRS 0001213900-24-106851 `(0.30)`.
2. **Extract:** `distributions._table_pieces` takes every column of that row in every filing. Each column's length comes from its own title via `tables.period_months` ("For the Six Months Ended…" → 6, "For the Year Ended…" → 12). An untitled short period gets no length and is never used.
3. **Resolve:** `distributions._best` makes one record per (period end, length). FY to 3/31/25 = 0.90 appears in two filings, which agree.
4. **TTM:** `distributions._ttm` = 6 months to 9/30/25 (0.54) + 12 months to 3/31/25 (0.90) − 6 months to 9/30/24 (0.30) = 1.14. The dates come from `months_before`.
5. **Normalization:** amounts printed in parentheses are used as positive (stated in the formula). Yield = 1.14 ÷ NAV 10.77 = 10.58%.
6. **Confidence:** Medium (arithmetic on verified inputs; no independent TTM figure exists). The cell shows "Trailing 12 months / NAV per share" and the 1Q lag.

GBDC uses tagged quarter and fiscal-year facts (`_ixbrl_pieces`, lengths from XBRL start/end dates and `config.DAYS_ONE_*`). TAKIX and KREF report a calendar fiscal year, so one 12-month piece is enough.

### 2e. Returns
- **TAKIX 1Y 6.27%:** `returns._interval` → `tables.find_named_columns_row(path, "^I Share$", …)` in the "Average Annual Total Returns through December 31, 2025" table. The column is found by header text (`config.RETURN_COLUMNS`). The gate checks the quote and the column position. `returns._highlights_check` compares it with the Financial Highlights "Total Return, at Net Asset Value" for the same year (6.27), so confidence is High.
- **TAKIX 3Y:** the header has no 3-Year column, so the cell says `Not reported by fund` with a link to the table row.
- **CCLFX 1Y:** same path, from N-CSR 0001213900-25-052571 (as of 3/31/25). `returns._highlights_candidate` reads the same year from the Financial Highlights as its own verified candidate: 11.58% vs 11.78%. Because they disagree, `returns._conflict` builds a record with status "conflict": no value, no confidence, both candidates with their own citations, and a cell citation that quotes neither. The cell says "Conflict: PM to choose" (client, W3: decision 56).
- **GBDC 9.36%:** `returns._gbdc` reads `config.GBDC_RETURN_CONCEPT` from the latest 10-K, keeping only facts whose context spans one year (a 10-Q's 3-month 1.65% can't slip in). The label is `config.GBDC_RETURN_LABEL` and the note `config.GBDC_RETURN_NOTE`. 3Y/5Y say `Not reported by fund`.
- **KREF:** not applicable (no NAV-based return).
- **Apex 1Y 10.31%:** from the CSV. `apex._compounding_issues` finds the 22 to 28 bps gap, and `pipeline._apex_column` attaches `config.APEX_GAP_NOTE` (Dana's approved framing, "fund accountant to confirm") as a footnote and an Exceptions line.

### 2f. Fees
`fees.records` finds `config.FEE_SECTION[fund]` in the latest report's text and cites the next 400 characters verbatim, with a find hint. The cell says `Not extracted in v1` and links there. If the phrase is gone, it links the report and says `config.FEES_IN_NARRATIVE`.

---

## 3. Every hard-coded value: where it lives and its source

**All business constants are in `benchmark/config.py`**, each with a comment naming its source. The groups:

| Constant(s) | Source |
|---|---|
| `DEFAULT_AS_OF`, `WINDOW_QUARTERS` | Apex's latest CSV quarter; W1/W2 decisions 4, 5, 9 |
| `EDGAR_PAUSE_SECONDS` | SEC fair-access policy (10 requests/second maximum) |
| `FUND_SETTINGS` (kind, class, forms) | Each fund's cover page / Item 1; Class I = W1 decision 3; ticker TAKIX = "I Share" in its performance table |
| `ROWS`, `APEX_FUND`, `APEX_COLUMNS` | `board_deck_excerpt.md` row order; CSV header; two leverage rows = W2 decision 10 |
| `KREF_BOOK_VALUE_LABEL`, `GBDC_RETURN_LABEL/NOTE`, `NOT_REPORTED_BY_FUND`, `NOT_IN_CLIENT_DATA`, `KREF_NOT_1940_ACT`, `FEES_*`, `AMENDMENT_FLAG`, `APEX_GAP_NOTE`, `FOOTNOTES` | Dana's own words in the W2 transcript (quoted next to each) |
| `NAV_END`, `NAV_BEGIN`, `TOTAL_OPS`, `TOTAL_DIST`, `BOOK_VALUE`, `COMMON_EQUITY`, `TOTAL_SHARES`, `NAV_CONCEPT` | Row labels / tag as printed in the named filings |
| `LEVERAGE_ROWS`, `TAKIX_COVERAGE_SENTENCE`, `COVERAGE_CONCEPT`, `KREF_*` | Balance-sheet labels, Note 7 sentence, highlights tag, KREF MD&A table, each with its accession |
| `COVERAGE_MINIMUM` | GBDC 10-K (150%); 1940 Act s.18(a)(1)(A) 300% and s.18(a)(2)(A) 200% |
| `DISTRIBUTION_ROWS`, `DISTRIBUTION_CONCEPT`, `PERIOD_LENGTHS` | Labels and column titles as printed (CCLFX, TAKIX, GBDC, KREF) |
| `RETURN_*`, `HIGHLIGHTS_RETURN_ROW`, `GBDC_RETURN_CONCEPT` | Performance-table caption, rows and headers; highlights rows; GBDC footnote (6) |
| `FEE_SECTION` | The first words of the fee sentence in each filing |
| `SCALE_WORDS` | KREF caption "(amounts in thousands, …)" |
| `PER_SHARE_TOLERANCE` 0.01 | Per-share figures are printed to the cent |
| `LEVERAGE_TOLERANCE` 0.05x | Half of KREF's 0.1x rounding step; coverage at principal vs balance sheet at carrying value (decision 37) |
| `RETURN_TOLERANCE` 0.00 | Returns printed to 2 decimals; agreement means equal |
| `DAYS_ONE_YEAR` 360–370, `DAYS_ONE_QUARTER` 88–93 | Calendar: 365/366 days; 90–92 days, with room for weekend period ends |
| `HEADER_WINDOW` 6000 | Measured: longest header-to-row distance is 1,721 characters; re-measured by a test on every run |
| `CAPTION_CHARS` 150 | CCLFX's balance-sheet caption is 73 characters; nothing further up is trusted |
| `BLOCK_TAGS` | HTML block and table elements (HTML spec) |

**Literals that remain in code, and why they are not business constants:**
- `tables._is_year` treats 1990–2100 as a year. It only separates a header year from a value, and no fund in the set predates 2009.
- `tables._preceding_text(limit=400)` is the text window used to find a table's heading and class label.
- `distributions._ttm` tries piece lengths of 3, 6 and 9 months: the only sub-year lengths `PERIOD_LENGTHS` can produce.
- Display rounding: `Decimal("0.01")` for ratios and yields, `Decimal("0.1")` for computed coverage.
- Per-fund branches in code: `leverage.records` (`fund.ticker == "TAKIX"` for the sentence; `kind` for the rest), `returns.records` and `distributions.record` (XBRL for the BDC, tables for the others). The fund kind comes from `FUND_SETTINGS`.
- `app.py`: host 127.0.0.1 and port 8000.

---

## 4. Where a filing-format change breaks it, and what happens then

The design rule: **every parse fails to a labeled gap, never to a different number.** The gate re-reads every shown number from the cached text, so a parse that grabbed the wrong cell would also have to fool the column-header check.

| If this changes in a filing… | Code that depends on it | What happens |
|---|---|---|
| A row label is reworded (e.g. "Net Assets" → "Total net assets") | `config.*_ROWS` patterns → `tables.find_row` | No row, so "Not found in the filings read" with the patterns listed; an Exceptions line |
| A new debt line appears on a balance sheet | `config.LEVERAGE_ROWS[...]["debt"]` | D/E would be understated, so the cross-check against reported coverage (or KREF's ratio) disagrees and the value drops to **Low** with "check_failed". **CCLFX has no cross-check:** a new CCLFX debt line would go unnoticed, which is why CCLFX D/E is Medium |
| Column headers change style | `tables._column_dates` (4 accepted layouts) | Unrecognized layout: the row is skipped, giving a gap. A header naming two periods that share a month-day is refused on purpose |
| Columns reordered | `_column_dates` dates each column from its own header; the gate re-derives the date (`verify._date_from_header`) | A wrong mapping can't pass the gate |
| A column title stops saying "Six Months Ended" / "Year Ended" | `config.PERIOD_LENGTHS` → `tables.period_months` | That piece has no length, so the TTM can't be built: a shorter-period yield flagged Low, or a gap |
| A table caption loses its date (single-column statements) | `_column_dates` case 3, `config.CAPTION_CHARS` | No date, so a gap |
| TAKIX rewords the asset-coverage sentence | `config.TAKIX_COVERAGE_SENTENCE` | The regulatory cell becomes "not found" and economic D/E drops to Medium (no check) |
| An XBRL concept is renamed or moved to a dimension | `config.*_CONCEPT`, `common.ixbrl_candidates` (dimensionless table-row facts only) | No fact, so a gap |
| The performance table gains or loses a column, or a "%" cell layout changes | `tables.find_named_columns_row` requires the header and row to have the same cell count | Refused, so a gap; a missing horizon says "Not reported by fund" with the columns it does show |
| The fee sentence is reworded | `config.FEE_SECTION` | Link to the report plus "Fee terms are in the prospectus narrative" |
| A filing is re-downloaded with different bytes | `cache.verify_hash` in the gate | Every value from it fails: "hash mismatch" |
| An amendment is filed | `amendments.flag` on every run | "Superseded by amendment: re-check" appears at the top of the cell, styled red, in the UI, Excel and Word, and in Exceptions (decision 58) |
| EDGAR is unreachable or refuses (403) | `edgar.get_bytes`, `pipeline.run` try/except per fund | That fund's column reads "EDGAR fetch failed"; the other funds still run |
| A filing declares no charset | `textnorm._parse` detects UTF-8 itself | Handled (it once produced "Â" for non-breaking spaces) |

---

## 5. Ten questions a skeptical interviewer will ask

1. **"Where does the label 'Return on average net assets' come from? How do you know?"**
   `config.GBDC_RETURN_LABEL`. The comment quotes Dana in Window 2 ("label it clearly as return on average net assets"). The measure itself is GBDC's 10-K footnote (6): net increase in net assets from operations ÷ daily average net assets. The concept is `us-gaap:InvestmentCompanyTotalReturn`, and the extractor only accepts a full-fiscal-year context.

2. **"Walk me through how 0.40x for TAKIX gets onto the screen."**
   `leverage._balance_sheet` finds the Net Assets row and the three debt rows in the same balance-sheet table, and each passes `verify.check` (hash, verbatim quote, column, header date). `leverage.records` divides, then compares with the 0.397x implied by the 352% coverage TAKIX reports. `common.computed` marks it High, and the panel shows all four quoted inputs (section 2b).

3. **"What if Carlyle adds a new credit facility line next quarter?"**
   We would sum only the configured lines, so D/E would be too low. But reported asset coverage includes all senior securities, so the cross-check fails and the cell drops to Low, with the disagreement in Exceptions. For CCLFX there is no such check, which is why it is Medium; adding its senior-securities table as a second source is the next step.

4. **"How do you know a number in the table is really in the filing?"**
   `verify.check` re-opens the cached file and checks: its SHA-256 matches the download; the quote occurs verbatim in the normalized text; the number at the expected column of that quote equals the value; the column header above it gives the period; for tags, the XBRL element with that id shows that number. `records.py` refuses a shown value without a citation, and a computed value whose inputs aren't all verified.

5. **"Why not just use an LLM to read the filings?"**
   An LLM can return a plausible number from the wrong share class or period, and the client's rule is that an unfindable figure counts as wrong. The extractors here are deterministic, and the gate rereads every number. An LLM was reserved for narrative items (fees) with mandatory verbatim-quote checking; in v1 the fees are links instead (decision 45).

6. **"CCLFX's annual report gives 11.78% and 11.58% for the same year. Which do you show?"**
   Neither as "the" value: the client's rule (W3, decision 56) is that the PM chooses. The cell says "Conflict: PM to choose" and lists both, each with its own verified citation (performance table and Financial Highlights). In code, that's `returns._conflict` producing status "conflict", which the model allows to have no value.

7. **"Your distribution yield for CCLFX: where are the 12 months?"**
   The six months to 9/30/25 (0.54), plus the year to 3/31/25 (0.90), minus the six months to 9/30/24 (0.30), from two semi-annual reports. Each period's length is read from its own column title, never assumed. Every piece is a verified, cited input, and the formula is shown in the cell's panel.

8. **"Why is a value 'Medium' and not 'High'?"**
   High needs a verified structured source plus an independent confirmation: another filing with the same value, a reconciliation, or a reported figure that agrees. Medium means verified but single-source; Low means a conflict, a failed check, narrative-only, or an assumption. The reason text always names the rule that fired (`confidence.score`, `common.computed`).

9. **"What happens when a filing is amended after you used it?"**
   Each run reads the fund's EDGAR index. `amendments.flag` marks any shown value whose filing (or any input's filing) has a later `/A` for the same form and period: "Superseded by amendment: re-check". Exceptions also lists every amended filing in the index. CCLFX's two N-CSRS/A for 9/30/23 show up there, and a unit test covers that real case.

10. **"How would someone maintain this when a fund changes its report layout?"**
    The likely change is a reworded label. They change one line in `config.py`, cite the new filing, rerun `tests/cut_fixtures.py` and the tests. Until then, the affected cell shows a labeled gap with the patterns it looked for, so nothing wrong reaches a deck while it is being fixed.
