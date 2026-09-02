"""T1 — fire exactly ONE real CAMARA call and record what actually came back.

Every statement this repo makes about Nokia Network-as-Code behaviour is an
assumption until a real response has been observed. `NacProvider.gather()`
cannot be used for that: it deliberately swallows the raw payload and returns a
generic EvidenceLink, which is right for production and useless for discovery.
This script calls the SDK directly and records the raw shape.

It costs money. Two guards, both required:

    ISNAD_T1_ARM=i-understand-this-costs-money
    ISNAD_T1_PHONE=+9627XXXXXXXX        (or pass as argv[1])

Exactly one call is made. There is no retry and no loop: a failed probe is a
result to read, not a thing to hammer. Run it again by hand if you want another.

    ISNAD_T1_ARM=i-understand-this-costs-money \
    ISNAD_T1_PHONE=+962... .venv311/bin/python scripts/t1_probe.py sim_swap

The observation is written to docs/T1_OBSERVATIONS.md, appended, never
overwritten — an earlier failed probe is evidence too. The phone number is
never written to that file: only its last two digits, so successive probes can
be told apart without committing a real identifier.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import traceback
from pathlib import Path

# Run from a checkout without installing: scripts/ is not on sys.path by default.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARM_VALUE = "i-understand-this-costs-money"
OUT = Path(__file__).resolve().parent.parent / "docs" / "T1_OBSERVATIONS.md"

# Kept deliberately small. Each entry is one billable call.
PROBES = {
    "sim_swap": "client.sim_swap.check(phone_number=..., max_age=...)",
    "device_swap": "client.device_swap.check(phone_number=..., max_age=...)",
    "reachability": "client.device_status.retrieve_reachability_status(device=...)",
    "roaming": "client.device_status.retrieve_roaming_status(device=...)",
}


def describe(value: object, depth: int = 0) -> object:
    """Render an SDK response without assuming it is a dict or a pydantic model."""
    if depth > 3:
        return f"<truncated {type(value).__name__}>"
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [describe(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {str(k): describe(v, depth + 1) for k, v in value.items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        try:
            return {"__model__": type(value).__name__, **describe(dump(), depth + 1)}
        except Exception:  # noqa: BLE001, S110 - inspection falls back to a generic object view
            pass
    attrs = {
        name: describe(getattr(value, name), depth + 1)
        for name in dir(value)
        if not name.startswith("_") and not callable(getattr(value, name, None))
    }
    return {"__type__": type(value).__name__, **attrs}


def main() -> int:
    if os.environ.get("ISNAD_T1_ARM") != ARM_VALUE:
        print(f"refusing to run: set ISNAD_T1_ARM={ARM_VALUE}", file=sys.stderr)
        print("this makes a real, billable network call.", file=sys.stderr)
        return 2

    probe = (sys.argv[1] if len(sys.argv) > 1 else "sim_swap").strip()
    if probe not in PROBES:
        print(f"unknown probe {probe!r}; choose one of {sorted(PROBES)}", file=sys.stderr)
        return 2

    phone = (os.environ.get("ISNAD_T1_PHONE") or "").strip()
    if not phone.startswith("+") or not phone[1:].isdigit():
        print("set ISNAD_T1_PHONE to an E.164 number, e.g. +9627XXXXXXXX", file=sys.stderr)
        return 2

    from app.config import settings

    if not settings.nac_api_key:
        print("ISNAD_NAC_API_KEY is not set", file=sys.stderr)
        return 2

    from app.providers.nac import NacProvider

    provider = NacProvider()
    client = provider.client
    device = {"phone_number": phone}

    started = dt.datetime.now(dt.UTC)
    outcome: dict[str, object]
    try:
        if probe == "sim_swap":
            response = client.sim_swap.check(phone_number=phone, max_age=settings.nac_max_age_hours)
        elif probe == "device_swap":
            response = client.device_swap.check(
                phone_number=phone, max_age=settings.nac_max_age_hours
            )
        elif probe == "reachability":
            response = client.device_status.retrieve_reachability_status(device=device)
        else:
            response = client.device_status.retrieve_roaming_status(device=device)
        outcome = {
            "ok": True,
            "python_type": type(response).__name__,
            "module": type(response).__module__,
            "value": describe(response),
        }
    except Exception as exc:  # noqa: BLE001 - the failure is the observation
        body = getattr(exc, "body", None) or getattr(exc, "response", None)
        outcome = {
            "ok": False,
            "exception_type": type(exc).__name__,
            "exception_module": type(exc).__module__,
            "status_code": getattr(exc, "status_code", None) or getattr(exc, "status", None),
            "message": str(exc)[:2000],
            "body": describe(body) if body is not None else None,
            "traceback": traceback.format_exc()[-2000:],
        }
    elapsed_ms = int((dt.datetime.now(dt.UTC) - started).total_seconds() * 1000)

    record = {
        "probe": probe,
        "sdk_call": PROBES[probe],
        "at": started.isoformat(),
        "elapsed_ms": elapsed_ms,
        "phone_suffix": phone[-2:],
        "rapidapi_host": settings.nac_rapidapi_host,
        **outcome,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not OUT.exists():
        OUT.write_text(
            "# T1 — observed CAMARA responses\n\n"
            "Appended by `scripts/t1_probe.py`. Every entry is one real, billable\n"
            "call. Anything about NaC that is not in this file is an assumption.\n",
            encoding="utf-8",
        )
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {probe} — {started.isoformat()}\n\n```json\n")
        fh.write(json.dumps(record, indent=2, default=str))
        fh.write("\n```\n")

    print(json.dumps(record, indent=2, default=str))
    print(f"\nappended to {OUT}", file=sys.stderr)
    return 0 if outcome["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
