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
SWITCH_JS = Path("app/static/i18n.js").read_text(encoding="utf-8")


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


# --- the shared locale switch (I6 steps 1-2) ----------------------------------
#
# One implementation, served from /ui/i18n.js and used by every page that has
# a language control. Two copies of the fallback rule would be two chances for
# one page to quietly start showing a blank or a raw key.


def test_the_switch_is_served_same_origin_and_is_javascript():
    response = client.get("/ui/i18n.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]
    assert response.text == SWITCH_JS


def test_the_switch_offers_exactly_the_supported_locales():
    assert "const SUPPORTED = ['en', 'ar'];" in SWITCH_JS
    # And it can only ever ask for one of them.
    assert re.search(r"SUPPORTED\.includes\(requested\)", SWITCH_JS)


def test_the_switch_sets_lang_and_direction_together():
    assert "document.documentElement.lang = activeLocale;" in SWITCH_JS
    assert "document.documentElement.dir = activeLocale === 'ar' ? 'rtl' : 'ltr';" in SWITCH_JS


def test_only_the_locale_preference_is_persisted():
    """Nothing about what the reader was looking at — no chain id, no verdict,
    no bytes — is written to their browser."""
    for name, source in (("i18n.js", SWITCH_JS), ("receipt.html", RECEIPT_SCRIPT)):
        stored = re.findall(r"localStorage\.setItem\(([^)]*)\)", source)
        assert stored in ([], ["LOCALE_KEY, activeLocale"]), name


def test_an_unknown_key_falls_back_to_english_visibly():
    """A missing translation must show the English sentence, never a raw key
    and never a blank — and must be marked so it does not read as deliberate."""
    assert "lookup(dicts.en, path)" in SWITCH_JS
    assert "el.setAttribute('lang', 'en')" in SWITCH_JS
    assert '[dir="rtl"] [lang="en"]' in RECEIPT_HTML
    # And the English dictionary is loaded whatever the reader chose, or there
    # would be nothing to fall back *to* on an Arabic-first page load.
    assert "[loadDictionary('en'), loadDictionary(locale)]" in SWITCH_JS


def test_a_draft_translation_says_so_on_the_page():
    """The Arabic dictionary is machine-assisted and unreviewed; a reader of
    the page, not only of the JSON file, has to be told."""
    assert "review_status" in SWITCH_JS
    assert "Locale.reviewStatus()" in RECEIPT_SCRIPT
    assert 'id="draftNote"' in RECEIPT_HTML


def test_signed_values_are_shown_as_signed_never_replaced_by_a_translation():
    """The translation is a gloss beside the signed token. Replacing CHALLENGE
    with an Arabic phrase would mean the receipt no longer displays the value
    the signature covers."""
    assert "el.replaceChildren(isolate(code));" in SWITCH_JS
    assert "el.appendChild(gloss);" in SWITCH_JS
    assert "Locale.codedInto($('decision'), signed.decision, 'decision');" in RECEIPT_SCRIPT


def test_identifiers_and_numbers_are_bidi_isolated():
    """Chain ids, hex keys, ISO timestamps, API names and signed numbers are
    reordered at their neutral edges by an RTL page unless isolated."""
    assert '<bdi id="chainId" dir="ltr">' in RECEIPT_HTML
    assert "bdi.dir = 'ltr';" in SWITCH_JS
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
    receipt_urls = re.findall(r"fetch\((`[^`]*`)", RECEIPT_SCRIPT)
    switch_urls = re.findall(r"fetch\((`[^`]*`)", SWITCH_JS)
    assert [u for u in receipt_urls if "locale" in u] == []
    assert [u for u in switch_urls if "locale" in u] == ["`/ui/i18n/${locale}.json`"]
    assert "`/v1/receipts/${encodeURIComponent(chainId)}`" in receipt_urls


def test_a_page_still_verifies_when_the_switch_fails_to_load():
    """Verification is what the receipt is *for*. An unreachable presentation
    module must not leave a reader unable to check a signature."""
    assert "typeof Isnad !== 'undefined'" in RECEIPT_SCRIPT
    # Every call site goes through the guarded reference, never the raw global.
    body = RECEIPT_SCRIPT.split("let signedState = null;")[1]
    assert "Isnad." not in body


def test_the_pages_load_the_switch_from_this_origin_only():
    """Zero external origins is the rule these pages keep; a shared module
    must not be the thing that breaks it."""
    for html in (RECEIPT_HTML,):
        assert '<script src="/ui/i18n.js"></script>' in html
        assert re.findall(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', html) == []


def test_the_verdict_is_never_encoded_in_colour_alone():
    """A reader who cannot distinguish the green from the red must still get
    the answer: every signature state carries a glyph and a sentence."""
    assert "ok ? '✓ ' : '✗ '" in RECEIPT_SCRIPT
    assert "ui.signature_valid" in RECEIPT_SCRIPT
    assert "ui.signature_invalid" in RECEIPT_SCRIPT
