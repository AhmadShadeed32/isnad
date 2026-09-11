"""R12 — the documented selective-live hybrid mode was unreachable.

With a non-empty action/number allowlist, `demo_mode=false` was rejected
because hybrid is demo-only and `demo_mode=true` was rejected because public
demo tokens must never authorize billable calls. Both rejections are
individually right; together they meant no configuration could serve the
feature the setup instructions described, and which refusal a reader saw
depended on which knob they had turned last.

It is retired rather than rebuilt. Making it reachable means minting an
authenticated path to billable calls, and the guard stopping public demo
tokens from authorizing spend is worth more than the feature. This file is the
configuration matrix: it states which combinations are permitted and asserts
that a public demo token can never authorize a paid call in any of them.
"""

from __future__ import annotations

import pytest

from app.config import (
    PUBLISHED_DEMO_KEY,
    InsecureConfiguration,
    Settings,
    check_startup_posture,
    makes_billable_calls,
)


def _settings(**overrides) -> Settings:
    base = {
        "provider": "mock",
        "demo_mode": False,
        "merchant_api_keys": "a-generated-key",
        "live_evidence_actions": "",
        "live_evidence_numbers": "",
        "nac_redirect_uri": "https://isnad.example.com/consent/complete",
    }
    return Settings(**{**base, "_env_file": None, **overrides})


@pytest.mark.parametrize("demo_mode", [True, False])
@pytest.mark.parametrize(
    ("actions", "numbers"),
    [("sim_swap", "+962790000001"), ("sim_swap", ""), ("", "+962790000001")],
)
def test_every_selective_live_hybrid_configuration_is_refused(demo_mode, actions, numbers):
    """The whole point: there is no longer a combination that gets through."""
    cfg = _settings(
        provider="hybrid",
        demo_mode=demo_mode,
        live_evidence_actions=actions,
        live_evidence_numbers=numbers,
    )

    with pytest.raises(InsecureConfiguration, match="retired"):
        check_startup_posture(cfg)


def test_the_refusal_names_the_retirement_not_a_contradiction():
    """A reader must learn the mode is gone, not that they turned the wrong knob."""
    cfg = _settings(provider="hybrid", demo_mode=True, live_evidence_actions="sim_swap",
                    live_evidence_numbers="+962790000001")

    with pytest.raises(InsecureConfiguration) as exc:
        check_startup_posture(cfg)

    message = str(exc.value)
    assert "retired" in message
    assert "ISNAD_PROVIDER=nac" in message, "the refusal must say what to use instead"


def test_hybrid_with_empty_allowlists_remains_a_scripted_test_seam():
    """With nothing configured it is a MockProvider with extra steps."""
    cfg = _settings(provider="hybrid", demo_mode=True)

    check_startup_posture(cfg)

    assert not makes_billable_calls(cfg)


def test_hybrid_still_cannot_serve_a_non_demo_deployment():
    """A production verdict must not be able to fall back to fixture evidence."""
    cfg = _settings(provider="hybrid", demo_mode=False)

    with pytest.raises(InsecureConfiguration, match="demo-only"):
        check_startup_posture(cfg)


def test_nac_is_the_supported_live_configuration():
    """The path the retirement points readers at must actually be startable."""
    cfg = _settings(
        provider="nac",
        demo_mode=False,
        nac_api_key="a-configured-operator-key",
        subject_pepper="a-persisted-pepper",
    )

    check_startup_posture(cfg)

    assert makes_billable_calls(cfg)


def test_a_published_demo_token_can_never_authorize_a_paid_call():
    """The guard the retirement exists to protect."""
    with pytest.raises(InsecureConfiguration):
        check_startup_posture(_settings(provider="nac", demo_mode=True))

    with pytest.raises(InsecureConfiguration, match="ISNAD_MERCHANT_API_KEYS"):
        check_startup_posture(
            _settings(provider="nac", demo_mode=False, merchant_api_keys=PUBLISHED_DEMO_KEY)
        )

    # And no hybrid configuration reaches a billable state at all any more.
    for demo_mode in (True, False):
        cfg = _settings(
            provider="hybrid",
            demo_mode=demo_mode,
            live_evidence_actions="sim_swap",
            live_evidence_numbers="+962790000001",
        )
        with pytest.raises(InsecureConfiguration):
            check_startup_posture(cfg)
