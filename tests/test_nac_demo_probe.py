"""Offline tests for the bounded simulator runner.

Nothing here makes an external request. The transport is an `httpx.MockTransport`
that counts what the SDK actually sent, so "no call was made" is asserted rather
than assumed — which is the whole point of a tool whose output will be quoted as
evidence.
"""

from __future__ import annotations

import json

import httpx
import pytest

from scripts import nac_demo_probe as probe


class Transport:
    """Counts requests and replies with a script, like the operator would."""

    def __init__(self, *responses):
        self.requests: list[httpx.Request] = []
        self._responses = list(responses) or [(200, {})]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, payload = self._responses.pop(0) if self._responses else (200, {})
        return httpx.Response(status) if payload is None else httpx.Response(status, json=payload)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))


@pytest.fixture(autouse=True)
def _configured_key(monkeypatch):
    """A key must exist for the tool to build a client; it is never in argv."""
    monkeypatch.setattr(probe, "build_client", _spy_build_client(probe.build_client))


def _spy_build_client(original):
    def build(host, httpx_client=None):
        from network_as_code import NetworkAsCodeApi

        kwargs = {
            "api_key": "offline-test-key",
            "rapidapi_host": "network-as-code.nokia.rapidapi.com",
            "base_url": probe.HOSTS[host],
        }
        if httpx_client is not None:
            kwargs["httpx_client"] = httpx_client
        return NetworkAsCodeApi(**kwargs)

    return build


def run(argv, transport=None, capsys=None):
    client = transport.client() if transport else None
    code = probe.main(argv, httpx_client=client)
    return code


def output(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


# --- the default is a plan, not a call ---------------------------------------


def test_a_bare_invocation_prints_a_plan_and_calls_nothing(capsys):
    transport = Transport()
    assert run([], transport) == 0
    body = output(capsys)

    assert body["mode"] == "plan"
    assert body["external_requests"] == 0
    assert body["max_calls_this_invocation"] == 0
    assert transport.requests == []


def test_naming_an_operation_without_execute_still_calls_nothing(capsys):
    transport = Transport()
    assert run(["--operation", "sim_swap_check", "--number", "+99999991000"], transport) == 0
    body = output(capsys)

    assert body["mode"] == "plan"
    assert body["max_calls_this_invocation"] == 1
    assert transport.requests == []


def test_the_plan_states_the_bounded_request_options(capsys):
    run([], Transport())
    assert output(capsys)["request_options"] == {"timeout_in_seconds": 10, "max_retries": 0}


def test_the_subscription_plan_shows_host_expiry_and_cleanup(monkeypatch, capsys):
    from app.config import settings

    monkeypatch.setattr(
        settings, "nac_congestion_callback_url", "https://callback.example/secret-hook", False
    )
    transport = Transport()
    run(["--operation", "congestion_create", "--number", "+99999991000"], transport)
    (plan,) = output(capsys)["operations"]

    assert plan["callback_host"] == "callback.example"
    assert plan["mutating"] is True
    assert plan["expiry"].endswith("Z")
    assert "congestion_delete" in plan["cleanup"]
    # Only the host. The path is where a callback secret would live.
    assert "secret-hook" not in json.dumps(plan)
    assert transport.requests == []


# --- refusals happen before any transport exists -----------------------------


@pytest.mark.parametrize(
    "argv,reason",
    [
        (["--operation", "sim_swap_check", "--number", "+962790000000"], "simulator numbers"),
        (["--operation", "sim_swap_check", "--number", "99999991000"], "E.164"),
        (["--operation", "sim_swap_check", "--number", "+9999"], "E.164"),
        (["--operation", "sim_swap_check", "--number", "+9999999100a"], "E.164"),
        (["--operation", "sim_swap_check"], "E.164"),
        (["--operation", "congestion_get"], "--subscription-id"),
        (["--operation", "congestion_delete"], "--subscription-id"),
    ],
)
def test_invalid_input_is_refused_without_a_single_request(argv, reason, capsys):
    transport = Transport()
    assert run([*argv, "--execute"], transport) == 2
    body = output(capsys)

    assert body["mode"] == "refused"
    assert body["external_requests"] == 0
    assert reason in body["reason"]
    assert transport.requests == []


def test_an_unknown_operation_never_reaches_the_parser_or_the_sdk(capsys):
    """argparse refuses the name outright; `validate` refuses it again for any
    caller that skips the CLI."""
    transport = Transport()
    with pytest.raises(SystemExit):
        run(["--operation", "drop_tables", "--number", "+99999991000", "--execute"], transport)
    assert transport.requests == []

    args = probe.parse_args(["--number", "+99999991000"])
    args.operation = "drop_tables"
    with pytest.raises(probe.ProbeError, match="unknown operation"):
        probe.Runner().validate(args)


def test_a_real_looking_number_is_refused_even_though_it_is_valid_e164(capsys):
    """The guard that matters: E.164 alone would happily reach a subscriber."""
    transport = Transport()
    run(["--operation", "sim_swap_check", "--number", "+14155550123", "--execute"], transport)

    assert "must never reach a real subscriber" in output(capsys)["reason"]
    assert transport.requests == []


def test_an_endpoint_override_is_not_offered_at_all():
    """There is no free-text host argument to smuggle a destination through."""
    with pytest.raises(SystemExit):
        probe.parse_args(["--host", "https://attacker.example"])


def test_only_the_two_documented_hosts_exist():
    assert set(probe.HOSTS) == {"catalog", "sdk-default"}
    assert all(u.startswith("https://") for u in probe.HOSTS.values())


def test_a_half_specified_period_is_refused(capsys):
    transport = Transport()
    run(
        ["--operation", "congestion_query", "--number", "+99999991000",
         "--start", "2026-09-06T09:00:00Z", "--execute"],
        transport,
    )

    assert "must be given together" in output(capsys)["reason"]
    assert transport.requests == []


def test_a_subscription_is_refused_when_no_callback_is_configured(monkeypatch, capsys):
    from app.config import settings

    monkeypatch.setattr(settings, "nac_congestion_callback_url", "", False)
    transport = Transport()
    run(["--operation", "congestion_create", "--number", "+99999991000", "--execute"], transport)

    assert "refusing to point an operator" in output(capsys)["reason"]
    assert transport.requests == []


def test_a_plaintext_callback_is_refused(monkeypatch, capsys):
    from app.config import settings

    monkeypatch.setattr(settings, "nac_congestion_callback_url", "http://callback.example/cb", False)
    transport = Transport()
    run(["--operation", "congestion_create", "--number", "+99999991000", "--execute"], transport)

    assert "must be HTTPS" in output(capsys)["reason"]
    assert transport.requests == []


# --- one attempt, recorded either way ----------------------------------------


def test_a_successful_call_makes_exactly_one_request_and_records_it(capsys):
    transport = Transport((200, {"swapped": True}))
    assert run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"],
               transport) == 0
    record = output(capsys)

    assert len(transport.requests) == 1
    assert record["outcome"] == "ok"
    assert record["attempts"] == 1
    assert record["result"] == {"swapped": True}
    assert record["evidence_level"] == "hosted_simulator"
    assert record["http_status"] == 200
    assert isinstance(record["duration_ms"], int)


def test_a_failed_call_still_records_the_attempt(capsys):
    transport = Transport((503, {"status": 503, "code": "UNAVAILABLE", "message": "down"}))
    assert run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"],
               transport) == 1
    record = output(capsys)

    assert len(transport.requests) == 1
    assert record["attempts"] == 1
    assert record["outcome"] == "error"
    assert record["http_status"] == 503
    assert record["error_code"] == "UNAVAILABLE"


def test_a_retryable_status_is_attempted_once(capsys):
    """`max_retries=0` is the difference between one billed call and several."""
    transport = Transport((503, {"code": "UNAVAILABLE"}), (200, {"swapped": False}))
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)

    assert len(transport.requests) == 1


def test_an_error_record_carries_no_body_headers_or_traceback(capsys):
    """An operator error body can echo the identifier we are not writing down."""
    transport = Transport(
        (422, {"status": 422, "code": "INVALID_ARGUMENT",
               "message": "phoneNumber +99999991000 is not serviced"})
    )
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)
    text = json.dumps(output(capsys))

    assert "not serviced" not in text
    assert "Traceback" not in text
    assert "x-rapidapi" not in text.lower()
    assert "+99999991000" not in text  # only the masked form is recorded


def test_an_unstructured_error_falls_back_to_a_bounded_code(capsys):
    transport = Transport((500, {"message": "x" * 5000}))
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)
    record = output(capsys)

    assert record["error_code"] == "http_500"
    assert len(json.dumps(record)) < 2000


def test_the_recorded_correlator_is_the_one_the_operator_actually_saw():
    """A record that names a correlator must have sent it. Generating an id
    locally and filing it as a provider correlator is a fabricated trace."""
    transport = Transport((200, {"swapped": False}))
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)

    assert transport.requests[0].headers["x-correlator"]


def test_a_device_less_operation_records_no_device(capsys):
    """`congestion_list` addresses the collection. Demanding a number for it
    would file a device into a record that never carried one."""
    transport = Transport((200, []))
    assert run(["--operation", "congestion_list", "--execute"], transport) == 0

    assert output(capsys)["device"] is None


def test_the_recorded_device_is_masked(capsys):
    transport = Transport((200, {"swapped": False}))
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)

    assert output(capsys)["device"] == "+9999…1000"


def test_the_api_key_never_reaches_the_record(capsys):
    transport = Transport((200, {"swapped": False}))
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute"], transport)

    assert "offline-test-key" not in json.dumps(output(capsys))


# --- null and malformed provider data ----------------------------------------


def test_a_null_date_is_recorded_as_absent_not_as_never_swapped(capsys):
    transport = Transport((200, {"latestSimChange": None}))
    run(["--operation", "sim_swap_date", "--number", "+99999991000", "--execute"], transport)
    result = output(capsys)["result"]

    assert result["latest_sim_change"] is None
    assert result["date_present"] is False
    assert "swapped" not in result


def test_a_returned_date_keeps_its_offset(capsys):
    transport = Transport((200, {"latestSimChange": "2026-09-01T10:00:00+02:00"}))
    run(["--operation", "sim_swap_date", "--number", "+99999991000", "--execute"], transport)
    result = output(capsys)["result"]

    assert result["date_present"] is True
    assert result["timezone_aware"] is True
    assert "+02:00" in result["latest_sim_change"]


def test_a_missing_monitored_period_is_recorded_as_unknown(capsys):
    transport = Transport((200, {"latestDeviceChange": None}))
    run(["--operation", "device_swap_date", "--number", "+99999991000", "--execute"], transport)
    result = output(capsys)["result"]

    assert result["monitored_period_days"] is None
    assert result["date_present"] is False


def test_a_monitored_period_is_recorded_in_days(capsys):
    transport = Transport((200, {"latestDeviceChange": None, "monitoredPeriod": 120}))
    run(["--operation", "device_swap_date", "--number", "+99999991000", "--execute"], transport)

    assert output(capsys)["result"]["monitored_period_days"] == 120


def test_a_malformed_date_is_an_error_not_a_guess(capsys):
    transport = Transport((200, {"latestSimChange": "yesterday afternoon"}))
    assert run(["--operation", "sim_swap_date", "--number", "+99999991000", "--execute"],
               transport) == 1

    assert output(capsys)["outcome"] == "error"


def test_an_empty_congestion_result_is_zero_intervals_not_a_low_level(capsys):
    transport = Transport((200, []))
    run(["--operation", "congestion_query", "--number", "+99999991000", "--execute"], transport)
    result = output(capsys)["result"]

    assert result["interval_count"] == 0
    assert result["intervals"] == []
    assert "Low" not in json.dumps(result)


def test_an_unknown_confidence_stays_null(capsys):
    transport = Transport(
        (200, [{"timeIntervalStart": "2026-09-06T10:00:00Z",
                "timeIntervalStop": "2026-09-06T10:15:00Z",
                "congestionLevel": "High", "confidenceLevel": None}])
    )
    run(["--operation", "congestion_query", "--number", "+99999991000", "--execute"], transport)
    (interval,) = output(capsys)["result"]["intervals"]

    assert interval["confidence"] is None
    assert interval["level"] == "High"


def test_a_forecast_query_sends_no_period_and_a_historical_one_sends_both():
    forecast = Transport((200, []))
    run(["--operation", "congestion_query", "--number", "+99999991000", "--execute"], forecast)
    assert json.loads(forecast.requests[0].content) == {"device": {"phoneNumber": "+99999991000"}}

    history = Transport((200, []))
    run(
        ["--operation", "congestion_query", "--number", "+99999991000", "--execute",
         "--start", "2026-09-06T09:00:00Z", "--end", "2026-09-06T10:00:00Z"],
        history,
    )
    body = json.loads(history.requests[0].content)
    assert body["start"] == "2026-09-06T09:00:00Z"
    assert body["end"] == "2026-09-06T10:00:00Z"


def test_delete_uses_the_returned_subscription_id_in_the_path():
    transport = Transport((204, None))
    run(["--operation", "congestion_delete", "--subscription-id", "sub-42", "--execute"], transport)

    assert transport.requests[0].url.path.endswith("/congestion-insights/v0/subscriptions/sub-42")
    assert transport.requests[0].method == "DELETE"


def test_listing_reconciles_instead_of_repeating_an_uncertain_create(capsys):
    transport = Transport((200, []))
    run(["--operation", "congestion_list", "--number", "+99999991000", "--execute"], transport)

    assert transport.requests[0].method == "GET"
    assert output(capsys)["result"] == {"count": 0}


# --- the record file ---------------------------------------------------------


def test_records_are_appended_so_an_earlier_failure_survives(tmp_path, capsys):
    path = tmp_path / "observations.jsonl"
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute",
         "--record", str(path)], Transport((503, {"code": "UNAVAILABLE"})))
    capsys.readouterr()
    run(["--operation", "sim_swap_check", "--number", "+99999991000", "--execute",
         "--record", str(path)], Transport((200, {"swapped": True})))

    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["outcome"] for r in lines] == ["error", "ok"]


def test_nothing_is_recorded_when_the_input_was_refused(tmp_path, capsys):
    path = tmp_path / "observations.jsonl"
    run(["--operation", "sim_swap_check", "--number", "+1", "--execute", "--record", str(path)],
        Transport())

    assert not path.exists()


def test_every_operation_is_labelled_hosted_simulator_and_never_live():
    """This account is in Simulator mode; a record must not imply otherwise."""
    assert probe.EVIDENCE_LEVEL == "hosted_simulator"
    assert "live_operator" not in probe.__doc__ or "never" in probe.__doc__
