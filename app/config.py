from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Everything is overridable via environment variables prefixed with ISNAD_,
    e.g. ISNAD_PROVIDER=nac, ISNAD_MERCHANT_API_KEYS=key1,key2
    """

    model_config = SettingsConfigDict(env_prefix="ISNAD_", env_file=".env", extra="ignore")

    # "mock" runs the scripted providers (tests + stage demo);
    # "nac" talks to the real Nokia Network-as-Code sandbox;
    # "nac_fake" talks to the offline fake operator (P4a): the same OAuth/OIDC
    # consent contract as "nac", against `demo/fake_operator` instead of Nokia.
    # It never leaves localhost and is excluded from makes_billable_calls below.
    provider: Literal["mock", "nac", "hybrid", "nac_fake"] = "mock"

    # Demo-only routes and controls. Off by default: on, it opens write
    # endpoints that a stranger can fire into the judges' console mid-demo (S4).
    # Turn it on deliberately for a local run, never in a reachable deployment.
    demo_mode: bool = False

    # "greedy" is deterministic and demo-safe; "llm" is the optional planner.
    planner: str = "greedy"

    # Comma-separated list of accepted merchant API keys. Empty by default:
    # a shipped default is a published credential, and `require_api_key` already
    # fails closed on an empty set, so the safe posture is no key until one is
    # configured (S1).
    merchant_api_keys: str = ""

    # Path to the policy / evidence-cost model.
    policy_path: Path = Path(__file__).parent / "policy" / "policy.yaml"

    # --- Verified Caller (CAMARA VerifiedCaller pre-announce) ---
    # Which institution each key may speak for: "key:institution_id,key2:id2".
    # Empty by default and fails closed. Without the binding, any key holder
    # could announce a call "from" a bank and have their own spoofed call come
    # back verified — the mechanism inverts into the attack it exists to stop.
    institution_keys: str = ""
    # The announcement window is the spoofing window: while one stands, a call
    # presenting that number verifies. The CAMARA examples use 45s.
    announce_ttl_seconds: int = 45
    announce_max_ttl_seconds: int = 300

    # --- Caller velocity ---
    # How long screen events are kept. They answer one question about the recent
    # past; keeping them forever would accumulate a record of who was screened
    # against whom for no benefit. An hour covers any window worth asking about.
    velocity_retention_seconds: int = 3600
    # How often the retention sweeper deletes what is past its window. Both
    # purge functions existed with no caller in app code, so nothing was ever
    # actually deleted. 0 disables the sweeper.
    purge_interval_seconds: int = 300

    # --- Number registry ---
    # Which published numbers belong to which institution. Answers the question
    # no CAMARA API can: the network attests the line, not the name on it.
    registry_path: Path = Path(__file__).parent / "registry" / "registry.yaml"
    # Refuse to start without a valid registry signature. Off by default so a
    # dev checkout works unsigned; a deployment that serves real institutional
    # numbers should turn it on. A signature that is present and WRONG is fatal
    # either way — that is tampering, not a posture choice.
    registry_signature_required: bool = False

    # --- Trust-with-a-TTL sessions ---
    session_ttl_seconds: int = 120  # how long trust stays live
    session_poll_seconds: float = 1.5  # how often the monitor re-checks signals
    # Caller-supplied TTL used to go up to 86400s, and every session polls SIM
    # Swap *and* Device Swap. At the default interval that is 115,200 billed
    # CAMARA calls from one request (S7a). These bound it.
    session_max_ttl_seconds: int = 300
    session_max_per_owner: int = 5
    # On the billable path, a 1.5s poll is a quota amplifier rather than a
    # feature. The floor does not apply to the mock provider, where the demo
    # needs a swap to show up on stage within a couple of seconds.
    session_min_poll_seconds_nac: float = 30.0

    # --- Evidence vault (Ed25519 chain signing) ---
    # If set, the signing key is loaded/persisted here so signatures survive
    # restarts. If None, an ephemeral key is generated per process.
    vault_key_path: Path | None = Path(".isnad/vault-key.pem")

    # Pepper for the subject binding in a signed verdict (S5). Keeping an HMAC
    # of the number rather than the number itself is what lets a chain say who it
    # is about without ever storing a phone number. It has the same persistence
    # requirement as the vault key: change it and every previously signed chain
    # stops matching its subject, which on stage looks like the vault failing.
    # Unset on the mock path, where it is derived from the vault key so a local
    # demo has exactly one secret to persist.
    subject_pepper: str | None = None

    # Encrypts the signing key at rest. Optional; the file mode is the primary
    # control (S7b) and this is defence in depth for a shared volume.
    vault_key_passphrase: str | None = None

    # Public keys (raw Ed25519, hex) this deployment still vouches for besides
    # the live one. A rotation without this orphans every chain signed by the
    # old key (S6). Comma-separated.
    vault_trusted_public_keys: str = ""

    # --- Persistence ---
    # SQLite by default (file below); set to a postgresql+psycopg URL in prod.
    database_url: str = "sqlite:///./isnad.db"

    # --- Nokia NaC (only used when provider == "nac") ---
    nac_api_key: str | None = None
    nac_rapidapi_host: str = "network-as-code.nokia.rapidapi.com"
    nac_max_age_hours: int = 240
    nac_location_max_age_seconds: int = 3600
    nac_timeout_seconds: float = 8.0
    # Localhost by default, which is only correct for local development: on a
    # deployed host it redirects a judge's browser to their own machine (S13).
    # check_startup_posture refuses it on the nac path.
    nac_redirect_uri: str = "http://localhost:8000/v1/consents/number-verification/callback"
    nac_authorization_endpoint: str | None = None
    nac_token_endpoint: str | None = None
    nac_client_id: str | None = None
    nac_client_secret: str | None = None
    nac_number_verification_scope: str = (
        "dpv:FraudPreventionAndDetection number-verification:verify"
    )
    nac_consent_ttl_seconds: int = 300
    # How long a COMPLETED/DENIED/FAILED/EXPIRED consent's result stays
    # retrievable after it finishes, even while other merchants' consents are
    # being created (P4a). Before this existed, ConsentStore._sweep() removed a
    # terminal record the instant *any* create() call ran, so a merchant
    # polling a just-completed flow could see it vanish into a 404 mid-poll.
    nac_consent_terminal_retention_seconds: int = 300

    # --- Number Verification OIDC contract (P4a) ---
    # The V1 documentation (networkascode.nokia.io, reviewed 6 Sep 2026) returns
    # both access_token and id_token from the token endpoint, and requires the
    # nonce sent in the authorization request to be validated as an id_token
    # claim. These three are only used on the manual (non-SDK) exchange path;
    # they have no effect on network-as-code's own OIDC client, if the
    # installed SDK version handles Number Verification internally.
    nac_issuer: str | None = None
    nac_jwks_uri: str | None = None
    # Clock skew tolerated when checking the id_token's exp/iat (seconds).
    nac_id_token_leeway_seconds: int = 60

    # --- Offline fake operator (P4a, ISNAD_PROVIDER=nac_fake) ---
    # demo/fake_operator is a small separate ASGI app started on loopback; it
    # is never a network call and never billed. Local development / the
    # browser journey only — never a production posture.
    nac_fake_base_url: str = "http://127.0.0.1:8801"

    # --- One live CAMARA link inside a scripted chain (ISNAD_PROVIDER=hybrid) ---
    # Every winner found of this hackathon series demoed on a live network and
    # this demo makes no live call at all. Naming an action and a number here
    # makes exactly those links real, so the judge page shows `LIVE · Nokia NaC`
    # beside `simulator` on one signed chain. Both empty (the default) is a
    # fully scripted run: nobody spends money by setting the provider alone.
    live_evidence_actions: str = ""  # csv of Action values, e.g. "sim_swap"
    live_evidence_numbers: str = ""  # csv of E.164 numbers the live call is allowed for

    # --- Gemini AI features (only used when planner == "llm") ---
    # Gemini is listed in the organiser's Resource & Tooling Guide as a runtime
    # model provider. This key also gates the display-only Ask-the-agent route;
    # it must never be present in source or a browser page.
    gemini_api_key: str | None = None
    # Measured 31 Aug against a live key: `gemini-2.5-flash` returns 404 "no
    # longer available to new users" and the API names this as its replacement.
    llm_model: str = "gemini-3.6-flash"
    # A hard ceiling per investigation. Without it one request can burn unbounded
    # model budget; past it the agent finishes on the greedy planner.
    llm_max_calls_per_investigation: int = 6
    # Short: a planner call sits in the request path, and on stage a slow verdict
    # is worse than a greedy one. A timeout is just another fallback.
    #
    # 6.0 is measured, not guessed (31 Aug, 15 sequential live calls): a call
    # that succeeds returns in 1.9-3.5s, median 2.4s. What the measurement also
    # found is that only 4 of 15 succeeded — the rest were read timeouts and
    # 429s from provider congestion under exactly the bursty sequential pattern
    # an investigation produces. So the timeout is set to fail FAST and hand
    # over to greedy, because dead air is the one failure the audience sees.
    llm_timeout_seconds: float = 6.0

    # --- Rate limiting (S12) ---
    # No limiting existed anywhere, and /v1/verify spends money per call on the
    # nac path. Per-minute, per bucket.
    rate_limit_enabled: bool = True
    rate_limit_per_key: int = 60  # authenticated, billable routes
    rate_limit_per_ip: int = 120  # anything reachable without a key
    # Tier 1 screening gets its own, higher bucket. 60/min is a SPEND guard —
    # /v1/verify costs real money per call on the nac path — and /v1/screen
    # spends nothing: no network call, no provider, purely local state. Sharing
    # the bucket throttled the cheap path to protect a budget it never touches,
    # and a caller-velocity burst (which is ordinary traffic for this endpoint)
    # exhausted it in seconds. Still bounded: each screen writes a row.
    rate_limit_per_key_screen: int = 600

    # --- CHALLENGE followups (P3) ---
    # How long a merchant has to report a followup before it expires unreported.
    # The spec's own proposed default.
    challenge_attempt_ttl_seconds: int = Field(900, gt=0)
    # How long a resolved (PASSED/FAILED/ABANDONED/EXPIRED) attempt and its
    # events stay queryable before the retention sweeper drops them. 30 days.
    challenge_followup_retention_seconds: int = Field(2592000, gt=0)

    # --- Merchant outcome reporting (P5) ---
    # How far into the future a merchant-supplied occurred_at may sit before
    # it is rejected — clock skew tolerance, not a business rule.
    outcome_future_tolerance_seconds: int = Field(300, ge=0)
    # How long an outcome event (current or already superseded) stays queryable
    # before the retention sweeper drops it. 180 days: long enough to cover a
    # calibration observation window, unlike P3's 30-day followup window.
    outcome_retention_seconds: int = Field(15552000, gt=0)

    # --- Expiring reviewer links (I13) ---
    proof_share_default_ttl_seconds: int = Field(259200, gt=0)  # 3 days
    proof_share_max_ttl_seconds: int = Field(2592000, gt=0)  # 30 days

    # --- Cache / idempotency ---
    cache_backend: str = "memory"  # memory | redis
    redis_url: str | None = None
    idempotency_ttl_seconds: int = 86400

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.merchant_api_keys.split(",") if k.strip()}


# The demo key that used to be the default. Named here so the startup guard can
# refuse it: it appeared in the console source, in .env.example and in the
# README, so it must be treated as public knowledge, not as a credential.
PUBLISHED_DEMO_KEY = "demo-merchant-key"


class InsecureConfiguration(RuntimeError):
    """Raised at startup for a configuration that cannot be safely exposed."""


def makes_billable_calls(cfg: Settings) -> bool:
    """Can a request cause a real, paid CAMARA call to leave this process?

    Keyed on behaviour rather than on one provider name, because keying on the
    name is exactly how `hybrid` slipped past this guard: it was added as a
    third provider that reaches the network for named actions, and every money
    check here still asked `== "nac"`. The hybrid condition mirrors
    `HybridProvider._is_live` — either list empty and nothing can go live — so
    the two cannot drift apart.
    """
    if cfg.provider == "nac":
        return True
    if cfg.provider == "hybrid":
        return bool(cfg.live_evidence_actions.strip() and cfg.live_evidence_numbers.strip())
    return False


def check_startup_posture(cfg: Settings) -> None:
    """Refuse to start a billable deployment with no key or a published one.

    Only enforced where a call can actually reach the network. Under the mock
    provider an open instance costs nothing and leaks nothing real, and the
    local demo has to stay frictionless; where calls are billable the same
    misconfiguration is a stranger spending money on real CAMARA calls — and
    that is not hypothetical the moment the demo is exposed through a tunnel.
    """
    # Hybrid deliberately mixes live and fixture evidence.  That is useful for
    # an isolated stage rehearsal, but issuing a production verdict from a
    # fixture fallback is unsafe.  A deployment must choose mock (no live
    # evidence) or nac (live evidence that degrades to unresolved on failure).
    if cfg.provider == "hybrid" and not cfg.demo_mode:
        raise InsecureConfiguration(
            "ISNAD_PROVIDER=hybrid is demo-only. Production must use "
            "ISNAD_PROVIDER=nac so provider failures cannot become mock evidence."
        )

    if not makes_billable_calls(cfg):
        return
    if cfg.demo_mode:
        raise InsecureConfiguration(
            f"ISNAD_DEMO_MODE=true while ISNAD_PROVIDER={cfg.provider} makes "
            "billable calls. Public demo tokens would authorize live requests; "
            "disable demo mode before starting."
        )
    keys = cfg.api_keys
    if not keys:
        raise InsecureConfiguration(
            f"ISNAD_MERCHANT_API_KEYS is empty while ISNAD_PROVIDER={cfg.provider} "
            "makes billable calls: every "
            "authenticated route would be unreachable and no key is configured "
            "to reach it. Set a generated key before starting."
        )
    if PUBLISHED_DEMO_KEY in keys:
        raise InsecureConfiguration(
            f"ISNAD_MERCHANT_API_KEYS contains the published demo key "
            f"'{PUBLISHED_DEMO_KEY}' while ISNAD_PROVIDER={cfg.provider} makes "
            f"billable calls. That value is in "
            f"the README and in .env.example; it is public. Generate a real key: "
            f"python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if not cfg.nac_api_key:
        raise InsecureConfiguration(
            f"ISNAD_NAC_API_KEY is empty while ISNAD_PROVIDER={cfg.provider} "
            "makes billable calls. Refuse startup rather than reporting healthy "
            "and failing the first verification request."
        )
    from app.chain.vault import resolve_key_path

    key_path = resolve_key_path(cfg.vault_key_path)
    if key_path is None or not key_path.exists():
        raise InsecureConfiguration(
            f"No vault signing key at {key_path} while ISNAD_PROVIDER={cfg.provider} "
            f"makes billable calls. "
            f"Starting would generate a fresh one and every chain issued before "
            f"this restart would report invalid (S6). Mount the volume holding "
            f"it, and set ISNAD_VAULT_KEY_PATH to an absolute path on it."
        )
    if not cfg.subject_pepper:
        raise InsecureConfiguration(
            "ISNAD_SUBJECT_PEPPER is unset while ISNAD_PROVIDER=nac. Signed "
            "chains bind to an HMAC of the subject under this pepper (S5); "
            "deriving it from the vault key is a local-demo convenience, and a "
            "real deployment must persist it explicitly or every chain issued "
            "before a key rotation stops matching its subject."
        )
    parsed_redirect = urlparse(cfg.nac_redirect_uri)
    if parsed_redirect.scheme != "https" or not parsed_redirect.hostname:
        raise InsecureConfiguration(
            f"ISNAD_NAC_REDIRECT_URI must be an absolute HTTPS callback while "
            f"ISNAD_PROVIDER={cfg.provider}; got {cfg.nac_redirect_uri!r}. "
            "Register that public HTTPS callback with the NaC application."
        )


settings = Settings()
