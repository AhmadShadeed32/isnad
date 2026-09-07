"""What the console does when its stream credential stops being honoured.

The demo token is minted into the page at render time and held in a
process-local dict, so restarting the server — `uvicorn --reload` does this on
every edit — invalidates the token the open tab is still holding. The tab then
asks for a new stream credential, is refused, and has to tell the presenter
that the fix is a reload.

These are browser tests rather than source assertions on purpose.
`tests/test_console.py::test_a_rejected_demo_token_tells_the_presenter_to_reload`
asserts the copy exists in the file, and passed throughout the period when the
console retried a rejected credential every five seconds forever and never put
that copy on screen. Only a running page can answer whether the message is
displayed and whether the loop stops.
"""

from __future__ import annotations

import json

import pytest

# The credential exchange rejects with either code depending on how the token
# failed, and `authFailureMessage` writes different copy for each. Both are
# terminal for the stream: no amount of retrying mints a token the dead
# process still knows about.
REJECTIONS = [
    (401, "demo session expired"),
    (403, "demo token was rejected"),
]


def _reject_stream_token(page, status: int) -> list[str]:
    """Refuse every stream-credential exchange, recording each attempt."""
    attempts: list[str] = []

    def handler(route, request):
        attempts.append(request.url)
        route.fulfill(
            status=status,
            content_type="application/json",
            body=json.dumps({"detail": {"code": "unauthorized", "message": "Bearer API key required"}}),
        )

    page.route("**/v1/console/stream-token", handler)
    return attempts


@pytest.mark.parametrize("status,copy", REJECTIONS)
def test_a_rejected_stream_credential_stops_retrying_and_says_to_reload(
    page, server, status, copy
):
    attempts = _reject_stream_token(page, status)
    page.goto(f"{server}/console")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)

    # The message is on screen, not merely in the source.
    page.wait_for_function(
        "copy => { const n = document.getElementById('streamNotice');"
        " return n && n.textContent.includes(copy); }",
        arg=copy,
        timeout=10000,
    )
    assert "reload the page" in page.locator("#streamNotice").inner_text()

    # And the status reads as needing attention rather than as recovering on
    # its own — "reconnecting…" beside a stopped stream is a lie.
    assert "attention" in (page.locator("#dot").get_attribute("class") or "")
    assert "reconnecting" not in page.locator("#statusText").inner_text().lower()

    # Past the first retry the loop would have taken. This is the defect: the
    # flat five-second retry issued a rejected exchange until the tab was
    # closed — 110 console errors in a couple of minutes, on stage.
    page.wait_for_timeout(7000)
    assert len(attempts) == 1, f"the credential exchange was retried: {attempts}"


def test_a_transient_stream_failure_still_reconnects(page, server):
    """The terminal case must not swallow the recoverable one. A 5xx, a dropped
    connection or a restarted-but-healthy server all deserve another try."""
    attempts: list[int] = []

    def handler(route, request):
        attempts.append(1)
        if len(attempts) == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": {"code": "unavailable", "message": "no"}}),
            )
        else:
            route.continue_()

    page.route("**/v1/console/stream-token", handler)
    page.goto(f"{server}/console")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=10000)

    page.wait_for_function(
        "() => document.getElementById('statusText').textContent.trim() === 'live'",
        timeout=20000,
    )
    assert len(attempts) >= 2
    assert page.locator("#streamNotice").inner_text().strip() == ""


def test_a_restart_mid_stream_halts_instead_of_looping(page, server):
    """The stage case, end to end: a live stream, then the process that minted
    the token goes away.

    The EventSource drop is what the presenter sees first, and that alone is not
    evidence of anything — so the page retries. The retry's credential exchange
    is where the truth arrives, and it has to be acted on there.
    """
    state = {"reject": False, "attempts": 0}

    def handler(route, request):
        state["attempts"] += 1
        if state["reject"]:
            route.fulfill(
                status=403,
                content_type="application/json",
                body=json.dumps({"detail": {"code": "forbidden", "message": "Bearer API key required"}}),
            )
        else:
            route.continue_()

    page.route("**/v1/console/stream-token", handler)
    page.goto(f"{server}/console")
    page.wait_for_function(
        "() => document.getElementById('statusText').textContent.trim() === 'live'",
        timeout=20000,
    )

    # From here the server no longer knows this tab's token.
    state["reject"] = True
    exchanges_before = state["attempts"]
    # The drop itself, as the browser delivers it: an error event with nothing
    # in it to distinguish a restarted server from a flaky one.
    page.evaluate("() => es.dispatchEvent(new Event('error'))")

    page.wait_for_function(
        "() => document.getElementById('streamNotice').textContent.includes('reload the page')",
        timeout=20000,
    )
    assert "attention" in (page.locator("#dot").get_attribute("class") or "")

    # Long enough to cover the next backed-off retry this path would take if the
    # halt did not hold — the drop already consumed the first interval, so seven
    # seconds here would pass whether or not the loop stopped.
    page.wait_for_timeout(13000)
    assert state["attempts"] - exchanges_before == 1
