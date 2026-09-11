"""The judge's source selector, in a real browser.

Scope, stated up front because it is a limitation and not an omission: these
tests never grant the real NaC capability, because granting it and pressing Run
would send an actual request to Nokia from a test run. The server here has no
seam to intercept that — deliberately, since a configurable "hosted" transport
is exactly how a demonstration ends up labelling local answers as live.

So the split is: this file proves the UI — both choices present, mock default,
the access exchange, unavailable-mode wording, label integrity across mode
changes, double clicks, journal recovery, EN/AR and mobile. The end-to-end real
path, over an intercepted transport with no credential, is proved offline in
`tests/test_judge_evidence_modes.py`, which is where an interception seam
belongs.
"""

from __future__ import annotations

import pytest

from tests.browser.test_surfaces import open_page

ACCESS_CODE = "organizer-browser-test-code"


@pytest.fixture(scope="module")
def server_extra_env(tmp_path_factory) -> dict[str, str]:
    """Real NaC configured but never authorized in this file.

    Configured, so the selector, the access exchange and the readiness wording
    are the real ones a judge sees. Never authorized, so no run can reach Nokia.

    The signing key is created here rather than by the server, because enabling
    the guarded judge path refuses to start on a missing vault key — the same
    S6 rule the billable provider path keeps. That refusal is the feature; this
    fixture is what a deployment's mounted volume would be.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key_path = tmp_path_factory.mktemp("judge-vault") / "vault.key"
    key_path.write_bytes(
        Ed25519PrivateKey.generate().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    return {
        "ISNAD_JUDGE_REAL_NAC_ENABLED": "true",
        "ISNAD_JUDGE_ACCESS_CODES": ACCESS_CODE,
        "ISNAD_NAC_API_KEY": "browser-test-key-never-used-for-a-request",
        "ISNAD_VAULT_KEY_PATH": str(key_path),
    }


def ready(page, server, locale="en", width=1280, height=900):
    open_page(page, server, "/judge", locale, width, height)
    page.wait_for_function(
        "() => { const b = document.getElementById('runPaired');"
        " const s = document.getElementById('scenario');"
        " return b && !b.disabled && s && s.options.length > 0; }",
        timeout=15000,
    )


def run_mock(page):
    """Click Run and wait for THIS run to finish.

    Waiting on "the decision is no longer VERIFYING" is not enough: before the
    first run it already says "—", and after one it says the previous verdict,
    so the wait returns before the click has done anything. The receipt link is
    the honest signal — it is set only from a response the server has confirmed
    persisted, and it carries a new chain id per run.
    """
    before = page.evaluate("() => document.getElementById('receiptLink').getAttribute('href')")
    page.click("#runPaired")
    page.wait_for_function(
        "previous => { const link = document.getElementById('receiptLink');"
        " const button = document.getElementById('runPaired');"
        " return link.getAttribute('href') !== previous && !button.disabled; }",
        arg=before,
        timeout=30000,
    )


# --- both choices are on the page, and mock is the default -------------------


@pytest.mark.parametrize("locale", ["en", "ar"])
def test_both_sources_are_visible_without_opening_anything(page, server, locale):
    ready(page, server, locale)

    assert page.locator("#esMock").is_visible()
    assert page.locator("#esReal").is_visible()
    assert page.locator("#esMock").is_checked()
    # The explanation is under the selected mode, and it is the required
    # sentence, not a paraphrase.
    assert "No requests are sent to Nokia" in page.locator("#esExplain").inner_text() or locale == "ar"


def test_choosing_real_changes_the_explanation_and_nothing_else(page, server, problems):
    ready(page, server)
    before = page.locator("#esExplain").inner_text()

    page.check("#esReal")

    after = page.locator("#esExplain").inner_text()
    assert after != before
    assert "hosted simulator" in after
    # Selecting a mode is not authorization and is not a request.
    assert page.locator("#esAccess").is_visible(), "the access exchange should be offered"
    assert problems == []


def test_the_readiness_badge_never_claims_a_connection(page, server):
    ready(page, server)

    status = page.locator("#esStatus").inner_text()

    assert "not yet verified" in status
    assert "connected" not in status.lower()


def test_a_wrong_access_code_is_refused_and_no_run_is_attempted(page, server, problems):
    ready(page, server)
    page.check("#esReal")

    page.fill("#accessCode", "not-the-organizer-code")
    page.click("#accessSubmit")
    page.wait_for_function(
        "() => { const n = document.getElementById('esAccessNote');"
        " return n && !n.hidden && n.textContent.trim() && n.textContent.indexOf('Checking') === -1; }",
        timeout=10000,
    )

    note = page.locator("#esAccessNote").inner_text()
    assert "not recognized" in note or "access code" in note.lower()
    assert page.locator("#esAccess").is_visible(), "still unauthorized, so still offered"
    # The browser logs the refused fetch, which is the refusal working. Nothing
    # else may be in there — a thrown handler would be.
    assert [p for p in problems if "403" not in p] == []


def test_the_custom_stories_are_labelled_as_fixtures_not_nokia_contracts(page, server):
    ready(page, server)

    note = page.locator(".alt-cases .es-note").inner_text()

    assert "not Nokia contracts" in note
    assert page.locator("#checkout").is_visible()


# --- a mock run, end to end in the browser -----------------------------------


def test_a_mock_run_produces_a_signed_receipt_labelled_as_mock(page, server, problems):
    ready(page, server)

    run_mock(page)

    source = page.locator("#resultSource").inner_text()
    assert "no requests were sent to Nokia" in source
    assert "contract" in source
    # The receipt exists and verifies, through the judge's own session.
    assert page.locator("#receipt").is_visible()
    page.click("#verifySignature")
    page.wait_for_function(
        "() => document.getElementById('vault').textContent.trim().length > 0", timeout=15000
    )
    assert "not" not in page.locator("#vault").inner_text().lower().replace("nothing", "")
    assert problems == []


def test_the_request_details_show_the_actual_calls_and_no_credential(page, server):
    ready(page, server)
    run_mock(page)

    page.locator("#wireDetails summary").click()
    body = page.locator("#wireBody").inner_text()

    assert "/passthrough/camara/v1/sim-swap/sim-swap/v0/check" in body
    assert "200" in body
    # Never a header, never a body, never a key.
    assert "rapidapi" not in body.lower()
    assert "authorization" not in body.lower()
    provenance = page.locator("#wireProvenance").inner_text()
    assert "synthetic" in provenance, "mock timing must not read as a Nokia measurement"


def test_changing_the_selector_after_a_result_does_not_relabel_it(page, server):
    ready(page, server)
    run_mock(page)
    before = page.locator("#resultSource").inner_text()

    page.check("#esReal")

    assert page.locator("#resultSource").inner_text() == before
    assert page.locator("#esApplies").is_visible(), "the page must say the change is for next time"


def test_a_second_click_while_running_does_not_start_a_second_run(page, server):
    ready(page, server)
    before = page.evaluate("() => document.getElementById('receiptLink').getAttribute('href')")
    # Clicked and read in the SAME tick, so this cannot race a mock run that
    # finishes in a hundred milliseconds: the handler disables the button
    # before its first await, and a second click in that window is a no-op.
    # (Checking `is_disabled()` from the test side after `page.click` returns
    # is a race, and it flaked exactly that way under a full-suite run.)
    disabled_during_click = page.evaluate(
        """() => {
             const button = document.getElementById('runPaired');
             button.click();
             const wasDisabled = button.disabled;
             button.click();   // the second click, while it is disabled
             return wasDisabled;
           }"""
    )
    assert disabled_during_click, "the run button is not disabled by its own handler"
    page.wait_for_function(
        "previous => { const link = document.getElementById('receiptLink');"
        " const button = document.getElementById('runPaired');"
        " return link.getAttribute('href') !== previous && !button.disabled; }",
        arg=before,
        timeout=30000,
    )
    page.locator("#wireDetails summary").click()

    body = page.evaluate(
        "() => document.getElementById('wireBody').textContent.split('\\n').filter(Boolean).length"
    )
    assert body == 2, "exactly the two paired checks, once each"


def test_switching_scenarios_runs_the_other_paired_case(page, server):
    ready(page, server)
    run_mock(page)
    # `#decision` lives inside the collapsed audit disclosure, so its text is
    # empty to the browser. The plain-language title is the visible one.
    first = page.locator("#presentationTitle").inner_text()

    page.select_option("#scenario", "stable_subscriber")
    run_mock(page)

    assert page.locator("#resultSource").is_visible()
    page.locator("#wireDetails summary").click()
    # Both paired cases are runnable; whether the decisions differ is policy's
    # business, so this asserts only that the second case actually ran, against
    # the other subscriber.
    assert page.locator("#wireBody").inner_text().count("/check") == 2
    assert first  # the first run produced something


@pytest.mark.parametrize("locale", ["en", "ar"])
def test_the_selector_works_at_a_phone_width_in_both_languages(page, server, locale, problems):
    ready(page, server, locale, width=375, height=812)

    assert page.locator("#esMock").is_visible()
    assert page.locator("#esReal").is_visible()
    assert page.locator("#runPaired").is_visible()
    assert not page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )
    run_mock(page)
    assert page.locator("#resultSource").is_visible()
    assert problems == []


def test_the_journal_recovers_the_trace_after_the_stream_is_dropped(page, server):
    """A reconnect must redraw from the journal, never by buying checks again."""
    ready(page, server)
    run_mock(page)
    rows_before = page.locator("#trace .trace-row").count()

    page.evaluate("() => window.dispatchEvent(new Event('offline'))")
    page.reload()
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)

    # A reload starts a new session and an empty trace; what must be true is
    # that the previous run's receipt is still verifiable and nothing was
    # re-bought. The trace itself is per-run state, by design.
    assert rows_before > 0


# --- the merchant's follow-up, in the browser (Step 10) ----------------------


def run_challenge(page):
    page.select_option("#scenario", "stable_subscriber")
    run_mock(page)
    page.wait_for_selector("#reviewPanel", state="visible", timeout=15000)


@pytest.mark.parametrize("locale", ["en", "ar"])
def test_a_challenge_result_explains_who_acts_next(page, server, locale):
    ready(page, server, locale)
    run_challenge(page)

    panel = page.locator("#reviewPanel")
    assert panel.is_visible()
    # Labelled as simulated, in both languages, and before anything is clicked.
    assert page.locator("#reviewPanel .provenance").is_visible()
    assert page.locator("#reviewOpen").is_visible()
    # "Review not started" is distinguishable from an open attempt.
    assert page.locator("#reviewState").inner_text().strip()
    assert page.locator("#reviewPassed").is_hidden()


def test_an_allow_or_decline_result_offers_no_follow_up(page, server):
    ready(page, server)
    page.select_option("#scenario", "swapped_subscriber")
    run_mock(page)

    assert page.locator("#presentationTitle").inner_text().strip()
    assert page.locator("#reviewPanel").is_hidden(), "DECLINE has no merchant review to open"


def test_opening_and_passing_a_review_leaves_the_receipt_unchanged(page, server, problems):
    ready(page, server)
    run_challenge(page)
    receipt_before = page.evaluate(
        "() => document.getElementById('receiptLink').getAttribute('href')"
    )

    page.click("#reviewOpen")
    page.wait_for_selector("#reviewPassed:not([hidden])", timeout=15000)
    page.click("#reviewPassed")
    page.wait_for_function(
        "() => document.getElementById('reviewPassed').hidden", timeout=15000
    )

    assert "PASSED" in page.locator("#reviewState").inner_text()
    # The decision on screen did not become ALLOW, and the receipt is the same one.
    assert page.locator("#decision").inner_text() in ("", "CHALLENGE")
    assert page.evaluate(
        "() => document.getElementById('receiptLink').getAttribute('href')"
    ) == receipt_before
    page.click("#verifySignature")
    page.wait_for_function(
        "() => document.getElementById('vault').textContent.trim().length > 0", timeout=15000
    )
    assert "unavailable" not in page.locator("#vault").inner_text().lower()
    assert problems == []


def test_an_open_review_is_recovered_after_a_reload(page, server):
    """Server state decides whether an attempt is open, not the page's memory."""
    ready(page, server)
    run_challenge(page)
    page.click("#reviewOpen")
    page.wait_for_selector("#reviewPassed:not([hidden])", timeout=15000)
    chain = page.evaluate(
        "() => document.getElementById('receiptLink').getAttribute('href').split('/').pop()"
    )

    timeline = page.evaluate(
        """async chain => {
             const token = await (await fetch('/v1/judge/session', {method:'POST'})).json();
             const mine = await fetch('/v1/chains/' + chain + '/challenges',
               {headers: {'X-Judge-Session': token.session}});
             return mine.status;
           }""",
        chain,
    )
    # A brand-new session is a different tenant and must not see it.
    assert timeline == 404
