"""The judge page's first screen, in both languages.

Step 4's acceptance criteria, executable. The failure these pin down is a real
one that shipped: at 1280 x 720 — the common judging laptop — the scenario and
its primary action sat below the fold, so the first thing a reviewer had to do
was scroll to find out what they were looking at.

Measured against layout, not against copy. Nothing here asserts a sentence, a
pixel-perfect snapshot, or a screenshot diff: those break on every wording
change and prove nothing about whether the page can be used.
"""

from __future__ import annotations

import pytest

from tests.browser.test_surfaces import LOCALES, open_page, ready_for_demo

# The two the guide names, plus the 768-high laptop that is just as common and
# is the tighter of the two.
DESKTOP = [(1280, 720), (1366, 768), (1440, 900)]


def _bottom(page, selector: str) -> float:
    box = page.locator(selector).bounding_box()
    assert box is not None, f"{selector} has no box"
    return box["y"] + box["height"]


def _overflows_horizontally(page) -> bool:
    # +1 for sub-pixel rounding; a genuine overflow is never one pixel.
    return page.evaluate(
        "() => document.documentElement.scrollWidth"
        " > document.documentElement.clientWidth + 1"
    )


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("width,height", DESKTOP)
def test_the_scenario_and_its_primary_action_are_on_the_first_screen(
    page, server, locale, width, height
):
    """Both, without scrolling and without opening anything.

    Parametrised over Arabic as well as English on purpose: Arabic wraps the
    hero and the merchant copy to more lines, so a layout tuned until English
    fitted would fit only English.
    """
    open_page(page, server, "/judge", locale, width, height)
    ready_for_demo(page, server, "/judge")

    assert page.locator("#customerTitle").is_visible()
    # The page's primary action is now the paired evidence-source run: a judge
    # chooses Mock or Real NaC and presses this. The custom mock stories moved
    # below it and became secondary, so this test follows the primary action
    # rather than the button id it used to be attached to — the guarantee is
    # "the thing a reviewer is meant to press is on the first screen", and that
    # is what is asserted, along with the choice it depends on.
    assert page.locator("#evidenceSource").is_visible()
    assert _bottom(page, "#runPaired") <= height, (
        f"the primary action ends below the fold at {width}x{height} ({locale})"
    )
    # And it is genuinely reachable, not merely positioned: a disabled or
    # covered button that happens to be above the fold is not an action.
    assert page.locator("#runPaired").is_enabled()
    # Both sources are visible without opening anything, and mock is preselected.
    assert page.locator("#esMock").is_checked()
    assert page.locator("#esReal").is_visible()


@pytest.mark.parametrize("locale", LOCALES)
@pytest.mark.parametrize("width,height", [(375, 812), (320, 640), (768, 1024)])
def test_no_narrow_or_tablet_width_overflows_the_page_sideways(
    page, server, locale, width, height
):
    open_page(page, server, "/judge", locale, width, height)
    ready_for_demo(page, server, "/judge")
    assert not _overflows_horizontally(page), f"{width}x{height} ({locale}) scrolls sideways"


@pytest.mark.parametrize("locale", LOCALES)
def test_a_phone_reaches_the_primary_action_within_one_screen_of_scrolling(
    page, server, locale
):
    open_page(page, server, "/judge", locale, 375, 812)
    ready_for_demo(page, server, "/judge")
    assert _bottom(page, "#runPaired") <= 812 * 2, "more than one screen of scrolling"
    # The secondary custom stories may sit lower, but not out of reach.
    assert _bottom(page, "#checkout") <= 812 * 3


@pytest.mark.parametrize("locale", LOCALES)
def test_two_hundred_percent_zoom_still_does_not_overflow_sideways(
    page, server, locale
):
    """Doubling the text size is the accessibility case, and it is the one that
    breaks a layout tuned by eye at one size."""
    open_page(page, server, "/judge", locale, 1280, 720)
    ready_for_demo(page, server, "/judge")
    page.evaluate("() => { document.documentElement.style.fontSize = '200%'; }")
    page.wait_for_timeout(150)
    try:
        assert not _overflows_horizontally(page)
    finally:
        page.evaluate("() => { document.documentElement.style.fontSize = ''; }")


@pytest.mark.parametrize("locale", LOCALES)
def test_the_demo_settings_are_collapsed_but_reachable_from_the_keyboard(
    page, server, locale
):
    """Planner and key entry are behind a disclosure now. Behind is fine;
    unreachable without a mouse is not."""
    open_page(page, server, "/judge", locale, 1280, 720)
    ready_for_demo(page, server, "/judge")

    assert page.evaluate("() => document.getElementById('demoSettings').open") is False
    summary = page.locator("#demoSettings > summary")
    summary.focus()
    # A focused control has to be visibly focused.
    assert page.evaluate(
        "() => document.activeElement === document.querySelector('#demoSettings > summary')"
    )
    page.keyboard.press("Enter")
    assert page.evaluate("() => document.getElementById('demoSettings').open") is True
    assert page.locator("#plannerChoice").is_visible()
    assert page.locator("#byok").is_visible()


@pytest.mark.parametrize("locale", LOCALES)
def test_the_running_planner_and_the_evidence_source_are_named_without_opening_anything(
    page, server, locale
):
    """The disclosure hides the controls, never the facts. A reader must be
    able to see which planner is actually selecting and that the operator
    answers are simulated, without touching a thing."""
    open_page(page, server, "/judge", locale, 1280, 720)
    ready_for_demo(page, server, "/judge")

    mode = page.locator("#mode")
    planner = page.locator("#planner")
    assert mode.is_visible() and planner.is_visible()

    # The provenance is carried by the class as well as by the sentence, so it
    # survives translation and does not depend on colour alone.
    assert "sim" in (mode.get_attribute("class") or "").split()
    assert mode.inner_text().strip() != ""
    if locale == "en":
        assert "SIMULATOR" in mode.inner_text().upper()

    # The planner name is an identifier, not prose: it keeps its exact value in
    # both languages, because it is the value a signed verdict also carries.
    assert any(name in planner.inner_text() for name in ("greedy", "llm", "policy"))


def test_the_network_conditions_panel_is_no_longer_on_this_page(page, server):
    """It moved to /console. If the markup were removed without removing the
    listeners that were bound to it at module load, this page would throw on
    load and nothing below would work at all — so the second half of this test
    is the one that matters."""
    open_page(page, server, "/judge", "en", 1280, 720)
    ready_for_demo(page, server, "/judge")

    assert page.locator("#ncSubscribe").count() == 0
    assert page.locator(".network-conditions").count() == 0
    # The page still runs: its own controls are wired and its config call ran.
    assert page.locator("#checkout").is_enabled()
    assert "checking environment" not in page.locator("#mode").inner_text()


def test_the_network_conditions_panel_is_on_the_console_and_asks_nothing_on_load(
    page, server
):
    calls: list[str] = []
    page.on(
        "request",
        lambda r: calls.append(r.url) if "/v1/network-conditions" in r.url else None,
    )
    open_page(page, server, "/console", "en", 1440, 900)
    page.wait_for_selector("#ncSubscribe", timeout=15000)
    page.wait_for_timeout(600)

    assert calls == [], "the panel requested something on load"
    assert page.locator("#ncForecast").is_disabled()
    assert page.locator("#ncDelete").is_disabled()


@pytest.mark.parametrize("locale", LOCALES)
def test_the_result_reads_before_the_technical_detail(page, server, locale):
    """Result, one short reason, then the merchant's next action — and the
    thresholds, exact score and chain grade still available, just not first."""
    open_page(page, server, "/judge", locale, 1440, 900)
    ready_for_demo(page, server, "/judge")
    page.click("#checkout")
    page.wait_for_function(
        "() => { const d = document.getElementById('presentationTitle');"
        " return d && d.textContent.trim() && d.textContent !== 'VERIFYING'; }",
        timeout=30000,
    )

    def top(selector):
        box = page.locator(selector).bounding_box()
        assert box is not None, selector
        return box["y"]

    assert top("#presentationTitle") < top("#presentationSummary")
    assert top("#presentationSummary") < top("#presentationAction")
    assert top("#presentationAction") < top(".audit")

    # The audit block is collapsed, and opening it is what reveals the score.
    assert page.evaluate("() => document.querySelector('.audit').open") is False
    page.locator(".audit summary").click()
    assert page.locator("#grade").inner_text().strip() != ""
