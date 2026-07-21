from __future__ import annotations

from typing import Optional

from app.config import settings
from app.providers.base import EvidenceProvider


def get_provider(number_verification_token: Optional[str] = None) -> EvidenceProvider:
    """Select the evidence provider from config.

    ISNAD_PROVIDER=mock -> scripted (tests + stage demo)
    ISNAD_PROVIDER=nac  -> real Nokia Network-as-Code sandbox
    """
    if settings.provider == "nac":
        from app.providers.nac import NacProvider

        return NacProvider(number_verification_token=number_verification_token)
    from app.providers.mock import MockProvider

    return MockProvider()
