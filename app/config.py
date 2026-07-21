from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Everything is overridable via environment variables prefixed with ISNAD_,
    e.g. ISNAD_PROVIDER=nac, ISNAD_MERCHANT_API_KEYS=key1,key2
    """

    model_config = SettingsConfigDict(env_prefix="ISNAD_", env_file=".env", extra="ignore")

    # "mock" runs the scripted providers (tests + stage demo);
    # "nac" talks to the real Nokia Network-as-Code sandbox.
    provider: str = "mock"

    # Demo-only routes and controls are enabled for local/stage use. Disable
    # this in any deployment reachable by untrusted clients.
    demo_mode: bool = True

    # "greedy" is deterministic and demo-safe; "llm" is the optional planner.
    planner: str = "greedy"

    # Comma-separated list of accepted merchant API keys (demo default below).
    merchant_api_keys: str = "demo-merchant-key"

    # Path to the policy / evidence-cost model.
    policy_path: Path = Path(__file__).parent / "policy" / "policy.yaml"

    # --- Trust-with-a-TTL sessions ---
    session_ttl_seconds: int = 120      # how long trust stays live
    session_poll_seconds: float = 1.5   # how often the monitor re-checks signals

    # --- Evidence vault (Ed25519 chain signing) ---
    # If set, the signing key is loaded/persisted here so signatures survive
    # restarts. If None, an ephemeral key is generated per process.
    vault_key_path: Optional[Path] = Path(".isnad/vault-key.pem")

    # --- Persistence ---
    # SQLite by default (file below); set to a postgresql+psycopg URL in prod.
    database_url: str = "sqlite:///./isnad.db"

    # --- Nokia NaC (only used when provider == "nac") ---
    nac_api_key: Optional[str] = None
    nac_rapidapi_host: str = "network-as-code.nokia.rapidapi.com"
    nac_max_age_hours: int = 240
    nac_location_max_age_seconds: int = 3600
    nac_timeout_seconds: float = 8.0
    nac_redirect_uri: str = "http://localhost:8000/v1/consents/number-verification/callback"
    nac_authorization_endpoint: Optional[str] = None
    nac_token_endpoint: Optional[str] = None
    nac_client_id: Optional[str] = None
    nac_client_secret: Optional[str] = None
    nac_number_verification_scope: str = (
        "dpv:FraudPreventionAndDetection number-verification:verify"
    )
    nac_consent_ttl_seconds: int = 300

    # --- LLM planner (only used when planner == "llm") ---
    anthropic_api_key: Optional[str] = None
    llm_model: str = "claude-sonnet-5"

    # --- Cache / idempotency ---
    cache_backend: str = "memory"       # memory | redis
    redis_url: Optional[str] = None
    idempotency_ttl_seconds: int = 86400

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.merchant_api_keys.split(",") if k.strip()}


settings = Settings()
