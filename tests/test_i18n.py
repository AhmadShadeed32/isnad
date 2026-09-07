"""I6 — locale dictionaries served through one explicit, allowlisted route.

Locale is UI-only: it must never reach a verification request commitment or
a policy decision, and the route must never interpolate an arbitrary path.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.ui_source import read_ui_source

client = TestClient(app)

RECEIPT_HTML = read_ui_source(Path("app/static/receipt.html"))
RECEIPT_SCRIPT = RECEIPT_HTML.split("<script>")[-1].split("</script>")[0]
SWITCH_JS = Path("app/static/i18n.js").read_text(encoding="utf-8")
JUDGE_HTML = read_ui_source(Path("app/static/judge.html"))
JUDGE_SCRIPT = JUDGE_HTML.split("<script>")[-1].split("</script>")[0]


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
    assert "el.setAttribute('lang', fellBack ? 'en' : activeLocale);" in SWITCH_JS
    assert '[dir="rtl"] [lang="en"]' in RECEIPT_HTML
    assert '[dir="rtl"] [data-i18n][lang="en"]' in JUDGE_HTML
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


# --- the judge page's slice (I6 step 1) ---------------------------------------

def test_the_judge_page_loads_the_same_shared_switch():
    assert '<script src="/ui/i18n.js"></script>' in JUDGE_HTML
    assert re.findall(r'(?:src|href)\s*=\s*["\'](?:https?:)?//', JUDGE_HTML) == []


def test_the_judge_page_translates_only_dictionary_covered_labels():
    """The result narrative is written server-side by app/presentation.py in
    English. Re-keying it would mean translating provider provenance and signed
    vocabulary, which I6 forbids."""
    en = client.get("/ui/i18n/en.json").json()
    keys = set(re.findall(r'data-i18n="ui\.([a-z_]+)"', JUDGE_HTML))
    assert keys, "the judge page translates nothing"
    assert keys <= set(en["ui"]), f"untranslatable keys: {keys - set(en['ui'])}"


def test_the_judge_page_discloses_translation_review_status():
    assert 'id="localeNote"' in JUDGE_HTML
    assert "Locale.reviewStatus()" in JUDGE_SCRIPT


def test_the_judge_page_survives_the_switch_failing_to_load():
    assert "typeof Isnad !== 'undefined'" in JUDGE_SCRIPT
    assert "checkout demonstration must not be lost" in JUDGE_SCRIPT


def test_the_judge_signature_result_carries_a_glyph_and_a_sentence():
    """Never colour alone, and translated through the same dictionary keys the
    receipt uses so the two pages cannot disagree."""
    assert "lastSignatureOk ? '✓ ' : '✗ '" in JUDGE_SCRIPT
    assert "'ui.signature_valid' : 'ui.signature_invalid'" in JUDGE_SCRIPT


def test_the_judge_page_isolates_its_identifier_line():
    assert "gradeLine.dir = 'ltr';" in JUDGE_SCRIPT
    assert 'bdi{unicode-bidi:isolate}' in JUDGE_HTML


def test_the_judge_page_regions_inherit_the_selected_direction():
    for region in ('class="lead"', 'class="card checkout"', 'class="card journey"',
                   'class="proof"', 'class="technical"'):
        marked = JUDGE_HTML.split(region)[1].split(">")[0]
        assert 'dir="ltr"' not in marked, region


def test_a_translated_label_inside_an_english_region_states_its_own_direction():
    """Otherwise the Arabic label inherits dir="ltr" from the region around it."""
    for key in ("supporting_evidence", "adverse_evidence", "unresolved_checks"):
        block = JUDGE_HTML.split(f'data-i18n="ui.{key}"')[0].rsplit("<div", 1)[1]
        assert 'dir="auto"' in block, key


# --- keys that must not drift from the server's own copy ---------------------


def _ui(locale: str) -> dict:
    import json
    from pathlib import Path

    return json.loads(
        (Path("app/static/i18n") / f"{locale}.json").read_text(encoding="utf-8")
    )["ui"]


def test_the_english_decision_copy_matches_what_the_server_actually_sends():
    """The dictionary wins over the element's literal text, so an English value
    that drifts from `app/presentation.py` makes the screen say something the
    API did not."""
    from app.presentation import _NEXT_ACTION, _TITLE

    english = _ui("en")
    for decision, title in _TITLE.items():
        assert english[f"decision_title_{decision.value}"] == title
    for decision, action in _NEXT_ACTION.items():
        assert english[f"next_action_{decision.value}"] == action


def test_every_speakable_signal_has_copy_in_both_languages():
    """Evidence sentences are keyed on the signal, not on the sentence: the
    English detail interpolates a window that policy can change."""
    from app.providers.vocabulary import SPEAKABLE_SIGNALS

    english, arabic = _ui("en"), _ui("ar")
    missing = [
        signal
        for signal in sorted(SPEAKABLE_SIGNALS)
        if not english.get(f"signal_{signal}") or not arabic.get(f"signal_{signal}")
    ]

    assert missing == []


def test_no_arabic_value_is_left_as_its_english_source():
    """A key present in both files with the same value is an untranslated
    string wearing a translated file's name."""
    english, arabic = _ui("en"), _ui("ar")
    identical = [
        key
        for key, value in arabic.items()
        # Single words that are the same in both are possible; a whole sentence
        # being identical is not a translation.
        if english.get(key) == value and len(str(value).split()) > 2
    ]

    assert identical == []
