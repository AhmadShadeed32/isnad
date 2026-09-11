"""Step 4 — is the local mock actually the same contract as the hosted one?

The trap this file exists to avoid: generating the "expected" Nokia response
from Isnad's own normalizer and then asserting the normalizer produces it. That
tests the code against itself and passes forever.

So the expectations come from `tests/fixtures/nac_contract/expected_wire.json`,
hand-written from Nokia's public operation pages and the SDK's own
serialization, and every assertion below compares one of:

* what the SDK really put on the wire, against that file;
* what the application mock answered, against that file;
* the SAME response body fed through the application mock and through the real
  adapter's intercepted transport, against each other.

The last one is the parity claim itself. Anything it does not cover — a live
Gemini path, dynamic operator values, timing — is deliberately not asserted
here, because demanding byte-identical live output would only make this file
lie in a different direction.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from network_as_code import NetworkAsCodeApi

from app.domain.enums import Action
from app.domain.schemas import VerificationRequest
from app.judge import evidence
from app.providers import nac_contract
from app.providers.nac import NacProvider

EXPECTED = json.loads(
    (Path(__file__).parent / "fixtures" / "nac_contract" / "expected_wire.json").read_text(
        encoding="utf-8"
    )
)

ACTION_FOR = {"sim_swap_check": Action.SIM_SWAP, "device_swap_check": Action.DEVICE_SWAP}


def _mock_provider(scenario: str, *, fault: str | None = None):
    log = nac_contract.AttemptLog(budget=8)
    client = nac_contract.build_mock_client(scenario, log, fault=fault)
    provider = NacProvider(
        httpx_client=client,
        api_key=nac_contract.MOCK_API_KEY,
        source=nac_contract.MOCK_SOURCE,
        environment=nac_contract.MOCK_ENVIRONMENT,
        contract_version=nac_contract.contract_version(),
    )
    return provider, log, client


def _intercepted_adapter(payload, status=200):
    """The real adapter over a transport that replays one recorded body."""
    seen: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, json=payload)

    provider = object.__new__(NacProvider)
    provider.client = NetworkAsCodeApi(
        api_key="parity-test-only",
        httpx_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    provider.number_verification_token = None
    return provider, seen


# --- the manifest agrees with the independently written expectations ---------


def test_every_pinned_operation_matches_the_sourced_contract():
    for name, expected in EXPECTED["operations"].items():
        spec = nac_contract.contract()["operations"][name]
        assert spec["method"] == expected["method"]
        assert spec["path"] == expected["path"], f"{name} path drifted from its source"
        assert sorted(spec["request_fields"]) == sorted(expected["body_keys"])
        assert spec["request_fields"]["maxAge"]["units"] == expected["max_age_units"]
        assert [
            spec["request_fields"]["maxAge"]["minimum"],
            spec["request_fields"]["maxAge"]["maximum"],
        ] == expected["max_age_range"]


def test_every_scenario_response_matches_the_sourced_fixture():
    for scenario, expected in EXPECTED["scenarios"].items():
        spec = nac_contract.contract()["scenarios"][scenario]
        assert spec["phone_number"] == expected["phone_number"]
        for operation in ACTION_FOR:
            answer = spec["responses"][operation]
            assert answer["status"] == expected[operation]["status"]
            assert answer["body"] == expected[operation]["body"]


def test_every_fixture_names_a_source_and_a_coverage_level():
    """Drift is only visible if each case says where it came from."""
    manifest = nac_contract.contract()
    known = {source["id"] for source in manifest["sources"]}
    for name, spec in manifest["operations"].items():
        assert spec["sources"], f"{name} cites no source"
        assert set(spec["sources"]) <= known
    for scenario, spec in manifest["scenarios"].items():
        for operation, answer in spec["responses"].items():
            assert answer["coverage"] in {"documented_example", "sanitized_hosted_observation"}, (
                f"{scenario}/{operation} has no coverage level"
            )
    for name, case in manifest["fault_cases"].items():
        # An authored fault is never evidence that Nokia returned that error.
        assert case["coverage"] == "authored_fault_injection", name
        assert case["documented"]


# --- what the SDK really sends, through the application mock -----------------


@pytest.mark.parametrize("scenario", sorted(EXPECTED["scenarios"]))
@pytest.mark.parametrize("operation", sorted(ACTION_FOR))
@pytest.mark.asyncio
async def test_the_mock_sees_the_request_the_contract_describes(scenario, operation):
    provider, log, client = _mock_provider(scenario)
    handler = client._transport._inner.handler  # the ContractMock itself
    request = VerificationRequest(phone_number=EXPECTED["scenarios"][scenario]["phone_number"])

    await provider.gather(ACTION_FOR[operation], request)

    sent = handler.requests[-1]
    expected = EXPECTED["operations"][operation]
    assert sent.method == expected["method"]
    assert sent.url.path == expected["path"]
    body = json.loads(sent.content)
    assert sorted(body) == sorted(expected["body_keys"])
    assert body["phoneNumber"] == EXPECTED["scenarios"][scenario]["phone_number"]
    low, high = expected["max_age_range"]
    assert isinstance(body["maxAge"], int) and low <= body["maxAge"] <= high
    for header in expected["required_headers"]:
        assert sent.headers.get(header), f"{header} did not travel"
    assert log.count == 1


@pytest.mark.parametrize("scenario", sorted(EXPECTED["scenarios"]))
@pytest.mark.parametrize("operation", sorted(ACTION_FOR))
@pytest.mark.asyncio
async def test_both_true_and_false_normalize_as_the_source_says(scenario, operation):
    provider, _, _ = _mock_provider(scenario)
    action = ACTION_FOR[operation]
    request = VerificationRequest(phone_number=EXPECTED["scenarios"][scenario]["phone_number"])

    link = await provider.gather(action, request)

    expected = EXPECTED["scenarios"][scenario]["expected_normalization"][action.value]
    assert link.result.value == expected["result"]
    assert link.signal == expected["signal"]
    assert link.source == nac_contract.MOCK_SOURCE


# --- the parity claim itself -------------------------------------------------


@pytest.mark.parametrize("scenario", sorted(EXPECTED["scenarios"]))
@pytest.mark.parametrize("operation", sorted(ACTION_FOR))
@pytest.mark.asyncio
async def test_one_response_body_normalizes_identically_through_both_paths(scenario, operation):
    """The same bytes, through the application mock and through the adapter.

    Differences are limited to declared provenance and per-run timing. If this
    ever fails, the mock and the hosted path have stopped being the same
    contract, whatever the documentation says.
    """
    action = ACTION_FOR[operation]
    body = EXPECTED["scenarios"][scenario][operation]["body"]
    request = VerificationRequest(phone_number=EXPECTED["scenarios"][scenario]["phone_number"])

    mock_provider, _, _ = _mock_provider(scenario)
    through_mock = await mock_provider.gather(action, request)

    adapter, _ = _intercepted_adapter(body)
    through_adapter = await adapter.gather(action, request)

    declared_differences = {"source", "latency_ms", "at"}
    left = through_mock.model_dump()
    right = through_adapter.model_dump()
    for field in declared_differences:
        left.pop(field), right.pop(field)
    assert left == right
    assert through_mock.source == nac_contract.MOCK_SOURCE
    assert through_adapter.source == nac_contract.HOSTED_SOURCE


@pytest.mark.parametrize("case", sorted(EXPECTED["malformed"]))
@pytest.mark.asyncio
async def test_a_malformed_success_is_never_read_as_false(case):
    body = EXPECTED["malformed"][case]["body"]
    expected = EXPECTED["malformed"][case]["expected"]

    adapter, _ = _intercepted_adapter(body)
    link = await adapter.gather(Action.SIM_SWAP, VerificationRequest(phone_number="+99999991000"))

    assert link.result.value == expected["result"]
    assert link.signal == expected["signal"]
    # The claim that actually matters, stated separately so it cannot be
    # weakened by editing the expectation above.
    assert link.signal not in {"SIM_STABLE", "DEVICE_STABLE"}


@pytest.mark.parametrize("status", sorted(EXPECTED["errors"]))
@pytest.mark.asyncio
async def test_documented_error_statuses_stay_errors(status):
    expected = EXPECTED["errors"][status]["expected"]
    adapter, _ = _intercepted_adapter({"status": int(status), "message": "x"}, status=int(status))

    link = await adapter.gather(Action.SIM_SWAP, VerificationRequest(phone_number="+99999991000"))

    assert link.result.value == expected["result"]
    assert link.signal == expected["signal"]


@pytest.mark.asyncio
async def test_an_injected_fault_reaches_the_adapter_as_that_fault():
    """Authored fault cases are exercised through the same mock transport."""
    provider, log, _ = _mock_provider("swapped_subscriber", fault="sim_swap_unavailable")

    link = await provider.gather(
        Action.SIM_SWAP, VerificationRequest(phone_number="+99999991000")
    )

    assert link.signal == "PROVIDER_UNAVAILABLE"
    # The attempt happened and is counted. A failure is still an attempt.
    assert log.count == 1


# --- the mock refuses what it cannot answer ----------------------------------


def test_the_mock_refuses_an_unknown_path():
    handler = nac_contract.ContractMock("swapped_subscriber")
    request = httpx.Request(
        "POST",
        "https://example.invalid/passthrough/camara/v1/kyc-tenure/v0.1/check-tenure",
        json={"phoneNumber": "+99999991000"},
        headers={"x-rapidapi-key": "k", "x-rapidapi-host": "h"},
    )

    with pytest.raises(nac_contract.ContractMockError, match="no pinned contract"):
        handler(request)


def test_the_mock_refuses_a_request_with_no_gateway_credential():
    handler = nac_contract.ContractMock("swapped_subscriber")
    request = httpx.Request(
        "POST",
        "https://example.invalid/passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        json={"phoneNumber": "+99999991000", "maxAge": 240},
    )

    with pytest.raises(nac_contract.ContractMockError, match="x-rapidapi-key"):
        handler(request)


def test_the_mock_refuses_a_substituted_subscriber():
    """The submitted subject is preserved, never swapped for a working one."""
    handler = nac_contract.ContractMock("stable_subscriber")
    request = httpx.Request(
        "POST",
        "https://example.invalid/passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        json={"phoneNumber": "+99999991000", "maxAge": 240},
        headers={"x-rapidapi-key": "k", "x-rapidapi-host": "h"},
    )

    with pytest.raises(nac_contract.ContractMockError, match="asked about a different number"):
        handler(request)


def test_the_mock_refuses_an_out_of_range_window():
    handler = nac_contract.ContractMock("stable_subscriber")
    request = httpx.Request(
        "POST",
        "https://example.invalid/passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        json={"phoneNumber": "+99999991001", "maxAge": 99999},
        headers={"x-rapidapi-key": "k", "x-rapidapi-host": "h"},
    )

    with pytest.raises(nac_contract.ContractMockError, match="documented range"):
        handler(request)


# --- no egress, even with a proxy configured ---------------------------------


@pytest.mark.asyncio
async def test_mock_mode_makes_no_request_even_with_proxy_environment(monkeypatch):
    """The isolation claim, tested the way it can actually fail.

    An ambient proxy is read at client construction. If the mock client trusted
    the environment, "no requests are sent to Nokia" would be true only on
    machines with no proxy set.
    """
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")

    provider, log, client = _mock_provider("swapped_subscriber")
    assert client._mounts == {}, "an environment proxy was mounted on the mock client"

    link = await provider.gather(
        Action.SIM_SWAP, VerificationRequest(phone_number="+99999991000")
    )

    assert link.signal == "SIM_SWAPPED"
    assert log.count == 1
    assert isinstance(client._transport._inner, httpx.MockTransport)


@pytest.mark.asyncio
async def test_mock_mode_needs_no_nokia_credential(monkeypatch):
    """No Nokia account is required to run the mock source."""
    from app.config import settings

    monkeypatch.setattr(settings, "nac_api_key", None)

    ctx = evidence.RunContext(
        source=evidence.EvidenceSource.MOCK_NOKIA,
        scenario="stable_subscriber",
        contract_version=nac_contract.contract_version(),
        planner=evidence.JudgePlanner.GREEDY,
        policy_digest=evidence.policy_digest(),
        run_id="r",
        owner="judge:test",
    )
    provider, log = evidence.build_provider(ctx)

    link = await provider.gather(
        Action.SIM_SWAP, VerificationRequest(phone_number="+99999991001")
    )

    assert link.signal == "SIM_STABLE"
    assert log.count == 1


def test_the_paired_demo_has_no_date_enrichment_in_either_mode():
    """Optional date operations are disabled in BOTH modes, so the pair stays
    comparable — and without editing policy.yaml, which would have changed every
    other run in the deployment to make one demonstration match."""
    for source in evidence.EvidenceSource:
        ctx = evidence.RunContext(
            source=source,
            scenario="stable_subscriber",
            contract_version=nac_contract.contract_version(),
            planner=evidence.JudgePlanner.GREEDY,
            policy_digest=evidence.policy_digest(),
            run_id="r",
            owner="judge:test",
        )
        if source is evidence.EvidenceSource.NOKIA_SIMULATOR:
            from app.config import settings

            if not settings.nac_api_key:
                continue
        provider, _ = evidence.build_provider(ctx)
        assert not hasattr(provider, "enrich_timing"), source
