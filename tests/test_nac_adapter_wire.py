"""Exercise Isnad's adapter through SDK 10's real HTTP serialization, offline."""
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from network_as_code import NetworkAsCodeApi

from app.domain.enums import Action, Result
from app.domain.schemas import RequestContext, VerificationRequest
from app.providers.nac import NacProvider

PHONE = '+99999991000'


def provider_for(payload, status=200):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json=payload)

    provider = object.__new__(NacProvider)
    provider.client = NetworkAsCodeApi(
        api_key='wire-test-only',
        httpx_client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    provider.number_verification_token = 'consent-test-only'
    return provider, requests


@pytest.mark.asyncio
async def test_number_verification_is_one_bounded_sdk_attempt():
    provider, requests = provider_for({'code': 'UNAVAILABLE'}, status=503)
    result = await provider.gather(Action.NUMBER_VERIFY, VerificationRequest(phone_number=PHONE))
    assert result.result == Result.INFO
    assert len(requests) == 1
    assert requests[0].headers['authorization'] == 'Bearer consent-test-only'
    assert requests[0].extensions['timeout']['read'] is not None


@pytest.mark.parametrize('action', [Action.SIM_SWAP, Action.DEVICE_SWAP, Action.REACHABILITY,
                                  Action.ROAMING, Action.NUMBER_RECYCLING])
@pytest.mark.asyncio
async def test_missing_provider_boolean_is_unknown_not_an_invented_fact(action):
    provider, requests = provider_for({})
    request = VerificationRequest(phone_number=PHONE, context=RequestContext(last_verified_at=date(2026, 1, 15)))
    result = await provider.gather(action, request)
    assert result.result == Result.INFO
    assert result.signal in {'EVIDENCE_UNAVAILABLE', 'PROVIDER_UNAVAILABLE'}
    assert len(requests) == 1


@pytest.mark.parametrize('action,field,path', [
    (Action.SIM_SWAP, 'latestSimChange', '/sim-swap/sim-swap/v0/retrieve-date'),
    (Action.DEVICE_SWAP, 'latestDeviceChange', '/device-swap/device-swap/v1/retrieve-date'),
])
@pytest.mark.asyncio
async def test_date_enrichment_uses_real_sdk_fields_and_preserves_time(action, field, path):
    observed = datetime.now(UTC) - timedelta(days=1)
    provider, requests = provider_for({field: observed.isoformat(), 'monitoredPeriod': 30})
    result = await provider.enrich_timing(action, VerificationRequest(phone_number=PHONE), 'SIM_STABLE')
    assert requests[0].url.path.endswith(path)
    assert result.provider_time == observed
