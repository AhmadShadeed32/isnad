"""Validate Isnad's Number Verification consent contract.

``contract`` is fully local and deterministic. It exercises the HTTP routes with
a fake provider and makes no network, model, or billable call.

``live`` targets an already-deployed Isnad service. It is separately armed
because completing the flow calls the configured provider. The authorization
URL is shown as a terminal QR code and is never written to the evidence report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import segno
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

REPO_ROOT = Path(__file__).resolve().parents[1]
ARM_VALUE = "i-understand-this-may-call-a-billable-provider"
CONTRACT_PHONE = "+99999991000"
DEFAULT_CONTRACT_OUTPUT = Path("/tmp/isnad-consent-contract.json")
DEFAULT_LIVE_OUTPUT = Path("/tmp/isnad-handset-validation.json")


class ValidationFailure(RuntimeError):
    """A contract assertion failed without exposing response bodies or credentials."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _assert_status(response: httpx.Response, expected: int, step: str) -> dict[str, Any]:
    if response.status_code != expected:
        code = "unknown"
        try:
            payload = response.json()
            detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
            if isinstance(detail, dict):
                code = str(detail.get("code", "unknown"))
        except (ValueError, TypeError):
            pass
        raise ValidationFailure(
            f"{step} returned HTTP {response.status_code}; error code={code}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValidationFailure(f"{step} did not return a JSON object")
    return payload


def _state_from_authorization_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValidationFailure("provider authorization URL is not absolute HTTPS")
    states = parse_qs(parsed.query).get("state", [])
    if len(states) != 1 or not states[0]:
        raise ValidationFailure("provider authorization URL has no unique OAuth state")
    return states[0]


def _verify_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("algorithm") != "Ed25519":
        raise ValidationFailure("receipt did not declare Ed25519")
    try:
        payload = str(receipt["signed_payload"])
        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(str(receipt["public_key"])))
        key.verify(bytes.fromhex(str(receipt["signature"])), payload.encode("utf-8"))
        signed = json.loads(payload)
    except (KeyError, ValueError, TypeError) as exc:
        raise ValidationFailure("receipt signature material is malformed") from exc
    except Exception as exc:  # cryptography deliberately exposes several failure types
        raise ValidationFailure("receipt signature is invalid") from exc
    if not isinstance(signed, dict):
        raise ValidationFailure("signed receipt payload is not a JSON object")
    return signed


def _number_link(signed: dict[str, Any], expected_source: str) -> dict[str, Any]:
    links = [
        link
        for link in signed.get("chain", [])
        if isinstance(link, dict) and link.get("action") == "number_verify"
    ]
    if len(links) != 1:
        raise ValidationFailure("signed chain does not contain exactly one Number Verification link")
    link = links[0]
    if link.get("source") != expected_source:
        raise ValidationFailure("Number Verification link has an unexpected provider source")
    if link.get("signal") not in {"NUMBER_MATCH", "NUMBER_MISMATCH"}:
        raise ValidationFailure("Number Verification did not return a usable match result")
    return link


def _report(
    *,
    mode: str,
    physical_handset: bool,
    network_calls: bool,
    connection: str,
    initiation: str,
    authorization: str,
    verification: dict[str, Any],
    number_link: dict[str, Any],
    checks: dict[str, Any],
) -> dict[str, Any]:
    chain_id = str(verification["chain_id"])
    return {
        "schema": "isnad_number_verification_validation/v1",
        "generated_at": _now(),
        "scope": {
            "mode": mode,
            "network_calls": network_calls,
            "physical_handset_reported": physical_handset,
            "operator_reported_connection": connection,
            "claim": (
                "Deterministic local route-contract proof; no operator or handset was used."
                if mode == "mock_contract"
                else "Operator-run live consent flow against the configured Isnad deployment."
            ),
        },
        "lifecycle": {
            "initiation_status": initiation,
            "authorization_status": authorization,
            "completion_status": "COMPLETED",
        },
        "verification": {
            "decision": verification.get("decision"),
            "chain_grade": verification.get("chain_grade"),
            "chain_id_suffix": chain_id[-8:],
            "number_verification": {
                "present_once": True,
                "signal": number_link.get("signal"),
                "source": number_link.get("source"),
                "consent_basis": number_link.get("consent_basis"),
            },
        },
        "checks": checks,
        "redaction": {
            "phone_number_saved": False,
            "authorization_url_saved": False,
            "oauth_state_saved": False,
            "authorization_code_saved": False,
            "access_token_saved": False,
            "api_key_saved": False,
        },
    }


def run_contract(output: Path) -> dict[str, Any]:
    """Exercise the complete route contract without leaving this process."""
    os.environ["ISNAD_PROVIDER"] = "mock"
    os.environ["ISNAD_PLANNER"] = "greedy"
    os.environ["ISNAD_DEMO_MODE"] = "true"
    os.environ["ISNAD_DATABASE_URL"] = "sqlite://"
    os.environ["ISNAD_MERCHANT_API_KEYS"] = "contract-smoke-key"
    os.environ["ISNAD_GEMINI_API_KEY"] = ""
    sys.path.insert(0, str(REPO_ROOT))

    from fastapi.testclient import TestClient

    from app.api import routes_consent
    from app.chain.models import EvidenceLink
    from app.chain.vault import vault
    from app.db.database import init_db
    from app.domain.enums import API_LABEL, Action, Result
    from app.main import app

    class ContractProvider:
        def __init__(self) -> None:
            self.number_verification_token: str | None = None
            self.exchanged_codes: list[str] = []
            self.gathered_actions: list[Action] = []

        async def begin_number_verification(self, phone_number, redirect_uri, state, nonce):
            if phone_number != CONTRACT_PHONE:
                raise AssertionError("unexpected contract phone")
            if not nonce or nonce == state:
                raise AssertionError("nonce must be a separate random value from state")
            return f"https://consent.invalid/authorize?state={state}"

        async def exchange_number_verification_code(self, code, redirect_uri, nonce):
            if not nonce:
                raise AssertionError("nonce was not forwarded to the token exchange")
            self.exchanged_codes.append(code)
            return "contract-access-token-never-returned"

        async def gather(self, action, request):
            self.gathered_actions.append(action)
            signal = "NUMBER_MATCH" if action == Action.NUMBER_VERIFY else "EVIDENCE_UNAVAILABLE"
            return EvidenceLink(
                step=0,
                action=action,
                api=API_LABEL[action],
                result=Result.PASS if signal == "NUMBER_MATCH" else Result.INFO,
                signal=signal,
                detail=(
                    "network number matches the provided number"
                    if signal == "NUMBER_MATCH"
                    else "contract provider has no result"
                ),
                consent_basis="NaC authorization / end-user consent",
                source="contract",
                latency_ms=1,
            )

    with tempfile.TemporaryDirectory(prefix="isnad-consent-") as temp_dir:
        vault.configure(Path(temp_dir) / "vault-key.pem")
        init_db()
        provider = ContractProvider()

        def get_provider(token=None):
            provider.number_verification_token = token
            return provider

        original = routes_consent.get_live_provider
        routes_consent.get_live_provider = get_provider
        try:
            client = TestClient(app)
            auth = {"Authorization": "Bearer contract-smoke-key"}
            started_response = client.post(
                "/v1/consents/number-verification",
                headers=auth,
                json={"phone_number": CONTRACT_PHONE, "context": {"event": "signup"}},
            )
            started = _assert_status(started_response, 202, "consent initiation")
            state = _state_from_authorization_url(str(started["authorization_url"]))
            consent_id = str(started["consent_id"])

            callback = _assert_status(
                client.get(
                    "/v1/consents/number-verification/callback",
                    params={"state": state, "code": "single-use-contract-code"},
                ),
                200,
                "consent callback",
            )
            replay = client.get(
                "/v1/consents/number-verification/callback",
                params={"state": state, "code": "replayed-code"},
            )
            if replay.status_code not in {404, 409}:
                raise ValidationFailure("replayed callback was not rejected")

            completed_response = client.post(f"/v1/consents/{consent_id}/verify", headers=auth)
            completed = _assert_status(completed_response, 200, "verification completion")
            duplicate = _assert_status(
                client.post(f"/v1/consents/{consent_id}/verify", headers=auth),
                200,
                "duplicate verification completion",
            )
            if duplicate != completed:
                raise ValidationFailure("duplicate verification did not return the cached response")

            status_payload = _assert_status(
                client.get(f"/v1/consents/{consent_id}", headers=auth),
                200,
                "completed consent status",
            )
            chain_check = _assert_status(
                client.get(f"/v1/consents/{consent_id}/verification", headers=auth),
                200,
                "authenticated chain verification",
            )
            receipt = _assert_status(
                client.get(f"/v1/receipts/{completed['chain_id']}"),
                200,
                "public receipt",
            )
            signed = _verify_receipt(receipt)
            number_link = _number_link(signed, "contract")
            if chain_check.get("valid") is not True or receipt.get("key_trusted") is not True:
                raise ValidationFailure("stored receipt did not verify under a trusted key")
            if provider.exchanged_codes != ["single-use-contract-code"]:
                raise ValidationFailure("authorization code exchange was not single-use")
            if provider.gathered_actions != [Action.NUMBER_VERIFY]:
                raise ValidationFailure("consent did not produce one required Number Verification call")
            exposed = json.dumps(
                [started, callback, completed, duplicate, status_payload, chain_check, receipt]
            )
            if "contract-access-token-never-returned" in exposed:
                raise ValidationFailure("an access token escaped into an HTTP response")

            report = _report(
                mode="mock_contract",
                physical_handset=False,
                network_calls=False,
                connection="none",
                initiation=str(started["status"]),
                authorization=str(callback["status"]),
                verification=completed,
                number_link=number_link,
                checks={
                    "oauth_state_single_use": True,
                    "callback_replay_http_status": replay.status_code,
                    "authorization_code_exchanged_once": True,
                    "completion_idempotent": True,
                    "receipt_signature_valid": True,
                    "receipt_key_trusted": True,
                    "access_token_absent_from_responses": True,
                },
            )
        finally:
            routes_consent.get_live_provider = original

    serialized = json.dumps(report)
    if CONTRACT_PHONE in serialized or CONTRACT_PHONE.lstrip("+") in serialized:
        raise ValidationFailure("redacted report contains the contract phone number")
    _write_report(output, report)
    return report


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    if os.environ.get("ISNAD_HANDSET_ARM") != ARM_VALUE:
        raise ValidationFailure(f"refusing live run: set ISNAD_HANDSET_ARM={ARM_VALUE}")
    api_key = (os.environ.get("ISNAD_HANDSET_API_KEY") or "").strip()
    phone = (os.environ.get("ISNAD_HANDSET_PHONE") or "").strip()
    if not api_key:
        raise ValidationFailure("ISNAD_HANDSET_API_KEY is not set")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise ValidationFailure("ISNAD_HANDSET_PHONE must be an E.164 mobile number")
    base = str(args.base_url).rstrip("/")
    parsed_base = urlsplit(base)
    if parsed_base.scheme != "https" or not parsed_base.hostname:
        raise ValidationFailure("--base-url must be an absolute HTTPS deployment URL")

    auth = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(base_url=base, headers=auth, timeout=args.request_timeout) as client:
        started = _assert_status(
            client.post(
                "/v1/consents/number-verification",
                json={"phone_number": phone, "context": {"event": "signup"}},
            ),
            202,
            "consent initiation",
        )
        authorization_url = str(started.get("authorization_url") or "")
        _state_from_authorization_url(authorization_url)
        consent_id = str(started["consent_id"])

        print("Scan this QR with the test handset. Disable Wi-Fi first for a mobile-data run.")
        segno.make(authorization_url, error="m").terminal(compact=True)
        if args.show_url:
            print(f"Authorization URL (contains short-lived OAuth state): {authorization_url}")
        print("Waiting for the provider callback; no OAuth state or code will be saved.")

        deadline = time.monotonic() + args.wait_seconds
        latest: dict[str, Any] = started
        while time.monotonic() < deadline:
            latest = _assert_status(
                client.get(f"/v1/consents/{consent_id}"),
                200,
                "consent polling",
            )
            status_value = str(latest.get("status"))
            if status_value in {"AUTHORIZED", "DENIED", "FAILED", "EXPIRED"}:
                break
            time.sleep(args.poll_seconds)
        if latest.get("status") != "AUTHORIZED":
            raise ValidationFailure(f"consent ended in status={latest.get('status', 'timeout')}")

        completed = _assert_status(
            client.post(f"/v1/consents/{consent_id}/verify"),
            200,
            "verification completion",
        )
        duplicate = _assert_status(
            client.post(f"/v1/consents/{consent_id}/verify"),
            200,
            "duplicate verification completion",
        )
        if duplicate != completed:
            raise ValidationFailure("duplicate verification did not return the cached response")
        chain_check = _assert_status(
            client.get(f"/v1/consents/{consent_id}/verification"),
            200,
            "authenticated chain verification",
        )
        receipt = _assert_status(
            client.get(f"/v1/receipts/{completed['chain_id']}"),
            200,
            "public receipt",
        )
        signed = _verify_receipt(receipt)
        number_link = _number_link(signed, "nac")
        if chain_check.get("valid") is not True or receipt.get("key_trusted") is not True:
            raise ValidationFailure("stored receipt did not verify under a trusted key")

    report = _report(
        mode="live_handset",
        physical_handset=args.connection in {"mobile-data", "wifi"},
        network_calls=True,
        connection=args.connection,
        initiation=str(started["status"]),
        authorization=str(latest["status"]),
        verification=completed,
        number_link=number_link,
        checks={
            "oauth_state_single_use": "not_replayed_live; covered by contract mode",
            "authorization_code_exchanged_once": "not observable outside deployment",
            "completion_idempotent": True,
            "receipt_signature_valid": True,
            "receipt_key_trusted": True,
            "number_verification_result_usable": True,
        },
    )
    serialized = json.dumps(report)
    if phone in serialized or phone.lstrip("+") in serialized or api_key in serialized:
        raise ValidationFailure("redacted report contains a live identifier or API key")
    _write_report(args.output, report)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    contract = subparsers.add_parser("contract", help="run the offline route-contract smoke")
    contract.add_argument("--output", type=Path, default=DEFAULT_CONTRACT_OUTPUT)

    live = subparsers.add_parser("live", help="run the separately armed handset flow")
    live.add_argument("--base-url", required=True)
    live.add_argument("--output", type=Path, default=DEFAULT_LIVE_OUTPUT)
    live.add_argument(
        "--connection",
        choices=("mobile-data", "wifi", "unknown"),
        default="unknown",
        help="operator-reported handset connection; the script cannot detect it",
    )
    live.add_argument("--wait-seconds", type=float, default=300.0)
    live.add_argument("--poll-seconds", type=float, default=2.0)
    live.add_argument("--request-timeout", type=float, default=15.0)
    live.add_argument(
        "--show-url",
        action="store_true",
        help="also print the short-lived authorization URL; it is never saved",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "contract":
            report = run_contract(args.output)
            output = args.output
        else:
            report = run_live(args)
            output = args.output
    except (ValidationFailure, httpx.HTTPError) as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 2
    print(
        f"PASS {report['scope']['mode']}: Number Verification "
        f"{report['verification']['number_verification']['signal']}; report={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
