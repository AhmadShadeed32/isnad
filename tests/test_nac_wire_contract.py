"""Wire-contract tests over the *installed* Network as Code SDK.

`tests/test_nac_contract.py` pins normalization against responses actually
captured from the simulator in August. This file answers a different question:
what does SDK 10.0.0 put on the wire, and what does it do with the response
bodies the authenticated catalog says the operator can return?

Every test drives the real `NetworkAsCodeApi` through an `httpx.MockTransport`,
so the request under assertion is the one the SDK would really have sent — not
an imitation of Isnad's own adapter interface. Zero external requests.

The point of these tests is to make the assumptions in
`docs/NAC_CONTRACT_MATRIX.md` executable. A path, a JSON key or a response
attribute name that changes under an SDK upgrade fails here, before it becomes
a wrong claim in a demo.
"""

from __future__ import annotations

import json

import httpx
import pytest
from network_as_code import NetworkAsCodeApi

# The catalog-generated host. The SDK's own default is
# `network-as-code.p-eu.rapidapi.com`; both are documented to take the same
# RapidAPI headers, and which one actually answers is an observation, not an
# assumption — see the matrix. Passing it explicitly here proves only that the
# SDK honours `base_url`.
CATALOG_HOST = "https://network-as-code.p-eu.apihub.nokia.io"
RAPIDAPI_HOST = "network-as-code.nokia.rapidapi.com"
SIMULATOR_NUMBER = "+99999991000"

# Every SDK call Isnad makes must be bounded. Asserted rather than assumed
# because a default retry would silently multiply a billed operator call.
BOUNDED = {"timeout_in_seconds": 10, "max_retries": 0}


class Recorder:
    """Collects the requests the SDK really sent, and replies with a script."""

    def __init__(self, responses):
        self.requests: list[httpx.Request] = []
        self._responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._responses:
            raise AssertionError(f"unscripted request: {request.method} {request.url}")
        status, payload = self._responses.pop(0)
        if payload is None:
            return httpx.Response(status)
        return httpx.Response(status, json=payload)

    @property
    def bodies(self) -> list[dict | None]:
        return [json.loads(r.content) if r.content else None for r in self.requests]

    @property
    def paths(self) -> list[str]:
        return [r.url.path for r in self.requests]


def api(recorder: Recorder) -> NetworkAsCodeApi:
    return NetworkAsCodeApi(
        api_key="wire-contract-test-key",
        rapidapi_host=RAPIDAPI_HOST,
        base_url=CATALOG_HOST,
        httpx_client=httpx.Client(transport=httpx.MockTransport(recorder)),
    )


# --- SIM swap ----------------------------------------------------------------


def test_sim_swap_check_posts_phone_number_and_max_age():
    rec = Recorder([(200, {"swapped": True})])
    response = api(rec).sim_swap.check(
        phone_number=SIMULATOR_NUMBER, max_age=24, request_options=BOUNDED
    )

    assert rec.paths == ["/passthrough/camara/v1/sim-swap/sim-swap/v0/check"]
    assert rec.requests[0].method == "POST"
    assert rec.bodies[0] == {"phoneNumber": SIMULATOR_NUMBER, "maxAge": 24}
    assert response.swapped is True


def test_sim_swap_retrieve_date_is_a_separate_operation_from_check():
    """A date is a second billable call, never a field of the boolean answer."""
    rec = Recorder([(200, {"latestSimChange": "2026-09-01T10:00:00.000+02:00"})])
    response = api(rec).sim_swap.retrieve_date(
        phone_number=SIMULATOR_NUMBER, request_options=BOUNDED
    )

    assert rec.paths == ["/passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date"]
    assert rec.bodies[0] == {"phoneNumber": SIMULATOR_NUMBER}
    # maxAge is not part of the date contract: the window belongs to `check`.
    assert "maxAge" not in (rec.bodies[0] or {})
    assert response.latest_sim_change.utcoffset().total_seconds() == 7200


def test_a_null_sim_change_stays_null():
    """`null` means no date was returned, not "never swapped"."""
    rec = Recorder([(200, {"latestSimChange": None})])
    response = api(rec).sim_swap.retrieve_date(phone_number=SIMULATOR_NUMBER)

    assert response.latest_sim_change is None


def test_an_absent_sim_change_key_is_also_null():
    rec = Recorder([(200, {})])
    assert api(rec).sim_swap.retrieve_date(phone_number=SIMULATOR_NUMBER).latest_sim_change is None


# --- Device swap -------------------------------------------------------------


def test_device_swap_uses_v1_not_v0():
    """The group's v1.0.0 label does not mean every CAMARA path carries v1 —
    SIM swap is v0 and device swap is v1. Getting this backwards 404s."""
    rec = Recorder([(200, {"swapped": False}), (200, {"latestDeviceChange": None})])
    client = api(rec)
    client.device_swap.check(phone_number=SIMULATOR_NUMBER, max_age=24, request_options=BOUNDED)
    client.device_swap.retrieve_date(phone_number=SIMULATOR_NUMBER, request_options=BOUNDED)

    assert rec.paths == [
        "/passthrough/camara/v1/device-swap/device-swap/v1/check",
        "/passthrough/camara/v1/device-swap/device-swap/v1/retrieve-date",
    ]


def test_the_device_monitoring_horizon_is_preserved_when_returned():
    """`monitoredPeriod` is how far back the operator actually looked. Without
    it, "no device change" has no scope and must not be read as "never"."""
    rec = Recorder([(200, {"latestDeviceChange": None, "monitoredPeriod": 120})])
    response = api(rec).device_swap.retrieve_date(phone_number=SIMULATOR_NUMBER)

    assert response.latest_device_change is None
    assert response.monitored_period == 120


def test_the_device_monitoring_horizon_is_optional_and_absent_means_unknown():
    rec = Recorder([(200, {"latestDeviceChange": "2026-08-30T12:00:00Z"})])
    response = api(rec).device_swap.retrieve_date(phone_number=SIMULATOR_NUMBER)

    assert response.monitored_period is None
    assert response.latest_device_change.tzinfo is not None


# --- Congestion Insights -----------------------------------------------------

SUBSCRIPTION = {
    "subscriptionId": "sub-42",
    "startedAt": "2026-09-06T10:00:00Z",
    "expiresAt": "2026-09-06T10:15:00Z",
    "subscriptionExpireTime": "2026-09-06T10:15:00Z",
    "device": {"phoneNumber": SIMULATOR_NUMBER},
    "webhook": {"notificationUrl": "https://callback.invalid/congestion"},
}


def test_a_created_subscription_exposes_subscription_id_and_started_at():
    """The public tutorial says `resource_id`/`starts_at`. The installed SDK
    does not have those attributes, and reading them would raise on the demo."""
    rec = Recorder([(201, SUBSCRIPTION)])
    created = api(rec).congestion_insights.create_subscription(
        device={"phone_number": SIMULATOR_NUMBER},
        webhook={"notification_url": "https://callback.invalid/congestion"},
        subscription_expire_time="2026-09-06T10:15:00Z",
        request_options=BOUNDED,
    )

    assert rec.paths == ["/congestion-insights/v0/subscriptions"]
    assert rec.requests[0].method == "POST"
    assert created.subscription_id == "sub-42"
    assert created.started_at is not None
    assert not hasattr(created, "resource_id")
    assert not hasattr(created, "starts_at")


def test_the_subscription_id_is_what_get_and_delete_take_as_resource_id():
    """`resource_id` is the SDK's *argument* name; its value is the returned
    `subscriptionId`. Mixing the two up deletes nothing and leaks a live
    subscription past the demo."""
    rec = Recorder([(201, SUBSCRIPTION), (200, SUBSCRIPTION), (204, None)])
    client = api(rec)
    created = client.congestion_insights.create_subscription(
        device={"phone_number": SIMULATOR_NUMBER},
        webhook={"notification_url": "https://callback.invalid/congestion"},
        subscription_expire_time="2026-09-06T10:15:00Z",
    )
    client.congestion_insights.get_subscription(resource_id=created.subscription_id)
    client.congestion_insights.delete_subscription(resource_id=created.subscription_id)

    assert rec.paths[1:] == [
        "/congestion-insights/v0/subscriptions/sub-42",
        "/congestion-insights/v0/subscriptions/sub-42",
    ]
    assert [r.method for r in rec.requests] == ["POST", "GET", "DELETE"]


def test_a_query_without_a_period_is_a_forecast_request():
    """Omitting both bounds asks for the upcoming interval. The catalog's own
    query example is wrong for its schema — it carries webhook and expiry
    fields — so the body is pinned here instead."""
    rec = Recorder([(200, [])])
    api(rec).congestion_insights.query(
        device={"phone_number": SIMULATOR_NUMBER}, request_options=BOUNDED
    )

    assert rec.paths == ["/congestion-insights/v0/query"]
    assert rec.bodies[0] == {"device": {"phoneNumber": SIMULATOR_NUMBER}}
    assert "webhook" not in (rec.bodies[0] or {})
    assert "subscriptionExpireTime" not in (rec.bodies[0] or {})


def test_a_historical_query_sends_both_bounds():
    rec = Recorder([(200, [])])
    api(rec).congestion_insights.query(
        device={"phone_number": SIMULATOR_NUMBER},
        start="2026-09-06T09:00:00Z",
        end="2026-09-06T10:00:00Z",
    )

    assert rec.bodies[0] == {
        "device": {"phoneNumber": SIMULATOR_NUMBER},
        "start": "2026-09-06T09:00:00Z",
        "end": "2026-09-06T10:00:00Z",
    }


def test_an_empty_query_result_is_empty_and_not_a_low_level():
    """No interval was returned. That is "unknown", and the difference matters:
    "Low" would be a claim about the network we were never told."""
    rec = Recorder([(200, [])])
    assert api(rec).congestion_insights.query(device={"phone_number": SIMULATOR_NUMBER}) == []


def test_a_missing_confidence_stays_none_rather_than_becoming_a_number():
    rec = Recorder(
        [
            (
                200,
                [
                    {
                        "timeIntervalStart": "2026-09-06T10:00:00Z",
                        "timeIntervalStop": "2026-09-06T10:15:00Z",
                        "congestionLevel": "High",
                        "confidenceLevel": None,
                    }
                ],
            )
        ]
    )
    (interval,) = api(rec).congestion_insights.query(device={"phone_number": SIMULATOR_NUMBER})

    assert interval.confidence_level is None
    assert interval.congestion_level == "High"
    assert interval.time_interval_stop > interval.time_interval_start


def test_the_sdk_does_not_constrain_the_congestion_level_vocabulary():
    """The schema is `Low|Medium|High` *or anything*. An unexpected value
    reaches the caller verbatim, so Isnad has to classify it as unknown itself
    rather than trust the SDK to have rejected it."""
    rec = Recorder(
        [
            (
                200,
                [
                    {
                        "timeIntervalStart": "2026-09-06T10:00:00Z",
                        "timeIntervalStop": "2026-09-06T10:15:00Z",
                        "congestionLevel": "catastrophic",
                    }
                ],
            )
        ]
    )
    (interval,) = api(rec).congestion_insights.query(device={"phone_number": SIMULATOR_NUMBER})

    assert interval.congestion_level == "catastrophic"


# --- Identity extensions the review shortlisted ------------------------------


def test_number_recycling_is_v0_2_and_requires_a_reference_date():
    rec = Recorder([(200, {"phoneNumberRecycled": False})])
    api(rec).number_recycling.check(
        phone_number=SIMULATOR_NUMBER, specified_date="2026-01-15", request_options=BOUNDED
    )

    assert rec.paths == [
        "/passthrough/camara/v1/number-recycling/number-recycling/v0.2/check"
    ]
    assert rec.bodies[0] == {"phoneNumber": SIMULATOR_NUMBER, "specifiedDate": "2026-01-15"}


def test_consent_info_is_v0_1_and_carries_scopes_purpose_and_capture_flag():
    rec = Recorder([(200, {"statusInfo": []})])
    api(rec).consent_info.retrieve(
        phone_number=SIMULATOR_NUMBER,
        scopes=["sim-swap:retrieve-date"],
        purpose="dpv:FraudPreventionAndDetection",
        request_capture_url=True,
        request_options=BOUNDED,
    )

    assert rec.paths == ["/passthrough/camara/v1/consent-info/consent-info/v0.1/retrieve"]
    assert rec.bodies[0] == {
        "phoneNumber": SIMULATOR_NUMBER,
        "scopes": ["sim-swap:retrieve-date"],
        "purpose": "dpv:FraudPreventionAndDetection",
        "requestCaptureUrl": True,
    }


# --- Transport-level facts the matrix depends on -----------------------------


def test_the_rapidapi_host_header_travels_with_the_catalog_base_url():
    """Both documented hosts take the same RapidAPI authentication headers."""
    rec = Recorder([(200, {"swapped": False})])
    api(rec).sim_swap.check(phone_number=SIMULATOR_NUMBER, max_age=24)

    headers = rec.requests[0].headers
    assert headers["x-rapidapi-host"] == RAPIDAPI_HOST
    assert headers["x-rapidapi-key"] == "wire-contract-test-key"
    assert str(rec.requests[0].url).startswith(CATALOG_HOST)


def test_max_retries_zero_means_one_attempt_for_a_retryable_status():
    """A 503 is exactly the status an SDK default would retry. One attempt is
    asserted so a hidden retry cannot double a billed call."""
    rec = Recorder([(503, {"status": 503, "message": "unavailable"})])

    with pytest.raises(Exception):  # noqa: B017 - the SDK's own error type
        api(rec).sim_swap.check(
            phone_number=SIMULATOR_NUMBER, max_age=24, request_options=BOUNDED
        )

    assert len(rec.requests) == 1


def test_an_error_status_raises_rather_than_returning_a_false_negative():
    """A 422 must never normalize to `swapped=False`."""
    rec = Recorder([(422, {"status": 422, "code": "INVALID_ARGUMENT", "message": "bad number"})])

    with pytest.raises(Exception):  # noqa: B017 - the SDK's own error type
        api(rec).sim_swap.check(phone_number="not-a-number", max_age=24)

    assert len(rec.requests) == 1
