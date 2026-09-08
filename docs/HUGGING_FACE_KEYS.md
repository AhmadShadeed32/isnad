# Server keys on Hugging Face

Open https://huggingface.co/spaces/AhmadShadeed32/isnad-trust-engine/settings
and use **Variables and secrets → New secret**. API keys belong in Secrets,
never public Variables, frontend code, Dockerfile values, or Git.

## Gemini for the public demo

Add the Secret `ISNAD_GEMINI_API_KEY` with your Google AI Studio key.
Keep `ISNAD_PROVIDER=mock` and `ISNAD_DEMO_MODE=true` as Variables.
Optionally set `ISNAD_PLANNER=llm` for API requests that do not explicitly select
another planner; the website's selector controls each interactive run.

After the Space restarts, refresh the website. It will report that a site key
is available. Select **Gemini · LLM**. Checkout, Console, and the Lab's
**Run this case with Gemini** use the server key without asking visitors for
one. A saved personal key takes precedence. Greedy mode makes no model calls.

The frontend receives only a boolean indicating server-key availability.
The backend sends the key to Google; it does not put the key in page markup,
responses, recordings, or application logs. Your quota funds public use.
Authentication, rate limits, and model quotas control who can spend that
quota; keeping a key secret alone does not restrict usage. The Lab uses fixed
synthetic cases, an IP rate limiter, and at most two concurrent model runs.

Set `ISNAD_LLM_MAX_CALLS_PER_HOUR` to a positive value to cap shared-key model
requests per rolling hour (the Space uses 120; zero disables the cap).
Every attempted Gemini HTTP call reserves a slot atomically, including calls
from cached clients and concurrent runs. Failed requests keep their slot because
they may have reached Google. A distinct visitor key uses that visitor's quota.
Once exhausted, ongoing investigations fall back to Greedy with a quota reason;
new Lab model runs report that the allowance is exhausted. The counter is
in-memory and resets on restart: keep one worker and one replica, and use provider
account limits for a durable spending boundary. This limits calls, not currency.

The Lab's recorded Greedy runs remain available without a model call. Fresh
Gemini simulations stay in the browser's current page memory, are unsigned,
and use mock network evidence. They never replace the committed recordings.

## Nokia Network-as-Code

Store the Nokia key as Secret `ISNAD_NAC_API_KEY`. Adding it alone does not
activate live calls while the provider remains `mock`.

For real Nokia calls, use an authenticated production deployment with:

| Setting | Where | Value |
| --- | --- | --- |
| `ISNAD_NAC_API_KEY` | Secret | Your Nokia key |
| `ISNAD_MERCHANT_API_KEYS` | Secret | A newly generated merchant credential, never `demo-merchant-key` |
| `ISNAD_SUBJECT_PEPPER` | Secret | A stable, random production secret |
| `ISNAD_PROVIDER` | Variable | `nac` |
| `ISNAD_DEMO_MODE` | Variable | `false` |
| `ISNAD_NAC_REDIRECT_URI` | Variable | Your registered HTTPS consent callback, ending `/v1/consents/number-verification/callback` |
| `ISNAD_VAULT_KEY_PATH` | Variable | Absolute path to an existing signing key on persistent storage |
| `ISNAD_DATABASE_URL` | Secret if it includes credentials | Your production database connection |

The current demo uses ephemeral storage. Provision durable storage and an
existing signing key before enabling NaC. The app intentionally refuses
`provider=nac` with public demo mode, a published merchant key, missing pepper,
missing signing key, or an invalid callback. Real number verification may also
require the subscriber's operator consent.

Visitors should authenticate to your application; they should never receive
your Nokia or Gemini credentials. The current public demo is not a production
merchant login application. A separate authenticated deployment is the right
place for live customer checks.

Protected Space visibility hides the Hub repository; it does not restrict
access to the public app or hide JavaScript delivered to browsers.

Reference: https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables
