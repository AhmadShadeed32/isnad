"""The judge's API-key page, in a real browser.

A judge enters the organizer's code, gets a key shown once, and the page hands
them three commands that already carry the key and this server's address. The
test then makes the first of those requests itself — the page is the source of
the exact bytes a judge would paste — and reads the chain back through the
page's own session, which is the property the page promises: the terminal's
chain is this tab's chain.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.browser.conftest import shot
from tests.browser.test_surfaces import CONTRAST_JS, open_page

ACCESS_CODE = "organizer-browser-test-code"


@pytest.fixture(scope="module")
def server_extra_env() -> dict[str, str]:
    """A code is configured; the real NaC path is not. The key mint depends on
    the former alone, and a deployment can offer keys without offering Nokia."""
    return {"ISNAD_JUDGE_ACCESS_CODES": ACCESS_CODE}


def ready(page, server, locale="en", width=1280, height=900):
    open_page(page, server, "/api-keys", locale, width, height)
    page.wait_for_function(
        "() => !['…','—'].includes(document.getElementById('factTtl').textContent.trim())",
        timeout=10000,
    )


def mint(page, code=ACCESS_CODE):
    page.fill("#accessCode", code)
    page.click("#mintButton")


def test_the_page_states_its_facts_before_anything_is_entered(page, server, problems):
    ready(page, server)

    assert "2 h" in page.text_content("#factTtl")
    assert "mock" in page.text_content("#factProvider")
    assert "greedy" in page.text_content("#factPlanner")
    assert page.is_hidden("#issued")
    assert "None yet" in page.text_content("#keyList")
    assert problems == []


def test_a_wrong_code_is_refused_in_the_servers_words(page, server, problems):
    ready(page, server)
    mint(page, "not-the-code")
    page.wait_for_function(
        "() => document.getElementById('mintNote').textContent.includes('not recognized')"
    )

    assert page.is_hidden("#issued")
    assert page.input_value("#accessCode") == "not-the-code"  # a typo is kept to be fixed
    # The refusal itself is the only console line: Chromium logs every 403.
    assert [p for p in problems if "403" not in p] == []


def test_the_right_code_mints_a_key_the_commands_carry_and_the_chain_is_this_tabs(
    page, server, problems
):
    ready(page, server)
    mint(page)
    page.wait_for_selector("#issued:not([hidden])")

    key = page.text_content("#apiKey").strip()
    assert key.startswith("mk_") and len(key) > 30
    assert page.input_value("#accessCode") == "", "the code must not stay in the page"
    assert ACCESS_CODE not in page.content()

    verify_cmd = page.text_content("#cmdVerify")
    assert f"Bearer {key}" in verify_cmd
    assert f"curl {server}/v1/verify" in verify_cmd
    assert "X-Isnad-Planner: greedy" in verify_cmd
    body = json.loads(re.search(r"-d '(\{.*\})'", verify_cmd, re.DOTALL).group(1))
    assert body["phone_number"] == "+99999991006"

    # The request the page printed, sent from the page's own origin.
    result = page.evaluate(
        """async ([key, body]) => {
          const r = await fetch('/v1/verify', {method: 'POST', headers: {
            'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
            'X-Isnad-Planner': 'greedy', 'Idempotency-Key': 'browser-judge-1'},
            body: JSON.stringify(body)});
          return {status: r.status, json: await r.json()};
        }""",
        [key, body],
    )
    assert result["status"] == 200, result
    assert result["json"]["decision"] == "CHALLENGE"
    assert result["json"]["chain_grade"] == "DEGRADED"
    assert result["json"]["confidence"] == 0.322
    assert result["json"]["planner"] == "greedy"
    chain_id = result["json"]["chain_id"]

    # Readable through the page's own judge session: one tenant, as promised.
    signature = page.evaluate(
        """async ([key, chainId]) => {
          const r = await fetch('/v1/chains/' + chainId + '/verification',
            {headers: {'Authorization': 'Bearer ' + key}});
          return {status: r.status, json: await r.json()};
        }""",
        [key, chain_id],
    )
    assert signature["status"] == 200 and signature["json"]["valid"] is True

    listing = page.text_content("#keyList")
    assert key[:10] in listing and key not in listing
    assert page.evaluate(CONTRAST_JS) == []
    assert problems == []
    shot(page, "api-keys-en-issued-1280")


def test_the_issued_section_reads_right_to_left_with_the_key_left_to_right(page, server, problems):
    ready(page, server, locale="ar", width=375, height=812)
    mint(page)
    page.wait_for_selector("#issued:not([hidden])")

    assert page.evaluate("() => document.documentElement.dir") == "rtl"
    assert page.evaluate("() => getComputedStyle(document.getElementById('apiKey')).direction") == "ltr"
    assert page.evaluate("() => getComputedStyle(document.getElementById('cmdVerify')).direction") == "ltr"
    assert page.text_content("h1").strip() != "Call the API the way a merchant would"
    moved = page.evaluate(
        "() => { const b = window.scrollX; window.scrollTo(9999, 0); const a = window.scrollX; window.scrollTo(b, 0); return a - b; }"
    )
    assert moved <= 1
    assert page.evaluate(CONTRAST_JS) == []
    assert problems == []
    shot(page, "api-keys-ar-issued-375")
