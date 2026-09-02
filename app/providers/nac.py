from __future__ import annotations

import asyncio
import importlib
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlencode

import httpx

from app.chain.models import EvidenceLink
from app.config import settings
from app.domain.enums import API_LABEL, Action, Result
from app.domain.schemas import VerificationRequest
from app.providers.vocabulary import detail_for, window_hours

# A dedicated, bounded pool for the blocking SDK (S12).
#
# asyncio.to_thread runs on the default executor, whose threads are shared with
# everything else and whose size grows with demand. A timed-out call abandons its
# thread — asyncio.wait_for cancels the await, never the work — so a provider
# that hangs leaks a thread per request out of the pool the rest of the
# application depends on. Bounded here, so the damage from a hanging provider is
# capped and confined to provider calls.
_NAC_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="nac")


class NacProvider:
    """Nokia Network-as-Code adapter.

    The current Python SDK exposes synchronous methods, so the adapter runs
    them in a worker thread and keeps the agent's provider contract async. The
    mock provider remains the deterministic stage path when credentials are
    unavailable.
    """

    @staticmethod
    def _in_pool(fn, *args):
        """Run a blocking SDK call on the dedicated pool."""
        return asyncio.get_running_loop().run_in_executor(_NAC_POOL, fn, *args)

    def __init__(self, number_verification_token: str | None = None) -> None:
        if not settings.nac_api_key:
            raise RuntimeError("ISNAD_NAC_API_KEY is required when ISNAD_PROVIDER=nac")

        self.number_verification_token = number_verification_token

        try:
            nac = importlib.import_module("network_as_code")
        except ImportError as exc:  # pragma: no cover - exercised in live setup
            raise RuntimeError(
                "Network as Code SDK is not installed. Run `pip install network-as-code[nac]`."
            ) from exc

        api_class = getattr(nac, "NetworkAsCodeApi", None)
        if api_class is not None:
            self.client = api_class(
                rapidapi_host=settings.nac_rapidapi_host,
                api_key=settings.nac_api_key,
            )
            return

        # Keep compatibility with older SDK releases that used this name and
        # accepted the application token directly.
        client_class = getattr(nac, "NetworkAsCodeClient", None)
        if client_class is not None:
            self.client = client_class(token=settings.nac_api_key)
            return

        raise RuntimeError("Installed Network as Code SDK has no supported client class")

    async def gather(self, action: Action, request: VerificationRequest) -> EvidenceLink:
        started = time.perf_counter()
        try:
            result, signal, detail = await asyncio.wait_for(
                self._in_pool(self._gather_sync, action, request),
                timeout=settings.nac_timeout_seconds,
            )
        except TimeoutError:
            return self._failure(action, "PROVIDER_UNAVAILABLE", "provider timeout", started)
        except Exception as exc:  # noqa: BLE001 - provider errors must not expose raw payloads
            return self._failure(action, self._error_signal(exc), self._error_detail(exc), started)

        return EvidenceLink(
            step=0,
            action=action,
            api=API_LABEL[action],
            result=result,
            signal=signal,
            detail=detail,
            consent_basis=self._consent_basis(action),
            source="nac",
            requires_consent=signal == "CONSENT_REQUIRED",
            max_age_hours=window_hours(action),
            latency_ms=self._latency_ms(started),
        )

    async def begin_number_verification(
        self, phone_number: str, redirect_uri: str, state: str
    ) -> str:
        return await asyncio.wait_for(
            self._in_pool(self._begin_number_verification_sync, phone_number, redirect_uri, state),
            timeout=settings.nac_timeout_seconds,
        )

    async def exchange_number_verification_code(self, code: str, redirect_uri: str) -> str:
        number_api = self._number_verification_api()
        if number_api is not None:
            for method_name in ("exchange_code_for_token", "create_camara_token"):
                method = getattr(number_api, method_name, None)
                if callable(method):
                    token = await asyncio.wait_for(
                        self._in_pool(method, code, redirect_uri),
                        timeout=settings.nac_timeout_seconds,
                    )
                    return self._extract_access_token(token)

        client_id = settings.nac_client_id
        client_secret = settings.nac_client_secret
        token_endpoint = settings.nac_token_endpoint
        if not client_id or not client_secret or not token_endpoint:
            try:
                client_id, client_secret, _, token_endpoint = await asyncio.wait_for(
                    self._in_pool(self._sdk_oauth_details_sync),
                    timeout=settings.nac_timeout_seconds,
                )
            except TimeoutError as exc:
                raise RuntimeError("Number Verification OAuth metadata request timed out") from exc
            except Exception as exc:
                raise RuntimeError("Number Verification OAuth credentials are unavailable") from exc

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        }
        auth = None
        if client_secret:
            auth = (client_id, client_secret)
            data.pop("client_id")
        try:
            async with httpx.AsyncClient(timeout=settings.nac_timeout_seconds) as client:
                response = await client.post(token_endpoint, data=data, auth=auth)
                response.raise_for_status()
                return self._extract_access_token(response.json())
        except Exception as exc:
            raise RuntimeError("Number Verification token exchange failed") from exc

    def _gather_sync(self, action: Action, request: VerificationRequest) -> tuple[Result, str, str]:
        phone = request.phone_number
        device = {"phone_number": phone}

        if action == Action.SIM_SWAP:
            response = self.client.sim_swap.check(
                phone_number=phone,
                max_age=settings.nac_max_age_hours,
            )
            swapped = bool(self._value(response, "swapped", False))
            signal = "SIM_SWAPPED" if swapped else "SIM_STABLE"
            # The window is the answer: the API returns a boolean against the
            # max_age we just sent, never a date. See providers/vocabulary.py.
            return Result.FLAG if swapped else Result.PASS, signal, detail_for(signal)

        if action == Action.DEVICE_SWAP:
            response = self.client.device_swap.check(
                phone_number=phone,
                max_age=settings.nac_max_age_hours,
            )
            swapped = bool(self._value(response, "swapped", False))
            signal = "DEVICE_SWAPPED" if swapped else "DEVICE_STABLE"
            return Result.FLAG if swapped else Result.PASS, signal, detail_for(signal)

        if action == Action.REACHABILITY:
            response = self.client.device_status.retrieve_reachability_status(device=device)
            reachable = self._value(response, "reachable", None)
            connectivity = self._value(response, "connectivity", None)
            if reachable:
                connection = ", ".join(connectivity or []) or None
                return (
                    Result.PASS,
                    "REACHABLE_NORMAL",
                    detail_for("REACHABLE_NORMAL", connectivity=connection),
                )
            return Result.FLAG, "REACHABLE_UNAVAILABLE", detail_for("REACHABLE_UNAVAILABLE")

        if action == Action.ROAMING:
            response = self.client.device_status.retrieve_roaming_status(device=device)
            roaming = bool(self._value(response, "roaming", False))
            countries = self._value(response, "countryName", []) or []
            if roaming:
                return (
                    Result.INFO,
                    "ROAMING_NETWORK",
                    detail_for("ROAMING_NETWORK", countries=", ".join(countries) or None),
                )
            return Result.PASS, "HOME_NETWORK", detail_for("HOME_NETWORK")

        if action == Action.LOCATION_VERIFY:
            claim = request.context.claimed_location
            if claim is None:
                return Result.INFO, "EVIDENCE_UNAVAILABLE", "claimed location is required"
            response = self.client.location.verify_v1(
                device=device,
                area={
                    "area_type": "CIRCLE",
                    "center": {"latitude": claim.lat, "longitude": claim.lon},
                    "radius": claim.radius_m,
                },
                max_age=settings.nac_location_max_age_seconds,
            )
            verification = str(self._value(response, "verification_result", "UNKNOWN")).upper()
            if verification == "TRUE":
                return Result.PASS, "AT_CLAIMED_LOCATION", detail_for("AT_CLAIMED_LOCATION")
            if verification == "FALSE":
                return (
                    Result.FLAG,
                    "NOT_AT_CLAIMED_LOCATION",
                    detail_for("NOT_AT_CLAIMED_LOCATION"),
                )
            if verification == "PARTIAL":
                return Result.INFO, "LOCATION_PARTIAL", detail_for("LOCATION_PARTIAL")
            return Result.INFO, "LOCATION_UNKNOWN", detail_for("LOCATION_UNKNOWN")

        if action == Action.NUMBER_VERIFY:
            if not self.number_verification_token:
                return Result.INFO, "CONSENT_REQUIRED", detail_for("CONSENT_REQUIRED")
            number_api = self._number_verification_api()
            verify = getattr(number_api, "verify", None) if number_api is not None else None
            if not callable(verify):
                return (
                    Result.INFO,
                    "EVIDENCE_UNAVAILABLE",
                    "number verification adapter is not configured",
                )
            try:
                response = verify(
                    authorization=f"Bearer {self.number_verification_token}",
                    phone_number=phone,
                )
            except TypeError:
                response = verify(self.number_verification_token, phone_number=phone)
            verified = self._value_any(
                response,
                "device_phone_number_verified",
                "devicePhoneNumberVerified",
                "verified",
            )
            if verified is True:
                return Result.PASS, "NUMBER_MATCH", detail_for("NUMBER_MATCH")
            if verified is False:
                return (
                    Result.FLAG,
                    "NUMBER_MISMATCH",
                    detail_for("NUMBER_MISMATCH"),
                )
            return (
                Result.INFO,
                "EVIDENCE_UNAVAILABLE",
                "number verification returned no usable result",
            )

        if action == Action.DEVICE_INTELLIGENCE:
            return (
                Result.INFO,
                "EVIDENCE_UNAVAILABLE",
                "device intelligence adapter is not configured",
            )

        return (
            Result.INFO,
            "CONSENT_REQUIRED",
            "step-up verification is not a network provider call",
        )

    def _begin_number_verification_sync(
        self, phone_number: str, redirect_uri: str, state: str
    ) -> str:
        number_api = self._number_verification_api()
        if number_api is not None:
            for method_name in ("get_oidc_url", "get_authorization_url"):
                method = getattr(number_api, method_name, None)
                if not callable(method):
                    continue
                try:
                    url = method(
                        redirect_uri=redirect_uri,
                        state=state,
                        login_hint=phone_number,
                        scope=settings.nac_number_verification_scope,
                    )
                except TypeError:
                    url = method(
                        redirect_uri=redirect_uri,
                        state=state,
                        login_hint=phone_number,
                    )
                return self._as_url(url)

        client_id = settings.nac_client_id
        authorization_endpoint = settings.nac_authorization_endpoint
        if not client_id or not authorization_endpoint:
            try:
                client_id, _, discovered_authorization_endpoint, _ = self._sdk_oauth_details_sync()
                authorization_endpoint = authorization_endpoint or discovered_authorization_endpoint
            except Exception as exc:
                raise RuntimeError(
                    "Number Verification authorization metadata is unavailable; configure "
                    "ISNAD_NAC_AUTHORIZATION_ENDPOINT and ISNAD_NAC_CLIENT_ID"
                ) from exc

        query = urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": settings.nac_number_verification_scope,
                "state": state,
                "login_hint": phone_number,
            }
        )
        separator = "&" if "?" in authorization_endpoint else "?"
        return f"{authorization_endpoint}{separator}{query}"

    def _sdk_oauth_details_sync(self) -> tuple[str, str, str, str]:
        credentials = self.client.oauth.get_client_credentials()
        metadata = self.client.well_known_metadata.get_oauth_authorization_server()
        return (
            credentials.client_id,
            credentials.client_secret,
            metadata.authorization_endpoint,
            metadata.token_endpoint,
        )

    def _number_verification_api(self) -> Any | None:
        for name in ("number_verification", "number_verify", "number_verification_api"):
            api = getattr(self.client, name, None)
            if api is not None:
                return api
        return None

    @staticmethod
    def _require_https(url: str) -> str:
        """Any URL from the SDK reaches window.open() in the console (S13).

        The SDK is an external source; an http:// or javascript: value from it
        must not become a navigation the browser performs.
        """
        if not url.lower().startswith("https://"):
            raise RuntimeError("provider returned a non-HTTPS authorization URL")
        return url

    @staticmethod
    def _as_url(value: Any) -> str:
        if isinstance(value, str):
            return NacProvider._require_https(value)
        url = getattr(value, "url", None) or getattr(value, "href", None)
        if isinstance(url, str):
            return NacProvider._require_https(url)
        raise RuntimeError("Network as Code returned an invalid authorization URL")

    @classmethod
    def _extract_access_token(cls, value: Any) -> str:
        if isinstance(value, str) and value:
            return value
        token = cls._value_any(value, "access_token", "accessToken", "token")
        if isinstance(token, str) and token:
            return token
        raise RuntimeError("Network as Code returned no access token")

    @staticmethod
    def _value_any(response: Any, *names: str) -> Any:
        for name in names:
            if isinstance(response, Mapping) and name in response:
                return response[name]
            value = getattr(response, name, None)
            if value is not None:
                return value
        return None

    @staticmethod
    def _value(response: Any, name: str, default: Any = None) -> Any:
        if isinstance(response, dict):
            return response.get(name, default)
        return getattr(response, name, default)

    @staticmethod
    def _consent_basis(action: Action) -> str:
        if action in {Action.NUMBER_VERIFY, Action.SIM_SWAP, Action.LOCATION_VERIFY}:
            return "NaC authorization / end-user consent"
        return "NaC application authorization"

    @staticmethod
    def _latency_ms(started: float) -> int:
        return max(1, int((time.perf_counter() - started) * 1000))

    def _failure(self, action: Action, signal: str, detail: str, started: float) -> EvidenceLink:
        return EvidenceLink(
            step=0,
            action=action,
            api=API_LABEL[action],
            result=Result.INFO,
            signal=signal,
            detail=detail,
            consent_basis=self._consent_basis(action),
            source="nac",
            requires_consent=signal == "CONSENT_REQUIRED",
            latency_ms=self._latency_ms(started),
        )

    @staticmethod
    def _error_signal(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status_code in {401, 403}:
            return "CONSENT_REQUIRED"
        if status_code in {404, 422}:
            return "EVIDENCE_UNAVAILABLE"
        return "PROVIDER_UNAVAILABLE"

    @staticmethod
    def _error_detail(exc: Exception) -> str:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status_code in {401, 403}:
            return "provider authorization or consent was not available"
        if status_code in {404, 422}:
            return "provider could not produce evidence for this device"
        return "provider request failed"
