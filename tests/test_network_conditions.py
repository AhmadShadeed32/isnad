"""Network conditions: information beside a decision, never inside one.

The tests that matter most here are the ones about what the feature refuses to
claim. An empty answer is not "Low". A missing confidence is not 0 and not 100.
A create that succeeded is not a notification that was delivered. And congestion
never touches a score.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import network_conditions as nc
from app.config import settings
from app.db.database import SessionLocal
from app.db.models import NetworkConditionSubscriptionRow
from app.main import app

AUTH = {"Authorization": "Bearer demo-merchant-key"}
OTHER = {"Authorization": "Bearer other-merchant-key"}
NUMBER = "+962790000002"
QUIET = "+962790000001"
NO_DATA = "+962790000005"


@pytest.fixture(autouse=True)
def _callback_configured(monkeypatch):
    monkeypatch.setattr(
        settings,
        "nac_congestion_callback_base_url",
        # The base must point at THIS service's own receiver, because the
        # subscription id is appended to it and the operator posts there.
        "https://isnad.example/v1/network-conditions/callbacks",
        False,
    )


@pytest.fixture(autouse=True)
def _two_tenants(monkeypatch):
    monkeypatch.setattr(
        settings, "merchant_api_keys", "demo-merchant-key,other-merchant-key", False
    )


@pytest.fixture(autouse=True)
def _unlimited(monkeypatch):
    """This file makes far more requests than the per-key minute limit allows,
    and a 429 late in the file fails a test that has nothing to do with rate
    limiting. The limiter has its own tests."""
    monkeypatch.setattr(settings, "rate_limit_enabled", False, False)


@pytest.fixture(autouse=True)
def _clean_tables():
    """The suite shares one in-memory database, and this feature's whole point
    is that a device may hold only one active subscription — so leftovers from
    a previous test would look exactly like the limit working."""
    from app.db.models import NetworkConditionEventRow

    with SessionLocal() as session:
        session.query(NetworkConditionEventRow).delete()
        session.query(NetworkConditionSubscriptionRow).delete()
        session.commit()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _subscribe(client, headers=AUTH, number=NUMBER):
    return client.post(
        "/v1/network-conditions/subscriptions", headers=headers, json={"phone_number": number}
    )


class Recording:
    """A provider that counts its calls, so "no request was made" is assertable."""

    def __init__(self, *, fail_create=False, fail_delete=False, fail_query=False, rows=None):
        self.creates = self.deletes = self.queries = 0
        self._fail_create = fail_create
        self._fail_delete = fail_delete
        self._fail_query = fail_query
        self._rows = rows

    def create_congestion_subscription(self, phone_number, callback_url, callback_token, expires_at):
        self.creates += 1
        if self._fail_create:
            raise RuntimeError("operator refused")
        self.callback_url = callback_url
        self.callback_token = callback_token
        return "provider-sub-1"

    def delete_congestion_subscription(self, provider_id):
        self.deletes += 1
        if self._fail_delete:
            raise RuntimeError("operator refused")

    def query_congestion(self, phone_number, start=None, end=None):
        self.queries += 1
        if self._fail_query:
            raise RuntimeError("operator refused")
        self.last_period = (start, end)
        if self._rows is not None:
            return self._rows
        now = datetime.now(UTC)
        return [
            {
                "start": now,
                "stop": now + timedelta(minutes=15),
                "level": "High",
                "confidence": None,
            }
        ]


@pytest.fixture
def provider(monkeypatch):
    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    return recording


# --- normalization: the claims this feature refuses to make ------------------


@pytest.mark.parametrize("raw", ["Low", "low", "LOW", " low "])
def test_a_documented_level_is_normalized_to_its_documented_spelling(raw):
    assert nc.normalize_level(raw) == "Low"


@pytest.mark.parametrize("raw", ["catastrophic", "", None, 3, {}])
def test_an_undocumented_level_is_unknown_rather_than_guessed(raw):
    """The SDK does not constrain this vocabulary, so an unexpected string
    arrives verbatim and must not be rendered as if it were a level."""
    assert nc.normalize_level(raw) == "unknown"


@pytest.mark.parametrize("raw", [None, "80", 101, -1, True])
def test_a_missing_or_impossible_confidence_stays_none(raw):
    """0 would invent certainty that the reading is worthless; 100 would invent
    certainty that it is perfect. Nobody made either claim."""
    assert nc.normalize_confidence(raw) is None


@pytest.mark.parametrize("raw", [0, 50, 100])
def test_a_real_confidence_is_kept_exactly(raw):
    assert nc.normalize_confidence(raw) == raw


def test_an_empty_result_is_empty_and_never_a_low_reading(client, monkeypatch):
    recording = Recording(rows=[])
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    created = _subscribe(client).json()
    body = client.post(
        f"/v1/network-conditions/subscriptions/{created['subscription_id']}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    ).json()

    assert body["empty"] is True
    assert body["intervals"] == []
    assert "Low" not in str(body)


# --- period validation -------------------------------------------------------


def test_no_bounds_is_a_forecast():
    assert nc.validate_period(None, None) == nc.FORECAST


def test_both_bounds_is_history():
    start = datetime.now(UTC) - timedelta(hours=2)
    assert nc.validate_period(start, start + timedelta(hours=1)) == nc.HISTORY


def test_one_bound_alone_is_refused_rather_than_silently_widened():
    """One bound implies a fifteen-minute interval on the other side that the
    caller never asked for."""
    with pytest.raises(nc.NetworkConditionError, match="together"):
        nc.validate_period(datetime.now(UTC), None)


def test_a_naive_bound_is_refused():
    naive = datetime(2026, 9, 6, 10, 0)  # noqa: DTZ001 - naiveness is the case
    with pytest.raises(nc.NetworkConditionError, match="timezone"):
        nc.validate_period(naive, naive + timedelta(hours=1))


def test_a_backwards_window_is_refused():
    now = datetime.now(UTC)
    with pytest.raises(nc.NetworkConditionError, match="after"):
        nc.validate_period(now, now - timedelta(hours=1))


def test_an_unbounded_window_is_refused():
    now = datetime.now(UTC)
    with pytest.raises(nc.NetworkConditionError, match="exceed"):
        nc.validate_period(now - timedelta(days=30), now)


# --- lifecycle ---------------------------------------------------------------


def test_create_get_query_delete_get_confirms_deletion(client, provider):
    created = _subscribe(client).json()
    subscription_id = created["subscription_id"]
    assert created["status"] == "active"
    # The mock provider is the mock provider. Calling its output
    # `hosted_simulator` would be a claim about where the data came from.
    assert created["scope"] == "mock"

    read = client.get(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    assert read.json()["status"] == "active"

    query = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )
    assert query.json()["mode"] == "forecast"

    deleted = client.delete(
        f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH
    )
    assert deleted.json()["status"] == "deleted"
    assert deleted.json()["terminal"] is True

    after = client.get(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    assert after.json()["status"] == "deleted"
    assert provider.creates == 1 and provider.queries == 1 and provider.deletes == 1


def test_a_scope_names_the_provider_that_actually_answered(client, provider):
    """A reading produced by MockProvider is a fixture this repository wrote.
    Labelling it `hosted_simulator` confused an authored fixture with an
    authenticated response from Nokia."""
    assert _subscribe(client).json()["scope"] == "mock"


def test_a_successful_call_never_promotes_the_scope_to_live(client, provider, monkeypatch):
    """The portal says Simulator. Nothing about a 200 changes that."""
    monkeypatch.setattr(settings, "provider", "nac", False)
    assert _subscribe(client).json()["scope"] == "hosted_simulator"


def test_a_second_delete_is_a_success_and_makes_no_second_provider_call(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    client.delete(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    again = client.delete(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)

    assert again.status_code == 200
    assert again.json()["status"] == "deleted"
    assert provider.deletes == 1


def test_a_failed_cleanup_is_surfaced_rather_than_reported_as_deleted(client, monkeypatch):
    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    subscription_id = _subscribe(client).json()["subscription_id"]
    recording._fail_delete = True

    response = client.delete(
        f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "cleanup_failed"

    still = client.get(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    assert still.json()["status"] == "active"
    assert "cleanup failed" in still.json()["reason"]


def test_an_uncertain_create_stays_non_terminal_so_it_must_be_reconciled(client, monkeypatch):
    """A timeout is not a refusal. The subscription may exist at the operator,
    so the row keeps this device's capacity and a retry is refused — creating a
    second one is exactly how the first is leaked."""
    recording = Recording(fail_create=True)
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    response = _subscribe(client)

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "provider_unreachable"
    with SessionLocal() as session:
        rows = session.query(NetworkConditionSubscriptionRow).all()
        assert [row.status for row in rows] == ["unknown"]

    retry = _subscribe(client)
    assert retry.json()["detail"]["code"] == "device_already_subscribed"
    assert recording.creates == 1


def test_a_definite_refusal_is_terminal_and_frees_the_device(client, monkeypatch):
    """A 4xx is an answer: nothing was created, so nothing needs reconciling."""

    class Refused(Recording):
        refuse = True

        def create_congestion_subscription(self, *args, **kwargs):
            if self.refuse:
                self.creates += 1
                error = RuntimeError("bad request")
                error.status_code = 422
                raise error
            return super().create_congestion_subscription(*args, **kwargs)

    recording = Refused()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    response = _subscribe(client)

    assert response.json()["detail"]["code"] == "provider_rejected"
    with SessionLocal() as session:
        assert [r.status for r in session.query(NetworkConditionSubscriptionRow).all()] == [
            "failed"
        ]
    # The device is free again, so an honest retry is allowed.
    recording.refuse = False
    assert _subscribe(client).status_code == 201


def test_an_empty_provider_id_never_becomes_an_active_subscription(client, monkeypatch):
    """An id we cannot read, delete or match a callback to is not one to
    activate: delete would skip the provider and report success."""

    class Nameless(Recording):
        def create_congestion_subscription(self, *args, **kwargs):
            self.creates += 1
            return "   "

    recording = Nameless()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    response = _subscribe(client)

    assert response.json()["detail"]["code"] == "provider_id_missing"
    with SessionLocal() as session:
        assert [r.status for r in session.query(NetworkConditionSubscriptionRow).all()] == [
            "unknown"
        ]


def test_a_query_needs_a_live_subscription(client, provider):
    """Nokia documents the subscription as a prerequisite for a query."""
    subscription_id = _subscribe(client).json()["subscription_id"]
    client.delete(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    provider.queries = 0

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "subscription_not_active"
    assert provider.queries == 0


def test_an_expired_subscription_stops_querying_without_a_worker_having_run(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    with SessionLocal() as session:
        row = session.get(NetworkConditionSubscriptionRow, subscription_id)
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()

    read = client.get(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)
    assert read.json()["status"] == "expired"
    assert read.json()["terminal"] is True


def test_a_provider_denial_on_query_is_a_502_not_an_invented_reading(client, monkeypatch):
    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    subscription_id = _subscribe(client).json()["subscription_id"]
    recording._fail_query = True

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )

    assert response.status_code == 502
    assert "operator refused" not in response.text


def test_a_historical_query_passes_both_bounds_to_the_operator(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    start = datetime.now(UTC) - timedelta(hours=2)
    end = start + timedelta(hours=1)

    body = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={
            "phone_number": NUMBER,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    ).json()

    assert body["mode"] == "history"
    assert provider.last_period == (start, end)


# --- limits ------------------------------------------------------------------


def test_one_device_may_not_hold_two_active_subscriptions(client, provider):
    _subscribe(client)
    second = _subscribe(client)

    assert second.status_code == 422
    assert second.json()["detail"]["code"] == "device_already_subscribed"
    assert provider.creates == 1


def test_an_owner_is_capped_and_the_cap_counts_only_active_ones(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "network_conditions_max_active_per_owner", 1, False)
    first = _subscribe(client).json()
    blocked = _subscribe(client, number=QUIET)
    assert blocked.json()["detail"]["code"] == "too_many_subscriptions"

    client.delete(f"/v1/network-conditions/subscriptions/{first['subscription_id']}", headers=AUTH)
    assert _subscribe(client, number=QUIET).status_code == 201


def test_no_subscription_is_created_without_a_configured_callback(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "nac_congestion_callback_base_url", "", False)
    response = _subscribe(client)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "callback_not_configured"
    assert provider.creates == 0


def test_a_plaintext_callback_is_refused(client, provider, monkeypatch):
    monkeypatch.setattr(
        settings, "nac_congestion_callback_base_url", "http://callbacks.example/x", False
    )
    assert _subscribe(client).json()["detail"]["code"] == "callback_not_https"
    assert provider.creates == 0


def test_the_operator_is_pointed_at_a_url_that_names_this_subscription(client, provider):
    """The host is ours and only ours — a destination supplied by a request
    would let a caller aim an operator at any host — and the path carries the
    subscription id, because one static URL cannot say which subscription an
    event belongs to."""
    created = _subscribe(client).json()

    assert provider.callback_url.startswith(
        "https://isnad.example/v1/network-conditions/callbacks/"
    )
    assert provider.callback_url.endswith(created["subscription_id"])


def test_an_event_posted_to_the_url_the_operator_was_given_reaches_the_right_row(
    client, monkeypatch
):
    """The wiring the old test could not see: it called the handler with an id
    it already knew, so a static callback URL passed."""
    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    first = _subscribe(client).json()["subscription_id"]
    first_token = recording.callback_token
    first_url = recording.callback_url
    second = _subscribe(client, number=QUIET).json()["subscription_id"]

    # Post exactly where the operator was told to, for the first subscription.
    path = "/" + first_url.split("/", 3)[3]
    assert path.startswith("/v1/network-conditions/callbacks/")
    response = client.post(
        path,
        headers={"Authorization": f"Bearer {first_token}"},
        json={
            "event_id": "evt-wired",
            "level": "High",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )

    assert response.status_code == 204
    assert nc.latest_event(_owner(), first)["event_id"] == "evt-wired"
    assert nc.latest_event(_owner(), second) is None


# --- tenant isolation --------------------------------------------------------


def test_another_tenant_cannot_read_this_tenants_subscription(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]

    assert client.get(
        f"/v1/network-conditions/subscriptions/{subscription_id}", headers=OTHER
    ).status_code == 404


def test_another_tenant_cannot_delete_this_tenants_subscription(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]

    response = client.delete(
        f"/v1/network-conditions/subscriptions/{subscription_id}", headers=OTHER
    )
    assert response.status_code == 404
    assert provider.deletes == 0
    assert client.get(
        f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH
    ).json()["status"] == "active"


def test_another_tenant_cannot_query_through_this_tenants_subscription(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    provider.queries = 0

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=OTHER,
        json={"phone_number": NUMBER},
    )
    assert response.status_code == 404
    assert provider.queries == 0


def test_an_unauthenticated_caller_reaches_nothing(client):
    assert client.get("/v1/network-conditions/subscriptions/anything").status_code == 401


# --- the callback ------------------------------------------------------------


def _callback(client, subscription_id, token, event_id="evt-1", level="High", occurred_at=None):
    return client.post(
        f"/v1/network-conditions/callbacks/{subscription_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_id": event_id,
            "level": level,
            "occurred_at": (occurred_at or datetime.now(UTC)).isoformat(),
        },
    )


def test_a_delivered_event_is_accepted_and_readable(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]

    assert _callback(client, subscription_id, provider.callback_token).status_code == 204
    latest = nc.latest_event(_owner(), subscription_id)
    assert latest["level"] == "High"


def _owner():
    from app.api.deps import owner_for

    return owner_for("demo-merchant-key")


def test_a_forged_token_is_rejected(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]

    assert _callback(client, subscription_id, "not-the-token").status_code == 401
    assert nc.latest_event(_owner(), subscription_id) is None


def test_a_missing_token_is_rejected(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]

    response = client.post(
        f"/v1/network-conditions/callbacks/{subscription_id}",
        json={"event_id": "e", "level": "Low", "occurred_at": datetime.now(UTC).isoformat()},
    )
    assert response.status_code == 401


def test_an_unknown_subscription_answers_exactly_like_a_wrong_token(client, provider):
    """Existence is not something to leak through a status code."""
    subscription_id = _subscribe(client).json()["subscription_id"]

    unknown = _callback(client, "ncs_does_not_exist", provider.callback_token)
    wrong = _callback(client, subscription_id, "wrong")
    assert unknown.status_code == wrong.status_code == 401


def test_one_subscriptions_token_does_not_authenticate_anothers_events(client, monkeypatch):
    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    first = _subscribe(client).json()["subscription_id"]
    first_token = recording.callback_token
    second = _subscribe(client, number=QUIET).json()["subscription_id"]

    assert _callback(client, second, first_token).status_code == 401
    assert _callback(client, first, first_token).status_code == 204


def test_a_duplicate_event_is_a_success_and_is_stored_once(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    moment = datetime.now(UTC)

    assert _callback(client, subscription_id, provider.callback_token, occurred_at=moment).status_code == 204
    assert _callback(client, subscription_id, provider.callback_token, occurred_at=moment).status_code == 204

    from app.db.models import NetworkConditionEventRow

    with SessionLocal() as session:
        rows = session.query(NetworkConditionEventRow).filter_by(
            subscription_id=subscription_id
        ).all()
        assert len(rows) == 1


def test_a_stale_event_is_refused(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    old = datetime.now(UTC) - timedelta(
        seconds=settings.network_conditions_max_event_age_seconds + 60
    )

    response = _callback(client, subscription_id, provider.callback_token, occurred_at=old)
    assert response.json()["detail"]["code"] == "event_stale"


def test_an_out_of_order_event_does_not_become_the_current_condition(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    now = datetime.now(UTC)
    _callback(client, subscription_id, provider.callback_token, "new", "High", now)
    response = _callback(
        client, subscription_id, provider.callback_token, "old", "Low", now - timedelta(minutes=5)
    )

    assert response.json()["detail"]["code"] == "event_out_of_order"
    assert nc.latest_event(_owner(), subscription_id)["level"] == "High"


def test_events_are_bounded_per_subscription(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "network_conditions_max_events_per_subscription", 3, False)
    subscription_id = _subscribe(client).json()["subscription_id"]
    base = datetime.now(UTC) - timedelta(minutes=5)
    for index in range(6):
        _callback(
            client,
            subscription_id,
            provider.callback_token,
            f"evt-{index}",
            "Low",
            base + timedelta(seconds=index),
        )

    from app.db.models import NetworkConditionEventRow

    with SessionLocal() as session:
        rows = session.query(NetworkConditionEventRow).filter_by(
            subscription_id=subscription_id
        ).all()
        assert len(rows) <= 3


def test_a_deleted_subscription_stops_accepting_events(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    client.delete(f"/v1/network-conditions/subscriptions/{subscription_id}", headers=AUTH)

    assert _callback(client, subscription_id, provider.callback_token).status_code == 410


# --- congestion is not evidence ----------------------------------------------


def test_a_verification_never_calls_the_congestion_provider(client, provider):
    """No provider request on a verification, a page load or a locale change."""
    client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": NUMBER, "context": {"event": "checkout"}},
    )
    client.get("/judge")
    client.get("/ui/i18n/ar.json")

    assert provider.creates == provider.queries == provider.deletes == 0


def test_no_congestion_field_reaches_a_signed_verdict(client, provider):
    body = client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": NUMBER, "context": {"event": "password_reset", "account_age_days": 0}},
    ).json()
    text = str(body).lower()

    assert "congestion" not in text
    assert "network_condition" not in text


# --- the panel on the judge page ---------------------------------------------


UI_KEYS = [
    "network_conditions_title",
    "network_conditions_scope",
    "network_conditions_subscribe",
    "network_conditions_forecast",
    "network_conditions_history",
    "network_conditions_delete",
    "network_conditions_idle",
    "network_conditions_working",
    "network_conditions_active",
    "network_conditions_read",
    "network_conditions_deleted",
    "network_conditions_failed",
    "network_conditions_empty",
    "network_conditions_updated",
    "network_conditions_provenance",
    "network_conditions_confidence",
    "network_conditions_confidence_unknown",
    "network_conditions_mode_forecast",
    "network_conditions_mode_history",
    "network_conditions_level_low",
    "network_conditions_level_medium",
    "network_conditions_level_high",
    "network_conditions_level_unknown",
]


@pytest.mark.parametrize("locale", ["en", "ar"])
def test_every_panel_string_is_authored_in_both_languages(locale):
    import json
    from pathlib import Path

    dictionary = json.loads(
        (Path("app/static/i18n") / f"{locale}.json").read_text(encoding="utf-8")
    )["ui"]

    assert [key for key in UI_KEYS if not dictionary.get(key)] == []


def test_the_panel_is_a_separate_section_from_the_verdict():
    from pathlib import Path

    page = Path("app/static/judge.html").read_text(encoding="utf-8")

    assert 'class="network-conditions"' in page
    assert "ui.network_conditions_scope" in page


def test_the_panel_states_that_congestion_is_not_evidence():
    import json
    from pathlib import Path

    english = json.loads(Path("app/static/i18n/en.json").read_text(encoding="utf-8"))["ui"]
    scope = english["network_conditions_scope"].lower()

    assert "not evidence" in scope
    assert "never changes the risk score" in scope


def test_a_level_carries_a_glyph_as_well_as_a_colour():
    """Colour alone is not a state — a reader who cannot distinguish them still
    has to be able to read the level."""
    from pathlib import Path

    page = Path("app/static/judge.html").read_text(encoding="utf-8")

    assert "ncLevelNode" in page
    assert "▲" in page and "◆" in page and "●" in page


def test_the_panel_never_requests_anything_on_load():
    """No fetch outside a click handler: a passive surface that calls an
    operator is a bill the reader never agreed to."""
    from pathlib import Path

    page = Path("app/static/judge.html").read_text(encoding="utf-8")
    panel = page[page.index("--- network conditions") : page.index("function setFactGroup")]

    for call in ("apiJson('/v1/network-conditions", "apiJson(`/v1/network-conditions"):
        for index in range(len(panel)):
            index = panel.find(call, index)
            if index == -1:
                break
            preceding = panel[:index]
            assert "addEventListener('click'" in preceding, call
            break


# --- the subscription is a prerequisite for ONE device -----------------------


def test_a_subscription_cannot_be_used_to_ask_about_another_number(client, provider):
    """Owner isolation was enforced and this was not, so one merchant could
    subscribe a single number and then query every other number it liked."""
    subscription_id = _subscribe(client, number=NUMBER).json()["subscription_id"]
    provider.queries = 0

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": QUIET},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "device_not_subscribed"
    assert provider.queries == 0


def test_the_subscribed_device_can_still_be_queried(client, provider):
    subscription_id = _subscribe(client, number=NUMBER).json()["subscription_id"]

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )

    assert response.status_code == 200


def test_a_subscription_is_not_reused_after_the_provider_changes(client, provider, monkeypatch):
    """A provider id minted by one backend handed to another is at best a 404
    and at worst a delete of somebody else's resource."""
    subscription_id = _subscribe(client).json()["subscription_id"]
    monkeypatch.setattr(settings, "provider", "nac", False)
    provider.queries = 0

    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )

    assert response.json()["detail"]["code"] == "provider_changed"
    assert provider.queries == 0


# --- pacing and concurrency --------------------------------------------------


def test_a_repeated_query_is_paced_rather_than_billed_twice(client, provider):
    subscription_id = _subscribe(client).json()["subscription_id"]
    body = {"phone_number": NUMBER}
    path = f"/v1/network-conditions/subscriptions/{subscription_id}/query"

    assert client.post(path, headers=AUTH, json=body).status_code == 200
    second = client.post(path, headers=AUTH, json=body)

    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "query_too_soon"
    assert provider.queries == 1


def test_pacing_releases_once_the_configured_interval_has_passed(client, provider, monkeypatch):
    monkeypatch.setattr(settings, "network_conditions_min_query_interval_seconds", 0, False)
    subscription_id = _subscribe(client).json()["subscription_id"]
    path = f"/v1/network-conditions/subscriptions/{subscription_id}/query"
    body = {"phone_number": NUMBER}

    assert client.post(path, headers=AUTH, json=body).status_code == 200
    assert client.post(path, headers=AUTH, json=body).status_code == 200
    assert provider.queries == 2


def test_two_concurrent_creates_for_one_device_produce_one_subscription(client, monkeypatch):
    """Counting and inserting were separate steps, and the routes run in worker
    threads: two requests interleaved between them both passed a limit of one."""
    import threading

    recording = Recording()
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    start = threading.Barrier(2)
    results: list[int] = []

    def attempt():
        start.wait(timeout=5)
        results.append(_subscribe(client).status_code)

    threads = [threading.Thread(target=attempt) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert sorted(results) == [201, 422]
    assert recording.creates == 1
    with SessionLocal() as session:
        active = [
            row
            for row in session.query(NetworkConditionSubscriptionRow).all()
            if row.status == "active"
        ]
        assert len(active) == 1


# --- malformed provider data -------------------------------------------------


@pytest.mark.parametrize(
    "row",
    [
        {"start": None, "stop": None, "level": "Low", "confidence": 10},
        {"level": "Low"},
        "not a mapping",
        {"start": "2026-09-06T10:00:00Z", "stop": "2026-09-06T10:15:00Z", "level": "Low"},
    ],
)
def test_a_malformed_interval_is_dropped_rather_than_crashing_the_response(
    client, monkeypatch, row
):
    """A missing key or a null timestamp used to escape normalization and
    surface as a 500."""
    recording = Recording(rows=[row])
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    subscription_id = _subscribe(client).json()["subscription_id"]
    response = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    )

    assert response.status_code == 200
    assert response.json()["intervals"] == []
    assert response.json()["empty"] is True


def test_a_reversed_interval_is_dropped(client, monkeypatch):
    now = datetime.now(UTC)
    recording = Recording(
        rows=[{"start": now, "stop": now - timedelta(minutes=15), "level": "High", "confidence": None}]
    )
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    subscription_id = _subscribe(client).json()["subscription_id"]
    body = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    ).json()

    assert body["intervals"] == []


def test_an_oversized_provider_array_is_bounded(client, monkeypatch):
    now = datetime.now(UTC)
    rows = [
        {
            "start": now + timedelta(minutes=i),
            "stop": now + timedelta(minutes=i + 1),
            "level": "Low",
            "confidence": None,
        }
        for i in range(500)
    ]
    recording = Recording(rows=rows)
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    subscription_id = _subscribe(client).json()["subscription_id"]
    body = client.post(
        f"/v1/network-conditions/subscriptions/{subscription_id}/query",
        headers=AUTH,
        json={"phone_number": NUMBER},
    ).json()

    assert len(body["intervals"]) == nc.MAX_INTERVALS


# --- input validation --------------------------------------------------------


@pytest.mark.parametrize("bad", ["notaphone", "12345678", "+0123456789", "+" + "9" * 20])
def test_a_phone_that_is_not_e164_never_reaches_the_operator(client, provider, bad):
    response = client.post(
        "/v1/network-conditions/subscriptions", headers=AUTH, json={"phone_number": bad}
    )

    assert response.status_code == 422
    assert provider.creates == 0


def test_a_window_entirely_in_the_future_is_not_history():
    """Two ordered bounds are not a historical window just because they are
    ordered. Nokia's forecast is the no-bounds call."""
    start = datetime.now(UTC) + timedelta(hours=1)
    with pytest.raises(nc.NetworkConditionError, match="past"):
        nc.validate_period(start, start + timedelta(hours=1))


def test_a_window_starting_within_clock_skew_is_still_accepted():
    start = datetime.now(UTC) + timedelta(seconds=30)
    assert nc.validate_period(start, start + timedelta(minutes=10)) == nc.HISTORY
