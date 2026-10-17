"""Fee links land on the fee sentence (client, Window 3: "at most two scrolls away; fix any that land on page one").

The link is a URL text fragment (#:~:text=...) built only from text that occurs once in the document,
so the browser cannot jump to a different, earlier copy of the words.
"""
from pathlib import Path
from urllib.parse import unquote

import pytest

from benchmark import textnorm
from benchmark.config import FEE_SECTION
from benchmark.metrics import fees

FIXTURES = Path(__file__).parent / "fixtures"
DOC_URL = "https://www.sec.gov/Archives/edgar/data/1/000000000000000000/doc.htm"


def test_fragment_encoding_escapes_dash_comma_ampersand_and_spaces():
    assert fees.encode_fragment_text("fee-paying, A&B 1.00%") == "fee%2Dpaying%2C%20A%26B%201.00%25"


def test_unique_phrase_is_used_as_is():
    text = "Intro. The fee is 1.00% of net assets. Other text."
    offset = text.find("The fee is")
    assert fees.unique_fragment_text(text, offset, "The fee is") == "The fee is"


def test_repeated_phrase_is_extended_until_unique():
    text = "The fee is waived for May. Later: the fee is 1.00% of net assets."
    offset = text.rfind("the fee is")
    # Browsers match text fragments case-insensitively, so "The fee is" also counts as a copy.
    assert fees.unique_fragment_text(text, offset, "the fee is") == "the fee is 1.00%"


def test_no_fragment_when_uniqueness_cannot_be_reached():
    text = "the fee is 1% and more. the fee is 1% and more."
    assert fees.unique_fragment_text(text, text.rfind("the fee"), "the fee") is None


def test_extension_stops_at_characters_the_text_normalizer_may_have_changed():
    # A straight quote or hyphen in our text may be a curly quote or en dash on the page,
    # which the browser would not match, so the fragment never grows past one.
    text = "the fee is x. the fee is Fund's 1%."
    assert fees.unique_fragment_text(text, text.rfind("the fee"), "the fee") is None


def test_fragment_url_keeps_the_document_url():
    url = fees.fragment_url(DOC_URL, "The fee, 1%")
    assert url == DOC_URL + "#:~:text=The%20fee%2C%201%25"


def test_id_anchor_fallback_when_text_is_not_unique(tmp_path):
    html = ("<html><body><p>the fee is 1% and more.</p><div id='note5'><p>Note 5. Fees</p></div>"
            "<p>the fee is 1% and more.</p></body></html>")
    path = tmp_path / "doc.htm"
    path.write_text(html)
    text = textnorm.document_text(path)
    url, how = fees.landing_url(DOC_URL, path, text, text.rfind("the fee"), "the fee")
    assert url == DOC_URL + "#note5" and how == "anchor"


def test_plain_url_when_nothing_close_enough(tmp_path):
    html = "<html><body><p>the fee is 1%.</p><p>the fee is 1%.</p></body></html>"
    path = tmp_path / "doc.htm"
    path.write_text(html)
    text = textnorm.document_text(path)
    assert fees.landing_url(DOC_URL, path, text, text.rfind("the fee"), "the fee") == (DOC_URL, "plain")


@pytest.mark.parametrize("fund,fixture", [
    ("CCLFX", "cclfx_ncsrs_2025-09_full.html"), ("TAKIX", "takix_ncsr_2025_full.html"),
    ("GBDC", "gbdc_10q_2025-12_full.html"), ("KREF", "kref_10k_2025.html")])
def test_real_fee_sentences_get_a_unique_text_fragment(fund, fixture):
    path = FIXTURES / fixture
    text = textnorm.document_text(path)
    phrase = FEE_SECTION[fund]
    url, how = fees.landing_url(DOC_URL, path, text, text.find(phrase), phrase)
    assert how == "text_fragment" and url.startswith(DOC_URL + "#:~:text=")
    words = unquote(url.split("#:~:text=")[1])
    assert words.startswith(phrase) and text.lower().count(words.lower()) == 1
