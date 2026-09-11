"""Steps 5, 6 and 12 — the judge's source choice, its guards, and its failures.

Everything here runs against intercepted transports. No Nokia credential, no
Gemini credential and no outbound request is involved, which is the only way a
suite can assert "this would not have spent anything" honestly.

The questions this file answers, in order: can an unauthorized caller reach the
real path (no), can a public demo token become one (no), can two judges see
each other's evidence, quota, receipts or journals (no), can a mock key replay
as a real result (no), and does every failure in the interrupted-demo matrix
leave the original run truthful.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import demo_token
from app.config import settings
from app.judge.access import access as judge_access
from app.providers import nac_contract

ACCESS_CODE = "organizer-code-for-tests"


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    """Each test starts with no sessions, no spend and no shared limiter state."""
    judge_access.clear()
    demo_token.clear()
    from app.api import rate_limit

    rate_limit.per_key.reset()
    rate_limit.per_ip.reset()
    monkeypatch.setattr(settings, "judge_access_codes", ACCESS_CODE)
    monkeypatch.setattr(settings, "judge_real_nac_enabled", True)
    monkeypatch.setattr(settings, "nac_api_key", "server-held-key-never-in-a-page")
    monkeypatch.setattr(settings, "planner", "greedy")
    monkeypatch.setattr(settings, "gemini_api_key", None)
    yield
    judge_access.clear()


@pytest.fixture
def client():
    from app.main import create_app

    return TestClient(create_app())


class HostedSpy:
    """Stands in for Nokia's hosted simulator, so no real request is made.

    It answers with the same pinned bodies the mock serves, which is exactly
    what makes a "the real path produced a different label" assertion mean
    something: the bytes are identical, so only provenance can differ.
    """

    def __init__(self, scenario: str = "swapped_subscriber", status: int | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self._scenario = scenario
        self._status = status

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self._status is not None:
            return httpx.Response(self._status, json={"status": self._status, "message": "x"})
        spec = nac_contract.contract()["scenarios"][self._scenario]
        for name, operation in nac_contract.contract()["operations"].items():
            if operation["path"] == request.url.path:
                answer = spec["responses"][name]
                return httpx.Response(answer["status"], json=answer["body"])
        raise AssertionError(f"unexpected hosted request: {request.url.path}")


@pytest.fixture
def hosted(monkeypatch):
    spy = HostedSpy()

    def build(log, timeout_seconds):
        return httpx.Client(
            transport=nac_contract.BoundedTransport(httpx.MockTransport(spy), log),
            trust_env=False,
        )

    monkeypatch.setattr(nac_contract, "build_hosted_client", build)
    return spy


def start(client) -> str:
    return client.post("/v1/judge/session").json()["session"]


def authorize(client, token: str) -> None:
    response = client.post(
        "/v1/judge/access", headers={"X-Judge-Session": token}, json={"access_code": ACCESS_CODE}
    )
    assert response.status_code == 200, response.text


def run(client, token, source="mock_nokia", scenario="swapped_subscriber", **headers):
    return client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": token, **headers},
        json={"evidence_source": source, "scenario": scenario, "planner": "greedy"},
    )


def allowance(client, token) -> dict:
    """What this session has left, read the way the page reads it."""
    response = client.get("/v1/judge/capabilities", headers={"X-Judge-Session": token})
    return response.json()["allowance"]


# --- authorization -----------------------------------------------------------


def test_minting_sessions_cannot_bypass_ip_limits_with_forged_headers(client, monkeypatch):
    from app.api import rate_limit

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(rate_limit.per_ip, "limit", 1)
    first = client.post("/v1/judge/session", headers={"Authorization": "Bearer invented-one"})
    second = client.post("/v1/judge/session", headers={"Authorization": "Bearer invented-two"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_forged_authorization_cannot_reset_a_judges_access_attempt_limit(client, monkeypatch):
    from app.api import rate_limit

    token = start(client)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(rate_limit.per_key, "limit", 1)
    statuses = [
        client.post(
            "/v1/judge/access",
            headers={"X-Judge-Session": token, "Authorization": f"Bearer invented-{index}"},
            json={"access_code": "incorrect-code"},
        ).status_code
        for index in range(2)
    ]
    assert statuses == [403, 429]


def test_mock_runs_immediately_with_no_code_at_all(client):
    """A judge must not have to ask anyone to see the demonstration."""
    token = start(client)

    response = run(client, token)

    assert response.status_code == 200
    body = response.json()
    assert body["judge"]["evidence_source"] == "mock_nokia"
    assert body["judge"]["evidence_environment"] == "nokia_contract_mock"
    assert body["provider_sources"] == ["nac_contract_mock"]


def test_real_without_the_capability_is_refused_before_anything_is_spent(client, hosted):
    token = start(client)

    response = run(client, token, source="nokia_simulator")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "nac_capability_required"
    assert hosted.requests == [], "a refused request must not reach the operator"


def test_selecting_a_mode_is_not_authorization_and_makes_no_request(client, hosted):
    """Reading capabilities, or choosing in the dropdown, contacts nobody."""
    token = start(client)

    capabilities = client.get("/v1/judge/capabilities", headers={"X-Judge-Session": token})

    assert capabilities.status_code == 200
    assert capabilities.json()["readiness"] == "configured_connection_not_verified"
    assert hosted.requests == []


def test_a_public_demo_token_can_never_become_a_judge_session(client, monkeypatch):
    """R12's guard, restated for the new path.

    A demo token authorizes the console's fixtures. It is not a judge session,
    and it cannot be presented as one to reach a billable request.
    """
    monkeypatch.setattr(settings, "demo_mode", True)
    minted = demo_token.mint()

    response = run(client, minted, source="nokia_simulator")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "judge_session_required"


def test_a_wrong_access_code_does_not_grant_the_capability(client, hosted):
    token = start(client)

    response = client.post(
        "/v1/judge/access",
        headers={"X-Judge-Session": token},
        json={"access_code": "not-the-code"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "invalid_access_code"
    assert run(client, token, source="nokia_simulator").status_code == 403
    assert hosted.requests == []


def test_real_mode_disabled_says_so_and_leaves_mock_usable(client, monkeypatch, hosted):
    monkeypatch.setattr(settings, "judge_real_nac_enabled", False)
    token = start(client)

    refused = run(client, token, source="nokia_simulator")

    assert refused.status_code == 503
    assert refused.json()["detail"]["code"] == "real_source_disabled"
    assert hosted.requests == []
    assert run(client, token).status_code == 200


def test_an_unknown_mode_is_refused_not_silently_ignored(client):
    token = start(client)

    response = client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": token},
        json={"evidence_source": "live_network", "scenario": "swapped_subscriber"},
    )

    assert response.status_code == 422


def test_an_unknown_field_is_refused_rather_than_dropped(client):
    """A field Pydantic silently ignores is how a request asks for one thing
    and gets whatever the global provider was configured for."""
    token = start(client)

    response = client.post(
        "/v1/judge/run",
        headers={"X-Judge-Session": token},
        json={
            "evidence_source": "mock_nokia",
            "scenario": "swapped_subscriber",
            "phone_number": "+962790000001",
        },
    )

    assert response.status_code == 422


def test_a_custom_mock_story_is_not_selectable_as_a_paired_case(client):
    token = start(client)

    response = run(client, token, scenario="replacement")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "unsupported_scenario"


# --- the real path, over an intercepted transport ----------------------------


def test_an_authorized_real_run_uses_the_hosted_transport_and_says_so(client, hosted):
    token = start(client)
    authorize(client, token)

    response = run(client, token, source="nokia_simulator")

    assert response.status_code == 200
    body = response.json()
    assert body["judge"]["evidence_source"] == "nokia_simulator"
    assert body["judge"]["evidence_environment"] == "nokia_hosted_simulator"
    assert body["provider_sources"] == ["nac"]
    assert len(hosted.requests) == body["judge"]["outbound_attempts"] == 2
    for request in hosted.requests:
        assert request.headers.get("x-rapidapi-key")
        assert request.headers.get("x-rapidapi-host")


def test_the_real_path_sends_to_the_host_that_has_actually_answered(client, hosted):
    """Asserted, not assumed. The SDK's own default host has never returned
    anything to this account; the catalog host has. A `base_url` a model
    accepts is not proof the request went there."""
    token = start(client)
    authorize(client, token)

    run(client, token, source="nokia_simulator")

    assert hosted.requests, "no request was made"
    for request in hosted.requests:
        assert str(request.url).startswith(settings.judge_nac_base_url), str(request.url)
        assert request.headers["x-rapidapi-host"] == settings.nac_rapidapi_host


def test_the_two_modes_reach_the_same_decision_on_the_same_scenario(client, hosted):
    """Same pinned bodies, same planner, same policy: only provenance differs."""
    token = start(client)
    authorize(client, token)

    mock_run = run(client, token, source="mock_nokia").json()
    real_run = run(client, token, source="nokia_simulator").json()

    assert mock_run["decision"] == real_run["decision"]
    assert mock_run["chain_grade"] == real_run["chain_grade"]
    assert mock_run["evidence_steps"] == real_run["evidence_steps"]
    assert mock_run["provider_sources"] != real_run["provider_sources"]


def test_the_run_buys_only_the_two_paired_checks(client, hosted):
    token = start(client)
    authorize(client, token)

    body = run(client, token, source="nokia_simulator").json()

    paths = {request.url.path for request in hosted.requests}
    assert paths == {
        "/passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        "/passthrough/camara/v1/device-swap/device-swap/v1/check",
    }
    assert body["judge"]["outbound_attempts"] <= settings.judge_nac_attempts_per_run
    # No `retrieve-date` in either mode: the optional priced operation is off,
    # so the two modes stay comparable.
    assert not any("retrieve-date" in path for path in paths)


# --- cross-mode identity -----------------------------------------------------


def test_replaying_a_mock_key_in_real_mode_is_a_conflict(client, hosted):
    token = start(client)
    authorize(client, token)
    before = allowance(client, token)
    first = run(client, token, source="mock_nokia", **{"Idempotency-Key": "one-key"})
    assert first.status_code == 200

    replayed = run(client, token, source="nokia_simulator", **{"Idempotency-Key": "one-key"})

    assert replayed.status_code == 409
    assert replayed.json()["detail"]["code"] == "idempotency_key_reused"
    assert hosted.requests == [], "a conflicting replay must not buy anything"
    after = allowance(client, token)
    # A refusal is not a spend. The reservation is taken before the idempotency
    # guard can answer, so a judge who reuses one key across the two modes would
    # otherwise be charged a whole run for a request that never left the process.
    assert after["session_attempts_left"] == before["session_attempts_left"]
    assert after["active_real_runs"] == 0


def test_replaying_the_same_mode_and_key_spends_nothing(client, hosted):
    token = start(client)
    authorize(client, token)
    first = run(client, token, source="nokia_simulator", **{"Idempotency-Key": "same"})
    assert first.status_code == 200
    spent = len(hosted.requests)

    again = run(client, token, source="nokia_simulator", **{"Idempotency-Key": "same"})

    assert again.status_code == 200
    assert again.json()["chain_id"] == first.json()["chain_id"]
    assert again.json()["judge"]["replayed"] is True
    assert len(hosted.requests) == spent


# --- isolation between judges ------------------------------------------------


def test_two_judges_run_different_modes_without_sharing_anything(client, hosted):
    first, second = start(client), start(client)
    authorize(client, first)

    real = run(client, first, source="nokia_simulator")
    mock = run(client, second, source="mock_nokia")

    assert real.json()["provider_sources"] == ["nac"]
    assert mock.json()["provider_sources"] == ["nac_contract_mock"]
    assert real.json()["chain_id"] != mock.json()["chain_id"]
    # The second judge never gained the capability from the first.
    assert run(client, second, source="nokia_simulator").status_code == 403


def test_one_judge_cannot_read_another_judges_chain(client):
    first, second = start(client), start(client)
    chain_id = run(client, first).json()["chain_id"]

    mine = client.get(f"/v1/chains/{chain_id}", headers={"X-Judge-Session": first})
    theirs = client.get(f"/v1/chains/{chain_id}", headers={"X-Judge-Session": second})

    assert mine.status_code == 200
    assert theirs.status_code == 404


def test_one_judge_cannot_recover_another_judges_journal(client):
    first, second = start(client), start(client)
    run(client, first, **{"X-Console-Run-Id": "judge-run-a"})

    mine = client.get(
        "/v1/console/runs/judge-run-a/events", headers={"X-Judge-Session": first}
    )
    theirs = client.get(
        "/v1/console/runs/judge-run-a/events", headers={"X-Judge-Session": second}
    )

    assert mine.status_code == 200 and mine.json()["events"]
    assert theirs.status_code == 200 and theirs.json()["events"] == []


def test_a_judge_session_is_not_a_merchant_key(client):
    """It authorizes the demonstration and nothing else."""
    token = start(client)

    response = client.post(
        "/v1/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone_number": "+99999991000"},
    )

    assert response.status_code == 403


# --- allowances --------------------------------------------------------------


def test_overlapping_runs_from_one_judge_each_keep_their_spend(client, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    # Both investigations reserve before either finishes. Synchronize at each
    # HTTP operation so this exercises the route's actual reservation lifecycle.
    barrier = Barrier(2)
    spy = HostedSpy()

    def answer(request):
        barrier.wait(timeout=5)
        return spy(request)

    monkeypatch.setattr(
        nac_contract, "build_hosted_client",
        lambda log, timeout_seconds: httpx.Client(
            transport=nac_contract.BoundedTransport(httpx.MockTransport(answer), log),
            trust_env=False,
        ),
    )
    token = start(client)
    authorize(client, token)
    before = allowance(client, token)
    with ThreadPoolExecutor(max_workers=2) as workers:
        pending = [workers.submit(run, client, token, "nokia_simulator") for _ in range(2)]
        results = [future.result(timeout=15) for future in pending]

    assert all(response.status_code == 200 for response in results)
    assert len(spy.requests) == 4
    after = allowance(client, token)
    assert before["session_attempts_left"] - after["session_attempts_left"] == 4
    assert before["deployment_attempts_left"] - after["deployment_attempts_left"] == 4
    assert after["active_real_runs"] == 0


def test_refunding_one_run_preserves_another_judges_hourly_charge(monkeypatch):
    from app.judge import access as access_module

    now = [1000.0]
    monkeypatch.setattr(access_module.time, "time", lambda: now[0])
    first, second = judge_access.mint(), judge_access.mint()
    judge_access.grant_nac(first.token, ACCESS_CODE)
    judge_access.grant_nac(second.token, ACCESS_CODE)
    earlier = judge_access.reserve_real_run(first, 2)
    now[0] += 10
    later = judge_access.reserve_real_run(second, 2)
    judge_access.settle_real_run(second, later, 2, clean=True)
    judge_access.settle_real_run(first, earlier, 0, clean=True)
    # Settling the same reservation twice cannot release another run's slots.
    judge_access.settle_real_run(first, earlier, 0, clean=True)
    now[0] = 4605.0
    assert judge_access.snapshot(second)["deployment_attempts_left"] == (
        settings.judge_nac_attempts_per_hour - 2
    )


def test_a_settled_run_cannot_send_late_sdk_requests():
    requests = []
    log = nac_contract.AttemptLog(budget=2)
    transport = nac_contract.BoundedTransport(
        httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(200)),
        log,
    )
    log.seal()
    with httpx.Client(transport=transport) as client, pytest.raises(nac_contract.AttemptBudgetExceeded):
        client.post("https://example.invalid/check")
    assert requests == []
    assert log.count == 0


def test_a_judges_session_allowance_stops_further_real_runs(client, hosted, monkeypatch):
    monkeypatch.setattr(settings, "judge_nac_attempts_per_session", 2)
    token = start(client)
    authorize(client, token)
    assert run(client, token, source="nokia_simulator").status_code == 200
    spent = len(hosted.requests)

    refused = run(client, token, source="nokia_simulator")

    assert refused.status_code == 429
    assert refused.json()["detail"]["code"] == "judge_allowance_exhausted"
    assert len(hosted.requests) == spent
    # Prior results are unaffected and mock remains available.
    assert run(client, token, source="mock_nokia").status_code == 200


def test_the_deployment_allowance_stops_every_judge(client, hosted, monkeypatch):
    monkeypatch.setattr(settings, "judge_nac_attempts_per_hour", 2)
    first, second = start(client), start(client)
    authorize(client, first)
    authorize(client, second)
    assert run(client, first, source="nokia_simulator").status_code == 200

    refused = run(client, second, source="nokia_simulator")

    assert refused.status_code == 429
    assert refused.json()["detail"]["code"] == "deployment_allowance_exhausted"


def test_a_failed_real_run_keeps_its_attempted_spend(client, monkeypatch):
    """An operator that may already have received the request is still spent."""
    spy = HostedSpy(status=503)

    def build(log, timeout_seconds):
        return httpx.Client(
            transport=nac_contract.BoundedTransport(httpx.MockTransport(spy), log),
            trust_env=False,
        )

    monkeypatch.setattr(nac_contract, "build_hosted_client", build)
    monkeypatch.setattr(settings, "judge_nac_attempts_per_session", 3)
    token = start(client)
    authorize(client, token)

    body = run(client, token, source="nokia_simulator").json()

    # The failure is reported as a failure, with its real source kept.
    assert body["provider_sources"] == ["nac"]
    assert body["judge"]["evidence_environment"] == "nokia_hosted_simulator"
    assert body["judge"]["outbound_attempts"] >= 1
    left = body["judge"]["allowance"]["session_attempts_left"]
    assert left < 3, "a failed attempt must not be refunded"


def test_a_failure_to_build_the_adapter_still_settles_the_run(client, monkeypatch):
    """An unsettled reservation would hold the only real-run slot forever.

    The attempts stay spent — this service cannot prove what a half-built
    adapter did — but the concurrency slot has to come back, or one unlucky
    judge closes the real path for everyone after them.
    """
    from app.judge import evidence as judge_evidence

    def explode(ctx, fault=None):
        raise RuntimeError("no SDK on this deployment")

    monkeypatch.setattr(judge_evidence, "build_provider", explode)
    token = start(client)
    authorize(client, token)

    with pytest.raises(RuntimeError):
        run(client, token, source="nokia_simulator")

    assert allowance(client, token)["active_real_runs"] == 0


def test_a_replay_and_a_capabilities_read_are_free_of_new_operations(client, hosted):
    token = start(client)
    authorize(client, token)
    run(client, token, source="nokia_simulator", **{"Idempotency-Key": "free"})
    spent = len(hosted.requests)

    client.get("/v1/judge/capabilities", headers={"X-Judge-Session": token})
    run(client, token, source="nokia_simulator", **{"Idempotency-Key": "free"})

    assert len(hosted.requests) == spent


# --- the interrupted-demo matrix (Step 12) -----------------------------------


def test_a_real_failure_is_never_replaced_by_mock_evidence(client, monkeypatch):
    spy = HostedSpy(status=503)

    def build(log, timeout_seconds):
        return httpx.Client(
            transport=nac_contract.BoundedTransport(httpx.MockTransport(spy), log),
            trust_env=False,
        )

    monkeypatch.setattr(nac_contract, "build_hosted_client", build)
    token = start(client)
    authorize(client, token)

    body = run(client, token, source="nokia_simulator").json()

    assert "nac_contract_mock" not in body["provider_sources"]
    assert body["judge"]["evidence_source"] == "nokia_simulator"


def test_running_in_mock_after_a_failure_is_a_new_distinct_run(client, monkeypatch):
    spy = HostedSpy(status=503)

    def build(log, timeout_seconds):
        return httpx.Client(
            transport=nac_contract.BoundedTransport(httpx.MockTransport(spy), log),
            trust_env=False,
        )

    monkeypatch.setattr(nac_contract, "build_hosted_client", build)
    token = start(client)
    authorize(client, token)
    failed = run(
        client, token, source="nokia_simulator", **{"Idempotency-Key": "failed-run"}
    ).json()

    retried = run(client, token, source="mock_nokia", **{"Idempotency-Key": "mock-retry"}).json()

    assert retried["chain_id"] != failed["chain_id"]
    assert retried["judge"]["evidence_source"] == "mock_nokia"
    # The original stays separately readable, with its own honest label.
    original = client.get(
        f"/v1/chains/{failed['chain_id']}", headers={"X-Judge-Session": token}
    )
    assert original.status_code == 200
    assert original.json()["provider_sources"] == ["nac"]


def test_an_expired_session_cannot_run_and_nothing_is_attempted(client, hosted, monkeypatch):
    token = start(client)
    authorize(client, token)
    record = judge_access.get(token)
    record.expires_at = 0.0

    response = run(client, token, source="nokia_simulator")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "judge_session_required"
    assert hosted.requests == []


def test_the_transport_budget_bounds_attempts_below_the_agent(client, monkeypatch):
    """The count that matters is the transport's, not the UI's step count."""
    log = nac_contract.AttemptLog(budget=1)
    log.reserve()
    log.complete(
        nac_contract.Attempt(
            operation="sim_swap_check",
            method="POST",
            path="/x",
            status=200,
            error=None,
            duration_ms=1,
        )
    )

    with pytest.raises(nac_contract.AttemptBudgetExceeded):
        log.reserve()


# --- signed provenance -------------------------------------------------------


def test_the_source_is_inside_the_signature_not_beside_it(client, hosted):
    token = start(client)
    authorize(client, token)
    chain_id = run(client, token, source="nokia_simulator").json()["chain_id"]

    from app.db import store
    from app.events import current_owner
    from app.judge.access import owner_for_token

    current_owner.set(owner_for_token(token))
    record = store.get_record(chain_id)

    assert record is not None
    assert '"evidence_source":"nac"' in record.verdict_json
    assert '"evidence_environment":"nokia_hosted_simulator"' in record.verdict_json
    assert nac_contract.contract_version() in record.verdict_json
    verification = client.get(
        f"/v1/chains/{chain_id}/verification", headers={"X-Judge-Session": token}
    ).json()
    assert verification["valid"] is True


def test_a_chain_signed_before_provenance_existed_reads_back_as_unknown():
    """"" is NOT mock and NOT hosted. A reader that cannot tell says unknown."""
    from app.chain.models import Verdict

    old = Verdict.model_validate_json(
        '{"decision":"ALLOW","confidence":0.1,"hypothesis":"legit","reason":"x","chain_id":"c1"}'
    )

    assert old.evidence_source == ""
    assert old.evidence_environment == ""
    assert old.contract_version == ""
    assert old.outbound_attempts == 0


def test_a_greedy_run_is_never_labelled_as_a_gemini_demonstration(client):
    token = start(client)

    body = run(client, token).json()

    assert body["planner"] in {"greedy", "policy"}
    assert body["judge"]["planner_requested"] == "greedy"


# --- the merchant's follow-up on a CHALLENGE (Step 10) -----------------------


def _challenged_chain(client, token) -> str:
    body = run(client, token, scenario="stable_subscriber").json()
    assert body["decision"] == "CHALLENGE", body["decision"]
    return body["chain_id"]


def test_a_judge_completes_their_own_follow_up_without_a_merchant_key(client):
    token = start(client)
    chain = _challenged_chain(client, token)
    headers = {"X-Judge-Session": token}

    opened = client.post(
        f"/v1/chains/{chain}/challenges",
        headers={**headers, "Idempotency-Key": "open"},
        json={"method": "manual_review"},
    )
    assert opened.status_code == 201
    attempt = opened.json()
    assert attempt["status"] == "PENDING" and attempt["expires_at"]

    reported = client.post(
        f"/v1/chains/{chain}/challenges/{attempt['attempt_id']}/events",
        headers={**headers, "Idempotency-Key": "report"},
        json={"result": "PASSED"},
    )
    assert reported.status_code == 200
    assert reported.json()["status"] == "PASSED"

    timeline = client.get(f"/v1/chains/{chain}/challenges", headers=headers)
    assert [row["status"] for row in timeline.json()["attempts"]] == ["PASSED"]


def test_a_passed_review_does_not_rewrite_the_signed_verdict(client):
    """Three separate facts: Isnad's CHALLENGE, the merchant's review result,
    and whatever the merchant then does. Only the first is signed, and it stays
    exactly as issued."""
    token = start(client)
    chain = _challenged_chain(client, token)
    headers = {"X-Judge-Session": token}
    before = client.get(f"/v1/receipts/{chain}").json()

    attempt = client.post(
        f"/v1/chains/{chain}/challenges",
        headers={**headers, "Idempotency-Key": "open"},
        json={"method": "manual_review"},
    ).json()
    client.post(
        f"/v1/chains/{chain}/challenges/{attempt['attempt_id']}/events",
        headers={**headers, "Idempotency-Key": "report"},
        json={"result": "PASSED"},
    )
    after = client.get(f"/v1/receipts/{chain}").json()

    assert after["signed_payload"] == before["signed_payload"], "the signed bytes moved"
    assert after["signature"] == before["signature"]
    assert after["signed_at"] == before["signed_at"]
    import json as _json

    assert _json.loads(after["signed_payload"])["decision"] == "CHALLENGE"


def test_a_double_click_opens_one_review_not_two(client):
    token = start(client)
    chain = _challenged_chain(client, token)
    headers = {"X-Judge-Session": token, "Idempotency-Key": "open"}

    first = client.post(
        f"/v1/chains/{chain}/challenges", headers=headers, json={"method": "manual_review"}
    ).json()
    second = client.post(
        f"/v1/chains/{chain}/challenges", headers=headers, json={"method": "manual_review"}
    ).json()

    assert first["attempt_id"] == second["attempt_id"]


def test_a_second_conflicting_result_is_refused(client):
    token = start(client)
    chain = _challenged_chain(client, token)
    headers = {"X-Judge-Session": token}
    attempt = client.post(
        f"/v1/chains/{chain}/challenges",
        headers={**headers, "Idempotency-Key": "open"},
        json={"method": "manual_review"},
    ).json()["attempt_id"]
    client.post(
        f"/v1/chains/{chain}/challenges/{attempt}/events",
        headers={**headers, "Idempotency-Key": "a"},
        json={"result": "PASSED"},
    )

    conflicting = client.post(
        f"/v1/chains/{chain}/challenges/{attempt}/events",
        headers={**headers, "Idempotency-Key": "b"},
        json={"result": "FAILED"},
    )

    assert conflicting.status_code == 409
    assert conflicting.json()["detail"]["code"] == "attempt_not_pending"


def test_another_judge_cannot_see_or_touch_this_follow_up(client):
    mine, theirs = start(client), start(client)
    chain = _challenged_chain(client, mine)
    client.post(
        f"/v1/chains/{chain}/challenges",
        headers={"X-Judge-Session": mine, "Idempotency-Key": "open"},
        json={"method": "manual_review"},
    )

    read = client.get(f"/v1/chains/{chain}/challenges", headers={"X-Judge-Session": theirs})
    write = client.post(
        f"/v1/chains/{chain}/challenges",
        headers={"X-Judge-Session": theirs, "Idempotency-Key": "intrude"},
        json={"method": "manual_review"},
    )

    # The same 404 a missing chain gets: existence must not be probeable.
    assert read.status_code == 404
    assert write.status_code == 404


def test_a_follow_up_is_refused_on_a_decision_that_was_not_a_challenge(client):
    token = start(client)
    declined = run(client, token, scenario="swapped_subscriber").json()
    assert declined["decision"] == "DECLINE"

    response = client.post(
        f"/v1/chains/{declined['chain_id']}/challenges",
        headers={"X-Judge-Session": token, "Idempotency-Key": "open"},
        json={"method": "manual_review"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "not_challenged"


def test_a_clean_two_check_run_is_not_described_as_adverse(client):
    """Friction found in the Step 13 walkthrough, fixed and pinned.

    `stable_subscriber` returns `swapped: false` from both checks, so nothing
    came back adverse — yet the run grades DEGRADED, because two links is a
    thin chain. The shared DEGRADED sentence said "one or more came back
    adverse to the claim", which was simply false for this case and is the one
    kind of error this project exists to not make.
    """
    token = start(client)

    body = run(client, token, scenario="stable_subscriber").json()

    assert body["chain_grade"] == "DEGRADED"
    summary = body["presentation"]["summary"]
    assert "came back adverse" not in summary, summary
    assert "none of them contradicted the claim" in summary


def test_an_uncorroborated_adverse_run_still_says_adverse(client):
    """The other half of DEGRADED must keep its accurate sentence."""
    from app.chain.models import EvidenceLink, Verdict
    from app.domain.enums import Action, ChainGrade, Decision, Result
    from app.presentation import present

    verdict = Verdict(
        decision=Decision.CHALLENGE,
        chain_grade=ChainGrade.DEGRADED,
        confidence=0.6,
        hypothesis="account_takeover",
        reason="x",
        chain_id="c1",
        chain=[
            EvidenceLink(
                step=1,
                action=Action.SIM_SWAP,
                api="SIM Swap",
                result=Result.FLAG,
                signal="SIM_SWAPPED",
                detail="d",
                delta_logodds=1.4,
            )
        ],
    )

    assert "came back adverse" in present(verdict).summary
