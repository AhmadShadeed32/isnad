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
        settings, "nac_congestion_callback_url", "https://callbacks.example/congestion", False
    )


@pytest.fixture(autouse=True)
def _two_tenants(monkeypatch):
    monkeypatch.setattr(
        settings, "merchant_api_keys", "demo-merchant-key,other-merchant-key", False
    )


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
    assert created["scope"] == "hosted_simulator"

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


def test_a_scope_is_never_inferred_from_a_call_that_worked(client, provider):
    """The portal says Simulator. Nothing about a 200 changes that."""
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


def test_an_uncertain_create_leaves_a_row_to_reconcile_against(client, monkeypatch):
    """The row is written before the provider call, so a create that timed out
    having actually succeeded can be found instead of repeated."""
    recording = Recording(fail_create=True)
    monkeypatch.setattr(
        "app.api.routes_network_conditions.get_live_provider", lambda *a, **k: recording
    )
    response = _subscribe(client)

    assert response.status_code == 502
    with SessionLocal() as session:
        rows = session.query(NetworkConditionSubscriptionRow).all()
        assert any(row.status == "failed" for row in rows)


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
    monkeypatch.setattr(settings, "nac_congestion_callback_url", "", False)
    response = _subscribe(client)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "callback_not_configured"
    assert provider.creates == 0


def test_a_plaintext_callback_is_refused(client, provider, monkeypatch):
    monkeypatch.setattr(
        settings, "nac_congestion_callback_url", "http://callbacks.example/x", False
    )
    assert _subscribe(client).json()["detail"]["code"] == "callback_not_https"
    assert provider.creates == 0


def test_the_operator_is_pointed_only_at_the_configured_callback(client, provider):
    """A destination supplied by a request would let a caller aim an operator
    at any host."""
    _subscribe(client)

    assert provider.callback_url == "https://callbacks.example/congestion"


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
