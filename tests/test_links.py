"""Every citation link lands on its source text, not the top of the filing (client/Aman requirement).

A URL text fragment (#:~:text=...) only works if (a) its words occur once in the document, since browsers
jump to the first match (decision 34: a repeated label landed on TAKIX Class A), and (b) its words sit in
one table cell or paragraph, since browsers never match across a block boundary.
"""
from urllib.parse import unquote

from benchmark import links, textnorm
from benchmark.records import Citation
from tests.test_pipeline import make_bundle

DOC_URL = "https://www.sec.gov/Archives/edgar/data/1/000000000000000000/doc.htm"
NAV = "Net asset value, end of period"


def _doc(tmp_path, body):
    path = tmp_path / "doc.htm"
    path.write_text(f"<html><body>{body}</body></html>")
    return path, textnorm.document_text(path)


def _row_citation(text, label, quote, nth=1):
    phrase = label or quote
    offset = -1
    for _ in range(nth):
        offset = text.find(quote, offset + 1)
    return Citation(cik="0000000001", form="N-CSR", accession="0000000000-00-000000", url=DOC_URL,
                    document="doc.htm", section="Financial Highlights", quote=quote, row_label=label,
                    char_offset=offset, find_match=text.count(phrase, 0, offset + len(phrase)),
                    find_total=text.count(phrase))


def _fragment(url):
    assert "#:~:text=" in url, url
    return unquote(url.split("#:~:text=", 1)[1])


def _table(label, value):
    return f"<table><tr><td>{label}</td><td>$ {value}</td></tr></table>"


def test_unique_label_gets_a_fragment_on_the_label(tmp_path):
    path, text = _doc(tmp_path, "<p>Financial Highlights</p>" + _table(NAV, "8.32"))
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32")
    url, hint = links.deep_link(cit, path)
    assert _fragment(url) == NAV and url.startswith(DOC_URL) and hint == ""


def test_narrative_quote_gets_the_shortest_unique_start_of_its_sentence(tmp_path):
    path, text = _doc(tmp_path, "<p>As of December 31, 2024, asset coverage was 210%.</p>"
                                "<p>As of December 31, 2025, asset coverage was 250%.</p>")
    cit = _row_citation(text, None, "As of December 31, 2025, asset coverage was 250%.")
    url, hint = links.deep_link(cit, path)
    fragment = _fragment(url)
    assert text.lower().count(fragment.lower()) == 1 and fragment.startswith("As of December 31, 2025")


def test_repeated_label_links_to_the_nearest_unique_heading_before_it(tmp_path):
    # Same numbers in both class tables, so no cell of the cited row is unique either.
    body = ("<p>Class A Shares</p>" + _table(NAV, "8.32") +
            "<p>Class I Shares</p>" + _table(NAV, "8.32"))
    path, text = _doc(tmp_path, body)
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32", nth=2)
    url, hint = links.deep_link(cit, path)
    assert _fragment(url) == "Class I Shares"
    assert hint == f"search “{NAV}”: match 2 of 2"


def test_a_unique_cell_of_the_cited_row_beats_a_heading(tmp_path):
    body = ("<p>Class A Shares</p>" + _table(NAV, "8.30") +
            "<p>Class I Shares</p>" + _table(NAV, "8.32"))
    path, text = _doc(tmp_path, body)
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32")
    url, hint = links.deep_link(cit, path)
    assert _fragment(url) == "$ 8.32" and hint == f"search “{NAV}”: match 2 of 2"


def test_fallback_never_lands_before_the_previous_copy_of_the_label(tmp_path):
    # "Class A Shares" is unique, but landing there would make the reader's next match the Class A row
    # (the decision 34 failure). Nothing unique sits between the two rows, so the link stays plain.
    body = "<p>Class A Shares</p>" + _table(NAV, "8.32") + _table(NAV, "8.32")
    path, text = _doc(tmp_path, body)
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32", nth=2)
    url, hint = links.deep_link(cit, path)
    assert url == DOC_URL and f"match 2 of 2" in hint


def test_fragment_never_runs_into_the_next_cell(tmp_path):
    # "Net Assets" repeats, and "Net Assets $ 100" is unique only by crossing into the number cell,
    # which a browser cannot match. The number cell alone is unique, so the link lands on it.
    body = "<p>Net Assets grew.</p><p>Statement of Assets and Liabilities</p>" + _table("Net Assets", "100")
    path, text = _doc(tmp_path, body)
    cit = _row_citation(text, "Net Assets", "Net Assets $ 100")
    url, hint = links.deep_link(cit, path)
    assert _fragment(url) == "$ 100"
    assert hint == "search “Net Assets”: match 2 of 2"


def test_hint_counts_ignore_case_like_a_browser_find(tmp_path):
    path, text = _doc(tmp_path, "<p>Book value per share rose.</p><p>Caption</p>" + _table("Book Value per Share", "13.04")
                      + "<p>book value per share fell.</p>")
    cit = _row_citation(text, "Book Value per Share", "Book Value per Share $ 13.04")
    url, hint = links.deep_link(cit, path)
    assert hint == "search “Book Value per Share”: match 2 of 3"


def test_curly_quote_label_is_not_used_but_a_straight_one_on_the_page_is(tmp_path):
    # Our normalizer turns curly quotes into straight ones, so a fragment with ' might not match the page,
    # unless the page itself has the straight quote.
    curly = "Total Stockholders\u2019 Equity"
    path, text = _doc(tmp_path, "<p>Balance Sheet</p>" + _table(curly, "1,172") + _table("Total", "1,172"))
    label = "Total Stockholders' Equity"
    cit = _row_citation(text, label, f"{label} $ 1,172")
    url, _ = links.deep_link(cit, path)
    assert _fragment(url) == "Balance Sheet"

    path, text = _doc(tmp_path, "<p>Balance Sheet</p>" + _table(label, "1,172"))
    cit = _row_citation(text, label, f"{label} $ 1,172")
    url, _ = links.deep_link(cit, path)
    assert _fragment(url) == label


def test_nothing_unique_gives_the_plain_url_and_says_so(tmp_path):
    path, text = _doc(tmp_path, _table(NAV, "8.32") + _table(NAV, "8.32"))
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32", nth=2)
    url, hint = links.deep_link(cit, path)
    assert url == DOC_URL
    assert "top of the filing" in hint and f"search “{NAV}”: match 2 of 2" in hint


def test_client_data_existing_fragments_and_non_https_are_left_alone(tmp_path):
    path, text = _doc(tmp_path, _table(NAV, "8.32"))
    cit = _row_citation(text, NAV, f"{NAV} $ 8.32")
    for url in (DOC_URL + "#:~:text=already", "http://example.com/doc.htm"):
        cit.url = url
        assert links.deep_link(cit, path) == (url, "")
    client = Citation(cik="client", form="CSV", accession="client", url="apex_ridge_fund_data.csv",
                      document="apex_ridge_fund_data.csv", section="row", quote="x")
    assert links.deep_link(client, path) == (client.url, "")


def _all_citations(bundle):
    for row in bundle.table.values():
        for record in row.values():
            if record.citation:
                yield record.citation
            for item in record.inputs + record.candidates:
                yield item.citation
    for points in bundle.trend.values():
        for point in points:
            if point.citation:
                yield point.citation


def test_every_exported_competitor_link_lands_on_text_that_occurs_once(tmp_path):
    bundle, cache = make_bundle(tmp_path)
    links.apply_deep_links(bundle, cache)
    checked = 0
    for cit in _all_citations(bundle):
        if cit.cik == "client" or "#:~:text=" not in cit.url:
            continue
        text = textnorm.document_text(cache.path(cit.cik, cit.accession, cit.document)).lower()
        assert text.count(_fragment(cit.url).lower()) == 1, (cit.document, cit.url)
        checked += 1
    assert checked > 20


def test_every_quoted_competitor_citation_gets_a_fragment(tmp_path):
    # In the real-filing fixtures something unique is always within reach; a plain link would be a regression.
    bundle, cache = make_bundle(tmp_path)
    links.apply_deep_links(bundle, cache)
    plain = [(c.document, c.row_label) for c in _all_citations(bundle)
             if c.cik != "client" and c.quote and cache.path(c.cik, c.accession, c.document).exists()
             and "#" not in c.url]
    assert plain == []


def test_every_exported_link_from_a_run_lands_on_cached_text(tmp_path):
    """The run itself applies deep links: every competitor link in the saved bundle (cells, inputs,
    conflict candidates, trend points) carries a fragment whose text is in the cached filing, except
    citations with nothing quoted, which stay plain."""
    from urllib.parse import unquote
    from benchmark import textnorm
    from tests.test_pipeline import make_bundle
    bundle, cache = make_bundle(tmp_path)
    cits = []
    for row in bundle.table.values():
        for rec in row.values():
            cits += ([rec.citation] if rec.citation else []) + [c.citation for c in rec.inputs + rec.candidates]
    cits += [p.citation for pts in bundle.trend.values() for p in pts if p.citation]
    checked = 0
    for c in cits:
        if c.cik == "client" or "#:~:text=" not in c.url:
            continue
        text = unquote(c.url.split("#:~:text=")[1].split(",")[0])
        doc = textnorm.document_text(cache.path(c.cik, c.accession, c.document)).lower()
        assert text.lower() in doc, (c.accession, text)
        checked += 1
    assert checked >= 30
