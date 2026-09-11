# Nokia documentation review and instructions for the implementing agent

Reviewed **9 September 2026**. This is research and an implementation
checklist, not a claim that these changes or new live calls have been completed.
For what was actually built and observed, read [the README](../README.md),
[the parity report](NAC_MOCK_PARITY.md) and
[the release validation record](RELEASE_VALIDATION_2026-09-09.md). The numbered
implementation guide this checklist was written against is a working document
and is kept outside `docs/` with the project's other internal notes.

## Coverage and limits

The review followed every public documentation family and its expanded sidebar
children: **50 distinct content pages**, listed below. This includes onboarding,
billing, registration, general concepts, every API tutorial family, consent,
Number Verification V1/V2, and notification/lifecycle pages. The `/_docs` index
redirected to Getting Started and is not counted again. The supplied
`/docs/getting-started` address also has a readable `/_docs/getting-started` form.

This is a review of the public documentation tree and its examples, not a claim
to have downloaded every authenticated API schema, executed every language
example, reviewed all SDK source, or read every external reference and attachment.
The catalog schemas for operations the agent exposes must still be pinned and
compared with installed SDK serialization in Step 2. Public prose alone does not
establish account entitlement or production availability. Recheck the inventory
at implementation time and add newly published pages.

Disposition below means: **Core** affects the required judge flow; **Audit**
applies to an existing adapter or separately exposed feature; **Later** was read
but does not justify adding unrelated capabilities to this fraud demonstration.
An Audit operation can enter the paired selector only after its own contract,
preconditions, local parity, and hosted validation are established.

## Complete public-page inventory

Each link is the source for the adjacent finding. Instructions are tailored to
Isnad; they are not additional Nokia platform requirements.

| # | Page read | Disposition and action for Isnad |
| --- | --- | --- |
| 1 | [Getting Started](https://networkascode.nokia.io/_docs/getting-started) | Core: use application credentials, supported simulator identifiers, and the repository's locked Python runtime. Distinguish client setup from a request. |
| 2 | [MCP Server](https://networkascode.nokia.io/_docs/mcp-server) | Later: Nokia describes an internal development/test tool. Keep customer-facing agent actions behind Isnad's bounded adapter; do not expose arbitrary NaC tools to judges. |
| 3 | [Billing overview](https://networkascode.nokia.io/_docs/billing/index) | Core setup knowledge: distinguish simulator setup from live-network commercial onboarding. |
| 4 | [Billing account](https://networkascode.nokia.io/_docs/billing/account) | Later production prerequisite: identify the organization administrator and required account setup in a runbook. |
| 5 | [Price plans](https://networkascode.nokia.io/_docs/billing/price-plans) | Core accounting: verify the selected account's allowance separately from Isnad's internal cost units. Do not invent a monetary bill from model costs. |
| 6 | [Application registration](https://networkascode.nokia.io/_docs/application-registration/index) | Later production prerequisite: catalog visibility and SDK availability are not completed operator onboarding. |
| 7 | [Business profile](https://networkascode.nokia.io/_docs/application-registration/business-profile) | Later: prepare required organization information; identify missing owner-supplied facts without fabricating a legal entity. |
| 8 | [Application profile](https://networkascode.nokia.io/_docs/application-registration/application-profile) | Audit: record intended APIs, countries, use case, processing purpose, consent approach, and data storage/processing locations separately. |
| 9 | [Architecture](https://networkascode.nokia.io/_docs/general-concepts/index-arch) | Core: document the boundary between Isnad, Nokia's platform, and the network operator. |
| 10 | [Diagram terms](https://networkascode.nokia.io/_docs/general-concepts/diagram-terms) | Core: distinguish application, authorization server, and operator responsibilities in consent diagrams. |
| 11 | [Identifying devices](https://networkascode.nokia.io/_docs/general-concepts/identifying-devices) | Core: validate identifiers per operation. Do not accept every identifier type on a phone-only endpoint. Preserve the subject throughout a run. |
| 12 | [Consent and identity management](https://networkascode.nokia.io/_docs/general-concepts/consent-identity-mgmt) | Core/Audit: scope, purpose, device, and authorization belong together. Registration purpose must match runtime use; authorization-list resubmission replaces the previous list. |
| 13 | [Network as Code client](https://networkascode.nokia.io/_docs/general-concepts/network-as-code-client) | Core: initialize the actual runtime SDK through an injectable client factory, with credentials confined to the server. |
| 14 | [Notification URL](https://networkascode.nokia.io/_docs/general-concepts/notification-url) | Audit: receiving notifications requires a reachable endpoint and verified sender credentials. A successful subscription create does not prove callback delivery. |
| 15 | [Error handling](https://networkascode.nokia.io/_docs/general-concepts/error-handling) | Core: preserve typed failures and HTTP status; invalid input, authorization failure, missing data, and upstream failure must not become a clean result. |
| 16 | [Proxy support](https://networkascode.nokia.io/_docs/general-concepts/proxy) | Core: test mock isolation with proxy environment variables present. No SDK helper or proxy may escape the local mock transport. |
| 17 | [SIM Swap](https://networkascode.nokia.io/_docs/sim-swap/sim-swap) | Core: check-window units are hours; boolean check and date retrieval are separate operations. Pin simulator cases and nullable date semantics. |
| 18 | [Device Swap](https://networkascode.nokia.io/_docs/device-swap/device-swap) | Core: preserve first-association and missing-data semantics; do not infer a boolean from a separate, potentially inconsistent date observation. |
| 19 | [Number Recycling overview](https://networkascode.nokia.io/_docs/number-recycling/index-number-recycling) | Audit: checks subscriber continuity since a supplied date; it is not SIM Swap or proof of merchant account ownership. |
| 20 | [Number Recycling usage](https://networkascode.nokia.io/_docs/number-recycling/number-recycling) | Audit: distinguish two-legged phone input from three-legged token subject; require the genuine merchant-held reference date. |
| 21 | [Number Recycling HTTP responses](https://networkascode.nokia.io/_docs/number-recycling/http-responses-number-recycling) | Audit: test out-of-range dates and missing/unnecessary identifiers as errors, separately from true/false continuity results. |
| 22 | [Consent Info overview](https://networkascode.nokia.io/_docs/consent-info/index-consent-info) | Audit: data-processing validity is an authorization state, not a fraud verdict. |
| 23 | [Consent Info usage](https://networkascode.nokia.io/_docs/consent-info/consent-info) | Audit: fixtures must depend on phone, requested scopes, purpose, and capture request; a returned capture URL does not grant consent. |
| 24 | [Consent Info HTTP responses](https://networkascode.nokia.io/_docs/consent-info/http-responses-consent-info) | Audit: distinguish disallowed scope/purpose from capture-frequency errors; do not retry automatically or manufacture valid consent. |
| 25 | [Number Verification overview](https://networkascode.nokia.io/_docs/number-verification/index-number-verification) | Audit: choose the supported flow explicitly; a phone number and server API key alone are insufficient proof. |
| 26 | [Number Verification V1](https://networkascode.nokia.io/_docs/number-verification/number-verification-v1) | Audit: the ordinary network-authentication flow needs the user's cellular connection. Standard code exchange and fast flow have different backend inputs. |
| 27 | [Number Verification V2](https://networkascode.nokia.io/_docs/number-verification/number-verification-v2) | Later: Android/TS.43/OpenID4VP credential flow has device/SIM prerequisites and can work over Wi-Fi. It is not a drop-in desktop bypass. |
| 28 | [Number Verification HTTP responses](https://networkascode.nokia.io/_docs/number-verification/http-responses-number-verif) | Audit: pin the versioned operation and response; do not confuse product labels with URL versions or share-token/verify schemas. |
| 29 | [Call Forwarding Signal](https://networkascode.nokia.io/_docs/call-forwarding-signal/call-forwarding-signal) | Audit: active forwarding types and unconditional forwarding's `active` boolean are distinct contracts. Voice forwarding does not establish SMS interception. |
| 30 | [KYC Match](https://networkascode.nokia.io/_docs/know-your-customer/kyc-match) | Later: unknown/unavailable matching fields are distinct from false; optional scores are not automatically zero. Minimize identity inputs. |
| 31 | [KYC Age Verification](https://networkascode.nokia.io/_docs/know-your-customer/kyc-age-verification) | Later: age threshold and optional verification/parental-control fields need separate semantics; they do not improve the initial swap demonstration. |
| 32 | [KYC Tenure](https://networkascode.nokia.io/_docs/know-your-customer/kyc-tenure) | Audit: a tenure-date check is not a returned account-creation date. Optional contract type must remain unknown when absent. |
| 33 | [KYC Fill-in](https://networkascode.nokia.io/_docs/know-your-customer/kyc-fill-in) | Later: only authorized/available identity fields are returned. Do not expand the demo into collecting unnecessary personal data. |
| 34 | [Location Verification](https://networkascode.nokia.io/_docs/location-verification/location-verification) | Audit: handle TRUE/FALSE/PARTIAL/UNKNOWN, freshness in seconds, and the actual circle geometry; unknown or stale results are not a match. |
| 35 | [Location Retrieval](https://networkascode.nokia.io/_docs/location-retrieval/location-retrieval) | Later: approximate network area, timestamp, and radius are not precise GPS or a continuous location stream. |
| 36 | [Roaming status](https://networkascode.nokia.io/_docs/status/device-roaming-status) | Audit: roaming may be national or international. Preserve optional freshness and distinguish country-code/list fields. Subscription contracts are separate from retrieval. |
| 37 | [Reachability status](https://networkascode.nokia.io/_docs/status/device-reachability-status) | Audit: DATA and SMS reachability differ; absent freshness remains unknown. A disconnected phone alone does not establish fraud. |
| 38 | [QoD overview](https://networkascode.nokia.io/_docs/quality-on-demand/index-qod) | Later: prioritized connectivity is a different use case from a fraud evidence lookup. |
| 39 | [QoD sessions](https://networkascode.nokia.io/_docs/quality-on-demand/qod-sessions) | Later: profiles, duration, extension, ports, and deletion form a resource lifecycle. Do not create a session merely to prove NaC connectivity. |
| 40 | [QoD notifications and lifecycle](https://networkascode.nokia.io/_docs/quality-on-demand/qod-notifications-and-life-cycle) | Later: REQUESTED is not AVAILABLE; termination reasons and nullable status information need faithful events if implemented. |
| 41 | [Geofencing](https://networkascode.nokia.io/_docs/geofencing/geofencing) | Later: coarse area entry/exit notifications require subscription ownership, expiry, authentication, and cleanup; they are not SMS/DATA status. |
| 42 | [Specialized Networks overview](https://networkascode.nokia.io/_docs/slicing/index-slc) | Later: operator identifiers and slice configuration are separate from subscriber fraud checks. |
| 43 | [Slice management](https://networkascode.nokia.io/_docs/slicing/slicing) | Later: create, activate, deactivate, and delete are stateful operations. If ever implemented, bound polling and resource duration. |
| 44 | [Slice attachments](https://networkascode.nokia.io/_docs/slicing/attach-detach) | Later: device/application attachment needs additional identifiers and authorization. Keep resource IDs distinct from phone numbers and slice names. |
| 45 | [Slice notifications and lifecycle](https://networkascode.nokia.io/_docs/slicing/slice-notifications-and-life-cycle) | Later: AVAILABLE and OPERATING differ; the notification example and handler disagree about state fields. Resolve against the versioned contract. |
| 46 | [Congestion Insights overview](https://networkascode.nokia.io/_docs/network-insights/index-insights) | Audit: network-performance analytics can inform delivery timing; they do not prove fraud or identity. |
| 47 | [Congestion notifications](https://networkascode.nokia.io/_docs/network-insights/congestion-notifications) | Audit: create a bounded subscription with an authenticated callback; pin SDK identifier/timestamp attributes before lifecycle calls. |
| 48 | [Congestion polling](https://networkascode.nokia.io/_docs/network-insights/congestion-levels) | Audit: a live subscription is a prerequisite. Preserve intervals and prediction confidence; no results means unknown, not low congestion. |
| 49 | [Getting Congestion subscriptions](https://networkascode.nokia.io/_docs/network-insights/get-congestion) | Audit: reconcile an uncertain creation through owned subscription lookup, not repeated creation. An empty collection is not a received metric. |
| 50 | [Congestion notification details](https://networkascode.nokia.io/_docs/network-insights/congestion-schema) | Audit: validate the CloudEvent and nested interval/level/confidence fields; the tutorial handler's single `level` field is insufficient. |

## Required actions from the full review

### A. Complete the shared mock and live application path first

1. Complete the implementation guide's baseline/setup and request-scoped judge
   selector. Use the two documented swap-check operations as the first vertical
   slice. Live HTTP to Nokia's hosted simulator is required integration evidence;
   it is distinct from local fixtures and from production subscriber evidence.
2. Build the fixture manifest independently from Isnad's output. Store source URL,
   source/version date, operation, request/response schema, scenario, and coverage
   status. The mock supplies Nokia-shaped HTTP responses; it never chooses
   Isnad's verdict. Test both normal and error handling through the shared SDK.
3. Make fixtures operation-specific. The same `...1000` number means swapped in
   the swap tables, SMS-only in reachability, and outside the requested area in
   Location Verification. It is not a universal "fraudulent subscriber" flag.
   Those mappings come from the corresponding operation pages above.
4. Preserve the input subscriber. Reject unsupported real-mode scenarios before
   spending a call; never replace the supplied subject with a known-working test
   number. Compare matched runs with identical request inputs and planner paths.
5. Add negative tests for missing booleans, malformed JSON, unknown enum values,
   transport failure, expired access, timeout, and non-success status. Authored
   fault cases must be labelled as tests, not historical Nokia observations.
6. Rehearse the actual `/judge` → authenticated Isnad endpoint → Nokia SDK → Nokia
   response → normalized evidence → signed receipt path. A separate probe is a
   useful diagnostic, but does not close this application's live-call requirement.

### B. Audit the existing consent and identity integrations

Inspect `app/consent.py`, `app/api/routes_consent.py`, `app/providers/nac.py`,
`app/config.py`, and their existing tests. Apply fixes for any already enabled
path; record a deferred feature explicitly instead of expanding the initial
two-check judge flow.

1. Keep authorization status separate from fraud evidence. Associate allowed
   scopes and purpose with the correct application and subject. The general
   consent documentation describes both transparent CIBA and interactive code
   flows; a longer consent wait must not become an unbounded demo timeout.
2. For **Consent Info**, preserve each scope's validity/reason/optional expiry
   and the optional top-level capture URL. Model PENDING, REQUESTED, REVOKED,
   EXPIRED, and OBJECTED separately. A capture redirect requires a subsequent
   validity check. Treat returned URLs as untrusted input: validate permitted
   destinations, do not fetch arbitrary URLs server-side, and do not place raw
   URLs or tokens in planner prompts or public traces.
3. For **Number Recycling**, two-legged requests carry the phone number; the
   three-legged flow uses the token's subject and omits that field. Validate the
   real merchant reference date and flow-specific inputs before any call. A
   successful `true` can describe lack of a continuous contract since that date;
   an invalid date is an error. Never invent a last-verification date.
4. For **Number Verification V1**, preserve the existing state/nonce/ownership
   protections. Standard code flow exchanges the code, validates the returned
   identity token as appropriate, and uses the authorized access token; fast
   flow forwards its documented code/state inputs differently. Bind one-time
   state to owner, run, redirect URI, subject, and expiry; reject replay and
   mismatch. Do not copy a tutorial's decode-only example as token validation.
5. For a later physical-device test, document supported country/operator,
   approved application, flow, device/network prerequisites, redirect setup,
   and evidence needed. V1's cellular requirement is not a universal statement
   about V2. A backend can perform the API call **after** the required device
   authorization; merely adding a backend credential does not supply it.
6. Keep **V2** a separately scoped Android integration unless Isnad actually
   gains that client. It uses an OpenID4VP/TS.43 device credential, fresh nonce,
   and the flow's backend preparation/exchange; do not reuse V1's code callback
   or claim a desktop selector completes it.

**Acceptance:** tests reject cross-run/replayed authorization, preserve absent
and denied states, and never report an unavailable identity check as successful.
The initial paired demo can disable these actions honestly; any action that
remains enabled must satisfy its own protocol.

### C. Audit callbacks and subscription features separately

For any existing congestion or future subscription surface, map its actual
routes, persistence, and tests before changing it. Read notification contracts
as well as request contracts.

1. Validate authentication before processing a callback. Check schema, event
   type, timestamps, and resource ownership; handle duplicate and out-of-order
   delivery idempotently. Unknown resource/event types must not mutate another
   run or become trusted planner evidence. Keep raw operator prose out of prompts.
2. Preserve the operation's own event envelope. Reachability, roaming, QoD, and
   geofencing use their documented CloudEvent variants; slicing's illustrated
   payload differs. Do not apply one tutorial handler indiscriminately.
3. Bound expiration, event count, create attempts, polling, and cleanup. Persist
   IDs and operation state. Reconcile uncertain creates before another create;
   preserve reservations while an upstream operation may still be running.
4. For congestion, require the subscription before polling and distinguish
   creation accepted, callback received/authenticated, metric obtained, and
   cleanup confirmed. Test empty metrics, unknown levels, missing confidence,
   stale intervals, duplicate callbacks, and failed deletion separately.
5. Supply local lifecycle fixtures if this feature is exposed in mock mode.
   Do not generate fake callbacks while labelling the feature Nokia-connected.

**Acceptance:** each exposed subscription has a demonstrated create/receive/use/
cleanup lifecycle or a precise pending state. Keep it outside the first paired
swap run and its two-attempt cap; enabling it requires a separate explicit budget.

### D. Resolve documentation disagreements before claiming parity

Use a versioned schema, actual SDK request/response types, and bounded sanitized
observations to resolve each relevant discrepancy. Record the resolution and a
regression test in `docs/NAC_MOCK_PARITY.md`; do not modify fixtures until they
agree merely to make the test pass.

| Discrepancy observed | Required resolution |
| --- | --- |
| Location Verification tutorial's circle example supplies only its type; a useful location check also needs the intended geometry. | Inspect the pinned `Area` serialization and catalog schema. Assert that Isnad's real request retains center and radius; a model accepting input does not prove those fields reach HTTP. |
| Reachability/roaming/QoD example Python handlers require fields or nesting absent from their illustrated CloudEvents. | Validate against the chosen event version; do not require an invented wrapper. Cover legitimate nullable status fields. |
| Geofencing's first event table describes DATA/SMS checks, while the notification schemas describe area entry/exit. | Use geofencing schema semantics and record the prose inconsistency; do not reinterpret geofence events as connectivity evidence. |
| Congestion examples mix `resource_id`, `subscription_id`, `starts_at`, and interval/level attributes. | Reconcile with installed SDK types and the existing wire tests. Keep JSON field names and Python attributes in separate matrix columns. |
| Slice examples mix name/ID forms and state payloads; some polling loops have no deadline. | If this deferred feature is ever added, pin method signatures, lifecycle states, payloads, and bounded cleanup before implementation. |
| Number Verification overview and HTTP examples use different product/path/version labels; V2 verification and number-sharing descriptions are not fully aligned. | Pin the exact operation and supported flow. Do not infer V2 number-sharing support from a generic response page. |
| `docs/NAC_CONTRACT_MATRIX.md` lists observed recycling/forwarding successes but later still asks whether those operations are entitled. Its Consent Info wording also needs checking against the top-level capture URL. | Reconcile the current summary against dated records and exact schema. Preserve historical observations; qualify access by account, environment, operation, and observation date. |

The relevant Nokia sources are inventory rows 23, 25–28, 34, 36–37, 40–41,
43–45, and 47–50. A tutorial discrepancy is neither permission to invent a wire
contract nor evidence that the current gateway will reject a valid one.

### E. Keep production prerequisites and unneeded APIs explicit

Add a small production-readiness table to the setup runbook: business/application
profiles, selected API plan and country/operator support, consent approach,
callback/redirect setup, and physical-device validation. Populate verified facts
or name the owner-supplied dependency. Do not claim worldwide access, guaranteed
fees, or legal compliance from simulator success.

The public consent page links an
[authorization template](https://networkascode.nokia.io/files/nokia-network-as-code-consent-authorization-template.xlsx).
This review read the accompanying instructions, not the workbook attachment.
If that B2B workflow is actually needed, inspect the current template, prepare
the complete intended authorization list, and obtain the account owner's required
input before submission: resubmitting can revoke omitted devices. Production
registration documents and consent-screen attachments likewise belong to that
specific onboarding task, not an automatic side effect of building this demo.

Keep KYC Match/Fill-in/Age, Location Retrieval, geofencing, QoD, and slicing as
documented deferrals unless an existing Isnad surface depends on them. Reading
the complete catalog should improve correctness; it does not require implementing
every API or increasing the number of paid checks.

## Handoff gate

- [ ] All 50 public pages have a disposition; new pages are added if the tree changes.
- [ ] Every exposed operation has pinned schema/SDK/scenario evidence and parity tests.
- [ ] Relevant discrepancies above are resolved or the dependent feature stays unavailable.
- [ ] Existing consent/callback paths are audited; disabled paths are labelled accurately.
- [ ] The required live call completes through Isnad and contributes to the same signed receipt.
- [ ] Mock purpose, bounded compatibility, live status, and production limitations agree in README and UI.

The numbered implementation guide these boxes were written against, and the
review of other entrants' public projects that fed into it, are working
documents rather than submission material; both are kept outside `docs/`.
