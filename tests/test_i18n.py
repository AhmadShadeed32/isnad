"""I6 — locale dictionaries served through one explicit, allowlisted route.

Locale is UI-only: it must never reach a verification request commitment or
a policy decision, and the route must never interpolate an arbitrary path.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

RECEIPT_HTML = Path("app/static/receipt.html").read_text(encoding="utf-8")
RECEIPT_SCRIPT = RECEIPT_HTML.split("<script>")[-1].split("</script>")[0]


def test_english_dictionary_loads():
    response = client.get("/ui/i18n/en.json")
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "en"
    assert body["decision"]["CHALLENGE"] == "Additional verification needed"


def test_arabic_dictionary_loads_and_is_marked_draft():
    response = client.get("/ui/i18n/ar.json")
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "ar"
    assert "review_status" in body, "an unreviewed translation must say so"


def test_an_unlisted_locale_is_rejected():
    response = client.get("/ui/i18n/fr.json")
    assert response.status_code in (404, 422)


def test_a_path_traversal_attempt_is_rejected_not_resolved():
    response = client.get("/ui/i18n/..%2f..%2fapp%2fconfig.json")
    assert response.status_code in (404, 400)


def test_both_dictionaries_share_the_same_keys():
    en = client.get("/ui/i18n/en.json").json()
    ar = client.get("/ui/i18n/ar.json").json()
    assert set(en["decision"]) == set(ar["decision"])
    assert set(en["chain_grade"]) == set(ar["chain_grade"])
    assert set(en["ui"]) == set(ar["ui"])


# --- the receipt page's switcher (I6 steps 1-2) -------------------------------


def test_the_receipt_page_offers_exactly_the_supported_locales():
    assert 'id="locale"' in RECEIPT_HTML
    assert "const SUPPORTED = ['en', 'ar'];" in RECEIPT_SCRIPT
    # And it can only ever ask for one of them.
    assert re.search(r"SUPPORTED\.includes\(requested\)", RECEIPT_SCRIPT)


def test_the_page_sets_lang_and_direction_together():
    assert "document.documentElement.lang = activeLocale;" in RECEIPT_SCRIPT
    assert "document.documentElement.dir = activeLocale === 'ar' ? 'rtl' : 'ltr';" in RECEIPT_SCRIPT


def test_the_page_persists_only_the_locale_preference():
    """Nothing about the receipt itself — no chain id, no verdict, no bytes —
    is written to this reader's browser."""
    stored = re.findall(r"localStorage\.setItem\(([^)]*)\)", RECEIPT_SCRIPT)
    assert stored == ["LOCALE_KEY, activeLocale"]


def test_an_unknown_key_falls_back_to_english_visibly():
    """A missing translation must show the English sentence, never a raw key
    and never a blank — and must be marked so it does not read as deliberate."""
    assert "lookup(dicts.en, path)" in RECEIPT_SCRIPT
    assert "el.setAttribute('lang', 'en')" in RECEIPT_SCRIPT
    assert '[dir="rtl"] [lang="en"]' in RECEIPT_HTML
    # And the English dictionary is loaded whatever the reader chose, or there
    # would be nothing to fall back *to* on an Arabic-first page load.
    assert "[loadDictionary('en'), loadDictionary(locale)]" in RECEIPT_SCRIPT


def test_a_draft_translation_says_so_on_the_page():
    """The Arabic dictionary is machine-assisted and unreviewed; a reader of
    the page, not only of the JSON file, has to be told."""
    assert "review_status" in RECEIPT_SCRIPT
    assert 'id="draftNote"' in RECEIPT_HTML


def test_signed_values_are_shown_as_signed_never_replaced_by_a_translation():
    """The translation is a gloss beside the signed token. Replacing CHALLENGE
    with an Arabic phrase would mean the receipt no longer displays the value
    the signature covers."""
    assert "isolated.textContent = code;" in RECEIPT_SCRIPT
    assert "el.appendChild(gloss);" in RECEIPT_SCRIPT


def test_identifiers_and_numbers_are_bidi_isolated():
    """Chain ids, hex keys, ISO timestamps, API names and signed numbers are
    reordered at their neutral edges by an RTL page unless isolated."""
    assert '<bdi id="chainId" dir="ltr">' in RECEIPT_HTML
    assert "function setIsolated(" in RECEIPT_SCRIPT
    for field in ("publicKey", "signature", "signedAt", "confidence", "mTotal"):
        assert f"setIsolated('{field}'" in RECEIPT_SCRIPT


def test_the_page_uses_logical_properties_so_a_flip_needs_no_extra_rules():
    style = RECEIPT_HTML.split("<style>")[-1].split("</style>")[0]
    assert "text-align:start" in style
    assert "margin-block-end" in style
    # A physical left/right rule would not follow dir="rtl".
    assert "text-align:left" not in style.replace("th{text-align:left", "")


def test_locale_never_reaches_a_verification_request():
    """I6 step 1's hard rule: locale is UI-only. The only request that may
    carry it is the dictionary read itself."""
    # Match the whole template literal each fetch is given, so a locale
    # smuggled into a later path segment or query string is caught too. A
    # naive `[^)]*` would stop at the ) inside encodeURIComponent(chainId).
    urls = re.findall(r"fetch\((`[^`]*`)", RECEIPT_SCRIPT)
    assert urls, "the page must still fetch something"
    assert [u for u in urls if "locale" in u] == ["`/ui/i18n/${locale}.json`"]
    assert "`/v1/receipts/${encodeURIComponent(chainId)}`" in urls


def test_the_verdict_is_never_encoded_in_colour_alone():
    """A reader who cannot distinguish the green from the red must still get
    the answer: every signature state carries a glyph and a sentence."""
    assert "ok ? '✓ ' : '✗ '" in RECEIPT_SCRIPT
    assert "ui.signature_valid" in RECEIPT_SCRIPT
    assert "ui.signature_invalid" in RECEIPT_SCRIPT
