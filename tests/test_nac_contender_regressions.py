"""Regressions motivated by defects found in public peer projects.

`docs/NAC_CONTENDER_REVIEW.md` inspected two public entrants' source. None of
what follows is a claim about their current deployments; they are concrete
failure modes that were visible in the revisions reviewed, and the reason to
write them down as tests is that each one turns an outage or a refusal into a
clean, confident, wrong answer.

Four defects, four sections:

1. A wrapper substituting a known-working test number for an unsupported one.
2. A SIM function calling `retrieve-date` and reading a `swapped` field with a
   `false` default — so "no date field here" becomes "the SIM is stable".
3. An exception handler returning a safe-looking SIM result or a successful
   location match.
4. A global real-mode flag, with some evidence still coming from a mock, and one
   "live" label over the top of both.
"""

from __future__ import annotations

import httpx
import pytest
from network_as_code import NetworkAsCodeApi

from app.domain.enums import Action, Result
from app.domain.schemas import Area, RequestContext, VerificationRequest
from app.providers import nac_contract
from app.providers.nac import NacProvider

PHONE = "+99999991000"


def adapter(handler, *, token: str | None = None):
    provider = object.__new__(NacProvider)
    provider.client = NetworkAsCodeApi(
        api_key="regression-test-only",
        httpx_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider.number_verification_token = token
    return provider


def always(payload, status=200):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return handler


def exploding(exc: Exception):
    def handler(_request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


# --- 1. the submitted subscriber is the one that is asked about ---------------


def test_an_unsupported_scenario_is_refused_rather_than_answered_about_another_number(
    monkeypatch,
):
    """Never "that number has no scenario, so here is one that does"."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.judge.access import access as judge_access
    from app.main import create_app

    judge_access.clear()
    monkeypatch.setattr(settings, "judge_real_nac_enabled", False)
    client = TestClient(create_app())
    token = client.post("/v1/judge/session").json()["session"]

    response = client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": token},
        json={"evidence_source": "mock_nokia", "scenario": "replacement", "planner": "greedy"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_scenario"
    judge_access.clear()


@pytest.mark.asyncio
async def test_the_mock_transport_will_not_answer_about_a_different_subscriber():
    handler = nac_contract.ContractMock("swapped_subscriber")
    request = httpx.Request(
        "POST",
        "https://x.invalid/passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        json={"phoneNumber": "+99999991001", "maxAge": 240},
        headers={"x-rapidapi-key": "k", "x-rapidapi-host": "h"},
    )

    with pytest.raises(nac_contract.ContractMockError):
        handler(request)


# --- 2. a date response is not a boolean --------------------------------------


@pytest.mark.asyncio
async def test_a_date_only_response_never_produces_a_stable_sim_verdict():
    """`check` and `retrieve-date` are separate priced operations with separate
    contracts. Reading a `swapped` field off a date response — and defaulting it
    to False when it is absent, which it always is — reports a stable SIM every
    time the date call happens to succeed."""
    provider = adapter(always({"latestSimChange": "2026-09-01T10:00:00Z"}))

    link = await provider.gather(Action.SIM_SWAP, VerificationRequest(phone_number=PHONE))

    # The date body has no `swapped`, so the SDK's model refuses it and this is
    # an unavailable answer — not a PASS, and above all not SIM_STABLE.
    assert link.result is Result.INFO
    assert link.signal != "SIM_STABLE"
    assert link.result is not Result.PASS


@pytest.mark.asyncio
async def test_date_enrichment_cannot_change_the_boolean_it_sits_beside():
    """A date that arrived late, or disagreed, must not move a decision the
    boolean already made."""
    provider = adapter(always({"latestSimChange": "2026-09-01T10:00:00Z", "monitoredPeriod": 30}))

    timing = await provider.enrich_timing(
        Action.SIM_SWAP, VerificationRequest(phone_number=PHONE), "SIM_SWAPPED"
    )

    assert not hasattr(timing, "result")
    assert not hasattr(timing, "signal")


# --- 3. an exception is not a clean result ------------------------------------


@pytest.mark.parametrize(
    "action,forbidden",
    [
        (Action.SIM_SWAP, {"SIM_STABLE"}),
        (Action.DEVICE_SWAP, {"DEVICE_STABLE"}),
        (Action.LOCATION_VERIFY, {"AT_CLAIMED_LOCATION"}),
        (Action.ROAMING, {"HOME_NETWORK"}),
        (Action.REACHABILITY, {"REACHABLE_NORMAL"}),
    ],
)
@pytest.mark.asyncio
async def test_a_transport_exception_never_becomes_a_reassuring_signal(action, forbidden):
    provider = adapter(exploding(httpx.ConnectError("no route to host")))
    request = VerificationRequest(
        phone_number=PHONE,
        context=RequestContext(claimed_location=Area(lat=31.95, lon=35.91, radius_m=2000)),
    )

    link = await provider.gather(action, request)

    assert link.result is Result.INFO
    assert link.signal not in forbidden
    assert link.signal in {"PROVIDER_UNAVAILABLE", "EVIDENCE_UNAVAILABLE", "CONSENT_REQUIRED"}


@pytest.mark.asyncio
async def test_an_unavailable_number_verification_is_never_a_successful_match():
    """A phone number and a server API key are not proof of possession."""
    provider = adapter(always({"code": "UNAVAILABLE"}, status=503), token=None)

    link = await provider.gather(Action.NUMBER_VERIFY, VerificationRequest(phone_number=PHONE))

    assert link.result is Result.INFO
    assert link.signal != "NUMBER_MATCH"


# --- 4. one run, one honest source label --------------------------------------


def test_a_run_carries_exactly_the_source_it_used(monkeypatch):
    """A global "real mode" flag is not a per-item claim. Here the source is
    per run, frozen at acceptance, and it is what the chain reports."""
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.judge.access import access as judge_access
    from app.main import create_app

    judge_access.clear()
    monkeypatch.setattr(settings, "judge_real_nac_enabled", False)
    client = TestClient(create_app())
    token = client.post("/v1/judge/session").json()["session"]

    body = client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": token},
        json={
            "evidence_source": "mock_nokia",
            "scenario": "swapped_subscriber",
            "planner": "greedy",
        },
    ).json()

    # Exactly one source, and it is the mock one. Not "nac", not a mixture
    # reported under a single live badge.
    assert body["provider_sources"] == [nac_contract.MOCK_SOURCE]
    assert body["judge"]["evidence_environment"] == nac_contract.MOCK_ENVIRONMENT
    judge_access.clear()


@pytest.mark.asyncio
async def test_reusing_the_adapter_locally_does_not_leave_hosted_provenance_on_it():
    """The defect this guards: `source` used to be the constant "nac", so the
    moment the same adapter answered a local transport, a locally produced
    result was labelled as a Nokia one."""
    log = nac_contract.AttemptLog(budget=2)
    provider = NacProvider(
        httpx_client=nac_contract.build_mock_client("swapped_subscriber", log),
        api_key=nac_contract.MOCK_API_KEY,
        source=nac_contract.MOCK_SOURCE,
        environment=nac_contract.MOCK_ENVIRONMENT,
        contract_version=nac_contract.contract_version(),
    )

    link = await provider.gather(Action.SIM_SWAP, VerificationRequest(phone_number=PHONE))

    assert link.source == nac_contract.MOCK_SOURCE
    assert link.source != nac_contract.HOSTED_SOURCE


def test_a_client_constructor_is_not_a_request():
    """Building a client contacts nobody. A readiness badge derived from it is
    a configuration statement, and the code says so in those words."""
    log = nac_contract.AttemptLog(budget=2)
    NacProvider(
        httpx_client=nac_contract.build_mock_client("stable_subscriber", log),
        api_key=nac_contract.MOCK_API_KEY,
        source=nac_contract.MOCK_SOURCE,
        environment=nac_contract.MOCK_ENVIRONMENT,
    )

    assert log.count == 0


# --- the measurement script cannot reach an operator -------------------------


def test_the_planner_comparison_cannot_open_a_hosted_transport(monkeypatch):
    """`ISNAD_PROVIDER=mock` does not cover this on its own.

    The judge path builds its own provider and never consults that setting, so
    a measurement script importing it could open a real transport through
    ambient configuration. The script closes that door explicitly; this asserts
    the door is closed rather than trusting the comment that says so.
    """
    import importlib

    import scripts.planner_divergence as divergence

    importlib.reload(divergence)
    original = nac_contract.build_hosted_client
    try:
        divergence._forbid_hosted_transport()
        with pytest.raises(RuntimeError, match="never open a hosted Nokia transport"):
            nac_contract.build_hosted_client(nac_contract.AttemptLog(budget=1), 8.0)
    finally:
        nac_contract.build_hosted_client = original
