"""A stranger may not spend the deployment's whole model quota.

The public demo carries its own Gemini key so a judge can see the agent choose
without supplying one. That means an anonymous caller can point the deployment
at the model with a single header, and nothing about the request costs them
anything — the per-investigation cap is no help, because nothing caps
investigations.

So calls charged to the deployment's key are rationed by the hour. When the
ceiling is reached the run falls back to greedy and says so, which is the same
path taken when no key is configured at all.
"""

from __future__ import annotations

import pytest

from app import model_budget, runtime_keys
from app.config import settings


@pytest.fixture(autouse=True)
def _clean_budget():
    model_budget.reset()
    yield
    model_budget.reset()


# --- the ceiling binds on the deployment's own key ---------------------------


def test_the_deployment_key_stops_being_handed_out_once_the_hour_is_spent(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 3, False)

    assert runtime_keys.effective_gemini_key() == "SERVER-KEY"
    for _ in range(3):
        model_budget.note_model_call()

    assert model_budget.budget_exhausted() is True
    assert runtime_keys.effective_gemini_key() is None


def test_a_stranger_forcing_the_model_planner_cannot_outlast_the_ceiling(monkeypatch):
    """The exact reported exposure: one header, no key of their own."""
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 2, False)
    monkeypatch.setattr(settings, "planner", "greedy", False)

    token = runtime_keys.set_request_planner("llm")
    try:
        assert runtime_keys.effective_gemini_key() == "SERVER-KEY"
        model_budget.note_model_call()
        model_budget.note_model_call()
        # Same header, same caller, and now they get nothing.
        assert runtime_keys.effective_gemini_key() is None
    finally:
        runtime_keys.reset_request_planner(token)


def test_an_exhausted_budget_reports_greedy_rather_than_claiming_an_agent(monkeypatch):
    """A run must never advertise a planner that is not going to choose."""
    from app.agent.planner import effective_planner

    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 1, False)
    monkeypatch.setattr(settings, "planner", "llm", False)

    assert effective_planner() == "llm"
    model_budget.note_model_call()
    assert effective_planner() == "greedy"


# --- a reviewer's own key is theirs, and is not rationed ---------------------


def test_a_reviewer_supplied_key_is_never_counted(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 1, False)

    token = runtime_keys.set_request_gemini_key("REVIEWER-KEY")
    try:
        assert runtime_keys.uses_server_key() is False
        # However many they make, the deployment's ledger stays empty.
        assert model_budget.calls_in_window() == 0
        assert runtime_keys.effective_gemini_key() == "REVIEWER-KEY"
    finally:
        runtime_keys.reset_request_gemini_key(token)


def test_a_reviewer_key_still_works_after_the_deployment_is_exhausted(monkeypatch):
    """Their quota, their run. Our ceiling must not lock them out."""
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 1, False)
    model_budget.note_model_call()
    assert runtime_keys.effective_gemini_key() is None

    token = runtime_keys.set_request_gemini_key("REVIEWER-KEY")
    try:
        assert runtime_keys.effective_gemini_key() == "REVIEWER-KEY"
    finally:
        runtime_keys.reset_request_gemini_key(token)


# --- the default must not ration anybody's local run ------------------------


def test_zero_means_unlimited_so_a_local_run_is_untouched(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "SERVER-KEY", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 0, False)

    for _ in range(50):
        model_budget.note_model_call()

    assert model_budget.budget_exhausted() is False
    assert runtime_keys.effective_gemini_key() == "SERVER-KEY"


def test_the_shipped_default_is_unlimited():
    """A developer on their own key should not meet a rationing scheme."""
    from app.config import Settings

    assert Settings.model_fields["llm_max_calls_per_hour"].default == 0


def test_no_key_configured_is_still_simply_no_key(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "", False)
    monkeypatch.setattr(settings, "llm_max_calls_per_hour", 5, False)
    assert runtime_keys.uses_server_key() is False
    assert runtime_keys.effective_gemini_key() is None
