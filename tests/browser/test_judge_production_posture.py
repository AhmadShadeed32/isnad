"""The judge page with `ISNAD_DEMO_MODE=false` — the posture Step 9 rehearsed.

Every other browser file runs with demo mode on, where the page is served a
short-TTL console token. A deployment that makes real Nokia calls cannot run
demo mode, so the page a judge actually uses in that posture carries **no**
credential at all, and its only identity is the judge session it mints for
itself.

Two defects lived in exactly that gap and are pinned here:

  * the live event stream was gated on the demo token, so a production-posture
    judge got the decision with none of the reasoning the page exists to show;
  * every request still sent `Authorization: Bearer ` with nothing after it,
    which the rate limiter buckets on — so every judge on the deployment would
    have shared one 60-per-minute bucket instead of one each.
"""

from __future__ import annotations

import pytest

from tests.browser.test_surfaces import open_page

ACCESS_CODE = "organizer-production-posture-code"


@pytest.fixture(scope="module")
def server_extra_env(tmp_path_factory) -> dict[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key_path = tmp_path_factory.mktemp("posture-vault") / "vault.key"
    key_path.write_bytes(
        Ed25519PrivateKey.generate().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    key_path.chmod(0o600)
    return {
        # The posture under test: no demo tokens are minted at all.
        "ISNAD_DEMO_MODE": "false",
        "ISNAD_JUDGE_REAL_NAC_ENABLED": "true",
        "ISNAD_JUDGE_ACCESS_CODES": ACCESS_CODE,
        "ISNAD_NAC_API_KEY": "posture-test-key-never-used-for-a-request",
        "ISNAD_VAULT_KEY_PATH": str(key_path),
        # Left ON, unlike the other files: a shared bucket is one of the two
        # defects this file exists to catch, and it is invisible with limiting off.
        "ISNAD_RATE_LIMIT_ENABLED": "true",
    }


def ready(page, server, locale="en", width=1280, height=900):
    open_page(page, server, "/judge", locale, width, height)
    page.wait_for_function(
        "() => { const b = document.getElementById('runPaired');"
        " const s = document.getElementById('scenario');"
        " return b && !b.disabled && s && s.options.length > 0; }",
        timeout=15000,
    )


def test_the_page_carries_no_credential_and_still_works(page, server, problems):
    ready(page, server)

    assert (
        page.evaluate("() => document.querySelector('meta[name=\"isnad-demo-token\"]').content")
        == ""
    ), "a production render must not contain a credential"
    # The custom stories are demo-mode fixtures and are correctly unavailable…
    assert page.locator("#checkout").is_disabled()
    # …and the paired Nokia sources are not, which is the point of the split.
    assert page.locator("#runPaired").is_enabled()
    assert page.locator("#esMock").is_checked()
    assert problems == []


def test_no_empty_bearer_header_is_sent(page, server):
    """An empty Bearer buckets every judge together in the rate limiter."""
    sent: list[str | None] = []
    page.on(
        "request",
        lambda request: sent.append(request.headers.get("authorization"))
        if "/v1/judge/" in request.url
        else None,
    )

    ready(page, server)

    assert sent, "no judge request was observed"
    assert all(header is None for header in sent), f"an Authorization header was sent: {sent}"


def test_each_tab_gets_its_own_judge_session(page, browser, server):
    """Two judges, two tenants. Not one shared console owner."""
    ready(page, server)
    first = page.evaluate("() => window.__judgeSessionProbe")

    context = browser.new_context()
    other = context.new_page()
    other.set_default_timeout(10000)
    try:
        open_page(other, server, "/judge", "en", 1280, 900)
        other.wait_for_function(
            "() => { const s = document.getElementById('scenario'); return s && s.options.length; }",
            timeout=15000,
        )
        # Read through a run rather than a global: the session token is
        # deliberately not exposed on `window`.
        page.click("#runPaired")
        other.click("#runPaired")
        for tab in (page, other):
            tab.wait_for_function(
                "() => document.getElementById('receiptLink').getAttribute('href')"
                " && document.getElementById('receiptLink').getAttribute('href') !== '#'",
                timeout=30000,
            )
        mine = page.evaluate("() => document.getElementById('receiptLink').getAttribute('href')")
        theirs = other.evaluate("() => document.getElementById('receiptLink').getAttribute('href')")
        assert mine != theirs, "two judges produced the same chain"
    finally:
        context.close()
    assert first is None  # nothing leaks the session onto the page object


def test_the_live_stream_connects_without_a_demo_token(page, server, problems):
    """The trace is the reasoning. Losing it outside demo mode was silent."""
    ready(page, server)
    page.click("#runPaired")
    page.wait_for_function(
        "() => document.querySelectorAll('#trace .trace-row').length > 0", timeout=30000
    )

    rows = page.locator("#trace .trace-row").count()
    assert rows >= 2, "the trace should show the selection and the evidence"
    assert problems == []


def test_the_receipt_verifies_through_the_judges_own_session(page, server):
    ready(page, server)
    page.click("#runPaired")
    page.wait_for_function(
        "() => { const l = document.getElementById('receiptLink');"
        " return l.getAttribute('href') && l.getAttribute('href') !== '#'; }",
        timeout=30000,
    )

    page.click("#verifySignature")
    page.wait_for_function(
        "() => document.getElementById('vault').textContent.trim().length > 0", timeout=15000
    )

    assert "unavailable" not in page.locator("#vault").inner_text().lower()
