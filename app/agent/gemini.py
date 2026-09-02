"""Small Gemini REST adapter shared by Isnad's optional AI features.

The hackathon Resource & Tooling Guide lists Google AI Studio / Gemini as a
runtime model provider. Keeping the integration here, on top of the project's
existing ``httpx`` dependency, avoids two failure modes: each agent feature
growing a different provider contract, and a missing SDK silently turning an
``llm`` demo into a greedy one.

The adapter intentionally knows nothing about decisions. Callers still validate
model output against their own schemas and fall back deterministically on every
transport, model, safety, or parsing failure.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx


class GeminiError(RuntimeError):
    """The provider did not return usable candidate text."""


class GeminiClient:
    """Minimal synchronous client for a single Gemini content-generation turn."""

    _BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str, timeout_seconds: float):
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate_json(self, system: str, prompt: str, max_tokens: int) -> dict[str, Any]:
        """Return a JSON object, or raise so the caller can use its fallback."""
        text = self._generate(system, prompt, max_tokens, response_mime_type="application/json")
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise GeminiError("Gemini returned JSON that was not an object")
        return parsed

    def generate_text(self, system: str, prompt: str, max_tokens: int) -> str:
        """Return candidate text for display-only explanation features."""
        return self._generate(system, prompt, max_tokens)

    def _generate(
        self,
        system: str,
        prompt: str,
        max_tokens: int,
        response_mime_type: str | None = None,
    ) -> str:
        # The model name is configuration, but it still becomes a URL path
        # segment. Quoting it keeps a malformed environment value from changing
        # the endpoint the process calls.
        model = quote(self._model, safe="-_.")
        body: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                # Gemini thinks by default, and thinking tokens are spent from
                # `maxOutputTokens`. Isnad's caps are deliberately small — 512
                # for a planner choice — so a thinking model can exhaust the
                # budget before it emits a single answer token and return a
                # candidate with no text. Every caller then takes its
                # deterministic fallback, and the run is entirely greedy while
                # still labelled `llm`. None of Isnad's asks need deliberation:
                # they are a constrained choice from an enumerated set and two
                # short pieces of display prose.
                #
                # The value is a small POSITIVE budget, not 0. Verified live on
                # 31 Aug: 2.5-series accepts 0, but `gemini-3.6-flash` rejects
                # it with 400 INVALID_ARGUMENT, and `thinkingLevel` does not
                # exist on v1beta at all. 128 is accepted by both and observed
                # to spend 0 thinking tokens — portable across the models this
                # is likely to be pointed at.
                "thinkingConfig": {"thinkingBudget": 128},
            },
        }
        if response_mime_type:
            body["generationConfig"]["responseMimeType"] = response_mime_type

        response = httpx.post(
            f"{self._BASE_URL}/{model}:generateContent",
            headers={"x-goog-api-key": self._api_key},
            json=body,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        return self._candidate_text(response.json())

    @staticmethod
    def _candidate_text(payload: Any) -> str:
        """Extract text only from a normal candidate; never invent an answer."""
        if not isinstance(payload, dict):
            raise GeminiError("Gemini returned a non-object response")
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            # A safety-blocked prompt or a provider error has no candidate. It
            # is no different from a timeout for Isnad: callers use their safe
            # deterministic path rather than guessing why.
            raise GeminiError("Gemini returned no candidate")
        first = candidates[0] if isinstance(candidates[0], dict) else {}
        # Carried into every error below: an empty candidate from a safety block
        # and one from an exhausted token budget look identical otherwise, and
        # they call for opposite fixes.
        reason = first.get("finishReason") or "no finishReason"
        content = first.get("content")
        parts = content.get("parts") if isinstance(content, dict) else None
        if not isinstance(parts, list):
            raise GeminiError(f"Gemini candidate had no text parts ({reason})")
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not text:
            raise GeminiError(f"Gemini candidate contained no text ({reason})")
        return text
