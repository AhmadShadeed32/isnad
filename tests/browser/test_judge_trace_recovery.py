"""The judge page's trace, when the live stream does not survive the run.

The hosted symptom this file exists for: a completed investigation whose result
listed four checks while `#trace` held a single row. The events were persisted
before they were ever sent (`app/events.py` writes the journal first), so every
one of them was recoverable and none of them were recovered.

These are browser tests against the real page and a real isolated server, not
assertions about the contents of `judge.js`. A source grep passed throughout the
period when the page appended rows straight into the DOM in arrival order and
recovered nothing at all; only a running page can answer whether a dropped
stream ends with a whole trace on screen.

Deterministic fixtures throughout: the module server runs the mock provider and
the greedy planner, so no model and no operator is involved and every run of a
given act produces the same journal.
"""

from __future__ import annotations

import json

import pytest

# The exact sentence the page is required to show when it cannot prove the
# trace is whole. It must never be softened into a claim of completeness.
INCOMPLETE = "Decision saved; some trace events are unavailable."

# The SSE stream itself. `**/v1/console/stream**` would also match
# `/v1/console/stream-token`, and killing the credential exchange is a
# different failure from killing the stream — the hosted symptom was a live,
# authorized session whose event stream did not arrive.
STREAM = "**/v1/console/stream?*"
STREAM_TOKEN = "**/v1/console/stream-token"
REPLAY = "**/v1/console/runs/*/events*"


@pytest.fixture(scope="module")
def server_extra_env() -> dict[str, str]:
    """A two-row replay page, so every test in this file pages through the
    journal rather than getting a short run back in one response. The paging
    loop is the part with no next-page cursor to follow, and a default page of
    500 would never exercise it on a five-event demo run."""
    return {"ISNAD_RUN_REPLAY_PAGE_SIZE": "2"}


# --- driving the page --------------------------------------------------------


def _open(page, server) -> None:
    page.set_default_timeout(20000)
    page.goto(f"{server}/judge")
    page.wait_for_function("() => window.Isnad !== undefined", timeout=15000)
    page.wait_for_function(
        "() => { const b = document.getElementById('checkout'); return b && !b.disabled; }",
        timeout=20000,
    )


def _stream_is_live(page) -> None:
    """The checkout button is enabled by `/v1/console/mode`, which resolves
    before the stream is connected. A test that clicks at that moment is an
    accidental missed-prefix run and cannot assert anything about a normal
    one."""
    page.wait_for_function(
        "() => typeof eventSource !== 'undefined' && eventSource && eventSource.readyState === 1",
        timeout=20000,
    )


def _drop_stream(page) -> None:
    """The live event stream never arrives.

    The credential exchange is answered locally rather than refused: the
    failure under test is the stream itself, not the authorization for it, and
    a page that cannot finish configuring has no checkout button to click. It
    also keeps the page's five-second reconnect loop from minting a fresh
    server-side stream credential every five seconds for the length of the
    test — the server caps those per owner, and a file that burns through them
    starts failing in tests that have nothing to do with the cap.
    """
    page.route(
        STREAM_TOKEN,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"stream_token": "browser-test-credential-that-never-connects"}),
        ),
    )
    page.route(STREAM, lambda route: route.abort())


def _wait_for_decision(page) -> str:
    page.wait_for_function(
        "() => { const d = document.getElementById('decision');"
        " return d && ['ALLOW','CHALLENGE','DECLINE'].includes(d.textContent.trim()); }",
        timeout=40000,
    )
    return page.evaluate("() => document.getElementById('decision').textContent.trim()")


def _wait_for_receipt(page) -> None:
    page.wait_for_function(
        "() => document.getElementById('receipt').classList.contains('visible')",
        timeout=40000,
    )


def _sequences(page) -> list[int]:
    """The journal sequence of every numbered row, in the order they are on
    screen. Ordering and deduplication are questions about this list."""
    return page.evaluate(
        "() => Array.from(document.querySelectorAll('#trace .trace-row[data-sequence]'))"
        ".map(r => Number(r.dataset.sequence))"
    )


def _recovered_count(page) -> int:
    return page.evaluate("() => document.querySelectorAll('#trace [data-recovered]').length")


def _row_count(page) -> int:
    return page.evaluate("() => document.querySelectorAll('#trace .trace-row').length")


def _status(page) -> str:
    return page.evaluate("() => document.getElementById('statusline').textContent")


def _trace_text(page) -> str:
    return page.evaluate("() => document.getElementById('trace').innerText")


def _settle(page, ms: int = 2500) -> None:
    """Let the detached final reconciliation finish. It is deliberately not
    awaited by the checkout, so the decision lands before the journal read
    does."""
    page.wait_for_timeout(ms)


def _assert_ordered_and_unique(sequences: list[int]) -> None:
    assert sequences, "the trace has no journal-numbered rows at all"
    assert sequences == sorted(sequences), f"rows are out of sequence order: {sequences}"
    assert len(sequences) == len(set(sequences)), f"a row was drawn twice: {sequences}"


# Sequence 1 of every run is the `start` event, which sets the status line and
# draws no row; the run's last sequence is its `verdict`, which the result panel
# owns. So a whole trace is every sequence in between, and it begins at 2.
FIRST_DRAWN_SEQUENCE = 2


def _assert_whole(sequences: list[int]) -> None:
    _assert_ordered_and_unique(sequences)
    assert sequences[0] == FIRST_DRAWN_SEQUENCE, (
        f"the trace does not start at the run's first drawn event: {sequences}"
    )
    expected = list(range(sequences[0], sequences[0] + len(sequences)))
    assert sequences == expected, f"the trace has a hole in it: {sequences}"


# --- the runs ----------------------------------------------------------------


def test_a_run_with_a_healthy_stream_needs_no_recovery(page, server, problems):
    """The baseline. Reconciliation runs on every completed checkout, so it has
    to be a no-op when nothing was missed: no duplicated rows, no rows restamped
    as recovered, and no claim that the trace is incomplete."""
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    assert _wait_for_decision(page) in {"ALLOW", "CHALLENGE", "DECLINE"}
    _wait_for_receipt(page)
    _settle(page)

    _assert_ordered_and_unique(_sequences(page))
    assert _recovered_count(page) == 0, "a live run recovered rows it had already seen"
    assert INCOMPLETE not in _status(page)
    assert problems == []


def test_a_run_that_never_sees_the_live_stream_still_shows_its_trace(page, server):
    """The hosted symptom, at its worst: the result arrives and not one event
    does. Every row on screen here came out of the journal."""
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    page.wait_for_function(
        "() => document.querySelectorAll('#trace [data-recovered]').length >= 4",
        timeout=30000,
    )

    sequences = _sequences(page)
    _assert_whole(sequences)
    assert _recovered_count(page) == _row_count(page)
    # The four checks the replacement-SIM fixture actually runs, recovered from
    # the journal rather than watched arriving.
    trace = _trace_text(page)
    for api in ("Number Verification", "SIM Swap", "Device Swap", "Location Verification"):
        assert api in trace, f"{api} is missing from the recovered trace"
    # Each recovered row says so, and carries the journal's own time rather
    # than the moment the reader reconnected.
    assert trace.count("recovered") >= 4
    # And no false claim in either direction: this journal is whole.
    assert INCOMPLETE not in _status(page)


def test_a_missed_prefix_is_recovered_into_sequence_order(page, server):
    """The stream arrives late, after the run has already started.

    The demo paces its checks about 650 ms apart, so holding the credential
    exchange for a second and a half loses the first events and only those. The
    recovered rows have to land above the live ones, not below them.
    """
    held: list[object] = []

    def handler(route):
        if not held:
            held.append(route)  # stalled: the page cannot connect yet
            return
        route.continue_()

    page.route(STREAM_TOKEN, handler)
    _open(page, server)
    assert not page.evaluate(
        "() => typeof eventSource !== 'undefined' && eventSource !== null"
    ), "the stream connected before the test released it"

    page.click("#checkout")
    page.wait_for_timeout(1500)
    held[0].continue_()

    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    _settle(page)

    sequences = _sequences(page)
    _assert_whole(sequences)
    recovered = page.evaluate(
        "() => Array.from(document.querySelectorAll('#trace .trace-row[data-sequence]'))"
        ".map(r => [Number(r.dataset.sequence), r.dataset.recovered === '1'])"
    )
    assert any(is_recovered for _, is_recovered in recovered), (
        "nothing was recovered, so this run did not actually miss its prefix"
    )
    assert any(not is_recovered for _, is_recovered in recovered), (
        "nothing arrived live, so this is the entirely-missed case, not a prefix"
    )
    # The recovered rows are the early ones, and they are above the live rows.
    first_live = next(i for i, (_, r) in enumerate(recovered) if not r)
    assert all(r for _, r in recovered[:first_live])
    assert INCOMPLETE not in _status(page)


def test_a_missed_middle_is_recovered_into_sequence_order(page, server):
    """The stream drops mid-run and comes back before the end.

    A hole in the middle is the case the old page could not fix even in
    principle: the events after the hole were already in the DOM, so anything
    recovered afterwards appended below them and the trace read in the wrong
    order.
    """
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    page.wait_for_function(
        "() => document.querySelectorAll('#trace .trace-row').length >= 2", timeout=20000
    )
    # The drop, as a venue proxy delivers it: the connection is simply gone.
    page.evaluate("() => { eventSource.close(); eventSource = null; }")
    page.wait_for_timeout(1400)  # roughly two paced checks fall in this hole
    page.evaluate("() => { connectStream().catch(() => {}); }")

    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    _settle(page)

    rows = page.evaluate(
        "() => Array.from(document.querySelectorAll('#trace .trace-row[data-sequence]'))"
        ".map(r => [Number(r.dataset.sequence), r.dataset.recovered === '1'])"
    )
    sequences = [sequence for sequence, _ in rows]
    _assert_whole(sequences)
    assert any(is_recovered for _, is_recovered in rows), (
        "no row was recovered, so the stream drop did not lose anything and this"
        " test is not exercising a missed middle"
    )
    assert any(not is_recovered for _, is_recovered in rows)
    # The hole is genuinely in the middle: rows arrived live, then a stretch was
    # recovered. The first row is one this page watched happen.
    assert not rows[0][1], f"the run missed its prefix, not its middle: {rows}"
    first_recovered = next(i for i, (_, r) in enumerate(rows) if r)
    assert first_recovered > 0
    assert INCOMPLETE not in _status(page)


def test_a_duplicate_reconnect_and_a_repeated_replay_never_double_draw(page, server):
    """I14 delivers at least once, and reconciliation can be triggered again by
    any reconnect. The same event may legitimately arrive three times."""
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    page.wait_for_function(
        "() => document.querySelectorAll('#trace .trace-row').length >= 2", timeout=20000
    )
    # Two reconnects and two explicit reconciliations, on top of the live
    # deliveries and the one the completed checkout runs for itself.
    page.evaluate("() => { eventSource.close(); eventSource = null; connectStream().catch(() => {}); }")
    page.wait_for_timeout(400)
    page.evaluate("() => { reconcileTrace(activeRunId).catch(() => {}); }")
    page.evaluate("() => { reconcileTrace(activeRunId).catch(() => {}); }")

    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    _settle(page)
    page.evaluate("() => { reconcileTrace(activeRunId).catch(() => {}); }")
    _settle(page, 1500)

    sequences = _sequences(page)
    _assert_whole(sequences)
    assert len(sequences) == _row_count(page), "a row was drawn without a sequence"


def test_a_late_replay_for_the_previous_run_cannot_contaminate_the_next_one(page, server):
    """Replay rows carry a sequence, an event type, a body and a server time —
    and no run_id. Sequences restart at 1 for every run, so a response that
    arrives after the reader has started another case has nothing in it that
    could reveal the mistake. The only binding available is the run the request
    asked about."""
    held: list[object] = []
    state = {"run_a": None}

    def handler(route):
        if state["run_a"] and state["run_a"] in route.request.url and not held:
            held.append(route)  # run A's journal read, stalled indefinitely
            return
        route.continue_()

    page.route(REPLAY, handler)
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    state["run_a"] = page.evaluate("() => activeRunId")
    assert state["run_a"]
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    for _ in range(60):
        if held:
            break
        page.wait_for_timeout(100)
    assert held, "run A's replay was never issued, so nothing is being held"

    # The reader moves on while run A's journal read is still in flight.
    page.click("#cleanCheckout")
    page.wait_for_function(
        "runA => activeRunId && activeRunId !== runA", arg=state["run_a"], timeout=20000
    )
    assert _wait_for_decision(page) == "ALLOW"
    _wait_for_receipt(page)

    # Now run A answers, with a row whose sequence run B also uses and an API
    # name that appears nowhere in run B's fixture.
    held[0].fulfill(
        status=200,
        content_type="application/json",
        body=json.dumps(
            {
                "run_id": state["run_a"],
                "events": [
                    {
                        "sequence": 1,
                        "event_type": "evidence",
                        "body": {
                            "api": "SENTINEL-API",
                            "result": "FLAG",
                            "signal": "SIM_SWAPPED",
                            "p_fraud": 0.99,
                            "source": "mock",
                        },
                        "server_time": "2026-09-08T10:00:00+00:00",
                    }
                ],
                "gap": False,
            }
        ),
    )
    _settle(page)

    assert "SENTINEL-API" not in _trace_text(page)
    assert _wait_for_decision(page) == "ALLOW", "run B's decision was disturbed"
    _assert_ordered_and_unique(_sequences(page))


def test_recovery_pages_through_the_journal_without_a_next_cursor(page, server):
    """The endpoint is bounded at `run_replay_page_size` (two, for this module)
    and returns no cursor. A client that reads one page and stops recovers the
    first two events of a five-event run and silently loses the rest."""
    requests: list[str] = []
    page.on(
        "request",
        lambda request: requests.append(request.url)
        if "/events?" in request.url
        else None,
    )
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    page.wait_for_function(
        "() => document.querySelectorAll('#trace [data-recovered]').length >= 4",
        timeout=30000,
    )
    _settle(page)

    assert len(requests) > 1, f"the journal was read in one page only: {requests}"
    # Every page after the first asks from where the last one ended, and the
    # first asks from zero — never from the highest sequence seen live, which
    # would skip everything before it.
    assert any(url.endswith("after=0") for url in requests)
    _assert_whole(_sequences(page))


def test_a_journal_missing_the_end_of_the_run_says_so(page, server):
    """A simulated journal-write failure: the last events, verdict included,
    never reached the journal.

    `gap` is false for all of it — `has_gap(after=0)` always is — so a page
    that trusted `gap` would report a complete trace over a journal that stops
    mid-run.
    """
    def handler(route):
        response = route.fetch()
        body = response.json()
        # Everything from the fourth event on was lost on its way to the
        # journal, the verdict among it.
        body["events"] = [row for row in body["events"] if row["sequence"] < 4]
        route.fulfill(
            status=200, content_type="application/json", body=json.dumps(body)
        )

    page.route(REPLAY, handler)
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    decision = _wait_for_decision(page)
    _wait_for_receipt(page)
    page.wait_for_function(
        "copy => document.getElementById('statusline').textContent.includes(copy)",
        arg=INCOMPLETE,
        timeout=30000,
    )

    # The decision itself is untouched: a trace this page cannot complete is not
    # a decision it may hide.
    assert decision == "CHALLENGE"
    assert page.evaluate("() => document.getElementById('decision').textContent.trim()") == "CHALLENGE"
    assert page.evaluate(
        "() => document.getElementById('receipt').classList.contains('visible')"
    )
    assert page.evaluate("() => document.getElementById('receiptLink').getAttribute('href')").startswith("/r/")


def test_a_transient_failure_is_retried_rather_than_given_up_on(page, server):
    """A 5xx or a dropped connection is the recoverable case, and it must not be
    treated like an expired credential. The journal is still there; asking
    again is all that is needed."""
    attempts: list[str] = []

    def handler(route):
        attempts.append(route.request.url)
        if len(attempts) == 1:
            route.fulfill(
                status=503,
                content_type="application/json",
                body=json.dumps({"detail": {"code": "unavailable", "message": "no"}}),
            )
            return
        route.continue_()

    page.route(REPLAY, handler)
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    page.wait_for_function(
        "() => document.querySelectorAll('#trace [data-recovered]').length >= 4",
        timeout=30000,
    )
    _settle(page)

    assert len(attempts) >= 2, f"the failed journal read was never retried: {attempts}"
    _assert_whole(_sequences(page))
    # It recovered, so it may not say it did not.
    assert INCOMPLETE not in _status(page)


def test_a_recovered_row_is_stamped_with_the_time_it_happened(page, server):
    """Not with the moment the reader reconnected. A run recovered an hour
    later, stamped with `Date.now()`, would date every one of its checks to the
    recovery — which is exactly the fact the trace exists to record."""
    # A browser clock far from the server's. Every live row would be stamped
    # from here; a recovered row has to come from the journal instead.
    page.clock.set_fixed_time("2030-01-01T12:00:00Z")
    _drop_stream(page)
    _open(page, server)
    # Exactly what a row stamped with `Date.now()` would read, in the page's own
    # formatting. If the clock were not frozen this string would keep moving and
    # the assertion below would prove nothing.
    frozen = page.evaluate(
        "() => { const p = n => String(n).padStart(2, '0'); const d = new Date();"
        " return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()); }"
    )
    assert page.evaluate("() => new Date().getUTCFullYear()") == 2030, (
        "the browser clock was not frozen, so this test cannot tell the two apart"
    )

    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    page.wait_for_function(
        "() => document.querySelectorAll('#trace [data-recovered]').length >= 4",
        timeout=30000,
    )

    stamps = page.evaluate(
        "() => Array.from(document.querySelectorAll('#trace [data-recovered] .trace-meta'))"
        ".map(m => m.textContent)"
    )
    assert stamps
    for stamp in stamps:
        assert "recovered" in stamp
        assert frozen not in stamp, (
            f"a recovered row was stamped with the browser's clock, not the journal's: {stamp}"
        )


def test_a_late_duplicate_delivery_is_dropped_rather_than_drawn_again(page, server):
    """I14 promises at-least-once, and a reconnect can replay an event the page
    already has. The sequence is the key the two deliveries share."""
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    _settle(page)

    before = _sequences(page)
    _assert_whole(before)
    status_before = _status(page)
    # The same event again, out of order and carrying a title that appears
    # nowhere else, delivered exactly as the stream would deliver it.
    page.evaluate(
        "seq => onEvent({type:'evidence', run_id: activeRunId, sequence: seq,"
        " api:'LATE-DUPLICATE', result:'PASS', signal:'SIM_NOT_SWAPPED',"
        " p_fraud:0.1, source:'mock'})",
        arg=before[0],
    )
    page.wait_for_timeout(300)

    assert _sequences(page) == before
    assert "LATE-DUPLICATE" not in _trace_text(page)
    # And a late live event may not rewrite the finished decision's status line.
    assert _status(page) == status_before


def test_a_journal_that_holds_nothing_is_never_reported_as_complete(page, server):
    """The retention case: the run's events are past their window, so the
    journal answers with nothing at all and `gap` is false, because
    `has_gap(after=0)` always is. An empty journal is not a whole trace."""
    def handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"run_id": "purged", "events": [], "gap": False}),
        )

    page.route(REPLAY, handler)
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    page.wait_for_function(
        "copy => document.getElementById('statusline').textContent.includes(copy)",
        arg=INCOMPLETE,
        timeout=30000,
    )
    assert _row_count(page) == 0
    assert page.evaluate(
        "() => document.getElementById('receipt').classList.contains('visible')"
    )


def test_a_replay_that_is_refused_cannot_hide_a_saved_decision(page, server):
    """An expired demo credential is not a recoverable transport failure. The
    loop has to stop and say to reload — and the verdict the server already
    persisted stays exactly where it is."""
    attempts: list[str] = []

    def handler(route):
        attempts.append(route.request.url)
        route.fulfill(
            status=401,
            content_type="application/json",
            body=json.dumps(
                {"detail": {"code": "unauthorized", "message": "Bearer API key required"}}
            ),
        )

    page.route(REPLAY, handler)
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
    page.wait_for_function(
        "copy => document.getElementById('statusline').textContent.includes(copy)",
        arg=INCOMPLETE,
        timeout=30000,
    )

    status = _status(page)
    assert "Reload" in status, status
    assert page.evaluate("() => document.getElementById('decision').textContent.trim()") == "CHALLENGE"
    assert page.evaluate(
        "() => document.getElementById('receipt').classList.contains('visible')"
    )
    # The signature check still works on the persisted chain: a failed journal
    # read did not reset the result state it has no business touching.
    page.click("#verifySignature")
    page.wait_for_function(
        "() => document.getElementById('vault').textContent.includes('valid')", timeout=20000
    )

    # And the refusal was terminal: no retry storm against a credential the
    # server will never honour again.
    before = len(attempts)
    page.wait_for_timeout(4000)
    assert len(attempts) == before, f"the refused replay was retried: {attempts}"
    assert before <= 2, f"a 401 was retried inside one reconciliation: {attempts}"


def test_recovery_buys_no_checks(page, server):
    """I14's bound, asserted rather than described: recovery resumes the record
    of a run, never the run. Nothing after the investigation POST may be a
    request that could cost an operator or a model call — the journal read is a
    GET against this server's own database."""
    seen: list[tuple[str, str]] = []
    page.on("request", lambda request: seen.append((request.method, request.url)))
    _drop_stream(page)
    _open(page, server)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    page.wait_for_function(
        "() => document.querySelectorAll('#trace [data-recovered]').length >= 4",
        timeout=30000,
    )
    _settle(page)

    runs = [url for method, url in seen if method == "POST" and "/v1/console/run/" in url]
    assert len(runs) == 1, f"the investigation was started more than once: {runs}"
    index = next(i for i, (method, url) in enumerate(seen) if (method, url) == ("POST", runs[0]))
    after = seen[index + 1:]
    assert after, "recovery issued no request at all"
    for method, url in after:
        if method == "POST":
            # The only write recovery is allowed to make is re-earning its own
            # stream credential: a session token exchange against this server,
            # which starts no investigation and reaches no operator.
            assert url.endswith("/v1/console/stream-token"), f"recovery issued a POST to {url}"
            continue
        assert method == "GET", f"recovery issued a {method} to {url}"
        # `/challenges` joined this list when the judge page gained the
        # merchant follow-up panel: after a CHALLENGE it reads the attempt
        # timeline so an attempt opened before a refresh is recovered from
        # server state rather than from browser memory. It is a read of this
        # service's own rows — no provider, no model, no investigator — which
        # is exactly what this allowlist is for.
        assert (
            "/events?" in url
            or "/v1/console/stream" in url
            or url.endswith("/challenges")
        ), url
    assert any("/events?" in url for _, url in after)
    # Nothing that could reach a provider, a model or the investigator.
    for _, url in after:
        for costly in ("/v1/console/run/", "/v1/verify", "/v1/network-conditions", "/v1/sessions"):
            assert costly not in url, f"recovery called {url}"


def test_another_tenant_still_cannot_read_this_run(page, server):
    """Recovery is authorized like every other console route, never derived
    from the run_id — which is in this page's own JavaScript and trivially
    copied."""
    _open(page, server)
    _stream_is_live(page)
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    run_id = page.evaluate("() => activeRunId")

    unauthenticated = page.request.get(f"{server}/v1/console/runs/{run_id}/events?after=0")
    assert unauthenticated.status == 401

    stranger = page.request.get(
        f"{server}/v1/console/runs/{run_id}/events?after=0",
        headers={"Authorization": "Bearer not-this-tenants-key"},
    )
    assert stranger.status in (401, 403), stranger.status


def test_a_refused_stream_credential_stops_the_reconnect_loop_and_says_why(
    page, server
):
    """The other half of the same rule, one step earlier.

    A refused *replay* already stops and says to reload. A refused *credential
    exchange* did not: it went back to `scheduleStreamReconnect` every five
    seconds against a pool the server had already refused, while the status
    line kept promising a reconnection that could not happen. The exchange caps
    credentials per owner, so this is reachable with no server fault at all —
    several tabs, or a long session, is enough.
    """
    attempts: list[str] = []

    def handler(route):
        attempts.append(route.request.url)
        route.fulfill(
            status=403,
            content_type="application/json",
            body=json.dumps(
                {"detail": {"code": "forbidden", "message": "stream credential limit"}}
            ),
        )

    page.route(STREAM_TOKEN, handler)
    _open(page, server)

    page.wait_for_function(
        "() => document.getElementById('statusline').textContent.includes('Reload')",
        timeout=20000,
    )
    status = _status(page)
    assert "expired" in status, status
    # It says what is still true as well as what stopped.
    assert "journal" in status, status

    # Terminal means terminal: the five-second loop does not run.
    before = len(attempts)
    page.wait_for_timeout(6000)
    assert len(attempts) == before, f"the refused credential was retried: {attempts}"

    # And the decision path is untouched — losing the live stream costs
    # liveness, never the verdict or the receipt.
    assert page.locator("#checkout").is_enabled()
    page.click("#checkout")
    assert _wait_for_decision(page) == "CHALLENGE"
    _wait_for_receipt(page)
