"""The judge lab page (I1/I2/I3/I4/I9) — a reader for recorded runs.

The page's central claim is that nothing on it can start work: every case is
a recording, and "replay" scrubs a captured event list. These tests hold that
claim to the route surface and to the page source, because it is the kind of
property that quietly stops being true the first time somebody adds a
convenience endpoint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.ui_source import read_ui_source

client = TestClient(app)

REPO_ROOT = Path(__file__).resolve().parents[1]
LAB_HTML = read_ui_source(REPO_ROOT / "app" / "static" / "lab.html")
LAB_SCRIPT = LAB_HTML.split("<script>")[-1].split("</script>")[0]
BUNDLE_PATH = REPO_ROOT / "demo" / "lab" / "artifacts" / "bundle.json"


@pytest.fixture(autouse=True)
def _reset_limiters():
    from app.api import rate_limit

    rate_limit.per_ip.reset()
    yield
    rate_limit.per_ip.reset()


# --- the committed bundle -----------------------------------------------------


def test_the_artifact_bundle_is_committed_and_complete():
    """The page has no generator behind it, so a missing bundle is a missing
    page — it must ship with the code, not be built on a judge's machine."""
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    assert bundle["schema_version"] == 1
    assert bundle["unresolved_signals"]
    assert bundle["cases"], "no recorded cases"
    assert bundle["evidence_report"]
    assert bundle["limits"]


def test_every_authored_case_has_a_recording():
    from demo.lab.challenge import CASES

    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    recorded = {case["case_id"] for case in bundle["cases"]}
    assert recorded == set(CASES), "a selectable case with no recording would select nothing"


def test_every_recording_ran_under_the_deterministic_planner():
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    for case in bundle["cases"]:
        assert case["run"]["planner_source"] == "greedy", case["case_id"]


def test_the_recordings_share_one_policy_digest():
    """"Nothing was tuned per case" has to be checkable, not just stated."""
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    digests = {case["run"]["policy_digest"] for case in bundle["cases"]}
    assert len(digests) == 1


def test_the_recorded_shuffle_reproduces():
    from demo.lab.challenge import seeded_order

    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    assert bundle["shuffled_order"] == seeded_order(bundle["shuffle_seed"])
    assert sorted(bundle["shuffled_order"]) == sorted(c["case_id"] for c in bundle["cases"])


def test_the_outage_case_stays_unresolved_rather_than_passing():
    """I4's rule: a provider that did not answer must not read as a pass."""
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    outage = next(c for c in bundle["cases"] if c["case_id"] == "provider_outage")
    assert outage["run"]["outcome"]["chain_grade"] == "UNRESOLVED"
    assert outage["run"]["outcome"]["decision"] != "ALLOW"


def test_the_pages_unresolved_set_is_the_investigators_own():
    """"The network did not answer" versus "the network reported a mismatch"
    is the distinction I4 turns on. A second copy of that set in the page's
    JavaScript would drift; it is shipped in the bundle instead."""
    from app.agent.investigator import _UNRESOLVED_SIGNALS

    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    assert set(bundle["unresolved_signals"]) == set(_UNRESOLVED_SIGNALS)
    assert "UNRESOLVED.includes(event.signal)" in LAB_SCRIPT
    assert "a hole in the chain, not a finding" in LAB_SCRIPT


def test_an_evidence_row_carries_what_the_network_answered():
    bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    run = next(c for c in bundle["cases"] if c["case_id"] == "legitimate_sim_replacement")["run"]
    evidence = [e for e in run["events"] if e["event_type"] == "evidence"]
    assert evidence
    assert all(e["signal"] and e["result"] for e in evidence)
    # And never the provider's own prose.
    assert all("detail" not in e for e in run["events"])


def test_the_bundle_carries_no_phone_number_or_owner():
    raw = BUNDLE_PATH.read_text(encoding="utf-8")
    assert re.search(r'"\+\d{8,15}"', raw) is None
    assert "owner_hash" not in raw


# --- the routes ----------------------------------------------------------------


def test_the_page_renders_with_its_artifacts_embedded():
    response = client.get("/lab")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '"__BUNDLE__"' not in response.text, "the placeholder was never filled"
    assert '"__LIVE_IDENTITY__"' not in response.text
    assert "provider_outage" in response.text


def test_the_embedded_bundle_parses_back_to_the_committed_artifact():
    """The escaping the page does to survive the HTML parser must be invisible
    to JSON.parse, or the reader is shown different numbers than were built."""
    body = client.get("/lab").text
    embedded = body.split('<script type="application/json" id="bundleData">')[1]
    embedded = embedded.split("</script>")[0]
    assert json.loads(embedded.replace("<\\/", "</")) == json.loads(
        BUNDLE_PATH.read_text(encoding="utf-8")
    )


def test_the_page_is_handed_the_live_identity_to_compare_against():
    body = client.get("/lab").text
    embedded = body.split('<script type="application/json" id="liveIdentity">')[1]
    identity = json.loads(embedded.split("</script>")[0])
    assert set(identity) == {"code_revision", "dirty", "policy_digest"}


def test_the_bundle_is_downloadable():
    response = client.get("/lab/bundle.json")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert response.json() == json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def test_model_runs_have_one_explicit_route_separate_from_readonly_pages():
    """Only the bounded case endpoint executes; page and bundle remain read-only."""
    from app.api import routes_lab

    paths = {(route.path, tuple(sorted(route.methods))) for route in routes_lab.router.routes}
    assert paths == {("/lab", ("GET",)), ("/lab/bundle.json", ("GET",)),
                     ("/v1/lab/run/{case_id}", ("POST",))}
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/lab").status_code == 405


def test_the_lab_page_is_read_only_over_the_whole_app():
    """Not just the router — nothing reachable under /lab accepts a body."""
    assert client.post("/lab/bundle.json").status_code == 405


# --- the page itself ------------------------------------------------------------


def test_the_page_loads_no_external_assets_and_only_links_to_studio():
    assert re.findall(r'src\s*=\s*["\'](?:https?:)?//', LAB_HTML) == []
    assert re.findall(r'href="(https?://[^" ]+)"', LAB_HTML) == [
        "https://aistudio.google.com/apikey"
    ]


def test_the_page_renders_every_value_as_text_not_markup():
    for sink in (r"\.innerHTML\s*=", r"\.insertAdjacentHTML\s*\(", r"document\.write\s*\("):
        assert re.search(sink, LAB_SCRIPT) is None, sink


def test_model_execution_is_an_explicit_button_action():
    assert "$('runLabLlm').addEventListener('click'" in LAB_SCRIPT
    assert "method:'POST'" in LAB_SCRIPT
    assert "'/v1/lab/run/'" in LAB_SCRIPT
    assert "EventSource" not in LAB_SCRIPT


def test_the_page_says_the_runs_are_recordings_before_any_result():
    prose = LAB_HTML.split("<script>")[0]
    assert "five recorded investigations" in prose
    assert "Offline playback · no API spend" in prose
    assert "re-sends nothing and costs nothing" in prose


def test_the_page_warns_when_the_recordings_no_longer_match_what_is_running():
    assert "renderProvenance" in LAB_SCRIPT
    assert "the policy file has changed since these runs were recorded" in LAB_SCRIPT
    assert "the code has moved to a different revision" in LAB_SCRIPT
    assert 'id="staleBanner"' in LAB_HTML


def test_the_page_says_so_when_a_recording_came_from_a_dirty_tree():
    assert 'id="dirtyBanner"' in LAB_HTML
    assert "uncommitted changes" in LAB_SCRIPT


def test_a_missing_bundle_gives_an_honest_empty_state_not_a_broken_page():
    assert 'id="emptyBanner"' in LAB_HTML
    assert "No artifacts have been generated" in LAB_HTML
    assert "build_lab_artifacts.py" in LAB_HTML


def test_the_page_labels_the_planner_from_the_recorded_source():
    """I1 step 2: a heuristic described as reasoning is worse than a heuristic."""
    assert "function plannerTag(" in LAB_SCRIPT
    assert "event.selection_source" in LAB_SCRIPT
    assert "no rationale was captured for this selection" in LAB_SCRIPT


def test_the_page_never_invents_a_rationale():
    assert re.search(r"rationale\s*=\s*['\"](?!\s*$)", LAB_SCRIPT) is None
    assert "event.rationale ||" in LAB_SCRIPT


def test_the_counterfactual_is_labelled_hypothetical_and_unsigned():
    prose = LAB_HTML.split("<script>")[0]
    assert "Hypothetical fixture" in prose
    assert "unsigned" in prose
    assert "needs a new real verification" in prose
    # And never advice to a customer.
    assert "not advice to a customer to answer differently" in LAB_SCRIPT


def test_a_variant_with_no_effect_is_reported_as_a_result():
    assert "no_observed_effect" in LAB_SCRIPT
    assert "That is a result, not a" in LAB_SCRIPT


def test_the_evidence_tables_name_their_denominators():
    assert "cases that should not be declined" in LAB_SCRIPT
    assert "innocent_denominator" in LAB_SCRIPT
    assert "guilty_denominator" in LAB_SCRIPT


def test_the_page_repeats_that_authored_data_is_not_ground_truth():
    prose = " ".join(LAB_HTML.split("<script>")[0].split())
    assert "Synthetic expectation agreement is not production accuracy" in prose
    assert "not proof that AI helped" in prose
    assert "not independent ground truth" in " ".join(LAB_SCRIPT.split())


def test_costs_are_named_configured_units_not_prices():
    prose = LAB_HTML.split("<script>")[0]
    assert "configured units" in prose.lower()
    assert "not contracted" in prose


def test_the_wide_tables_scroll_inside_their_own_container():
    """P2's receipt-table lesson, applied before it can be repeated here."""
    assert "class = 'table-wrap'" in LAB_SCRIPT or "className = 'table-wrap'" in LAB_SCRIPT
    assert ".table-wrap{overflow-x:auto" in LAB_HTML
    assert "wrap.tabIndex = 0" in LAB_SCRIPT  # reachable by keyboard, not just by touch


def test_the_page_respects_reduced_motion():
    assert "@media(prefers-reduced-motion:reduce)" in LAB_HTML


def test_the_page_offers_the_artifacts_it_rendered_from():
    assert '/lab/bundle.json' in LAB_HTML
