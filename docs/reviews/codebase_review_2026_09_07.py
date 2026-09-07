"""Offline reproductions for handoff R01-R06/R08/R12, 7 September 2026.

STATUS, 7 September 2026, after commit `af6936b`: **R01, R02, R03, R04, R06 and
R08 are fixed**, so this script no longer reaches past its first reproduction —
`nc.query` for an unsubscribed device now raises "this subscription is for a
different device" instead of quietly calling the provider. Kept as the record of
what was observed, not as a passing check. The regression tests that replaced
each reproduction live in `tests/test_network_conditions.py`:

    device binding        test_a_subscription_cannot_be_used_to_ask_about_another_number
    callback wiring       test_an_event_posted_to_the_url_the_operator_was_given_reaches_the_right_row
    quota race + pacing   test_two_concurrent_creates_for_one_device_produce_one_subscription
                          test_a_repeated_query_is_paced_rather_than_billed_twice
    uncertain create      test_an_uncertain_create_stays_non_terminal_so_it_must_be_reconciled
                          test_an_empty_provider_id_never_becomes_an_active_subscription
    provenance            test_a_scope_names_the_provider_that_actually_answered
    validation            test_a_phone_that_is_not_e164_never_reaches_the_operator
                          test_a_malformed_interval_is_dropped_rather_than_crashing_the_response

R05 (session TTL), R12 (unreachable hybrid mode) and the P2 items R07, R09, R10
and R13 are **still open** and this script still reproduces them if the earlier
sections are commented out.

Run from the repository root. Prints observed defects, not acceptance assertions.
Each invocation creates its own temporary SQLite database and signing key.
No Nokia or Gemini requests are made. The thread barrier deliberately exposes
an existing subscription reservation race; short session timings expose the
same expiry window without waiting for production polling intervals.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
work = Path(tempfile.mkdtemp(prefix="isnad-review-"))
os.environ.update(
    ISNAD_PROVIDER="mock",
    ISNAD_PLANNER="greedy",
    ISNAD_GEMINI_API_KEY="",
    ISNAD_NAC_API_KEY="",
    ISNAD_CACHE_BACKEND="memory",
    ISNAD_POLICY_PATH=str(Path.cwd() / "app/policy/policy.yaml"),
    ISNAD_DEMO_MODE="true",
    ISNAD_DATABASE_URL=f"sqlite:///{work}/review.db",
    ISNAD_VAULT_KEY_PATH=str(work / "vault.pem"),
    ISNAD_SUBJECT_PEPPER="review-only",
    ISNAD_MERCHANT_API_KEYS="review-only",
    # Renamed and re-specified on 7 September 2026: this is now a BASE, and the
    # subscription id is appended to it. See the R02 fix.
    ISNAD_NAC_CONGESTION_CALLBACK_BASE_URL="https://callbacks.invalid/v1/network-conditions/callbacks",
    ISNAD_VAULT_TRUSTED_PUBLIC_KEYS="4034e169495122a893d8fe6738c2b0f54655fdfb6ec3c6d0eeb938d1330e7f9f",
)
import asyncio
from unittest.mock import patch

from app import network_conditions as nc
from app.chain.vault import vault
from app.config import InsecureConfiguration, Settings, check_startup_posture, settings
from app.db.database import SessionLocal, init_db
from app.db.models import NetworkConditionSubscriptionRow
from app.domain.schemas import NetworkConditionSubscribeRequest
from app.events import current_owner
from app.providers.mock import MockProvider
from app.session.manager import SessionManager

init_db()
vault.configure(settings.vault_key_path)


class Recorder:
    def __init__(self):
        self.calls = []
        self.callback = None

    def create_congestion_subscription(self, **kwargs):
        self.callback = kwargs["callback_url"]
        return "remote-1"

    def query_congestion(self, **kwargs):
        self.calls.append(kwargs["phone_number"])
        return []

    def delete_congestion_subscription(self, provider_id):
        pass


p = Recorder()
created = nc.create("owner", "+962790000001", p)
sid = created["subscription_id"]
nc.query("owner", sid, "+962790000002", p)
nc.query("owner", sid, "+962790000002", p)
print("NC other-device and immediate repeat calls:", p.calls)
print("NC callback contains local subscription ID:", sid in p.callback)
print("NC mock provenance:", nc.query("owner", sid, "+962790000001", MockProvider()).provenance)
print(
    "NC invalid phone accepted:",
    NetworkConditionSubscribeRequest(phone_number="notaphone").phone_number,
)


class TimeoutRecorder(Recorder):
    def create_congestion_subscription(self, **kwargs):
        raise TimeoutError("uncertain")


for _ in range(2):
    try:
        nc.create("timeout-owner", "+962790000003", TimeoutRecorder())
    except nc.NetworkConditionError:
        pass
with SessionLocal() as s:
    rows = s.query(NetworkConditionSubscriptionRow).filter_by(owner_hash="timeout-owner").all()
    print("NC repeated uncertain creates:", [(r.status, r.provider_id) for r in rows])


class EmptyID(Recorder):
    def create_congestion_subscription(self, **kwargs):
        return ""


print(
    "NC empty provider ID status:", nc.create("empty-owner", "+962790000004", EmptyID())["status"]
)
for demo in [False, True]:
    cfg = Settings(
        _env_file=None,
        provider="hybrid",
        demo_mode=demo,
        live_evidence_actions="sim_swap",
        live_evidence_numbers="+962790000001",
    )
    try:
        check_startup_posture(cfg)
    except InsecureConfiguration as e:
        print("hybrid demo=", demo, "rejected:", str(e).split(".")[0])


async def session_probe():
    manager = SessionManager()
    current_owner.set("owner")
    calls = []

    class Fake:
        async def gather(self, action, req):
            calls.append(action.value)
            return await MockProvider().gather(action, req)

    with patch.object(manager, "_emit", return_value=None):
        rec = await manager.create(
            "+962790000001", ttl_seconds=0.02, poll_seconds=0.1, provider=Fake()
        )
        await asyncio.sleep(0.05)
        print("Session status after TTL before wake:", manager.get(rec.id).status.value)
        await asyncio.sleep(0.1)
        print("Session calls made after TTL:", calls)
        await manager.shutdown()


asyncio.run(session_probe())
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

barrier = Barrier(2)
original_counts = nc._active_counts


def raced_counts(*args):
    result = original_counts(*args)
    barrier.wait(timeout=5)
    return result


with (
    patch.object(nc, "_active_counts", side_effect=raced_counts),
    ThreadPoolExecutor(max_workers=2) as executor,
):
    futures = [
        executor.submit(nc.create, "race-owner", "+962790000007", Recorder()) for _ in range(2)
    ]
    print("NC concurrent same-device create statuses:", [f.result()["status"] for f in futures])
