from __future__ import annotations

from app.config import settings
from app.providers.base import EvidenceProvider


def get_provider(number_verification_token: str | None = None) -> EvidenceProvider:
    """Select the evidence provider from config.

    ISNAD_PROVIDER=mock   -> scripted (tests + stage demo)
    ISNAD_PROVIDER=nac    -> real Nokia Network-as-Code sandbox
    ISNAD_PROVIDER=hybrid -> scripted, except the links named by
                             `live_evidence_actions` / `live_evidence_numbers`
    """
    from app.providers.mock import MockProvider

    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "nac":
        from app.providers.nac import NacProvider

        return NacProvider(number_verification_token=number_verification_token)
    if settings.provider == "hybrid":
        if not settings.demo_mode:
            raise RuntimeError("ISNAD_PROVIDER=hybrid is demo-only; production must use nac")
        from app.providers.hybrid import HybridProvider
        from app.providers.nac import NacProvider

        return HybridProvider(
            live=NacProvider(number_verification_token=number_verification_token),
            fallback=MockProvider(),
            actions=settings.live_evidence_actions,
            numbers=settings.live_evidence_numbers,
        )
    # Settings validates this at startup.  Keep the runtime boundary fail-closed
    # as well, because tests and embedding applications can still mutate the
    # settings object after it was constructed.
    raise RuntimeError(f"Unsupported ISNAD_PROVIDER={settings.provider!r}")
