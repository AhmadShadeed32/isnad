"""The judge's evidence source: one validated choice, frozen for one run.

Both choices run the same code. The SDK that serializes the request, the
adapter that parses the response, the investigator that chose the check, the
policy that scored it, the journal and the signature are identical; what
differs is which transport the SDK is holding and what provenance the answer
carries. That is the entire point — a mock run is evidence that the request
Isnad builds is the right one, and nothing more than that.

Only the two documented swap checks are exposed here, in both modes together.
Expanding either mode alone would make the pair stop being comparable, and
exposing an operation whose contract has not been pinned would make the parity
claim broader than the tests behind it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.domain.enums import Action
from app.domain.schemas import Money, RequestContext, VerificationRequest
from app.providers import nac_contract
from app.providers.base import EvidenceProvider
from app.providers.nac import NacProvider


class EvidenceSource(str, Enum):
    """What a judge picked. Server-validated; an unknown value is refused."""

    MOCK_NOKIA = "mock_nokia"
    NOKIA_SIMULATOR = "nokia_simulator"


class JudgePlanner(str, Enum):
    GEMINI = "gemini"
    GREEDY = "greedy"


# The paired demonstration buys these two checks and no others. Told to the
# planner as availability rather than enforced by refusing its choice later: a
# planner offered a check it cannot have spends budget discovering that.
PAIRED_ACTIONS: frozenset[Action] = frozenset({Action.SIM_SWAP, Action.DEVICE_SWAP})


@lru_cache(maxsize=1)
def policy_digest() -> str:
    """A short identity for the policy a run was decided under.

    Not a version string, because the file does not carry one. A digest is
    honest about what it is: two runs with the same digest were scored by
    literally the same bytes.
    """
    return hashlib.sha256(Path(settings.policy_path).read_bytes()).hexdigest()[:12]


def request_for(scenario: str) -> VerificationRequest:
    """The one request context both paired scenarios share.

    Identical apart from the subscriber, so the two runs differ by exactly the
    thing under demonstration. A cross-border COD checkout by a brand-new
    account is the case the whole product exists for, and it is what makes the
    hypothesis form and the swap checks worth buying.
    """
    return VerificationRequest(
        phone_number=nac_contract.scenario_number(scenario),
        context=RequestContext(
            event="checkout",
            payment_method="cod",
            account_age_days=0,
            amount=Money(value=1500),
        ),
    )


def scenario_catalogue() -> list[dict]:
    """Safe metadata for the page: ids, labels, masked numbers. No credentials."""
    rows = []
    for name, spec in nac_contract.paired_scenarios().items():
        number = str(spec["phone_number"])
        rows.append(
            {
                "id": name,
                "label_en": spec["label_en"],
                "label_ar": spec["label_ar"],
                # Masked in the catalogue like everywhere else, even though a
                # documented simulator number is not personal data. One rule.
                "masked_number": number[:5] + "…" + number[-4:],
                "operations": sorted(spec["responses"]),
            }
        )
    return rows


class PairedSwapProvider:
    """A provider that can answer exactly the two paired swap checks.

    It wraps `NacProvider` rather than subclassing it for one reason that
    matters: it deliberately does **not** expose `enrich_timing`. The
    investigator calls date enrichment only when the provider has that method,
    so omitting it disables the separately priced `retrieve-date` operation in
    BOTH modes without editing `policy.yaml` — which would have changed every
    other run in the deployment to make one demonstration comparable.
    """

    def __init__(self, inner: NacProvider, log: nac_contract.AttemptLog) -> None:
        self._inner = inner
        self.log = log
        self.source = inner.source
        self.environment = inner.environment
        self.contract_version = inner.contract_version

    async def gather(self, action: Action, request: VerificationRequest):
        return await self._inner.gather(action, request)


@dataclass(frozen=True)
class RunContext:
    """Everything frozen at request acceptance, before any work happens.

    Frozen because these are the facts the result is committed to. The judge can
    change the dropdown while a run is in flight; that must change the next run
    and nothing about this one.
    """

    source: EvidenceSource
    scenario: str
    contract_version: str
    planner: JudgePlanner
    policy_digest: str
    run_id: str
    owner: str

    @property
    def environment(self) -> str:
        return (
            nac_contract.MOCK_ENVIRONMENT
            if self.source is EvidenceSource.MOCK_NOKIA
            else nac_contract.HOSTED_ENVIRONMENT
        )

    @property
    def evidence_source_label(self) -> str:
        return (
            nac_contract.MOCK_SOURCE
            if self.source is EvidenceSource.MOCK_NOKIA
            else nac_contract.HOSTED_SOURCE
        )

    def as_metadata(self) -> dict:
        return {
            "evidence_source": self.source.value,
            "evidence_environment": self.environment,
            "contract_version": self.contract_version,
            "scenario": self.scenario,
            "planner_requested": self.planner.value,
            "policy_digest": self.policy_digest,
        }


def build_provider(
    ctx: RunContext, *, fault: str | None = None
) -> tuple[EvidenceProvider, nac_contract.AttemptLog]:
    """One provider instance for one run. Nothing global is mutated.

    The transport, the credential and the provenance are per instance. Two
    judges running different sources at the same moment hold two unrelated
    objects, and neither one can change what the other's SDK is holding.
    """
    log = nac_contract.AttemptLog(budget=settings.judge_nac_attempts_per_run)
    if ctx.source is EvidenceSource.MOCK_NOKIA:
        client = nac_contract.build_mock_client(ctx.scenario, log, fault=fault)
        inner = NacProvider(
            httpx_client=client,
            # A fixed non-secret placeholder, used only inside the mock SDK. No
            # Nokia account is required to run this mode, and a configured real
            # key is not read here even when one exists.
            api_key=nac_contract.MOCK_API_KEY,
            source=nac_contract.MOCK_SOURCE,
            environment=nac_contract.MOCK_ENVIRONMENT,
            contract_version=ctx.contract_version,
        )
    else:
        client = nac_contract.build_hosted_client(log, settings.nac_timeout_seconds)
        inner = NacProvider(
            httpx_client=client,
            api_key=settings.nac_api_key,
            source=nac_contract.HOSTED_SOURCE,
            environment=nac_contract.HOSTED_ENVIRONMENT,
            contract_version=ctx.contract_version,
            # The observed host, not the SDK's untested default. See the note on
            # `judge_nac_base_url`.
            base_url=settings.judge_nac_base_url,
        )
    return PairedSwapProvider(inner, log), log
