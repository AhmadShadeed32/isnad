"""Test configuration.

Two things must be pinned before `app.config` — and therefore anything that
imports it — is first imported.

`Settings` reads a developer's `.env` (``env_file=".env"``), so without this the
suite inherits whatever that file happens to say. On a machine configured for
real work that means `ISNAD_PROVIDER=nac`, and a plain `pytest` run issues live,
billable CAMARA calls: the observed cost was three failures and 127 seconds
against the network. Tests must describe the code, not the developer's box.
"""

import os

# Must be set before app.config / app.db import.
os.environ["ISNAD_DATABASE_URL"] = "sqlite://"
# Never let a local .env point the suite at a billable provider.
os.environ["ISNAD_PROVIDER"] = "mock"
# `merchant_api_keys` no longer ships a usable default (S1), so the suite states
# the key it authenticates with rather than relying on one being built in. The
# existing tests keep using this exact value; what changed is that it is now
# configuration rather than a credential shipped to every deployment.
os.environ["ISNAD_MERCHANT_API_KEYS"] = "demo-merchant-key"
# The suite covers the demo-only routes, so it opts into them explicitly.
# `demo_mode` now defaults to False (S4) for the same reason the key default
# went away: the safe resting state is off, and a test that needs a feature
# should say so rather than inherit it from a permissive default.
os.environ["ISNAD_DEMO_MODE"] = "true"
# Same reasoning as the provider pin, for the same reason it was needed: once a
# developer's .env carries ISNAD_PLANNER=llm and a real key, every test that runs
# an investigation calls a live model — slowly, and on the developer's tab. The
# T3/T4 tests inject their own fake clients explicitly, so pinning greedy here
# costs no coverage; it only removes the accidental live path.
os.environ["ISNAD_PLANNER"] = "greedy"
os.environ["ISNAD_GEMINI_API_KEY"] = ""
# Harness tests must also be independent of collection order and local credentials.
os.environ["ISNAD_MERCHANT_API_KEY"] = "test-merchant-key"
os.environ["PILOT_OPERATOR_USERNAME"] = "operator"
os.environ["PILOT_OPERATOR_PASSWORD"] = "correct-horse-battery-staple"
# The shipped demo registry is signed by a deployment-independent public key.
# CI creates a fresh vault key, so it must explicitly trust this pinned public
# key in order to verify the committed signature. This is public material, not
# a signing secret; a changed signature key is still rejected as untrusted.
os.environ["ISNAD_VAULT_TRUSTED_PUBLIC_KEYS"] = (
    "4034e169495122a893d8fe6738c2b0f54655fdfb6ec3c6d0eeb938d1330e7f9f"
)


def pytest_configure() -> None:
    """Tests prepare their ephemeral schema explicitly.

    Production schema work belongs to the application lifespan (and migrations
    for non-SQLite databases), never to importing ``app.db.store``.
    """
    from app.chain.vault import vault
    from app.config import settings
    from app.db.database import init_db

    init_db()
    vault.configure(settings.vault_key_path)
