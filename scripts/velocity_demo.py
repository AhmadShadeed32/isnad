"""Drive one number against many callees, so Act VII can show caller velocity.

Run this BEFORE going on stage if the room's network is unreliable — the events
persist, and the flag stays lit for the length of the policy window.

    PYTHONPATH=. .venv311/bin/python scripts/velocity_demo.py [--calls 40]
    PYTHONPATH=. .venv311/bin/python scripts/velocity_demo.py --reset

ORDER MATTERS ON STAGE. This bursts Demo Bank's real switchboard number, which
is the same number Act VII uses — deliberately, because "the campaign is wearing
the bank's number" is the strongest version of the point. But once the flag is
lit, Act VII's first beat answers SUSPECTED_SPOOF / caller_velocity instead of
UNKNOWN / registry_match_unannounced, and the act stops making its own point.

    Run Act VII FIRST, then this. Or run --reset in between.

Screen events live in the database, so restarting the server does not clear
them; --reset does.

It talks to the local API rather than the database on purpose: the point being
demonstrated is that ordinary screen traffic produces the signal, not that a
row can be inserted.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8010"
SPOOFED_CALLER = "+96265000000"  # Demo Bank's real switchboard number


def console_token(base: str) -> str:
    page = urllib.request.urlopen(f"{base}/console", timeout=10).read().decode()
    marker = "const CONSOLE_TOKEN = '"
    start = page.index(marker) + len(marker)
    return page[start : page.index("'", start)]


def screen(base: str, token: str, caller: str, callee: str) -> dict:
    import json

    request = urllib.request.Request(
        f"{base}/v1/screen",
        data=json.dumps({"caller_number": caller, "callee_number": callee}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--calls", type=int, default=40)
    parser.add_argument("--caller", default=SPOOFED_CALLER)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="purge all screen events and exit, so Act VII reads clean again",
    )
    args = parser.parse_args()

    if args.reset:
        from app import velocity

        print(f"purged {velocity.purge_older_than(0)} screen events")
        return 0

    try:
        token = console_token(args.base)
    except (urllib.error.URLError, ValueError) as err:
        print(f"could not read a console token from {args.base}: {err}")
        print("is the server running with ISNAD_DEMO_MODE=true?")
        return 1

    print(f"screening {args.caller} against {args.calls} different people…")
    flagged_at = None
    for index in range(args.calls):
        # Distinct callees: the check counts people, not calls, so repeating one
        # number would not produce the signal however many times it was sent.
        result = screen(args.base, token, args.caller, f"+96279{index:06d}")
        if flagged_at is None and result["basis"] == "caller_velocity":
            flagged_at = index + 1
            print(f"  flagged after {flagged_at} distinct callees: {result['label']}")
        time.sleep(0.01)

    final = screen(args.base, token, args.caller, "+962790000001")
    print(f"\n{final['label']} · {final['basis']}")
    print(final["reason"])
    if flagged_at is None:
        print("\nNot flagged. Check velocity.distinct_callees_flag in policy.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
