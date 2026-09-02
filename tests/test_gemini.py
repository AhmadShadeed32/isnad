"""Gemini adapter and runtime-dependency regression tests.

No test here contacts Google. The client is exercised against a tiny HTTP stub;
planner and explanation tests inject their own adapter fakes in
``test_llm_planner.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.gemini import GeminiClient, GeminiError


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.checked = False

    def raise_for_status(self):
        self.checked = True

    def json(self):
        return self._payload


def test_json_generation_uses_the_gemini_rest_contract(monkeypatch):
    seen = {}
    response = _Response({"candidates": [{"content": {"parts": [{"text": '{"action":"STOP"}'}]}}]})

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen.update(kwargs)
        return response

    monkeypatch.setattr("app.agent.gemini.httpx.post", fake_post)
    result = GeminiClient("test-key", "gemini-2.5-flash", 3.0).generate_json(
        system="system rules", prompt='{"safe":true}', max_tokens=128
    )

    assert result == {"action": "STOP"}
    assert response.checked is True
    assert seen["url"].endswith("/gemini-2.5-flash:generateContent")
    assert seen["headers"]["x-goog-api-key"] == "test-key"
    assert seen["timeout"] == 3.0
    assert seen["json"]["systemInstruction"]["parts"] == [{"text": "system rules"}]
    assert seen["json"]["contents"][0]["parts"] == [{"text": '{"safe":true}'}]
    assert seen["json"]["generationConfig"] == {
        "maxOutputTokens": 128,
        "thinkingConfig": {"thinkingBudget": 128},
        "responseMimeType": "application/json",
    }


def test_missing_candidate_is_an_error_not_an_invented_answer(monkeypatch):
    monkeypatch.setattr(
        "app.agent.gemini.httpx.post", lambda *args, **kwargs: _Response({"promptFeedback": {}})
    )
    client = GeminiClient("test-key", "gemini-2.5-flash", 3.0)

    with pytest.raises(GeminiError, match="no candidate"):
        client.generate_text(system="rules", prompt="data", max_tokens=20)


def test_production_runtime_has_no_anthropic_dependency():
    """The production runtime uses only its configured provider client."""
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "app" / "agent",
        root / "app" / "config.py",
        root / "requirements.txt",
        root / "requirements.lock.txt",
        root / "pyproject.toml",
        root / "Dockerfile",
        root / ".env.example",
    ]
    forbidden = "anthropic"
    for path in paths:
        files = path.rglob("*.py") if path.is_dir() else [path]
        for file in files:
            assert forbidden not in file.read_text(encoding="utf-8").lower(), file


def test_thinking_is_disabled_so_the_token_budget_buys_an_answer(monkeypatch):
    """`gemini-2.5-flash` thinks by default, and thinking tokens are spent from
    `maxOutputTokens`. Isnad's caps are small on purpose (512 for a planner
    choice), so a default-thinking model can burn the whole budget reasoning and
    return a candidate with no text at all — which this adapter correctly turns
    into a GeminiError, which every caller correctly turns into its
    deterministic fallback. The result is an all-greedy run wearing an `llm`
    label: the exact silent degrade the suite cannot see, because every test
    here fakes the transport."""
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs)
        return _Response({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    monkeypatch.setattr("app.agent.gemini.httpx.post", fake_post)
    GeminiClient("test-key", "gemini-2.5-flash", 3.0).generate_text(
        system="rules", prompt="data", max_tokens=512
    )

    # A small POSITIVE budget, never 0: gemini-3.6-flash rejects 0 outright
    # with 400 INVALID_ARGUMENT, so the "disable thinking" value that works on
    # 2.5 takes the whole demo down on 3.x.
    assert seen["json"]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 128}


def test_an_exhausted_budget_is_diagnosable(monkeypatch):
    """The failure above is indistinguishable from a safety block unless the
    finish reason survives into the error. This path has never run against the
    live provider, so the first real failure has to explain itself."""
    monkeypatch.setattr(
        "app.agent.gemini.httpx.post",
        lambda *args, **kwargs: _Response(
            {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]}
        ),
    )
    client = GeminiClient("test-key", "gemini-2.5-flash", 3.0)

    with pytest.raises(GeminiError, match="MAX_TOKENS"):
        client.generate_text(system="rules", prompt="data", max_tokens=20)
