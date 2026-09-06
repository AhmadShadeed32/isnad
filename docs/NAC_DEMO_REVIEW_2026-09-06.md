# Nokia API additions and demo call plan

Reviewed 6 September 2026. App implementation is paused at the user's request
while API selection and demo testing are reviewed. This is a recommendation and
runbook, not a claim that new capabilities are implemented.

## Recommended additions

| Priority | Capability | Proposed Isnad behavior | Evidence and limits |
| --- | --- | --- | --- |
| First | SIM and Device Swap dates | Put the provider-reported change time, observation time and age beside each check; distinguish a recent change from an old one. | [SIM](https://networkascode.nokia.io/_docs/sim-swap/sim-swap), [Device](https://networkascode.nokia.io/_docs/device-swap/device-swap). Both SDK date methods exist. Dates can mean activation/first association; null is not proof of no fraud. Preserve Device Swap monitoring horizon. |
| First | Number Recycling | Before relying on an established customer's saved phone number, check whether the subscriber changed since the merchant last verified ownership. Ask for fresh verification when ownership continuity fails. | [Nokia overview](https://networkascode.nokia.io/_docs/number-recycling/index-number-recycling). SDK `number_recycling.check` exists. Requires a genuine stored reference date; out-of-range is unknown, not a false result. No live capture yet. |
| First, separate from risk | Congestion Insights | Show network condition, forecast interval and confidence; offer bounded retry guidance for interrupted verification. Preserve checkout state. | [Notifications](https://networkascode.nokia.io/_docs/network-insights/congestion-notifications), [subscription prerequisite](https://networkascode.nokia.io/_docs/network-insights/get-congestion). Requires subscription lifecycle and a reachable callback. Never lower verification requirements or add fraud weight because of congestion. No observed simulator result yet. |
| Next | SIM Swap subscriptions | Replace the demo-only simulated post-checkout event with an authenticated network event that revokes a short trust session. | Authenticated catalog lists v0.3.0. No `sim_swap_subscriptions` resource on installed SDK 10.0.0. Contract/entitlement and REST or SDK upgrade path must be verified first. |
| Next | Consent Info | Show which requested checks are permitted and send the user to operator consent when required. | [Nokia overview](https://networkascode.nokia.io/_docs/consent-info/index-consent-info). SDK `consent_info.retrieve` exists. It checks status and may return an operator capture URL; it does not itself grant consent. |
| Optional | Call Forwarding Signal | For voice-dependent recovery, flag unconditional forwarding and choose another merchant verification route. | [Nokia CFS](https://networkascode.nokia.io/_docs/call-forwarding-signal/call-forwarding-signal). SDK supports active-services and unconditional checks. Forwarding can be legitimate and is not proof of fraud; do not describe it as SMS forwarding. |
| Optional | KYC Tenure | Corroborate continuity for a returning subscriber when the scenario needs it. | [Nokia tenure](https://networkascode.nokia.io/_docs/know-your-customer/kyc-tenure). SDK `kyc.check_tenure` exists. Continuous operator tenure is not merchant history or proof of identity. Do not penalize new/prepaid users solely on tenure. |

Defer KYC Fill-in/Match/Age, precise location retrieval/geofencing, QoD and network
slicing for this checkout demo. They add inputs, permissions or infrastructure
without a clear additional demonstration of Isnad's central trust decision.
This prioritization is an engineering recommendation, not an operator claim.

## What was actually verified

- Signed-in portal account banner: **Simulator mode**. No new subscription was
  created, no Run button was used, and no operator API call was made in this review.
- Installed SDK: `network-as-code==10.0.0`.
- Five locally intercepted SDK HTTP requests: SIM date, device date, congestion
  create, congestion query, congestion delete. All serialized the expected JSON
  keys and parsed authored responses. **Zero external requests**. This validates
  SDK serialization only, not account entitlement or service availability.
- Historical repository captures cover existing signals (see
  `app/nac_capabilities.json`); those captures are not today's readiness check.

### Contract corrections to implement before demo calls

Authenticated [catalog](https://networkascode.nokia.io/network-as-code-network-as-code-default/api/network-as-code)
inspection and local SDK request interception agree on these paths:

| Operation | Path | Response fields |
| --- | --- | --- |
| SIM date | `/passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date` | `latestSimChange`: required nullable timezone-aware date-time in catalog |
| Device date | `/passthrough/camara/v1/device-swap/device-swap/v1/retrieve-date` | `latestDeviceChange`: required nullable timezone-aware date-time; optional `monitoredPeriod`, days |
| Congestion create | `/congestion-insights/v0/subscriptions` | SDK `subscription_id`, `started_at`, `expires_at`, `subscription_expire_time` |
| Congestion query | `/congestion-insights/v0/query` | List of intervals with `timeIntervalStart`, `timeIntervalStop`, `congestionLevel` Low/Medium/High, optional nullable `confidenceLevel` 0–100 |
| Congestion delete | `/congestion-insights/v0/subscriptions/{id}` | No response body expected |

Catalog generated host is `https://network-as-code.p-eu.apihub.nokia.io`;
SDK default is `https://network-as-code.p-eu.rapidapi.com`. The SDK accepts
`base_url`, so use the catalog host explicitly in the first isolated probe and
record it. Do not change production defaults until the response is observed.
Both use the documented `x-rapidapi-host: network-as-code.nokia.rapidapi.com`.
The v1.0.0 group label does not mean every path contains v1.

The catalog congestion **query example is wrong for its schema**: it contains
webhook and expiry fields. Query requires `device`, optionally `start` and `end`.
Omitting both means the upcoming 15-minute forecast. Supplying a start or end
alone implies a 15-minute interval on the other side. Record forecast/history
explicitly. Do not treat example empty timestamps as real measurements.

The subscription example uses a non-simulator phone and a 2045 expiry: replace
both before running it. Use a documented `+9999` identifier and a short UTC expiry.
The public tutorial uses `resource_id`/`starts_at` in places; installed response
fields are `subscription_id`/`started_at`. Delete/get methods take `resource_id`
as an argument whose value should be the returned `subscription_id`.

## How to test the calls

Use three clearly labelled evidence levels:

1. **Local fixtures:** regression cases, timeouts, duplicate/reordered callbacks,
   unknown dates, malformed timestamps and deterministic judge story. No external calls.
2. **Nokia hosted simulator:** actual authenticated HTTP requests using Nokia's
   documented simulated identifiers. Proves the hosted integration; not real radio data.
3. **Real handset/operator:** separate trial after onboarding and per-API access.
   For Number Verification, complete the operator/device OAuth flow on the handset;
   a desktop request with a phone number alone does not demonstrate silent verification.
   [Number Verification V1](https://networkascode.nokia.io/_docs/number-verification/number-verification-v1)

Nokia routes phone numbers with the `+9999` prefix to simulation. Use each API's
published scenario table for predictable results; arbitrary suffixes do not have
guaranteed outcomes. Live-network onboarding includes billing/plan and provider
registration. [Getting started](https://networkascode.nokia.io/_docs/getting-started)

### First bounded simulator matrix

| Test | Device/input | Documented expectation / acceptance |
| --- | --- | --- |
| SIM check | `+99999991000`, then `+99999991001`; fixed 24-hour window | Swapped, then not swapped; record actual result. [SIM table](https://networkascode.nokia.io/_docs/sim-swap/sim-swap) |
| Device check | Same two numbers/window | Swapped, then not swapped. [Device table](https://networkascode.nokia.io/_docs/device-swap/device-swap) |
| SIM date, device date | Each operation once on `+99999991000` | Parse nullable timestamp; preserve timezone and device monitoring days. Do not assert a particular example date or consistency with check until observed. |
| Optional forwarding check | `+99999991000`, then `+99999991001` | Unconditional forwarding active, then inactive. [CFS table](https://networkascode.nokia.io/_docs/call-forwarding-signal/call-forwarding-signal) |
| Number Verification | `+99999991000`, then `+99999991001`, with its auth flow | Verified, then not verified. Consent/error paths tested separately. [NV table](https://networkascode.nokia.io/_docs/number-verification/number-verification-v1) |
| Error handling | CFS `+99999990422`, `+99999990503` | Documented 422/503; present unavailable evidence, no invented PASS. The error-number mapping is API-specific. |
| Congestion lifecycle | One `+9999` test device, callback on our controlled HTTPS endpoint | Create → get returned ID → forecast query → historical query → delete → get confirms deletion. Six outbound calls, no repeated polling. Callback delivery is an additional observed event, not guaranteed by create success. |

Start with the **six swap calls** (four booleans, two dates). Inspect every response
before expanding the matrix. For every SDK operation set
`request_options={"timeout_in_seconds": 10, "max_retries": 0}`. Do not repeat
an uncertain subscription creation blindly; reconcile by returned ID/list first.
A subscription may still need cleanup if a later read/query fails.

The existing `scripts/t1_probe.py` is a useful reference but not yet the recommended
runner for this expanded plan: it supports only four operations, does not set
per-call retry limits, and records raw exception/body text. Prepare a dedicated
simulator-only runner with these contracts before a batch. It should reject
non-`+9999` numbers, limit operations/call count, omit keys and callback tokens,
store only allowlisted response fields, and record HTTP status plus error code
without raw response headers or tracebacks. This tooling is **planned**, not added.

For a first manual call now: open the relevant endpoint in the signed-in Nokia
playground, select the demo app, open Body, substitute the documented simulator
number and window, then click Run once. Inspect **Results**, not Example Responses.
Record endpoint/version, UTC time, status, latency and sanitized result. The
playground's App/Code Snippets tabs display the API key; use our own sanitized
result view for the eventual demo recording.

### Congestion callback acceptance

Use a callback owned by this project with a random bearer token and a short
subscription expiry (propose 15 minutes; verify service accepts it). Validate
schema, authentication and subscription ownership. Record event ID/time, reject
stale updates, ignore duplicates, and confirm a replay does not repeat an action.
Local tests cover Low/Medium/High and unknown confidence; the hosted simulator
must be observed before promising controllable congestion states. A successful
query is not proof that an unsolicited notification was delivered.

### Important story limitation

The documented `...1000` returns both SIM and device swaps; `...1001` returns
neither. Neither documents our authored **new SIM, same handset** case. Do not
query one phone for SIM and another for device and present them as one customer.
Keep that case labelled local fixture, or obtain a supported simulator scenario
from Nokia. Neither individual boolean dictates Isnad's final decision.

## Proposed five-minute demo

1. Show a Nokia simulator result with provenance, then Gemini's recorded evidence
   choice and policy-constrained decision.
2. Display retrieved swap dates and uncertainty beside the signed receipt.
3. Replay the clearly labelled new-SIM/same-handset fixture to explain why Isnad
   corroborates evidence instead of declining every SIM replacement.
4. Show congestion separately, with its interval/confidence and a retry path that
   preserves the pending order and verification requirements.
5. Show one unavailable-provider case and verify the resulting receipt. For a
   Gemini response show Gemini; only an absent answer permits greedy fallback.

Next gate: implement the bounded simulator runner, observe the first six calls,
record any host/contract differences, then resume the app work. New API additions
above remain proposals until their contract, tests and useful UI behavior exist.
