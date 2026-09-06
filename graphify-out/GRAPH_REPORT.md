# Graph Report - isnad  (2026-09-06)

## Corpus Check
- 242 files · ~279,864 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3258 nodes · 7385 edges · 178 communities (143 shown, 10 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 679 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b6c35c10`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Hypothesis
- test_t6_receipt.py
- compare_missing_location_claim
- main.py
- test_llm_planner.py
- Investigator
- _written
- test_velocity.py
- test_presentation.py
- routes_console.py
- IdTokenError
- Request
- test_challenge_contract.py
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- owner_hash
- test_t4_ask_the_agent.py
- check_startup_posture
- VaultSigner
- test_t5_counterfactual.py
- GeminiClient
- velocity.py
- test_judge.py
- test_act7.py
- test_nac_provider.py
- timeline.js
- events.py
- routes_proof_shares.py
- test_outcomes_contract.py
- ConsentStore
- get_chain
- test_s2_stream_isolation.py
- VerificationRequest
- store.py
- signing.py
- test_lab_page.py
- schemas.py
- challenges.py
- rate_limit.py
- test_s12_runtime_posture.py
- test_run_replay_endpoint.py
- test_nac_capabilities.py
- SessionManager
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_proof_shares.py
- test_s10_xss_and_headers.py
- test_merchant_pilot.py
- MockProvider
- UtcDateTime
- run_case
- test_nac_contract.py
- test_review_regressions.py
- run_scenario
- Isnad · إسناد
- console.html — live agent console
- PolicyEngine
- test_audit_low.py
- test_consent_html_redirect.py
- 7. Competition feature implementation plan
- proof_shares.py
- independent_evaluation.py
- Project Brief
- test_fake_operator.py
- P4a implementation record
- init_db
- NacProvider
- Action
- test_registry.py
- Phase 2 Agent Runbook
- policy.yaml — the single tuning surface
- routes_lab.py
- outcomes.py
- emit
- test_s14_no_tracked_secrets.py
- merchant_pilot/app.py
- 11. UI review and implementation plan — 6 September 2026
- P5 implementation record
- test_s9_consent_replay.py
- P1 and P2 implementation records
- test_s7_quota_and_key_mode.py
- CURRENT_STATE.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- Choice
- database.py
- test_receipt_download.py
- Decision
- FlowRecord
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- owner_for
- evidence_pack.py
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- routes_registry.py
- What the risk score means
- routes_challenge.py
- stream_token.py
- InMemoryCache
- test_s1_console_credential.py
- retention.py
- GreedyPlanner
- test_false_decline_baseline.py
- routes_receipt.py
- test_an_announcement_cannot_outvote_a_network_contradiction
- P3 implementation record
- test_consent_contract.py
- verify_receipt.py
- routes_privacy.py
- _announce
- build_evidence_comparison.py
- test_hardening.py
- JUDGE_WALKTHROUGH.md
- test_s11_claimed_identity.py
- test_s4_demo_mode.py
- routes_outcomes.py
- 3. Recommended app work — not implemented in this documentation pass
- 6. MENA Ignite submission priorities — reviewed 6 September 2026
- 9. Sonnet code review — 6 September 2026
- .trusts
- test_outcome_report_review_metrics.py
- bound_key
- config.py
- Isnad — compact handoff
- test_i18n.py
- run_events.py
- test_hypothesis_relevance.py
- test_evidence_comparison.py
- test_independent_evaluation.py
- TraceEvent
- test_a_clean_signup_does_not_rest_on_an_orthogonal_check_alone
- .__init__
- i18n_switch
- LoginThrottle
- .__call__
- Code review and hackathon readiness — 6 September 2026
- t1_probe.py
- build_judge_lab.py
- test_pilot_polling.py
- test_s5_subject_binding.py
- FakeNumberVerificationBareToken
- _reset_limiters
- _configured_for_llm
- i18n.js

## God Nodes (most connected - your core abstractions)
1. `Action` - 156 edges
2. `VerificationRequest` - 116 edges
3. `Decision` - 102 edges
4. `MockProvider` - 94 edges
5. `Result` - 90 edges
6. `Verdict` - 69 edges
7. `RequestContext` - 67 edges
8. `Hypothesis` - 65 edges
9. `EvidenceLink` - 64 edges
10. `PolicyEngine` - 64 edges

## Surprising Connections (you probably didn't know these)
- `Demo/production parity — only the provider differs` --references--> `MockProvider`  [EXTRACTED]
  docs/02_API_Build_Plan.md → app/providers/mock.py
- `T3 — rebuild the planner so the agent actually reasons` --references--> `LLMPlanner`  [EXTRACTED]
  docs/PHASE2_AGENT_RUNBOOK.md → app/agent/planner.py
- `test_corroboration_baseline_does_not_double_count_one_change_event()` --uses--> `Decision`  [INFERRED]
  tests/test_independent_evaluation.py → app/domain/enums.py
- `test_fixed_cases_cover_the_risky_shapes_the_report_claims()` --uses--> `Decision`  [INFERRED]
  tests/test_independent_evaluation.py → app/domain/enums.py
- `test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()` --uses--> `Decision`  [INFERRED]
  tests/test_independent_evaluation.py → app/domain/enums.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pitch Video Render Pipeline (narration to encoded cut)** — docs_video_readme_video_build_pipeline, docs_video_timings_spine, docs_video_scene_scenes, docs_video_encode_pipeline, docs_video_readme_narration_anchored_timing [EXTRACTED 1.00]
- **Supply-Chain Pinning and Audit Flow (S8)** — requirements_runtime_pins, requirements_lock_runtime_closure, requirements_dev_toolchain, github_workflows_ci_verify, requirements_network_as_code_pip_defect, setup_bootstrap_venv [EXTRACTED 1.00]
- **Nokia NaC / CAMARA Evidence Capture Catalogue** — docs_nac_sim_swap_capture, docs_nac_device_swap_capture, docs_nac_location_verify_capture, docs_nac_number_verify_capture, docs_nac_reachability_capture, docs_nac_roaming_capture, docs_nac_device_intelligence_capture, docs_nac_step_up_otp_capture, docs_nac_sim_swap_normalized_envelope [INFERRED 0.95]

## Communities (178 total, 10 thin omitted)

### Community 0 - "Hypothesis"
Cohesion: 0.09
Nodes (27): Planner, Protocol, Hypothesis, _engine(), Belief cleared overall, but one check pushed toward fraud — that chain is not…, `grade` treats `adverse_delta` as "at least" — `d >= threshold` — and…, A chain with a hole in it was never fully attested, however clean the remaining…, It graded ATTESTED_PARTIAL — "the links resolved and nothing contradicted the… (+19 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (34): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+26 more)

### Community 2 - "compare_missing_location_claim"
Cohesion: 0.24
Nodes (13): compare_missing_location_claim(), Comparison, NoClaimedLocation, ValueError, I2 — one-fact counterfactual explorer. Changes exactly one input on an existing…, The base scenario has no claimed_location to remove, so there is no single-fact…, asyncio, I2 — one-fact counterfactual explorer. The only supported variant is removing… (+5 more)

### Community 3 - "main.py"
Cohesion: 0.09
Nodes (24): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+16 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.08
Nodes (45): deterministic(), _facts(), narrate(), Everything the narrator may see. Enums, numbers, booleans., The always-available narrative. No model, no key, no network., A sentence-level account of the finished chain. Falls back to the deterministic…, _engine(), FakeClient (+37 more)

### Community 5 - "Investigator"
Cohesion: 0.12
Nodes (17): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+9 more)

### Community 6 - "_written"
Cohesion: 0.10
Nodes (21): Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and…, An institution may publish a block inside a block — a branch range carved out… (+13 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.12
Nodes (39): distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., _as(), _burst(), _clean(), _engine() (+31 more)

### Community 8 - "test_presentation.py"
Cohesion: 0.08
Nodes (43): present(), Presentation, BaseModel, Project a signed Verdict into a plain-language Presentation. Pure function:…, What a first-time visitor sees. Never signed, never part of `Verdict`, safe to…, _facts_known_to_the_chain(), asyncio, parametrize (+35 more)

### Community 9 - "routes_console.py"
Cohesion: 0.07
Nodes (54): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, get_live_provider(), key_from_bearer(), Merchant API-key auth: `Authorization: Bearer <key>`., Extract a validated key from an Authorization header, or None., Resolve the configured provider as an API-level 503 when unavailable., require_api_key() (+46 more)

### Community 10 - "IdTokenError"
Cohesion: 0.09
Nodes (50): fetch_jwks(), IdTokenError, Any, AsyncClient, RuntimeError, ID-token validation shared by every OIDC-based Number Verification path (P4a).…, The id_token is missing, malformed, or fails contract validation. Deliberately…, Validate signature, iss, aud, exp/iat and nonce. Returns the claims. Fails… (+42 more)

### Community 11 - "Request"
Cohesion: 0.16
Nodes (24): _client_is_private(), create_flow(), create_flow_challenge(), get_capabilities(), open_trust_session(), post, Request, This harness has no TLS and one operator account: it must never be reachable… (+16 more)

### Community 12 - "test_challenge_contract.py"
Cohesion: 0.13
Nodes (38): _as_the_merchant(), _create(), _extra_merchant_key(), _fresh_headers(), fixture, parametrize, P3 — finish CHALLENGE without rewriting its receipt. A merchant that gets…, Not an in-memory cache (P4a's rule for /v1/verify explicitly does not apply… (+30 more)

### Community 13 - "announce.py"
Cohesion: 0.09
Nodes (34): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+26 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (17): Directory, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",…, The institution that published this number, or None. None means "not in the… (+9 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (24): asyncio, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the…, An em dash looks like a rendering defect in a live demo, not the deliberate… (+16 more)

### Community 17 - "owner_hash"
Cohesion: 0.31
Nodes (14): owner_hash(), _as_the_merchant(), _owner(), fixture, P5's offline report: denominators and unknowns must stay honest. Loaded from…, A challenge PASS is not a fraud label. Only an explicit CONFIRMED_LEGITIMATE…, _report(), _seed() (+6 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (17): The sentence a merchant reads. It has to name the links the decision actually…, chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for. (+9 more)

### Community 19 - "check_startup_posture"
Cohesion: 0.14
Nodes (23): check_startup_posture(), InsecureConfiguration, RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Refuse to start a billable deployment with no key or a published one. Only…, Settings, BaseSettings (+15 more)

### Community 20 - "VaultSigner"
Cohesion: 0.09
Nodes (30): _key_passphrase(), MissingVaultKey, Path, RuntimeError, The secret a subject binding is computed under (S5). Configured explicitly in…, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same… (+22 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.08
Nodes (28): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+20 more)

### Community 23 - "velocity.py"
Cohesion: 0.09
Nodes (24): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), _owner(), purge_older_than(), The tenant this request belongs to, set at the auth boundary (S2)., Note that this caller was screened against this callee, for this tenant. (+16 more)

### Community 24 - "test_judge.py"
Cohesion: 0.16
Nodes (13): judge_page(), get, HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that… (+5 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (27): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not… (+19 more)

### Community 26 - "test_nac_provider.py"
Cohesion: 0.12
Nodes (26): _ClientWithNoNumberVerificationApi, _consent_provider(), FakeClient, FakeNumberVerification, FakeNumberVerificationRejectsNonce, _jwks_handler(), _manual_id_token(), _manual_provider() (+18 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "events.py"
Cohesion: 0.20
Nodes (16): create_session(), end_session(), get_session(), delete, get, post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.… (+8 more)

### Community 29 - "routes_proof_shares.py"
Cohesion: 0.15
Nodes (14): accept_quality(), prefers_html(), Whether a caller is a browser navigating or a script fetching. Extracted from…, The q-value Accept assigns to an exact media type (no wildcard credit). A `*/*`…, Whether a browser's Accept header prefers text/html over JSON. Absent,…, create_proof_share(), delete, get (+6 more)

### Community 30 - "test_outcomes_contract.py"
Cohesion: 0.15
Nodes (33): _as_the_merchant(), _extra_merchant_key(), _fresh_headers(), _get(), fixture, P5 — collect outcomes before calibrating scores. Merchants report what actually…, P3's own dimension is derived, not reported through this endpoint — reporting…, This file fires many requests against a couple of fixed keys; do not leak that… (+25 more)

### Community 31 - "ConsentStore"
Cohesion: 0.07
Nodes (40): consent_complete_page(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), get, HTMLResponse, HTTPException (+32 more)

### Community 32 - "get_chain"
Cohesion: 0.29
Nodes (7): get_chain(), get, Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, The public key anyone can use to independently verify a chain signature., vault_public_key(), verify_chain()

### Community 33 - "test_s2_stream_isolation.py"
Cohesion: 0.18
Nodes (12): subscriber_count(), asyncio, S2 — the SSE stream must be authenticated and must not cross tenants., End to end through the HTTP surface, not just the bus., A disconnect that is never noticed must not pin memory forever (S12)., The finding, verbatim: `curl -N /v1/console/stream` harvested everything., A background emit with no owner must not fan out to a real tenant., test_a_subscriber_never_sees_an_event_emitted_for_nobody() (+4 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.06
Nodes (68): Money, RequestContext, VerificationRequest, Receive the events emitted for `owner`, and only those., subscribe(), main(), T1 — call every CAMARA action for real and record what came back. The runbook's…, Never write a real identifier to a file that gets committed. (+60 more)

### Community 35 - "store.py"
Cohesion: 0.16
Nodes (22): owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainAlreadyExists, ChainRecord, get(), get_async() (+14 more)

### Community 36 - "signing.py"
Cohesion: 0.15
Nodes (23): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+15 more)

### Community 37 - "test_lab_page.py"
Cohesion: 0.04
Nodes (23): fixture, The judge lab page (I1/I2/I3/I4/I9) — a reader for recorded runs. The page's…, The escaping the page does to survive the HTML parser must be invisible to…, I9's bound: the only input is which recording to show. If a POST, or a…, Not just the router — nothing reachable under /lab accepts a body., Replay is a local scrub over an embedded list. A fetch here would be the first…, I1 step 2: a heuristic described as reasoning is worse than a heuristic., P2's receipt-table lesson, applied before it can be repeated here. (+15 more)

### Community 38 - "schemas.py"
Cohesion: 0.07
Nodes (46): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), explain_chain(), post (+38 more)

### Community 39 - "challenges.py"
Cohesion: 0.13
Nodes (30): AttemptNotFound, AttemptNotPending, create_attempt(), _expire_if_due(), _finalize_or_replay(), IdempotencyKeyConflict, _now(), _owner() (+22 more)

### Community 40 - "rate_limit.py"
Cohesion: 0.24
Nodes (12): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+4 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.09
Nodes (17): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files., /docs, /redoc and /openapi.json all answered 200 unauthenticated. (+9 more)

### Community 42 - "test_run_replay_endpoint.py"
Cohesion: 0.06
Nodes (32): _delivered(), _extra_merchant_key(), asyncio, fixture, I14's HTTP surface: GET /v1/console/runs/{run_id}/events. Authorized the same…, At-least-once means the same event legitimately arrives twice — once live, once…, Numbering a live-only event as if it were in the journal would promise a…, Most emissions carry no run_id and are not replayable at all. (+24 more)

### Community 43 - "test_nac_capabilities.py"
Cohesion: 0.25
Nodes (13): capability_for(), load_capabilities(), preflight(), I10 — provider capability and consent readiness. Reads the authored…, Local-only readiness: {"ready": bool, "reason": str | None}., I10 — provider capability and consent readiness. Local-only: preflight() never…, test_an_unavailable_capability_is_never_ready(), test_an_unknown_action_is_not_ready() (+5 more)

### Community 44 - "SessionManager"
Cohesion: 0.14
Nodes (19): SessionStatus, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+11 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.12
Nodes (24): Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The window is the spoofing opportunity: while an announcement stands, a call…, Matching the caller alone would let one genuine announcement verify a burst of…, The load-bearing test of this whole feature. Caller ID is spoofable, so a…, The mismatch that is real: this number is Demo Bank's, and the caller says they…, "Arab Bank" is not in the registry, so the registry knows nothing about whether…, The shape that broke: every extra honest word made condemnation more likely,…, Absence from a hand-curated registry is not evidence. Almost every number in… (+16 more)

### Community 47 - "test_proof_shares.py"
Cohesion: 0.14
Nodes (32): _as_the_merchant(), _create(), _extra_merchant_key(), _fresh_headers(), fixture, I13 — expiring reviewer links with explicit disclosure scope. A proof share is…, The token must be recoverable for a replay, but never sit in the database in…, I13's UI: same content negotiation as P4a's consent callback — JSON is the… (+24 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "test_merchant_pilot.py"
Cohesion: 0.09
Nodes (53): _challenge_handler(), _client(), _login(), _make_allowed_flow(), _make_challenged_flow(), _patch_isnad(), fixture, Request (+45 more)

### Community 50 - "MockProvider"
Cohesion: 0.09
Nodes (44): build_investigator(), Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, FaultInjectingProvider, ValueError, UnknownFaultProfile (+36 more)

### Community 51 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 52 - "run_case"
Cohesion: 0.19
Nodes (15): ValueError, I9 — judge-controlled scenario challenge. A small, versioned, authored case set…, The requested case id is not in the authored set — reject before doing any…, A reproducible shuffle of the case set — same seed, same order, always., run_case(), seeded_order(), UnknownCase, asyncio (+7 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "test_review_regressions.py"
Cohesion: 0.12
Nodes (31): _poll_and_maybe_complete(), Best-effort: Isnad being briefly unreachable must surface as "still polling",…, asyncio, parametrize, Idle retention and one trust-session binding per merchant order., test_completed_phone_expires_without_a_request(), test_idle_cleanup_and_shutdown(), test_retention_must_be_positive() (+23 more)

### Community 55 - "run_scenario"
Cohesion: 0.13
Nodes (28): _fixture_digest(), ValueError, Run the named scenario's fixture, or `request_override` (a full…, run_scenario(), UnknownScenario, asyncio, I1's shared runner: deterministic, isolated, offline investigation replays. No…, `detail` on the NaC path is operator-supplied text, and these artifacts are… (+20 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.15
Nodes (13): A changed SIM should start an investigation., Developer guide, Hackathon readiness, How it works, Integrate from a merchant backend, Isnad · إسناد, Operational boundaries, Results you can reproduce (+5 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.16
Nodes (13): investigate(), console.html — live agent console, askTheAgent(), showReceiptQr(), judge.html — Judge Mode verified checkout, runCheckout(), receipt.html — public evidence receipt, renderArithmetic() (+5 more)

### Community 58 - "PolicyEngine"
Cohesion: 0.07
Nodes (12): p_to_logodds(), PolicyEngine, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., The checks that can move this hypothesis, in either direction. Empty for…, What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain. (+4 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.10
Nodes (20): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read… (+12 more)

### Community 60 - "test_consent_html_redirect.py"
Cohesion: 0.24
Nodes (9): FakeConsentProvider, _patched(), P4a step 8 — a browser-preferring callback gets a generic HTML redirect. The…, _start(), test_a_browser_preferring_callback_is_redirected_even_when_denied(), test_a_browser_preferring_callback_is_redirected_to_the_generic_page(), test_a_script_client_with_no_accept_header_still_gets_json(), test_a_tied_preference_keeps_json() (+1 more)

### Community 61 - "7. Competition feature implementation plan"
Cohesion: 0.11
Nodes (19): 7. Competition feature implementation plan, Agent execution and release checklist, Evidence behind the recommendations, I10 — Provider capability and consent readiness, I11 — Reference merchant integration and location-claim capture, I12 — Outcome learning and safe policy comparison, I13 — Expiring reviewer links with explicit disclosure scope, I14 — Durable trace recovery after a disconnect (+11 more)

### Community 62 - "proof_shares.py"
Cohesion: 0.15
Nodes (22): IdempotencyRecordRow, ProofShareRow, A durable record of one merchant write, keyed by owner + operation + the…, An expiring reviewer link onto one chain's separately issued attestation (I13)…, create_share(), _decrypt(), _encrypt(), _fernet() (+14 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (21): logodds_to_p(), BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy() (+13 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "test_fake_operator.py"
Cohesion: 0.13
Nodes (33): FakeNacProvider, _AccessToken, _AuthCode, authorize(), authorize_decide(), discovery(), _issuer(), jwks() (+25 more)

### Community 66 - "P4a implementation record"
Cohesion: 0.17
Nodes (12): A real defect found during browser verification, not just written to pass tests, Browser evidence, actually performed, Consent-contract defects fixed first (before the OAuth work), Contract decision, checked against the source before building, Files changed, ID-token validation, shared rather than duplicated, Known gaps, stated plainly, P4a implementation record (+4 more)

### Community 67 - "init_db"
Cohesion: 0.07
Nodes (50): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, _assert_status(), main() (+42 more)

### Community 68 - "NacProvider"
Cohesion: 0.15
Nodes (8): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., nac.py's _as_url returned any string the SDK provided., test_a_non_https_authorization_url_is_refused()

### Community 69 - "Action"
Cohesion: 0.05
Nodes (59): Small Gemini REST adapter shared by Isnad's optional AI features. The hackathon…, EvidenceLink, _now(), datetime, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, Result (+51 more)

### Community 70 - "test_registry.py"
Cohesion: 0.06
Nodes (38): _directory(), The number registry — which published numbers belong to which institution. The…, Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., The bug this replaced: every word of the claim had to be indexed, so the more… (+30 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.17
Nodes (15): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, Phase 2 Agent Runbook (+7 more)

### Community 72 - "policy.yaml — the single tuning surface"
Cohesion: 0.15
Nodes (16): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP_CONFIRMED — reserved, nothing emits it, OTP counterfactual pricing block, REGISTRY_MATCH_UNANNOUNCED = 0.0 (+8 more)

### Community 73 - "routes_lab.py"
Cohesion: 0.13
Nodes (23): _embed(), lab_bundle(), lab_page(), _live_identity(), get, HTMLResponse, JSONResponse, Request (+15 more)

### Community 74 - "outcomes.py"
Cohesion: 0.16
Nodes (22): MerchantOutcomeEventRow, One merchant-reported outcome on an owned chain — order status or fraud…, challenge_execution_summary(), current_and_timeline(), _current_head(), DimensionAlreadyLabelled, _event_dict(), IdempotencyKeyConflict (+14 more)

### Community 75 - "emit"
Cohesion: 0.21
Nodes (19): events_after(), Persisted events for this owner's run, strictly newer than `after`, in order.…, emit(), Deliver an event to the subscribers belonging to the current owner. Persisted…, The Verified Caller act emits the calling number. A journal outlives the…, test_the_journal_keeps_no_subscriber_number(), _owner(), asyncio (+11 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "merchant_pilot/app.py"
Cohesion: 0.19
Nodes (18): capabilities_page(), ChallengeEventBody, dashboard(), flow_page(), get_flow(), lifespan(), login(), login_page() (+10 more)

### Community 78 - "11. UI review and implementation plan — 6 September 2026"
Cohesion: 0.22
Nodes (9): 11. UI review and implementation plan — 6 September 2026, U1 — Make the first visit usable, including failure states (P0), U2 — Bring the action into the first mobile screen (P1), U3 — Show the decision first, with concise supporting reasons (P1), U4 — Repair mobile trace layout and make progress meaningful (P1), U5 — Give CHALLENGE a visible continuation (P1), U6 — Make receipt verification understandable (P1), U7 — Make the new features discoverable without crowding checkout (P2) (+1 more)

### Community 79 - "P5 implementation record"
Cohesion: 0.20
Nodes (10): Browser evidence (this session, real processes, not mocked), Contract decisions made explicit before writing code, Idempotency: durable, plus its own audit columns, Insert-then-single-transaction, not two-phase, Known gaps, Merchant pilot harness, P5 implementation record, Retention (+2 more)

### Community 80 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 81 - "P1 and P2 implementation records"
Cohesion: 0.67
Nodes (3): P1 and P2 implementation records, P2 implementation — 6 Sep (follow-up session), Preserved P1 implementation record

### Community 82 - "test_s7_quota_and_key_mode.py"
Cohesion: 0.13
Nodes (20): InsecureVaultKey, The signing key is readable by someone other than its owner., RuntimeError, This owner already has as many live sessions as it is allowed., SessionQuotaExceeded, asyncio, S7 — the two unbounded amplifiers: session quota, and the key file mode., `_sessions` was never pruned, so it grew for the life of the process. (+12 more)

### Community 84 - "Q: What changed in the 5 September review and what remains unproven?"
Cohesion: 0.40
Nodes (4): Answer, Outcome, Q: What changed in the 5 September review and what remains unproven?, Source Nodes

### Community 85 - "verify_runtime_lock.py"
Cohesion: 0.60
Nodes (5): _canonical(), _locked(), main(), _project_dependencies(), Validate the committed runtime lock without contacting a package index. The…

### Community 86 - "test_evidence_pack.py"
Cohesion: 0.29
Nodes (5): evidence_pack_module(), asyncio, fixture, Focused contract tests for the offline, judge-reviewable evidence pack., test_evidence_pack_is_offline_and_verifies_the_stored_chain()

### Community 87 - "test_mock_scenarios.py"
Cohesion: 0.47
Nodes (5): Guards on the demo fixture table itself. A dict literal with a repeated key is…, Read the keys from the SOURCE, not the dict. By the time the module is imported…, _scenario_keys(), test_every_scenario_number_is_e164(), test_no_scenario_number_is_defined_twice()

### Community 88 - "Choice"
Cohesion: 0.07
Nodes (20): Choice, LLMPlanner, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as… (+12 more)

### Community 89 - "database.py"
Cohesion: 0.16
Nodes (13): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for (+5 more)

### Community 90 - "test_receipt_download.py"
Cohesion: 0.12
Nodes (17): CompletedProcess, Path, I7 — portable receipt verification. The existing GET /v1/receipts/{chain_id}…, The one mistake that would make an honestly-signed receipt look tampered:…, A download assembled from the rendered summary would omit exactly the fields…, The receipt a reader most needs to keep and check elsewhere is the one that did…, I7 step 4: pseudonymous is not anonymous, and a downloaded file cannot be…, _run_verify_script() (+9 more)

### Community 91 - "Decision"
Cohesion: 0.10
Nodes (34): Verdict, ChainGrade, Decision, How much the evidence chain itself was worth, independent of the decision. The…, _degraded_context(), _fact(), A deterministic, plain-language projection of an already-signed Verdict. P2…, One human sentence for a link, traceable to that exact link. `link.api` and… (+26 more)

### Community 92 - "FlowRecord"
Cohesion: 0.15
Nodes (8): FlowRecord, FlowStore, _now(), datetime, Internal, unauthorized lookup — background completion polling only. Every…, R1 + R3: sweeps expired flows first (retention enforced on every read, not only…, _Session, SessionStore

### Community 101 - "owner_for"
Cohesion: 0.12
Nodes (17): owner_for(), The tenant a validated key belongs to., console_mode(), console_page(), console_stream(), console_stream_token(), get, HTMLResponse (+9 more)

### Community 110 - "evidence_pack.py"
Cohesion: 0.21
Nodes (16): build_report(), EvidenceCase, main(), parse_args(), Any, Namespace, Path, Generate a reproducible, offline evidence pack for the scripted Isnad demo.… (+8 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 120 - "routes_registry.py"
Cohesion: 0.21
Nodes (13): _directory(), get, Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), One institution's claim on a number, with the basis for the claim., RegistryInstitution (+5 more)

### Community 121 - "What the risk score means"
Cohesion: 0.50
Nodes (4): Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability

### Community 125 - "routes_challenge.py"
Cohesion: 0.18
Nodes (15): create_challenge(), get_challenge_timeline(), _owned_challenged_chain(), get, post, The owned followup history for a chain. Available on any decision — empty on…, The chain this caller owns, or the same 404 a missing one gets (P3 mirrors…, Open a followup on a CHALLENGE decision. Refused on any other decision: a… (+7 more)

### Community 126 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 127 - "InMemoryCache"
Cohesion: 0.08
Nodes (13): Cache, get_cache(), InMemoryCache, Protocol, Redis-backed cache for token caching + idempotency across instances., Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one. (+5 more)

### Community 128 - "test_s1_console_credential.py"
Cohesion: 0.15
Nodes (18): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+10 more)

### Community 129 - "retention.py"
Cohesion: 0.18
Nodes (13): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+5 more)

### Community 130 - "GreedyPlanner"
Cohesion: 0.09
Nodes (21): get_planner(), GreedyPlanner, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, A planner that opens on the SIM swap, as the LLM planner is free to do. This is…, _SwapFirstPlanner, test_the_factory_still_selects_by_config() (+13 more)

### Community 132 - "test_false_decline_baseline.py"
Cohesion: 0.21
Nodes (11): _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and…, The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean line'.…, Guards against a baseline so blunt it declines everyone, which would make the…, The whole thesis is that these two rules disagree about an unanswered check. If…, test_a_clean_chain_declines_under_neither_baseline(), test_every_generated_case_differs_from_clean_in_exactly_one_check() (+3 more)

### Community 133 - "routes_receipt.py"
Cohesion: 0.24
Nodes (11): get, HTMLResponse, Request, The page a judge opens from the QR code., Give the QR a viewBox so it scales with its container., An inline SVG QR for this receipt's public URL. Generated server-side and…, The exact signed bytes, the signature, and the key that signed them. Public and…, receipt_data() (+3 more)

### Community 134 - "test_an_announcement_cannot_outvote_a_network_contradiction"
Cohesion: 0.17
Nodes (12): asyncio, REGISTRY_MATCH_UNANNOUNCED is zeroed in policy.yaml on purpose., Act IV must not regress: adding local evidence to the chain must not rescue a…, The combination that matters: the bank's real number, announced, but the…, The standalone reverse-verify path must keep working — it is a public API in…, The H3 exploit: one announcement, repeated reverse-verify calls, each minting a…, test_a_registry_match_alone_does_not_move_belief(), test_a_replayed_chain_cannot_be_minted_twice() (+4 more)

### Community 135 - "P3 implementation record"
Cohesion: 0.22
Nodes (9): Browser evidence (this session, real processes, not mocked), CHALLENGE followups, in their own tables, Idempotency, durable rather than in-memory, Insert-only `store.save` (step 1), Known gaps, Merchant pilot harness: "Continue merchant verification", P3 implementation record, Retention and posture (+1 more)

### Community 136 - "test_consent_contract.py"
Cohesion: 0.11
Nodes (20): asyncio, Reverse Isnad — verify an inbound caller to the customer (Act IV)., The real institution line is network-attested -> TRUST (ALLOW)., A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)., test_genuine_caller_is_trusted(), test_spoofed_caller_is_rejected(), P4a — consent-contract defects fixed before building the live-consent journey.…, A record that times out without ever being touched must still get a… (+12 more)

### Community 137 - "verify_receipt.py"
Cohesion: 0.36
Nodes (8): BundleError, load_bundle(), load_trusted_keys(), main(), Path, ValueError, I7 — verify a downloaded Isnad receipt entirely offline. Verifies the exact…, verify()

### Community 138 - "routes_privacy.py"
Cohesion: 0.22
Nodes (9): _human(), posture(), privacy_page(), get, HTMLResponse, Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page… (+1 more)

### Community 139 - "_announce"
Cohesion: 0.15
Nodes (13): _announce(), The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call…, An institution announcing a call is telling this service who it is about to…, A non-spending read is for a party that already holds the use. Anyone else gets…, test_a_published_inbound_only_number_cannot_be_announced_from(), test_a_reader_that_never_screened_cannot_inspect_an_announcement() (+5 more)

### Community 140 - "build_evidence_comparison.py"
Cohesion: 0.46
Nodes (7): build_report(), _code_revision(), _load(), main(), _policy_digest(), Path, I3 — evidence budget and decision comparison, combined into one report. Reuses…

### Community 141 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 144 - "test_s11_claimed_identity.py"
Cohesion: 0.27
Nodes (10): S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge(), test_ordinary_organisation_names_still_pass() (+2 more)

### Community 145 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 146 - "routes_outcomes.py"
Cohesion: 0.27
Nodes (8): get_outcomes(), _owned_chain(), get, post, Ownership only — no decision gate. Unlike P3, an outcome may be reported on any…, report_outcome(), OutcomeTimelineResponse, OutcomeReportRequest

### Community 147 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 148 - "6. MENA Ignite submission priorities — reviewed 6 September 2026"
Cohesion: 0.20
Nodes (10): 6. MENA Ignite submission priorities — reviewed 6 September 2026, H0 — Confirm the submission contract before building more, H1 — Make the AI contribution visible and measurable, H2 — Show verifiable Nokia NaC integration, with precise scope, H2a — Live API calls to Nokia's hosted simulator, H3 — Make one MENA customer problem specific, H4 — Demonstrate the benefit without hiding the tradeoff, H5 — Ship one coherent, remotely accessible demonstration (+2 more)

### Community 149 - "9. Sonnet code review — 6 September 2026"
Cohesion: 0.25
Nodes (8): 9. Sonnet code review — 6 September 2026, R1 — Bind merchant harness flows to their creating session (high), R2 — Recover completed verification after a lost response (high), R3 — Enforce harness flow retention on reads and while idle (medium), R4 — Enforce terminal consent retention without new traffic (medium), R5 — Remove the unvalidated SDK token-exchange branch (high, conditional), R6 — Freeze outcome operations for safe retries (high), R7 — Validate flow context before constructing upstream input (medium)

### Community 150 - ".trusts"
Cohesion: 0.20
Nodes (6): Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, _trusted_from_settings(), _verify_with_key(), Ed25519PublicKey

### Community 151 - "test_outcome_report_review_metrics.py"
Cohesion: 0.38
Nodes (9): _as_the_merchant(), _owner(), fixture, I12 — review metrics and an optional business-impact worksheet, added on top of…, _seed(), test_a_worksheet_with_assumptions_is_report_only(), test_challenge_completion_time_is_averaged_over_completed_attempts(), test_manually_accepted_orders_are_counted() (+1 more)

### Community 152 - "bound_key"
Cohesion: 0.29
Nodes (7): bound_key(), _no_leftover_announcements(), fixture, The suite shares one in-memory database, so an announcement made by one test…, demo-merchant-key, bound to the institution that owns BANK_NUMBER., A registry holding Demo Bank and one other institution. The shipped registry…, two_bank_registry()

### Community 153 - "config.py"
Cohesion: 0.09
Nodes (28): form(), Read the request context and commit to a risk hypothesis. This is what makes…, effective_planner(), The planner that will actually choose, not the one config asked for.…, get_engine(), Path, Load the policy once and reuse it — avoids re-reading/parsing YAML per request., Offline, deterministic investigation runs for the judge lab (I1). Reuses the… (+20 more)

### Community 154 - "Isnad — compact handoff"
Cohesion: 0.20
Nodes (10): 10. Follow-up code review — 6 September 2026, 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 4. Path to a live product, 5. Code map and working rules, 8. Latest session, F1 — Keep polling while a completed receipt is still missing (high; R2), F2 — Finish idle cleanup and terminal data minimization (medium; R3) (+2 more)

### Community 155 - "test_i18n.py"
Cohesion: 0.05
Nodes (29): I6 — locale dictionaries served through one explicit, allowlisted route. Locale…, The Arabic dictionary is machine-assisted and unreviewed; a reader of the page,…, The translation is a gloss beside the signed token. Replacing CHALLENGE with an…, Chain ids, hex keys, ISO timestamps, API names and signed numbers are reordered…, I6 step 1's hard rule: locale is UI-only. The only request that may carry it is…, Verification is what the receipt is *for*. An unreachable presentation module…, Zero external origins is the rule these pages keep; a shared module must not be…, A reader who cannot distinguish the green from the red must still get the… (+21 more)

### Community 156 - "run_events.py"
Cohesion: 0.29
Nodes (9): _allowlisted_body(), has_gap(), _now(), persist_event(), purge_older_than(), datetime, Durable event journal for one investigation run (I14). `persist_event()` is…, True when a client's own cursor cannot be trusted: it claims to have already… (+1 more)

### Community 157 - "test_hypothesis_relevance.py"
Cohesion: 0.25
Nodes (8): _act_one(), Every check a hypothesis may buy has to be able to move that hypothesis. The…, The sentence is what a merchant reads. Naming only the orthogonal check was the…, A check listed for a hypothesis must have a signal that can move it. `gain`…, `legit` lists nothing, and that has to mean "no hypothesis-driven check", not…, test_no_relevant_check_is_a_zero_information_choice(), test_the_engine_does_not_treat_an_empty_relevant_list_as_everything(), test_the_verdict_sentence_names_the_check_that_carried_it()

### Community 158 - "test_evidence_comparison.py"
Cohesion: 0.47
Nodes (5): asyncio, I3 — the combined evidence/decision comparison report. Loaded from the script…, test_false_declines_are_counted_only_among_the_innocent_denominator(), test_the_report_carries_both_sources_and_named_denominators(), test_the_report_is_reproducible_across_two_runs()

### Community 159 - "test_independent_evaluation.py"
Cohesion: 0.22
Nodes (6): asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()

### Community 161 - "TraceEvent"
Cohesion: 0.25
Nodes (4): LabRun, Versioned artifacts for the judge lab (I1's shared contract). A `LabRun` is a…, TraceEvent, _planner_source()

### Community 164 - "test_a_clean_signup_does_not_rest_on_an_orthogonal_check_alone"
Cohesion: 0.29
Nodes (7): asyncio, `grade` reads adverse_delta as "at least"; the explanation used a strict hard-…, The general form, so the next hypothesis added cannot repeat this., The Act I trace, end to end. Buying the cheap number-association check first is…, test_a_clean_signup_does_not_rest_on_an_orthogonal_check_alone(), test_a_link_exactly_at_the_material_bar_is_named(), test_every_hypothesis_only_selects_checks_it_lists()

### Community 165 - ".__init__"
Cohesion: 0.29
Nodes (3): FakeDeviceStatus, FakeReachability, FakeSimSwap

### Community 166 - "i18n_switch"
Cohesion: 0.33
Nodes (6): i18n_dictionary(), i18n_switch(), get, Response, `Literal["en", "ar"]` rejects anything else at the routing layer itself —…, The locale switch itself, shared by every page that has one. One more explicit,…

### Community 168 - ".__call__"
Cohesion: 0.50
Nodes (3): Receive, Scope, Send

### Community 169 - "Code review and hackathon readiness — 6 September 2026"
Cohesion: 0.40
Nodes (5): Code review and hackathon readiness — 6 September 2026, Fixes delivered, Outcome, Suggestions for MENA Ignite, Verification

### Community 170 - "t1_probe.py"
Cohesion: 0.50
Nodes (4): describe(), main(), T1 — fire exactly ONE real CAMARA call and record what actually came back.…, Render an SDK response without assuming it is a dict or a pydantic model.

### Community 171 - "build_judge_lab.py"
Cohesion: 0.67
Nodes (3): _build_all(), main(), Build LabRun artifacts for every judge-lab scenario (I1). Fully offline: mock…

### Community 172 - "test_pilot_polling.py"
Cohesion: 0.50
Nodes (3): skipif, Execute the shipped poll loop with controlled HTTP replies and a tiny DOM., test_poll_recovers_after_http_error_and_missing_receipt()

### Community 173 - "test_s5_subject_binding.py"
Cohesion: 0.16
Nodes (18): get_record(), _as_the_merchant(), _chain_for(), fixture, S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., Read chains directly as the key that created them. store.get_record() is scoped… (+10 more)

### Community 175 - "_reset_limiters"
Cohesion: 0.67
Nodes (3): fixture, These console checks deliberately make authenticated requests. Keep their…, _reset_limiters()

### Community 176 - "_configured_for_llm"
Cohesion: 0.67
Nodes (3): _configured_for_llm(), fixture, Global config asking for the model, with a credential present.

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **152 isolated node(s):** `Isnad`, `encode.sh script`, `L`, `TOTAL`, `SCENES` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1325 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Action`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `IdTokenError`, `t1_probe.py`, `test_review_regressions.py`, `test_nac_provider.py`, `ConsentStore`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `JUDGE_WALKTHROUGH.md`, `Phase 2 Agent Runbook`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `NaC integration — observed, not assumed` connect `Phase 2 Agent Runbook` to `console.html — live agent console`, `NacProvider`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Are the 82 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 82 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 69 inferred relationships involving `Decision` (e.g. with `Investigator` and `create_challenge()`) actually correct?**
  _`Decision` has 69 INFERRED edges - model-reasoned connections that need verification._