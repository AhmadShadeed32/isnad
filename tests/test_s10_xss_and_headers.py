"""S10 — DOM XSS sinks in the console, and the missing CSP."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from tests.ui_source import read_ui_source

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}

CONSOLE_HTML = read_ui_source(Path("app/static/console.html"))
PAYLOAD = "<img src=x onerror=alert(1)>"


def test_the_console_never_parses_a_string_as_markup():
    """addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,
    ev.api, ev.source and err.message, all unescaped.

    Matched against uses rather than the bare word, so the comments explaining
    the fix do not fail the test that proves it.
    """
    script = CONSOLE_HTML.split("<script>")[-1].split("</script>")[0]

    for sink in (
        r"\.innerHTML\s*=",
        r"\.outerHTML\s*=",
        r"\.insertAdjacentHTML\s*\(",
        r"document\.write\s*\(",
    ):
        assert re.search(sink, script) is None, sink


def test_untrusted_text_reaches_the_dom_only_through_textcontent():
    script = CONSOLE_HTML.split("<script>")[-1].split("</script>")[0]
    # The one helper that writes caller-supplied text into a row.
    assert "el.textContent = text == null ? '' : String(text);" in script


def test_a_missing_chain_error_does_not_reflect_the_path():
    """The acceptance criterion, verbatim.

    routes_verify.py reflected a raw path parameter into a message that apiJson
    threw and addRow injected.
    """
    response = client.get(f"/v1/chains/{PAYLOAD}", headers=AUTH)

    assert response.status_code == 404
    assert PAYLOAD not in response.text
    assert "<img" not in response.text
    assert response.json()["detail"]["message"] == "No such chain"


def test_a_missing_session_error_does_not_reflect_the_path():
    response = client.get(f"/v1/sessions/{PAYLOAD}", headers=AUTH)

    assert response.status_code == 404
    assert PAYLOAD not in response.text


def test_the_error_message_is_constant_across_inputs():
    """A constant message cannot carry an injected payload."""
    first = client.get("/v1/chains/chn_aaaaaaaaaaaaaaaaaaaa", headers=AUTH).json()
    second = client.get(f"/v1/chains/{PAYLOAD}", headers=AUTH).json()

    assert first["detail"] == second["detail"]


def test_security_headers_are_present_on_every_response():
    for path in ("/console", "/health"):
        headers = client.get(path).headers
        assert "content-security-policy" in headers, path
        assert headers["x-content-type-options"] == "nosniff", path
        assert headers["referrer-policy"] == "no-referrer", path
        assert "frame-ancestors 'none'" in headers["content-security-policy"], path


def test_the_csp_permits_no_external_origin():
    """console.html has zero external origins; the policy must keep it that way."""
    csp = client.get("/console").headers["content-security-policy"]

    for directive in csp.split(";"):
        assert "http://" not in directive
        assert "https://" not in directive
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp


def test_the_console_still_loads_nothing_from_an_external_origin():
    """The invariant the runbook says to keep: a venue may be offline."""
    external = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//', CONSOLE_HTML)
    assert external == []


def test_headers_are_present_on_the_streaming_response(monkeypatch):
    """The middleware must not have been written in a way that buffers SSE.

    BaseHTTPMiddleware would have: it buffers a StreamingResponse, which would
    hold the console's events until the connection closed.
    """
    from app.api import routes_console, stream_token

    monkeypatch.setattr(routes_console, "SSE_KEEPALIVE_SECONDS", 0.05)
    credential = stream_token.mint("stream-test-owner")
    with client.stream("GET", f"/v1/console/stream?stream_token={credential}") as response:
        assert response.status_code == 200
        assert "content-security-policy" in response.headers
        # Arrives without the connection having to close, so nothing buffered it.
        assert next(response.iter_lines()) == ": keepalive"
