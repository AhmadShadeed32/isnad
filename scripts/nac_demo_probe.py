"""Bounded, simulator-only runner for Nokia Network as Code observations.

Why this exists rather than `scripts/t1_probe.py`: that script supports four
operations, sets no per-call retry limit, and records raw exception text. This
one is built for a batch of observations that will be quoted as evidence, so
the things that make evidence trustworthy are enforced rather than remembered.

  * Nothing external happens without `--execute`. The default run prints a plan.
  * One `--execute` invocation performs at most **one** operation. There is no
    loop, no retry and no automatic model call. Run it again to observe again.
  * Only `+9999` simulator numbers are accepted, and only after E.164 parsing.
  * Only the two documented hosts may be selected, by name. There is no free
    endpoint override.
  * Every SDK call carries `timeout_in_seconds=10, max_retries=0`, so an
    attempt is an attempt.
  * Credentials come from the server-side settings that already exist. They are
    never command arguments and never enter a record, a report or a screenshot.
  * Records carry an allowlist of fields. Raw response bodies, headers and
    tracebacks are deliberately dropped: an operator error body can contain the
    identifiers we are trying not to write down.
  * Observations are labelled `hosted_simulator`. This account is in Simulator
    mode; nothing here may be presented as `live_operator`.

    .venv311/bin/python scripts/nac_demo_probe.py --plan
    .venv311/bin/python scripts/nac_demo_probe.py \
        --operation sim_swap_check --number +99999991000 --execute \
        --record /tmp/isnad-nac-observations.jsonl
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Nokia routes this prefix to simulation. Anything else could be a real
# subscriber, so it is rejected before the SDK is even constructed.
SIMULATOR_PREFIX = "+9999"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# The only two hosts this tool will talk to, selected by name. A free-text
# endpoint override is exactly how a credential ends up posted somewhere else.
HOSTS = {
    "catalog": "https://network-as-code.p-eu.apihub.nokia.io",
    "sdk-default": "https://network-as-code.p-eu.rapidapi.com",
}

# Every call this tool can make is bounded the same way.
REQUEST_OPTIONS = {"timeout_in_seconds": 10, "max_retries": 0}

EVIDENCE_LEVEL = "hosted_simulator"

# Error bodies are not recorded, but a short machine code from one is useful
# and safe. Anything longer or oddly shaped is dropped for a generic label.
MAX_ERROR_CODE_CHARS = 48


class ProbeError(RuntimeError):
    """Refused before anything left the process."""


@dataclass
class Operation:
    """One allowlisted call, with the path it is documented to reach."""

    name: str
    path: str
    summary: str
    run: Callable[[Any, argparse.Namespace], Any]
    normalize: Callable[[Any], dict[str, Any]]
    # Creating or deleting operator-side state is called out in the plan.
    mutating: bool = False
    needs_callback: bool = False
    needs_subscription: bool = False
    # Some operations address the collection, not a device. Demanding a number
    # for those puts a device into a record that never carried one.
    needs_device: bool = True


def _iso(value: Any) -> str | None:
    """A timestamp as text, or None. Never a fabricated value."""
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.isoformat()
    return str(value)[:64]


# --- normalizers: allowlisted response fields only ---------------------------


def _norm_swap_check(response: Any) -> dict[str, Any]:
    swapped = getattr(response, "swapped", None)
    return {"swapped": bool(swapped) if swapped is not None else None}


def _norm_sim_date(response: Any) -> dict[str, Any]:
    value = getattr(response, "latest_sim_change", None)
    return {
        "latest_sim_change": _iso(value),
        # `null` is a real answer that means "no date returned". Recording the
        # distinction stops a later reader from turning it into "never swapped".
        "date_present": value is not None,
        "timezone_aware": isinstance(value, dt.datetime) and value.tzinfo is not None,
    }


def _norm_device_date(response: Any) -> dict[str, Any]:
    value = getattr(response, "latest_device_change", None)
    return {
        "latest_device_change": _iso(value),
        "date_present": value is not None,
        "timezone_aware": isinstance(value, dt.datetime) and value.tzinfo is not None,
        # Days the operator actually looked back. Without it, a null date has
        # no scope at all.
        "monitored_period_days": getattr(response, "monitored_period", None),
    }


def _norm_forwarding(response: Any) -> dict[str, Any]:
    return {"active": getattr(response, "active", None)}


def _norm_subscription(response: Any) -> dict[str, Any]:
    return {
        "subscription_id": getattr(response, "subscription_id", None),
        "started_at": _iso(getattr(response, "started_at", None)),
        "expires_at": _iso(getattr(response, "expires_at", None)),
    }


def _norm_query(response: Any) -> dict[str, Any]:
    intervals = list(response or [])
    return {
        # An empty list is "we were told nothing", not a Low reading.
        "interval_count": len(intervals),
        "intervals": [
            {
                "start": _iso(getattr(i, "time_interval_start", None)),
                "stop": _iso(getattr(i, "time_interval_stop", None)),
                "level": getattr(i, "congestion_level", None),
                "confidence": getattr(i, "confidence_level", None),
            }
            for i in intervals[:8]
        ],
    }


def _norm_empty(_response: Any) -> dict[str, Any]:
    return {"body": "none expected"}


OPERATIONS: dict[str, Operation] = {
    "sim_swap_check": Operation(
        "sim_swap_check",
        "passthrough/camara/v1/sim-swap/sim-swap/v0/check",
        "Boolean: was the SIM changed inside the window we send?",
        lambda c, a: c.sim_swap.check(
            phone_number=a.number,
            max_age=a.max_age,
            correlator=a.correlator,
            request_options=REQUEST_OPTIONS,
        ),
        _norm_swap_check,
    ),
    "device_swap_check": Operation(
        "device_swap_check",
        "passthrough/camara/v1/device-swap/device-swap/v1/check",
        "Boolean: was the handset changed inside the window we send?",
        lambda c, a: c.device_swap.check(
            phone_number=a.number,
            max_age=a.max_age,
            correlator=a.correlator,
            request_options=REQUEST_OPTIONS,
        ),
        _norm_swap_check,
    ),
    "sim_swap_date": Operation(
        "sim_swap_date",
        "passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date",
        "Nullable timestamp of the latest SIM change. A separate billable call.",
        lambda c, a: c.sim_swap.retrieve_date(
            phone_number=a.number, correlator=a.correlator, request_options=REQUEST_OPTIONS
        ),
        _norm_sim_date,
    ),
    "device_swap_date": Operation(
        "device_swap_date",
        "passthrough/camara/v1/device-swap/device-swap/v1/retrieve-date",
        "Nullable timestamp plus the monitored period in days.",
        lambda c, a: c.device_swap.retrieve_date(
            phone_number=a.number, correlator=a.correlator, request_options=REQUEST_OPTIONS
        ),
        _norm_device_date,
    ),
    "forwarding_unconditional": Operation(
        "forwarding_unconditional",
        "passthrough/camara/v1/call-forwarding-signal/call-forwarding-signal"
        "/v0.3/unconditional-call-forwardings",
        "Voice forwarding only. Not SMS forwarding, and not fraud by itself.",
        lambda c, a: c.call_forwarding_signal.retrieve_unconditional_call_forwarding(
            phone_number=a.number, correlator=a.correlator, request_options=REQUEST_OPTIONS
        ),
        _norm_forwarding,
    ),
    "congestion_create": Operation(
        "congestion_create",
        "congestion-insights/v0/subscriptions",
        "Creates operator-side state. Requires the configured HTTPS callback.",
        lambda c, a: c.congestion_insights.create_subscription(
            device={"phone_number": a.number},
            webhook={"notification_url": a.callback_url, "notification_auth_token": a.callback_token},
            subscription_expire_time=a.expire_time,
            request_options=REQUEST_OPTIONS,
        ),
        _norm_subscription,
        mutating=True,
        needs_callback=True,
    ),
    "congestion_get": Operation(
        "congestion_get",
        "congestion-insights/v0/subscriptions/{id}",
        "Reads back one subscription by the id create returned.",
        lambda c, a: c.congestion_insights.get_subscription(
            resource_id=a.subscription_id, request_options=REQUEST_OPTIONS
        ),
        _norm_subscription,
        needs_subscription=True,
    ),
    "congestion_query": Operation(
        "congestion_query",
        "congestion-insights/v0/query",
        "Forecast with no bounds; history when --start and --end are given.",
        lambda c, a: c.congestion_insights.query(
            device={"phone_number": a.number},
            **({"start": a.start, "end": a.end} if a.start and a.end else {}),
            request_options=REQUEST_OPTIONS,
        ),
        _norm_query,
    ),
    "congestion_delete": Operation(
        "congestion_delete",
        "congestion-insights/v0/subscriptions/{id}",
        "Removes operator-side state. Run this even if a query failed.",
        lambda c, a: c.congestion_insights.delete_subscription(
            resource_id=a.subscription_id, request_options=REQUEST_OPTIONS
        ),
        _norm_empty,
        mutating=True,
        needs_subscription=True,
    ),
    "congestion_list": Operation(
        "congestion_list",
        "congestion-insights/v0/subscriptions",
        "Reconciles an uncertain create instead of repeating it.",
        lambda c, a: c.congestion_insights.list_subscriptions(request_options=REQUEST_OPTIONS),
        lambda r: {"count": len(list(r or []))},
        needs_device=False,
    ),
}


@dataclass
class Runner:
    """Holds the attempt counter so a record is honest about failed calls too."""

    attempts: int = 0
    records: list[dict[str, Any]] = field(default_factory=list)

    def validate(self, args: argparse.Namespace) -> Operation:
        """Every refusal here happens before any transport exists."""
        operation = OPERATIONS.get(args.operation or "")
        if operation is None:
            raise ProbeError(f"unknown operation: {args.operation!r}")
        if args.host not in HOSTS:
            raise ProbeError(f"host must be one of {sorted(HOSTS)}, not {args.host!r}")
        if operation.needs_device and not operation.needs_subscription:
            number = args.number or ""
            if not E164.match(number):
                raise ProbeError("number must be E.164, for example +99999991000")
            if not number.startswith(SIMULATOR_PREFIX):
                raise ProbeError(
                    f"only {SIMULATOR_PREFIX} simulator numbers are allowed; "
                    "this tool must never reach a real subscriber"
                )
        if operation.needs_subscription and not args.subscription_id:
            raise ProbeError(f"{operation.name} needs --subscription-id from a create record")
        if operation.needs_callback:
            if not args.callback_url:
                raise ProbeError(
                    "no congestion callback is configured "
                    "(ISNAD_NAC_CONGESTION_CALLBACK_URL); refusing to point an "
                    "operator at an unowned destination"
                )
            if not args.callback_url.startswith("https://"):
                raise ProbeError("the congestion callback must be HTTPS")
        if (args.start or args.end) and not (args.start and args.end):
            raise ProbeError("--start and --end must be given together")
        return operation

    def plan(self, args: argparse.Namespace, operation: Operation | None) -> dict[str, Any]:
        chosen = [operation] if operation else list(OPERATIONS.values())
        return {
            "mode": "plan",
            "external_requests": 0,
            "host": HOSTS.get(args.host),
            "evidence_level": EVIDENCE_LEVEL,
            "max_calls_this_invocation": 1 if operation else 0,
            "request_options": REQUEST_OPTIONS,
            "operations": [
                {
                    "operation": op.name,
                    "path": op.path,
                    "summary": op.summary,
                    "mutating": op.mutating,
                    "callback_host": (
                        _host_only(args.callback_url) if op.needs_callback else None
                    ),
                    "device": _masked(args.number) if op.needs_device and not op.needs_subscription else None,
                    "expiry": args.expire_time if op.needs_callback else None,
                    "cleanup": (
                        "congestion_delete with the returned subscription_id"
                        if op.name == "congestion_create"
                        else None
                    ),
                }
                for op in chosen
            ],
        }

    def execute(self, args: argparse.Namespace, operation: Operation, client: Any) -> dict[str, Any]:
        """Exactly one attempt. The record is written whether or not it worked."""
        # Sent as CAMARA's `x-correlator` on the operations whose contract has
        # one, so the id in this record is the id the operator saw. It is ours,
        # random, and carries nothing about the subscriber.
        args.correlator = str(uuid.uuid4())
        started = time.perf_counter()
        record: dict[str, Any] = {
            "operation": operation.name,
            "evidence_level": EVIDENCE_LEVEL,
            "host": HOSTS[args.host],
            "path": operation.path,
            "observed_at_utc": dt.datetime.now(dt.UTC).isoformat(),
            "device": (
                _masked(args.number)
                if operation.needs_device and not operation.needs_subscription
                else None
            ),
            "request_correlator": args.correlator,
            "request_options": dict(REQUEST_OPTIONS),
        }
        self.attempts += 1
        try:
            response = operation.run(client, args)
        except Exception as exc:  # noqa: BLE001 - sanitized on purpose
            record.update(
                outcome="error",
                http_status=_status_of(exc),
                error_code=_error_code(exc),
                duration_ms=int((time.perf_counter() - started) * 1000),
                attempts=1,
            )
        else:
            record.update(
                outcome="ok",
                http_status=200,
                result=operation.normalize(response),
                duration_ms=int((time.perf_counter() - started) * 1000),
                attempts=1,
            )
        self.records.append(record)
        return record


def _masked(number: str | None) -> str | None:
    """Enough to tell two simulator numbers apart, not enough to be an identifier."""
    if not number:
        return None
    return f"{SIMULATOR_PREFIX}…{number[-4:]}"


def _host_only(url: str | None) -> str | None:
    """A callback host for the plan. Never the path, which carries the secret."""
    if not url:
        return None
    from urllib.parse import urlparse

    return urlparse(url).hostname


def _status_of(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    return status if isinstance(status, int) else None


def _error_code(exc: Exception) -> str:
    """A bounded machine code. Never the body, the headers or a traceback.

    An operator error body is the last place we want to copy verbatim: it can
    echo the phone number back, and it is the SDK's raw text.
    """
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        code = body.get("code")
        if isinstance(code, str) and 0 < len(code) <= MAX_ERROR_CODE_CHARS and code.isascii():
            return code
    status = _status_of(exc)
    if status is not None:
        return f"http_{status}"
    return type(exc).__name__[:MAX_ERROR_CODE_CHARS]


def build_client(host: str, httpx_client: Any = None) -> Any:
    """Construct the SDK client from server-side settings. No request is made."""
    from network_as_code import NetworkAsCodeApi

    from app.config import settings

    if not settings.nac_api_key:
        raise ProbeError("ISNAD_NAC_API_KEY is not configured")
    kwargs: dict[str, Any] = {
        "api_key": settings.nac_api_key,
        "rapidapi_host": settings.nac_rapidapi_host,
        "base_url": HOSTS[host],
    }
    if httpx_client is not None:
        kwargs["httpx_client"] = httpx_client
    return NetworkAsCodeApi(**kwargs)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--operation", choices=sorted(OPERATIONS), default=None)
    parser.add_argument("--number", default=None, help="a +9999 simulator number")
    parser.add_argument("--host", choices=sorted(HOSTS), default="catalog")
    parser.add_argument("--max-age", type=int, default=24, help="check window in hours")
    parser.add_argument("--start", default=None, help="historical query start, RFC 3339")
    parser.add_argument("--end", default=None, help="historical query end, RFC 3339")
    parser.add_argument("--subscription-id", default=None)
    parser.add_argument("--record", default=None, help="append the sanitized record here")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="perform ONE real call. Without it nothing external happens.",
    )
    parser.add_argument("--plan", action="store_true", help="print the plan and exit")
    args = parser.parse_args(argv)
    # Never a command argument: a key or a callback token in argv is a key in
    # the shell history and in any screenshot of the terminal.
    from app.config import settings

    args.callback_url = settings.nac_congestion_callback_url or ""
    args.callback_token = settings.nac_congestion_callback_token or ""
    args.expire_time = (
        dt.datetime.now(dt.UTC)
        + dt.timedelta(seconds=settings.nac_congestion_subscription_ttl_seconds)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return args


def main(argv: list[str] | None = None, httpx_client: Any = None) -> int:
    args = parse_args(argv)
    runner = Runner()

    operation = None
    if args.operation:
        try:
            operation = runner.validate(args)
        except ProbeError as exc:
            print(json.dumps({"mode": "refused", "external_requests": 0, "reason": str(exc)}, indent=2))
            return 2

    if not args.execute or args.plan:
        print(json.dumps(runner.plan(args, operation), indent=2))
        return 0

    if operation is None:
        print(json.dumps({"mode": "refused", "external_requests": 0,
                          "reason": "--execute needs --operation"}, indent=2))
        return 2

    try:
        client = build_client(args.host, httpx_client)
    except ProbeError as exc:
        print(json.dumps({"mode": "refused", "external_requests": 0, "reason": str(exc)}, indent=2))
        return 2

    record = runner.execute(args, operation, client)
    print(json.dumps(record, indent=2))
    if args.record:
        with open(args.record, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    return 0 if record["outcome"] == "ok" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
