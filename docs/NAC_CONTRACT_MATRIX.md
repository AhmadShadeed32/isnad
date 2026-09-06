# Nokia Network as Code contract matrix

Compiled 6 September 2026 for gate 2 of `docs/EXECUTION_RUNBOOK.md`. It reconciles
three sources and says which one each claim comes from:

1. **Installed SDK** — `network-as-code==10.0.0`, exported without any network
   request by `scripts/export_nac_contracts.py` into `docs/NAC_SDK_CONTRACTS.json`
   (79 operations, `network_calls: 0`). Paths below are the SDK's own request AST.
2. **Authenticated catalog** — the signed-in Nokia catalog inspection recorded in
   `docs/NAC_DEMO_REVIEW_2026-09-06.md`.
3. **Observation** — a response this project actually received. Where the "Last
   observation" column says *none*, nothing has been received and no claim of
   working integration may be made from this row.

Executable form: `tests/test_nac_wire_contract.py` drives the real SDK through an
`httpx.MockTransport` and asserts the paths, request bodies, response attribute
names and bounded request options in this table. `tests/test_nac_contract.py`
separately pins normalization against the August simulator captures in `docs/nac/`.

## Account and transport facts

| Fact | Value | Source |
| --- | --- | --- |
| Account mode | **Simulator**. Catalog visibility and SDK availability do **not** establish live-network entitlement. | Portal banner, 2026-09-06 |
| SDK default base URL | `https://network-as-code.p-eu.rapidapi.com` | SDK `NetworkAsCodeApiEnvironment.DEFAULT` |
| Catalog-generated base URL | `https://network-as-code.p-eu.apihub.nokia.io` | Authenticated catalog |
| Which host answers | **Unobserved.** Both are documented to take the same RapidAPI headers, and five locally intercepted requests agree on paths. Host compatibility is untested; do not change the application default until a response is observed. | — |
| Authorization | `x-rapidapi-key` (from `ISNAD_NAC_API_KEY`) + `x-rapidapi-host` (`ISNAD_NAC_RAPIDAPI_HOST`, `network-as-code.nokia.rapidapi.com`), injected by the SDK client wrapper. `number_recycling.check` additionally accepts a per-call `authorization` header for a three-legged token. | SDK wire AST; asserted in `test_the_rapidapi_host_header_travels_with_the_catalog_base_url` |
| Timeout | Application calls: `ISNAD_NAC_TIMEOUT_SECONDS`, enforced by `asyncio.wait_for` around the pooled SDK call in `app/providers/nac.py`. Probe calls: `request_options={"timeout_in_seconds": 10}`. | `app/providers/nac.py`, `scripts/nac_demo_probe.py` |
| Retries | `request_options={"max_retries": 0}` on every probe call — one attempt per operation, asserted in `test_max_retries_zero_means_one_attempt_for_a_retryable_status`. The application path sets no retry and the SDK performs none by default. | — |
| Simulator routing | Numbers with the `+9999` prefix route to simulation. Arbitrary suffixes have no guaranteed outcome; use each API's published scenario table. | Nokia getting-started |

## Operations Isnad calls today

| Operation | SDK method | Method + path (relative to base URL) | Request fields | Response fields the app reads | Entitlement | Simulator scenario | Last observation | Response limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SIM swap check | `sim_swap.check` | `POST passthrough/camara/v1/sim-swap/sim-swap/v0/check` | `phoneNumber`, `maxAge` (hours) | `swapped` (required bool) | Simulator only | `+99999991000` swapped, `+99999991001` not | 2026-08-30 capture, `docs/nac/` | Boolean against the window we sent. It carries **no date**; the window is the whole answer. |
| Device swap check | `device_swap.check` | `POST passthrough/camara/v1/device-swap/device-swap/v1/check` | `phoneNumber`, `maxAge` | `swapped` | Simulator only | Same two numbers | 2026-08-30 capture | Path is **v1** while SIM swap is v0; the v1.0.0 group label is not a per-path version. |
| Reachability | `device_status.retrieve_reachability_status` | `POST device-status/device-reachability-status/v1/retrieve` | `device` | `reachable`, `connectivity[]` | Simulator only | — | 2026-08-30 capture | `connectivity` is operator prose; it never enters a planner prompt. |
| Roaming | `device_status.retrieve_roaming_status` | `POST device-status/device-roaming-status/v1/retrieve` | `device` | `roaming`, `countryName[]` | Simulator only | — | 2026-08-30 capture | Roaming is `INFO`, not a fraud signal on its own. |
| Location verify | `location.verify_v1` | `POST location-verification/v1/verify` | `device`, `area` (CIRCLE, centre, radius), `maxAge` seconds | `verification_result` (`TRUE`/`FALSE`/`PARTIAL`/other) | Simulator only | — | 2026-08-30 capture | **Precondition:** a request with no `claimed_location` makes **zero** SDK calls — `tests/test_provider_preconditions.py::test_nac_location_with_no_claim_is_unavailable_and_never_touches_the_sdk`. Unknown verdicts stay `INFO`. |
| Number verification | `number_verification.verify` / OIDC flow | `POST passthrough/camara/v1/number-verification/number-verification/v0/verify` | `phoneNumber`, three-legged token | verification result | Requires the operator/device OAuth round trip | `+99999991000` verified, `+99999991001` not | **none** — the consent round trip has not been completed against the hosted simulator | A desktop request with a phone number alone does not demonstrate silent verification. Recorded as `CONSENT_REQUIRED` until a token exists. |

## Operations added or shortlisted by the API review

| Operation | SDK method | Method + path | Request fields | Response fields | Entitlement | Simulator scenario | Last observation | Response limitations |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SIM swap date | `sim_swap.retrieve_date` | `POST passthrough/camara/v1/sim-swap/sim-swap/v0/retrieve-date` | `phoneNumber` only — **no** `maxAge` | `latestSimChange`: nullable, RFC 3339, timezone-aware | Simulator only | `+99999991000` documents a swap; the *date value* is not documented | see gate 3 record | A **second billable operation**, not a field of `check`. `null` means no date was returned — never "never swapped". The date may be an activation or first-association time, not a replacement event. |
| Device swap date | `device_swap.retrieve_date` | `POST passthrough/camara/v1/device-swap/device-swap/v1/retrieve-date` | `phoneNumber` | `latestDeviceChange` (nullable, tz-aware), `monitoredPeriod` (optional, **days**) | Simulator only | as above | see gate 3 record | Without `monitoredPeriod` a null date has no scope and must be shown as unknown-horizon, not "never". |
| Congestion create | `congestion_insights.create_subscription` | `POST congestion-insights/v0/subscriptions` | `device`, `webhook.notificationUrl` (+ auth token), `subscriptionExpireTime` | `subscriptionId`, `startedAt`, `expiresAt`, `subscriptionExpireTime` | Simulator only; needs a reachable HTTPS callback | one `+9999` device | **none** | SDK attributes are `subscription_id`/`started_at`. The public tutorial's `resource_id`/`starts_at` **do not exist** on the response. A successful create is not proof a notification was delivered. |
| Congestion get | `congestion_insights.get_subscription` | `GET congestion-insights/v0/subscriptions/{resource_id}` | `resource_id` = the returned `subscriptionId` | subscription record | Simulator only | — | **none** | `resource_id` is the argument name; its value is the returned id. |
| Congestion query | `congestion_insights.query` | `POST congestion-insights/v0/query` | `device`, optional `start`, optional `end` | list of `timeIntervalStart`, `timeIntervalStop`, `congestionLevel`, nullable `confidenceLevel` | Requires an existing subscription | — | **none** | The catalog's query **example is wrong for its schema** (it carries webhook/expiry fields). Both bounds omitted = upcoming 15-minute forecast; one bound = a 15-minute interval on the other side. An empty list is unknown, **not** Low. Missing confidence stays null, never 0 or 100. The SDK does **not** constrain the level vocabulary — an unexpected string reaches the caller verbatim. |
| Congestion delete | `congestion_insights.delete_subscription` | `DELETE congestion-insights/v0/subscriptions/{resource_id}` | `resource_id` | no body | Simulator only | — | **none** | Must be idempotent on our side; a leaked subscription outlives the demo. |
| Number recycling | `number_recycling.check` | `POST passthrough/camara/v1/number-recycling/number-recycling/v0.2/check` | `phoneNumber`, `specifiedDate` (date, **required**) | `phoneNumberRecycled` | Simulator only | — | **none** | Path is **v0.2**. `specifiedDate` must be a genuine merchant-held last-verified date, not a backend guess. Out-of-range is unknown, not "not recycled". |
| Consent info | `consent_info.retrieve` | `POST passthrough/camara/v1/consent-info/consent-info/v0.1/retrieve` | `phoneNumber`, `scopes[]`, `purpose`, `requestCaptureUrl` | `statusInfo[]` with per-scope status and optional capture URL | Simulator only | — | **none** | Path is **v0.1**. It reports status and may return an operator capture URL; it does **not** grant consent. Consent status is never fraud evidence. |
| Call forwarding | `call_forwarding_signal.retrieve_unconditional_call_forwarding` | `POST passthrough/camara/v1/call-forwarding-signal/call-forwarding-signal/v0.3/unconditional-call-forwardings` | `phoneNumber` | forwarding state | Simulator only | `...1000` active, `...1001` inactive; `+99999990422`/`+99999990503` documented errors | **none** | Voice forwarding only. It does **not** imply SMS forwarding and is not fraud by itself. |
| KYC tenure | `kyc.check_tenure` | `POST passthrough/camara/v1/kyc-tenure/kyc-tenure/v0.1/check-tenure` | `phoneNumber`, tenure date | tenure result | Simulator only | — | **none** | Operator tenure is not merchant history and not proof of identity. |
| SIM swap subscriptions | **no SDK resource** | catalog lists v0.3.0 | — | — | **Unknown.** Catalog listing is not entitlement. | — | **none** | SDK 10.0.0 exposes only `sim_swap.check` and `sim_swap.retrieve_date` — verified against the exported operation list. Any implementation needs a narrowly scoped REST adapter or a justified, tested SDK upgrade, never a guessed method name. |

## Explicitly deferred, with reason

`kyc.fill_in` (v0.4), `kyc.match` (v0.3), `kyc.verify_age` (v0.1), `location.retrieve`
(`location-retrieval/v0/retrieve`), the `geofencing` subscription group, QoD and
network slicing. Each adds inputs, permissions or infrastructure without adding a
demonstration of Isnad's trust decision. Deferral is a recorded disposition, not an
oversight; re-open it only if the use case expands.

The `device_status` subscription families (v0.7/v0.8 reachability and roaming) and
`number_verification` v2 exist in the SDK and are not used. Isnad calls the
synchronous `retrieve` forms; adding a subscription family would need the same
callback ownership, replay and cleanup contract as congestion.

## Unknowns recorded as unknown

- Which base URL the account actually answers on.
- Whether any date operation returns a non-null value for the simulator numbers.
- Whether the account may create a congestion subscription at all, and whether a
  15-minute `subscriptionExpireTime` is accepted.
- Whether an unsolicited congestion notification is ever delivered to a callback.
- Whether number recycling, consent info, call forwarding or KYC tenure are
  entitled on this account.
- Whether the authored *new SIM, same handset* story has any supported simulator
  scenario. It does not today: `...1000` documents both swaps and `...1001`
  neither. That case stays a visibly labelled local fixture.
