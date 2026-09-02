"""S5 — a signature must say what it is evidence *of*."""

from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.chain import subject
from app.chain.models import Verdict
from app.config import InsecureConfiguration, Settings, check_startup_posture
from app.db import store
from app.domain.enums import Decision
from app.domain.schemas import VerificationRequest
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-merchant-key"}


@pytest.fixture(autouse=True)
def _as_the_merchant():
    """Read chains directly as the key that created them.

    store.get_record() is scoped to the caller since S3, and a test calling it
    outside a request has no caller. The HTTP requests below set this for
    themselves; these direct reads have to say who they are.
    """
    from app.events import current_owner
    from app.ownership import owner_hash

    token = current_owner.set(owner_hash("demo-merchant-key"))
    yield
    current_owner.reset(token)


NUMBER_A = "+99999991001"
NUMBER_B = "+99999991002"


def _chain_for(number: str) -> str:
    response = client.post(
        "/v1/verify",
        headers=AUTH,
        json={"phone_number": number, "context": {"event": "signup"}},
    )
    assert response.status_code == 200
    return response.json()["chain_id"]


def test_a_chain_issued_for_a_does_not_verify_against_b():
    """The finding, verbatim: a clean chain for any other number used to verify.

    This is the whole value proposition. Before S5 a merchant in a COD dispute
    could present an ALLOW / ATTESTED_FULL chain obtained for a different number
    and it checked out.
    """
    chain_id = _chain_for(NUMBER_A)

    same = client.post(
        f"/v1/chains/{chain_id}/verification", headers=AUTH, json={"phone_number": NUMBER_A}
    ).json()
    other = client.post(
        f"/v1/chains/{chain_id}/verification", headers=AUTH, json={"phone_number": NUMBER_B}
    ).json()

    assert same["valid"] is True and same["subject_match"] is True
    assert other["valid"] is True and other["subject_match"] is False


def test_the_binding_is_inside_the_signed_bytes():
    """Not a sibling column: it has to be covered by the signature."""
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)

    assert record is not None
    assert record.verdict.subject_hash
    assert record.verdict.subject_hash in record.verdict_json
    assert record.verdict.owner_hash in record.verdict_json
    assert record.verdict.request_hash in record.verdict_json
    assert record.verdict.signed_at in record.verdict_json


def test_the_chain_never_contains_the_phone_number():
    """The binding must not cost the no-PII property it exists to preserve."""
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)

    assert NUMBER_A not in record.verdict_json


def test_public_request_binding_is_not_an_offline_guessable_sha256_digest():
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)
    request = {"phone_number": NUMBER_A, "context": {"event": "signup"}}

    assert record is not None
    assert (
        record.verdict.request_hash
        != hashlib.sha256(
            VerificationRequest.model_validate(request).model_dump_json().encode("utf-8")
        ).hexdigest()
    )


def test_signed_at_cannot_be_backdated_without_breaking_the_signature():
    """It used to be a sibling column, outside the signed bytes."""
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)

    tampered = record.verdict.model_copy(update={"signed_at": "1999-01-01T00:00:00+00:00"})
    from app.chain.vault import vault

    assert vault.verify(tampered.model_dump_json().encode("utf-8"), record.signature) is False


def test_tampering_with_the_subject_breaks_the_signature():
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)

    forged = record.verdict.model_copy(update={"subject_hash": subject.subject_hash(NUMBER_B)})
    from app.chain.vault import vault

    assert vault.verify(forged.model_dump_json().encode("utf-8"), record.signature) is False


def test_a_reverse_chain_binds_to_the_caller_being_checked():
    response = client.post(
        "/v1/reverse-verify",
        headers=AUTH,
        json={"caller_number": "+96279999999", "claimed_identity": "Bank of Jordan"},
    )
    assert response.status_code == 200
    chain_id = response.json()["chain_id"]

    match = client.post(
        f"/v1/chains/{chain_id}/verification",
        headers=AUTH,
        json={"phone_number": "+96279999999"},
    ).json()
    assert match["subject_match"] is True


def test_an_unbound_pre_s5_chain_reads_back_as_unbound_not_as_matching():
    """An old row must parse, and must never claim to be about a number."""
    legacy = Verdict(
        decision=Decision.ALLOW,
        confidence=0.1,
        hypothesis="legit",
        reason="issued before subject binding existed",
        chain_id="chn_legacy0000000000",
    )
    round_tripped = Verdict.model_validate_json(legacy.model_dump_json())

    assert round_tripped.subject_hash == ""
    assert subject.matches(round_tripped.subject_hash, NUMBER_A) is False
    assert subject.matches(round_tripped.subject_hash, "") is False


def test_the_owner_binding_is_peppered_not_a_bare_key_hash():
    """The payload becomes public on the receipt page (T6)."""
    from app.ownership import owner_hash

    bare = owner_hash("demo-merchant-key")
    chain_id = _chain_for(NUMBER_A)
    record = store.get_record(chain_id)

    assert record.verdict.owner_hash != bare
    assert bare not in record.verdict_json


def test_startup_requires_a_persisted_pepper_on_the_billable_path(tmp_path):
    """Same failure mode as S6: a pepper that changes unbinds every old chain."""
    from app.chain.vault import VaultSigner

    key_path = tmp_path / "vault-key.pem"
    VaultSigner(key_path)  # so the S6 check passes and the pepper check is reached

    with pytest.raises(InsecureConfiguration, match="ISNAD_SUBJECT_PEPPER"):
        check_startup_posture(
            Settings(
                _env_file=None,
                provider="nac",
                demo_mode=False,
                merchant_api_keys="a-real-key",
                nac_api_key="test-nac-key",
                vault_key_path=key_path,
            )
        )
