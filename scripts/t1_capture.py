"""T1 — call every CAMARA action for real and record what came back.

The runbook's T1 asks for one real call per action, the raw SDK response stored
verbatim under docs/nac/, and contract tests built from those recordings that
run offline. This produces the recordings.

Each action is captured twice, because the two answer different questions:

  raw        — what the SDK actually returned (or raised). This is the evidence.
               NacProvider.gather() cannot supply it: it deliberately swallows
               payloads so a provider error can never reach a caller.
  normalized — what NacProvider.gather() turned that into. This is what the
               contract tests assert on, and it is where a wrong assumption
               about the SDK's response shape would show up.

Identifiers are redacted before anything is written: the device number is
replaced by its last two digits everywhere it appears.

    PYTHONPATH=. ISNAD_T1_ARM=i-understand-this-costs-money \
    ISNAD_T1_PHONE=+99999991000 .venv311/bin/python scripts/t1_capture.py
"""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib.metadata as md
import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARM_VALUE = "i-understand-this-costs-money"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "nac"


def describe(value: object, depth: int = 0) -> object:
    if depth > 4:
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
    return {
        "__type__": type(value).__name__,
        **{
            n: describe(getattr(value, n), depth + 1)
            for n in dir(value)
            if not n.startswith("_") and not callable(getattr(value, n, None))
        },
    }


def redact(obj: object, phone: str) -> object:
    """Never write a real identifier to a file that gets committed."""
    tail = phone[-2:]
    if isinstance(obj, str):
        return obj.replace(phone, f"+<redacted>{tail}").replace(
            phone.lstrip("+"), f"<redacted>{tail}"
        )
    if isinstance(obj, list):
        return [redact(v, phone) for v in obj]
    if isinstance(obj, dict):
        return {k: redact(v, phone) for k, v in obj.items()}
    return obj


async def main() -> int:
    if os.environ.get("ISNAD_T1_ARM") != ARM_VALUE:
        print(f"refusing to run: set ISNAD_T1_ARM={ARM_VALUE}", file=sys.stderr)
        return 2
    phone = (os.environ.get("ISNAD_T1_PHONE") or "").strip()
    if not phone.startswith("+") or not phone[1:].isdigit():
        print("set ISNAD_T1_PHONE to an E.164 number", file=sys.stderr)
        return 2

    os.environ["ISNAD_PROVIDER"] = "nac"
    from app.config import settings
    from app.domain.enums import API_LABEL, Action
    from app.domain.schemas import RequestContext, VerificationRequest
    from app.providers.nac import NacProvider

    if not settings.nac_api_key:
        print("ISNAD_NAC_API_KEY is not set", file=sys.stderr)
        return 2

    provider = NacProvider()
    sdk_version = md.version("network-as-code")
    request = VerificationRequest(
        phone_number=phone,
        context=RequestContext(event="checkout", account_age_days=0),
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for action in Action:
        started = dt.datetime.now(dt.UTC)
        raw: dict[str, object]
        # 1) the raw SDK call, so a failure is legible
        try:
            result, signal, detail = provider._gather_sync(action, request)
            raw = {"ok": True, "result": str(result), "signal": signal, "detail": detail}
        except Exception as exc:  # noqa: BLE001 - this probe records every SDK failure
            raw = {
                "ok": False,
                "exception_type": type(exc).__name__,
                "exception_module": type(exc).__module__,
                "status_code": getattr(exc, "status_code", None) or getattr(exc, "status", None),
                "message": str(exc)[:1500],
                "traceback": traceback.format_exc()[-1200:],
            }
        # 2) what the provider normalizes it to — what the app actually consumes
        link = await provider.gather(action, request)
        elapsed = int((dt.datetime.now(dt.UTC) - started).total_seconds() * 1000)

        record = {
            "action": action.value,
            "api": API_LABEL[action],
            "sdk": "network-as-code",
            "sdk_version": sdk_version,
            "rapidapi_host": settings.nac_rapidapi_host,
            "captured_at": started.isoformat(),
            "elapsed_ms": elapsed,
            "device_suffix": phone[-2:],
            "raw": raw,
            "normalized": {
                "result": str(link.result),
                "signal": link.signal,
                "detail": link.detail,
                "source": link.source,
                "requires_consent": link.requires_consent,
                "consent_basis": link.consent_basis,
            },
        }
        record = redact(record, phone)
        path = OUT_DIR / f"{action.value}.json"
        path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
        state = "live" if raw.get("ok") else f"error:{raw.get('exception_type')}"
        summary.append((action.value, state, link.signal, elapsed))
        print(f"  {action.value:22} {state:28} -> {link.signal:24} {elapsed:>6}ms")

    print(f"\nwrote {len(summary)} fixtures to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
