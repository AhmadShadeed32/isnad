"""A local HTTP transport that answers the real Nokia SDK.

The point of this module is what it is *not*: it is not a second normalizer and
not a hand-written verdict. `app/providers/nac_contract.json` holds Nokia-shaped
HTTP responses; the request that reaches this handler is the one
`network_as_code==10.0.0` actually serialized, and the response that leaves it
is parsed by the same SDK models and the same `NacProvider` code the hosted path
uses. So a mock run exercises the whole adapter, and the only declared
differences are provenance, timing and run identifiers.

The handler validates before it answers. An unknown method, path, header or
field is an explicit failure, never a catch-all success: a mock that answers
anything would stop being evidence that the request was right.

Nothing here reaches the network. `httpx.MockTransport` has no socket at all,
and `build_mock_client` builds its client with `trust_env=False` so an ambient
`HTTPS_PROXY` cannot introduce one.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

CONTRACT_PATH = Path(__file__).with_name("nac_contract.json")

# The credential the mock SDK client carries. It is a fixed non-secret string,
# checked for presence only: mock mode must work on a machine that has never
# had a Nokia key, and must never be able to spend a real one.
MOCK_API_KEY = "mock-nokia-contract-transport-key"

# What a mock answer is labelled as, everywhere it is recorded. Deliberately
# not "nac": reusing NacProvider must not leave its hosted provenance on a
# locally produced answer.
MOCK_SOURCE = "nac_contract_mock"
MOCK_ENVIRONMENT = "nokia_contract_mock"
HOSTED_SOURCE = "nac"
HOSTED_ENVIRONMENT = "nokia_hosted_simulator"


class ContractMockError(RuntimeError):
    """The mock was asked something its pinned contract does not cover."""


class AttemptBudgetExceeded(RuntimeError):
    """A run tried to make more outbound attempts than it reserved."""


@lru_cache(maxsize=1)
def contract() -> dict[str, Any]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def contract_version() -> str:
    return str(contract()["contract_version"])


def paired_scenarios() -> dict[str, dict[str, Any]]:
    return {
        name: body for name, body in contract()["scenarios"].items() if body.get("paired") is True
    }


def scenario_number(scenario: str) -> str:
    try:
        return str(contract()["scenarios"][scenario]["phone_number"])
    except KeyError as exc:  # pragma: no cover - callers validate first
        raise ContractMockError(f"no such contract scenario: {scenario!r}") from exc


def _operation_for(method: str, path: str) -> tuple[str, dict[str, Any]]:
    for name, spec in contract()["operations"].items():
        if spec["method"] == method and spec["path"] == path:
            return name, spec
    raise ContractMockError(f"no pinned contract for {method} {path}")


def _validate_headers(request: httpx.Request) -> None:
    """The gateway credential and host header must actually travel.

    Asserted here rather than assumed, because the whole reason this transport
    exists is to check the request Isnad builds. A mock that answered without
    them would hide the exact failure Aegis reported publicly.
    """
    for header in ("x-rapidapi-key", "x-rapidapi-host"):
        value = request.headers.get(header, "")
        if not value.strip():
            raise ContractMockError(f"request is missing the {header} header")


def _validate_body(operation: str, spec: dict[str, Any], body: Any) -> None:
    if not isinstance(body, dict):
        raise ContractMockError(f"{operation}: request body is not a JSON object")
    fields = spec["request_fields"]
    unknown = sorted(set(body) - set(fields))
    if unknown:
        raise ContractMockError(f"{operation}: unexpected request field(s) {unknown}")
    for name, rule in fields.items():
        if name not in body:
            if rule.get("required"):
                raise ContractMockError(f"{operation}: required field {name!r} is absent")
            continue
        value = body[name]
        if rule["type"] == "string":
            if not isinstance(value, str) or not value.startswith("+"):
                raise ContractMockError(f"{operation}: {name!r} must be an E.164 string")
        elif rule["type"] == "integer":
            # bool is an int in Python and would silently pass an isinstance
            # check; a boolean maxAge is not an hour count.
            if isinstance(value, bool) or not isinstance(value, int):
                raise ContractMockError(f"{operation}: {name!r} must be an integer")
            low, high = rule.get("minimum"), rule.get("maximum")
            if low is not None and high is not None and not low <= value <= high:
                raise ContractMockError(
                    f"{operation}: {name!r}={value} is outside the documented range {low}-{high}"
                )


@dataclass
class Attempt:
    """One outbound HTTP attempt, as the transport actually saw it."""

    operation: str
    method: str
    path: str
    status: int | None
    error: str | None
    duration_ms: int
    at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class AttemptLog:
    """Counts and bounds real outbound attempts, below the SDK and the agent.

    The UI step count and a `source=nac` label are both derived numbers; this
    is the only place that knows an HTTP request was actually made. A failed
    attempt keeps its slot, because the operator may already have received it.
    """

    def __init__(self, budget: int) -> None:
        self._lock = threading.Lock()
        self._budget = budget
        self._sealed = False
        self.attempts: list[Attempt] = []

    def reserve(self) -> None:
        with self._lock:
            if self._sealed:
                raise AttemptBudgetExceeded("this run has finished; no new attempt is allowed")
            if len(self.attempts) >= self._budget:
                raise AttemptBudgetExceeded(
                    f"this run may make at most {self._budget} outbound attempts"
                )
            # Reserved by appending a placeholder the caller then completes, so
            # two concurrent calls cannot both pass the check.
            self.attempts.append(
                Attempt(operation="", method="", path="", status=None, error="in flight",
                        duration_ms=0)
            )

    def seal(self) -> None:
        """Refuse late SDK work before signing and settling a finished run.

        Cancelling an asyncio wait does not stop an already running SDK thread.
        Every admitted request is counted before the lock is released; a thread
        arriving after settlement must never consume a refunded allowance slot.
        """
        with self._lock:
            self._sealed = True

    def complete(self, attempt: Attempt) -> None:
        with self._lock:
            for index in range(len(self.attempts) - 1, -1, -1):
                if self.attempts[index].error == "in flight":
                    self.attempts[index] = attempt
                    return
            self.attempts.append(attempt)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self.attempts)

    def as_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "operation": a.operation,
                    "method": a.method,
                    "path": a.path,
                    "status": a.status,
                    "error": a.error,
                    "duration_ms": a.duration_ms,
                    "at": a.at,
                }
                for a in self.attempts
            ]


class BoundedTransport(httpx.BaseTransport):
    """Wraps a transport so every attempt is reserved, counted and described.

    Identical in both modes: the mock's inner transport is an
    `httpx.MockTransport`, the hosted one is a real `httpx.HTTPTransport`, and
    the accounting around them is the same code. That is what makes the two
    modes' attempt counts comparable.
    """

    def __init__(self, inner: httpx.BaseTransport, log: AttemptLog) -> None:
        self._inner = inner
        self._log = log

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._log.reserve()
        started = datetime.now(UTC)
        try:
            operation = _describe(request)
        except ContractMockError:
            operation = "unknown"
        try:
            response = self._inner.handle_request(request)
        except Exception as exc:
            self._log.complete(
                Attempt(
                    operation=operation,
                    method=request.method,
                    path=request.url.path,
                    status=None,
                    error=type(exc).__name__,
                    duration_ms=_elapsed_ms(started),
                )
            )
            raise
        self._log.complete(
            Attempt(
                operation=operation,
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                error=None,
                duration_ms=_elapsed_ms(started),
            )
        )
        return response

    def close(self) -> None:  # pragma: no cover - delegated lifecycle
        self._inner.close()


def _elapsed_ms(started: datetime) -> int:
    return max(0, int((datetime.now(UTC) - started).total_seconds() * 1000))


def _describe(request: httpx.Request) -> str:
    name, _ = _operation_for(request.method, request.url.path)
    return name


class ContractMock:
    """The `httpx.MockTransport` handler for one pinned scenario.

    One instance serves one investigation. It holds no global state, mutates no
    settings and shares nothing with another judge's run.
    """

    def __init__(self, scenario: str, *, fault: str | None = None) -> None:
        scenarios = contract()["scenarios"]
        if scenario not in scenarios:
            raise ContractMockError(f"no such contract scenario: {scenario!r}")
        self.scenario = scenario
        self.spec = scenarios[scenario]
        self.fault = fault
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        _validate_headers(request)
        operation, spec = _operation_for(request.method, request.url.path)
        body = json.loads(request.content) if request.content else None
        _validate_body(operation, spec, body)

        expected = self.spec["phone_number"]
        supplied = (body or {}).get("phoneNumber")
        if supplied != expected:
            # The subject is preserved, never substituted. A run that asks
            # about a different number than the scenario declares is a bug in
            # the caller, not something to answer helpfully.
            raise ContractMockError(
                f"{operation}: scenario {self.scenario!r} is about {expected}, "
                f"but the request asked about a different number"
            )

        if self.fault is not None:
            case = contract()["fault_cases"].get(self.fault)
            if case is None:
                raise ContractMockError(f"no such fault case: {self.fault!r}")
            if case["operation"] == operation:
                return httpx.Response(case["status"], json=case["body"])

        answer = self.spec["responses"].get(operation)
        if answer is None:
            raise ContractMockError(
                f"scenario {self.scenario!r} has no pinned response for {operation}"
            )
        return httpx.Response(answer["status"], json=answer["body"])


def build_mock_client(scenario: str, log: AttemptLog, *, fault: str | None = None) -> httpx.Client:
    """An httpx client that cannot leave the process.

    `trust_env=False` is not decoration: with it left on, an ambient
    `HTTPS_PROXY` in the judge's environment is read at client construction,
    and "the mock made no request" would depend on the machine it ran on.
    """
    return httpx.Client(
        transport=BoundedTransport(httpx.MockTransport(ContractMock(scenario, fault=fault)), log),
        trust_env=False,
    )


def build_hosted_client(log: AttemptLog, timeout_seconds: float) -> httpx.Client:
    """The real transport, with the same accounting wrapped around it."""
    return httpx.Client(
        transport=BoundedTransport(httpx.HTTPTransport(retries=0), log),
        timeout=timeout_seconds,
        trust_env=False,
    )
