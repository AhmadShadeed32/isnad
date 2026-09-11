from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_api_key
from app.api.rate_limit import limit_per_key
from app.config import settings
from app.domain.schemas import (
    RegistryInstitution,
    RegistryLookupResponse,
    RegistryMatch,
    RegistryNumber,
)
from app.registry.directory import get_directory

router = APIRouter(prefix="/v1/registry", tags=["registry"], dependencies=[Depends(limit_per_key)])

# The registry answers a question no CAMARA API can: the network attests the
# LINE, this attests the NAME on it. Neither is sufficient alone, and the pair
# is the point — see the reject case in the lookup docstring below.


def _directory():
    return get_directory(str(settings.registry_path))


@router.get("/lookup", response_model=RegistryLookupResponse)
async def registry_lookup(
    number: str = Query(pattern=r"^\+[1-9]\d{7,14}$"),
    claimed_identity: str | None = Query(default=None, max_length=120),
    _key: str = Depends(require_api_key),
) -> RegistryLookupResponse:
    """Which institution published this number, if any.

    Read this response the right way round. A match is NOT a reason to trust a
    caller: caller ID is spoofable, so a scammer presenting the bank's real
    number produces exactly the same match a genuine call does. The match is
    only useful next to network evidence, and the dangerous combination is a
    match plus a `NUMBER_MISMATCH` — that is someone wearing the bank's number
    who is demonstrably not calling from it.

    `claimed_identity` is compared, never rendered and never echoed into a
    prompt (S11); the caller learns only whether their own claim lined up.
    """
    directory = _directory()
    entry = directory.lookup(number)
    institutions, numbers = directory.size

    if entry is None:
        # Absent is not the same as fraudulent. Most numbers in the world are
        # not in this file and are perfectly ordinary, so the honest answer to
        # an unlisted number is "unknown", never "unlisted therefore bad".
        return RegistryLookupResponse(
            number=number,
            found=False,
            registry_size=numbers,
            institutions_indexed=institutions,
        )

    return RegistryLookupResponse(
        number=number,
        found=True,
        registry_size=numbers,
        institutions_indexed=institutions,
        match=RegistryMatch(
            institution_id=entry.institution_id,
            institution_name=entry.institution_name,
            country=entry.country,
            kind=entry.kind,
            outbound=entry.outbound,
            matched_on=entry.matched_on,
            matched_value=entry.value,
            basis=entry.basis,
            source=entry.source,
            # Tri-state on purpose: true, false, or "the registry cannot say".
            claim_matches_registry=directory.check_claim(claimed_identity, entry),
        ),
    )


@router.get("/institution", response_model=list[RegistryInstitution])
async def registry_institution(
    name: str = Query(min_length=2, max_length=120),
    _key: str = Depends(require_api_key),
) -> list[RegistryInstitution]:
    """The numbers an institution publishes — the call-back question.

    "Hang up and dial the number on your card" is the one piece of advice that
    reliably defeats a spoofed call, and it fails only because the victim does
    not have the real number to hand. Every match is returned rather than a best
    guess: a directory that picks between two banks for you can pick wrong, and
    the wrong number here is a scammer's.
    """
    directory = _directory()
    out: list[RegistryInstitution] = []
    for institution_id in directory.find_institution(name):
        numbers = directory.numbers_for(institution_id)
        if not numbers:
            continue
        out.append(
            RegistryInstitution(
                institution_id=institution_id,
                institution_name=numbers[0].institution_name,
                country=numbers[0].country,
                basis=numbers[0].basis,
                source=numbers[0].source,
                numbers=[
                    RegistryNumber(value=n.value, kind=n.kind, outbound=n.outbound) for n in numbers
                ],
            )
        )
    return out
