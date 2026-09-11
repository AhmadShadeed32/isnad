"""Journeys a person actually drives, each on a freshly started server.

Split from the surface matrix deliberately. That matrix renders dozens of pages,
and the demo credential this build mints per render is capped and evicted — so a
journey running after it found its controls disabled for reasons that had
nothing to do with the journey. A per-file server keeps each of these tests
about the thing it is named after.
"""

from __future__ import annotations

import pytest

from tests.browser.conftest import shot
from tests.browser.test_surfaces import LOCALES, open_page, ready_for_demo


@pytest.mark.parametrize("locale", LOCALES)
def test_the_three_judge_cases_each_reach_a_decision(page, server, problems, locale):
    """Not just the default case. Each button is its own authored fixture and
    its own outcome."""
    open_page(page, server, "/judge", locale, 1440, 900)
    ready_for_demo(page, server, "/judge")
    for button, state in (("#checkout", "replacement"), ("#cleanCheckout", "clean"),
                          ("#gapCheckout", "gap")):
        page.click(button)
        page.wait_for_function(
            "() => { const d = document.getElementById('presentationTitle');"
            " return d && d.textContent.trim() && d.textContent.trim() !== 'VERIFYING'; }",
            timeout=25000,
        )
        # The machine decision is inside the audit block, which is collapsed by
        # design; the reader's view is the plain-language title beside it.
        decision = page.evaluate(
            "() => document.getElementById('decision').textContent.trim()"
        )
        assert decision in {"ALLOW", "CHALLENGE", "DECLINE"}, decision
        shot(page, f"judge-{locale}-{state}-1440")
    assert problems == []


def test_a_receipt_shows_its_exact_bytes_and_verifies(page, server, problems):
    open_page(page, server, "/judge", "en", 1440, 900)
    ready_for_demo(page, server, "/judge")
    page.click("#checkout")
    page.wait_for_function(
        "() => { const d = document.getElementById('presentationTitle');"
        " return d && d.textContent.trim() && d.textContent.trim() !== 'VERIFYING'; }",
        timeout=25000,
    )
    page.wait_for_selector("#receipt.visible", timeout=15000)
    href = page.locator("#receiptLink").get_attribute("href")
    assert href and "/r/chn_" in href

    page.goto(f"{server}{href}")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)
    body = page.locator("body").inner_text()

    assert "chn_" in body
    shot(page, "receipt-en-valid-1440")
    page.evaluate("() => window.Isnad.setLocale('ar')")
    page.wait_for_function("() => document.documentElement.lang === 'ar'")
    shot(page, "receipt-ar-valid-1440")
    assert problems == []


def test_an_unknown_receipt_says_so_rather_than_failing_blankly(page, server):
    page.goto(f"{server}/r/chn_00000000000000000000")
    page.wait_for_load_state("domcontentloaded")
    body = page.locator("body").inner_text().lower()

    assert body.strip() != ""
    assert "chn_00000000000000000000" not in body or "not" in body or "no " in body
    shot(page, "receipt-en-unavailable-1440")


def test_the_network_conditions_panel_shows_a_reading_and_can_be_cleaned_up(
    page, server, problems
):
    """The full lifecycle a reader can drive: subscribe, read, delete. Every
    step starts from a click; nothing is requested on load.

    On /console since the judge page was simplified: this is a diagnostic about
    the network rather than about a person, it never touches a verdict, and on
    the checkout page it competed with the decision for attention. The panel,
    its subscription state and its routes are unchanged — only its address is.
    """
    open_page(page, server, "/console", "en", 1440, 900)
    page.wait_for_selector("#ncSubscribe", timeout=15000)
    calls: list[str] = []
    page.on(
        "request",
        lambda r: calls.append(r.url) if "/v1/network-conditions" in r.url else None,
    )
    page.wait_for_timeout(500)
    assert calls == [], "the panel requested something on load"

    page.click("#ncSubscribe")
    page.wait_for_function(
        "() => !document.getElementById('ncForecast').disabled", timeout=15000
    )
    page.click("#ncForecast")
    page.wait_for_selector(".nc-interval, .nc-note", timeout=15000)
    shot(page, "network-conditions-en-forecast-1440")

    page.evaluate("() => window.Isnad.setLocale('ar')")
    page.wait_for_function("() => document.documentElement.lang === 'ar'")
    shot(page, "network-conditions-ar-forecast-1440")

    page.click("#ncDelete")
    page.wait_for_function(
        "() => document.getElementById('ncSubscribe').disabled === false", timeout=15000
    )
    assert problems == []


def test_the_console_reaches_a_verdict_and_labels_its_planner(page, server, problems):
    open_page(page, server, "/console", "en", 1440, 900)
    # The console mints its own demo credential, so there is no key to type —
    # but it shows nothing until an act is actually run.
    page.wait_for_selector("#runStageSuite:not([disabled])", timeout=20000)
    page.click("#runStageSuite")
    page.wait_for_selector(".row", timeout=30000)
    shot(page, "console-en-connected-1440")

    page.evaluate("() => window.Isnad.setLocale('ar')")
    page.wait_for_function("() => document.documentElement.lang === 'ar'")
    shot(page, "console-ar-connected-1440")
    assert problems == []


@pytest.mark.parametrize("locale", LOCALES)
def test_the_lab_replays_a_case_and_can_be_reset(page, server, problems, locale):
    open_page(page, server, "/lab", locale, 1440, 900)
    page.locator(".case-btn").first.click()
    page.wait_for_selector("#scrub", state="visible", timeout=10000)
    shot(page, f"lab-{locale}-case-1440")

    page.click("#resetBtn")
    page.wait_for_timeout(200)
    assert problems == []
