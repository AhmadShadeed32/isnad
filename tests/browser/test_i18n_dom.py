"""Bilingual behaviour in a real browser, not in source strings.

`tests/test_i18n.py` asserts that the dictionaries exist and that the pages load
the switch. None of that answers the questions a reader would notice first: does
a result that rendered in English become Arabic when they switch, does a signed
value survive the switch unchanged, and does switching cost an API call.
"""

from __future__ import annotations

import pytest

from tests.browser.conftest import shot


def switch(page, locale: str) -> None:
    page.evaluate("locale => window.Isnad.setLocale(locale)", locale)
    page.wait_for_function("locale => document.documentElement.lang === locale", arg=locale)


def test_switching_sets_language_and_direction_together(judge, problems):
    switch(judge, "ar")

    assert judge.locator("html").get_attribute("lang") == "ar"
    assert judge.locator("html").get_attribute("dir") == "rtl"
    switch(judge, "en")
    assert judge.locator("html").get_attribute("dir") == "ltr"
    assert problems == []


def test_the_newest_request_wins_a_race(judge, problems):
    """Three switches fired without waiting. The last one asked for is the one
    the reader gets — an earlier dictionary resolving late must not repaint."""
    judge.evaluate(
        "() => { window.Isnad.setLocale('ar');"
        " window.Isnad.setLocale('en');"
        " window.Isnad.setLocale('ar'); }"
    )
    judge.wait_for_function("() => document.documentElement.lang === 'ar'")
    judge.wait_for_timeout(400)

    assert judge.locator("html").get_attribute("lang") == "ar"
    assert judge.locator("html").get_attribute("dir") == "rtl"
    assert problems == []


def test_a_result_rendered_in_english_becomes_arabic_when_the_reader_switches(judge, problems):
    """The case source-string tests cannot reach. A row written straight into
    textContent at insertion time never changes again."""
    judge.click("#checkout")
    judge.wait_for_selector(".trace-row", timeout=20000)
    judge.wait_for_function(
        "() => document.getElementById('decision').textContent.trim() !== 'VERIFYING'",
        timeout=20000,
    )
    # The result itself and a row inserted while the page was in English. The
    # network-conditions panel used to stand in for this; it lives on /console
    # now, and the decision is the better subject anyway — it is the sentence a
    # reader is actually here for.
    english = judge.locator("#presentationTitle").inner_text()
    english_rows = judge.locator(".trace-row .trace-title").all_inner_texts()
    assert english_rows

    switch(judge, "ar")
    arabic = judge.locator("#presentationTitle").inner_text()

    assert english != arabic
    assert arabic.strip() == "يلزم تحقق إضافي"
    # And the rows written into the DOM while the page was English followed.
    assert judge.locator(".trace-row .trace-title").all_inner_texts() != english_rows
    assert problems == []
    shot(judge, "judge-ar-after-checkout-1440")


def test_a_failed_dictionary_leaves_the_page_english_and_working(page, server):
    """A dictionary that will not load must degrade to readable English, not to
    raw keys, a blank page or a thrown error."""
    problems: list[str] = []
    # The aborted fetch itself is logged by the browser and is the thing being
    # simulated. What must not appear is an unhandled exception from our code.
    page.on(
        "console",
        lambda m: problems.append(m.text)
        if m.type == "error" and "Failed to load resource" not in m.text
        else None,
    )
    page.on("pageerror", lambda e: problems.append(str(e)))
    page.route("**/ui/i18n/ar.json", lambda route: route.abort())
    page.goto(f"{server}/judge")
    page.wait_for_function("() => window.Isnad !== undefined")

    page.evaluate("() => window.Isnad.setLocale('ar')")
    page.wait_for_timeout(500)

    assert page.locator("html").get_attribute("lang") == "en"
    # A `[data-i18n]` element that is on this page and visible. It used to be
    # the network-conditions heading, which moved to /console; the nav link is
    # the same kind of witness — authored copy the dictionary would have
    # replaced — and it is not going anywhere.
    keyed = page.locator('.site-nav a[data-i18n="ui.nav_console"]')
    assert "وحدة" not in keyed.inner_text()
    assert keyed.inner_text().strip() != ""
    # The page is still usable: the primary action has not been disabled by the
    # failure, and nothing threw.
    assert page.locator("#checkout").count() == 1
    assert problems == []


def test_the_choice_survives_a_reload(judge, server):
    switch(judge, "ar")
    judge.reload()
    judge.wait_for_function("() => document.documentElement.lang === 'ar'")

    assert judge.locator("html").get_attribute("dir") == "rtl"


def test_switching_preserves_input_value_and_focus(page, server):
    """A form value is state, not display text. The translator must not touch
    it, and the reader must not lose their place in the form."""
    page.goto(f"{server}/lab")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)
    # The scrub control only exists once a case is being replayed, which is the
    # state a reader would actually be in when they switch language.
    page.locator(".case-btn").first.click()
    scrub = page.locator("#scrub")
    scrub.wait_for(state="visible", timeout=10000)
    before_max = scrub.get_attribute("max")
    scrub.focus()
    page.keyboard.press("Home")
    before = scrub.input_value()

    page.evaluate("() => window.Isnad.setLocale('ar')")
    page.wait_for_function("() => document.documentElement.lang === 'ar'")
    page.wait_for_timeout(200)

    assert scrub.input_value() == before
    assert scrub.get_attribute("max") == before_max
    assert page.evaluate("() => document.activeElement.id") == "scrub"


def test_a_signed_payload_is_byte_identical_after_a_switch(judge, server, problems):
    """The receipt's bytes are what the signature covers. A translator that
    touched them would break every verification while looking like a UI change."""
    judge.click("#checkout")
    judge.wait_for_function(
        "() => document.getElementById('decision').textContent.trim() !== 'VERIFYING'",
        timeout=20000,
    )
    chain_id = judge.evaluate("() => window.latestChainId || null")
    if not chain_id:
        link = judge.locator("#receiptLink").get_attribute("href") or ""
        chain_id = link.rsplit("/", 1)[-1]
    assert chain_id and chain_id.startswith("chn_")

    judge.goto(f"{server}/r/{chain_id}")
    judge.wait_for_function("() => window.Isnad !== undefined")
    before = judge.locator("code, pre, bdi").first.inner_text()

    judge.evaluate("() => window.Isnad.setLocale('ar')")
    judge.wait_for_function("() => document.documentElement.lang === 'ar'")
    after = judge.locator("code, pre, bdi").first.inner_text()

    assert before == after
    assert problems == []


def test_a_locale_change_makes_no_api_request(judge):
    """Switching language is a rendering decision. It must not cost a call to
    this service, and certainly not to an operator."""
    calls: list[str] = []
    judge.on(
        "request",
        lambda request: calls.append(request.url) if "/v1/" in request.url else None,
    )
    switch(judge, "ar")
    switch(judge, "en")
    judge.wait_for_timeout(300)

    assert calls == []


def test_the_arabic_dictionary_still_says_it_is_a_draft(judge):
    """Human review stays pending until a human actually reviews it."""
    switch(judge, "ar")
    status = judge.evaluate("() => window.Isnad.reviewStatus()")

    assert status
    assert "مسودة" in status


@pytest.mark.parametrize("width,height,label", [(375, 812, "375"), (1440, 900, "1440")])
@pytest.mark.parametrize("locale", ["en", "ar"])
def test_no_page_wide_horizontal_overflow_in_either_language(page, server, width, height, label, locale):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(f"{server}/judge")
    page.wait_for_function("() => window.Isnad !== undefined")
    page.evaluate("locale => window.Isnad.setLocale(locale)", locale)
    page.wait_for_function("locale => document.documentElement.lang === locale", arg=locale)
    page.wait_for_timeout(200)

    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 1, f"{locale} at {label}px overflows by {overflow}px"
    shot(page, f"judge-{locale}-initial-{label}")
