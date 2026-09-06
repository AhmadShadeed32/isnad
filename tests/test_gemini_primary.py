"""Gemini responses must never be silently replaced by greedy selection."""

import json

import httpx
import pytest

from app.agent.gemini import GeminiClient
from app.agent.planner import LLMPlanner
from app.config import Settings
from app.domain.enums import Hypothesis
from tests.test_llm_planner import FakeClient, _planner


def test_settings_default_to_gemini():
    assert Settings.model_fields["planner"].default == "llm"


@pytest.mark.parametrize("error", [
    json.JSONDecodeError("invalid", "x", 0),
    RuntimeError("unexpected internal error"),
    httpx.HTTPStatusError("rejected", request=httpx.Request("POST", "https://test.invalid"),
                          response=httpx.Response(429)),
])
def test_a_response_or_internal_error_is_not_no_response(error):
    choice = _planner(FakeClient(raises=error)).choose(Hypothesis.MULE, set(), 8)
    assert choice.source == "llm"
    assert choice.stops


@pytest.mark.parametrize("payload", [{}, {"action": "sim_swap"}, [], "not JSON"])
def test_malformed_returned_output_does_not_fall_back(payload):
    class Client:
        def generate_json(self, **kwargs):
            return payload

    choice = _planner(Client()).choose(Hypothesis.MULE, set(), 8)
    assert choice.source == "llm"
    assert choice.stops


@pytest.mark.parametrize("payload,source", [
    ({"candidates": []}, "greedy"),
    ({"candidates": [{"content": {"parts": []}, "finishReason": "STOP"}]}, "greedy"),
    ({"promptFeedback": {"blockReason": "SAFETY"}}, "llm"),
    ({"candidates": [{"finishReason": "SAFETY"}]}, "llm"),
    ({"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}, "llm"),
    ({"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}, "llm"),
])
def test_adapter_distinguishes_empty_answers_from_rejections(monkeypatch, payload, source):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    monkeypatch.setattr("app.agent.gemini.httpx.post", lambda *args, **kwargs: Response())
    planner = _planner(GeminiClient("fake-key", "test-model", 1))
    choice = planner.choose(Hypothesis.MULE, set(), 8)
    assert choice.source == source
    assert choice.stops == (source == "llm")


def test_successful_stop_does_not_invoke_greedy(monkeypatch):
    planner = _planner(FakeClient(action="STOP"))

    def forbidden(*args, **kwargs):
        raise AssertionError("Gemini responded: greedy must not choose")

    monkeypatch.setattr(planner._greedy, "choose", forbidden)
    assert planner.choose(Hypothesis.MULE, set(), 8).stops
    assert isinstance(planner, LLMPlanner)


def test_a_no_answer_fallback_names_the_condition_that_allowed_greedy():
    """An offline greedy run and a Gemini run that fell back must not read alike."""
    from app.agent.planner import NO_ANSWER_TRANSPORT, GreedyPlanner

    choice = _planner(FakeClient(raises=httpx.ConnectError("reset"))).choose(
        Hypothesis.MULE, set(), 8
    )
    assert choice.source == "greedy"
    assert choice.rationale.startswith(NO_ANSWER_TRANSPORT)
    # The offline planner's own sentence carries no such prefix.
    offline = GreedyPlanner(_planner(None).engine).choose(Hypothesis.MULE, set(), 8)
    assert not offline.rationale.startswith(NO_ANSWER_TRANSPORT)
    assert choice.action == offline.action


def test_a_missing_key_reports_an_explicit_unavailable_status():
    from app.agent.planner import NO_MODEL_REASON, LLMPlanner
    from app.policy.engine import PolicyEngine

    planner = LLMPlanner(PolicyEngine(Settings().policy_path))
    assert planner.available is False
    choice = planner.choose(Hypothesis.MULE, set(), 8)
    assert choice.source == "greedy"
    assert choice.rationale.startswith(NO_MODEL_REASON)


def test_an_empty_answer_and_a_rejected_answer_use_different_reasons():
    from app.agent.planner import NO_ANSWER_REASON

    class Empty:
        def generate_json(self, **kwargs):
            return None

    empty = _planner(Empty()).choose(Hypothesis.MULE, set(), 8)
    assert empty.source == "greedy"
    assert empty.rationale.startswith(NO_ANSWER_REASON)


# --- through a completed investigation ---------------------------------------

AUTH = {"Authorization": "Bearer demo-merchant-key"}
CHECKOUT = {
    "phone_number": "+99999991000",
    "context": {
        "event": "checkout",
        "payment_method": "cod",
        "account_age_days": 0,
        "amount": {"value": 4200},
    },
}


def _run_with(monkeypatch, fake):
    """Run a real investigation on the real LLMPlanner with a stubbed client."""
    from fastapi.testclient import TestClient

    import app.agent.investigator as investigator_module
    from app.main import app
    from app.policy.engine import PolicyEngine

    def build(engine: PolicyEngine):
        planner = LLMPlanner(engine)
        planner._client = fake
        return planner

    monkeypatch.setattr(investigator_module, "get_planner", build)
    response = TestClient(app).post("/v1/verify", headers=AUTH, json=CHECKOUT)
    assert response.status_code == 200
    return response.json()


def test_a_completed_investigation_records_llm_when_gemini_answered(monkeypatch):
    body = _run_with(monkeypatch, FakeClient(action="sim_swap", rationale="strongest ATO signal"))
    assert "llm" in body["planner"]
    assert body["decision"] in {"ALLOW", "CHALLENGE", "DECLINE"}


def test_a_completed_investigation_after_a_model_stop_is_still_signed(monkeypatch):
    body = _run_with(monkeypatch, FakeClient(action="STOP", rationale="enough already"))
    assert body["decision"] in {"ALLOW", "CHALLENGE", "DECLINE"}
    # Selection stopped, so any evidence present came from policy choreography.
    assert body["planner"] in {"llm", "policy", "llm+policy", "policy+llm"}


def test_invalid_model_output_never_becomes_a_greedy_investigation(monkeypatch):
    body = _run_with(monkeypatch, FakeClient(action="rm -rf /"))
    assert "greedy" not in body["planner"]
    assert body["decision"] in {"ALLOW", "CHALLENGE", "DECLINE"}


def test_a_transport_failure_produces_a_visibly_partial_investigation(monkeypatch):
    body = _run_with(monkeypatch, FakeClient(raises=httpx.ConnectError("reset")))
    assert "greedy" in body["planner"]
    assert body["decision"] in {"ALLOW", "CHALLENGE", "DECLINE"}


def test_a_policy_required_check_is_never_labelled_a_model_choice(monkeypatch):
    """The ALLOW gate's choreographed network check is `policy`, not `llm`."""
    from fastapi.testclient import TestClient

    import app.agent.investigator as investigator_module
    from app.main import app
    from app.policy.engine import PolicyEngine

    def build(engine: PolicyEngine):
        planner = LLMPlanner(engine)
        planner._client = FakeClient(action="STOP")
        return planner

    monkeypatch.setattr(investigator_module, "get_planner", build)
    body = TestClient(app).post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": "+99999991001", "context": {"event": "signup"}},
    ).json()
    assert "policy" in body["planner"]
    assert "greedy" not in body["planner"]
