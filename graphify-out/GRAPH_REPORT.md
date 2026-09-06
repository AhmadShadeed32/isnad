# Graph Report - isnad  (2026-09-06)

## Corpus Check
- 232 files · ~186,705 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2985 nodes · 6964 edges · 176 communities (130 shown, 21 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 655 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9498cf9b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ChainGrade
- test_t6_receipt.py
- run_scenario
- main.py
- test_llm_planner.py
- Investigator
- test_registry.py
- test_velocity.py
- Verdict
- config.py
- IdTokenError
- merchant_pilot/app.py
- test_challenge_contract.py
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- Decision
- test_t4_ask_the_agent.py
- check_startup_posture
- VaultSigner
- test_t5_counterfactual.py
- GeminiClient
- retention.py
- test_judge.py
- test_act7.py
- test_nac_provider.py
- timeline.js
- routes_session.py
- routes_registry.py
- test_outcomes_contract.py
- ConsentStore
- routes_consent.py
- test_s2_stream_isolation.py
- VerificationRequest
- store.py
- signing.py
- policy.yaml — the single tuning surface
- routes_verified_caller.py
- challenges.py
- rate_limit.py
- test_s12_runtime_posture.py
- NacProvider
- test_fake_operator.py
- test_s7_quota_and_key_mode.py
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_proof_shares.py
- test_s10_xss_and_headers.py
- test_merchant_pilot.py
- MockProvider
- UtcDateTime
- velocity.py
- test_nac_contract.py
- test_s5_subject_binding.py
- test_s6_vault_keys.py
- Isnad · إسناد
- console.html — live agent console
- PolicyEngine
- test_audit_low.py
- test_consent_html_redirect.py
- 7. Competition feature implementation plan
- proof_shares.py
- independent_evaluation.py
- Project Brief
- fake_operator/app.py
- P4a implementation record
- evidence_pack.py
- Signal → log-odds vocabulary
- Action
- _directory
- Phase 2 Agent Runbook
- _two_banks
- vault.py
- outcomes.py
- emit
- test_s14_no_tracked_secrets.py
- test_acts.py
- routes_proof_shares.py
- P5 implementation record
- test_s9_consent_replay.py
- P1 and P2 implementation records
- routes_verify.py
- CURRENT_STATE.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- Choice
- database.py
- test_receipt_download.py
- NaC integration — observed, not assumed
- enums.py
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_hardening.py
- get_chain
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- routes_privacy.py
- What the risk score means
- schemas.py
- test_run_replay_endpoint.py
- InMemoryCache
- run_reverse
- run_events.py
- GreedyPlanner
- test_false_decline_baseline.py
- SessionManager
- counterfactual.py
- P3 implementation record
- test_reverse.py
- verify_receipt.py
- test_consent_contract.py
- _announce
- build_evidence_comparison.py
- stream_token.py
- JUDGE_WALKTHROUGH.md
- sonnet_review_regressions.py
- test_s4_demo_mode.py
- owner_hash
- 3. Recommended app work — not implemented in this documentation pass
- 6. MENA Ignite submission priorities — reviewed 6 September 2026
- 9. Sonnet code review — 6 September 2026
- merchant_outcome_report.py
- test_outcome_report_review_metrics.py
- bound_key
- SlidingWindowLimiter
- Isnad — compact handoff
- test_i18n.py
- _verdict
- ._tz_aware
- test_evidence_comparison.py
- test_an_unreadable_signature_is_tampering_not_absence
- explain_chain
- test_a_tampered_registry_refuses_to_load
- test_the_page_renders_no_reason_string
- test_the_published_bytes_verify_against_the_published_key
- test_the_published_bytes_are_the_stored_bytes_not_a_reserialization
- test_the_summary_agrees_with_the_signed_payload
- test_the_receipt_page_has_zero_external_origins
- test_the_qr_markup_renders_once_the_console_declares_the_namespace
- test_the_receipt_publishes_everything_needed_to_redo_the_decision
- test_the_threshold_snapshot_is_inside_the_signed_payload
- test_no_recorded_camara_response_carries_a_timestamp
- test_the_receipt_contains_no_phone_number
- test_the_rendered_summary_exposes_signals_not_details

## God Nodes (most connected - your core abstractions)
1. `Action` - 154 edges
2. `VerificationRequest` - 113 edges
3. `Decision` - 101 edges
4. `MockProvider` - 92 edges
5. `Result` - 88 edges
6. `Verdict` - 69 edges
7. `EvidenceLink` - 64 edges
8. `RequestContext` - 64 edges
9. `ChainGrade` - 58 edges
10. `PolicyEngine` - 58 edges

## Surprising Connections (you probably didn't know these)
- `Demo/production parity — only the provider differs` --references--> `MockProvider`  [EXTRACTED]
  docs/02_API_Build_Plan.md → app/providers/mock.py
- `T3 — rebuild the planner so the agent actually reasons` --references--> `LLMPlanner`  [EXTRACTED]
  docs/PHASE2_AGENT_RUNBOOK.md → app/agent/planner.py
- `MockProvider` --implements--> `EvidenceProvider adapter contract`  [EXTRACTED]
  app/providers/mock.py → docs/02_API_Build_Plan.md
- `NacProvider` --implements--> `EvidenceProvider adapter contract`  [EXTRACTED]
  app/providers/nac.py → docs/02_API_Build_Plan.md
- `NacProvider` --references--> `Nokia Network as Code (NaC)`  [EXTRACTED]
  app/providers/nac.py → docs/02_API_Build_Plan.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pitch Video Render Pipeline (narration to encoded cut)** — docs_video_readme_video_build_pipeline, docs_video_timings_spine, docs_video_scene_scenes, docs_video_encode_pipeline, docs_video_readme_narration_anchored_timing [EXTRACTED 1.00]
- **Supply-Chain Pinning and Audit Flow (S8)** — requirements_runtime_pins, requirements_lock_runtime_closure, requirements_dev_toolchain, github_workflows_ci_verify, requirements_network_as_code_pip_defect, setup_bootstrap_venv [EXTRACTED 1.00]
- **Nokia NaC / CAMARA Evidence Capture Catalogue** — docs_nac_sim_swap_capture, docs_nac_device_swap_capture, docs_nac_location_verify_capture, docs_nac_number_verify_capture, docs_nac_reachability_capture, docs_nac_roaming_capture, docs_nac_device_intelligence_capture, docs_nac_step_up_otp_capture, docs_nac_sim_swap_normalized_envelope [INFERRED 0.95]

## Communities (176 total, 21 thin omitted)

### Community 0 - "ChainGrade"
Cohesion: 0.08
Nodes (46): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, Money, p_to_logodds(), _engine(), _gate(), _investigator(), asyncio (+38 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.09
Nodes (10): chain_id(), fixture, T6 — the public, independently verifiable receipt., The tamper control, and the reason it is worth putting on stage., Published beside the deltas but outside the signature, the starting point would…, A receipt nobody can fetch cannot be verified by anybody., test_one_flipped_bit_breaks_verification(), test_the_prior_is_inside_the_signed_bytes() (+2 more)

### Community 2 - "run_scenario"
Cohesion: 0.06
Nodes (51): ValueError, I9 — judge-controlled scenario challenge. A small, versioned, authored case set…, The requested case id is not in the authored set — reject before doing any…, A reproducible shuffle of the case set — same seed, same order, always., run_case(), seeded_order(), UnknownCase, compare_missing_location_claim() (+43 more)

### Community 3 - "main.py"
Cohesion: 0.07
Nodes (29): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+21 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.09
Nodes (45): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+37 more)

### Community 5 - "Investigator"
Cohesion: 0.14
Nodes (15): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+7 more)

### Community 6 - "test_registry.py"
Cohesion: 0.06
Nodes (33): The number registry — which published numbers belong to which institution. The…, Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and… (+25 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.12
Nodes (39): distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., _as(), _burst(), _clean(), _engine() (+31 more)

### Community 8 - "Verdict"
Cohesion: 0.08
Nodes (50): Verdict, _degraded_context(), _fact(), present(), Presentation, BaseModel, A deterministic, plain-language projection of an already-signed Verdict. P2…, Project a signed Verdict into a plain-language Presentation. Pure function:… (+42 more)

### Community 9 - "config.py"
Cohesion: 0.05
Nodes (59): form(), Read the request context and commit to a risk hypothesis. This is what makes…, effective_planner(), The planner that will actually choose, not the one config asked for.…, is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one. (+51 more)

### Community 10 - "IdTokenError"
Cohesion: 0.09
Nodes (50): fetch_jwks(), IdTokenError, Any, AsyncClient, RuntimeError, ID-token validation shared by every OIDC-based Number Verification path (P4a).…, The id_token is missing, malformed, or fails contract validation. Deliberately…, Validate signature, iss, aud, exp/iat and nonce. Returns the claims. Fails… (+42 more)

### Community 11 - "merchant_pilot/app.py"
Cohesion: 0.05
Nodes (65): Area, A claimed location — never a tracked coordinate. Used only for yes/no verify., ChallengeEventBody, _client_is_private(), create_flow(), create_flow_challenge(), dashboard(), flow_page() (+57 more)

### Community 12 - "test_challenge_contract.py"
Cohesion: 0.13
Nodes (38): _as_the_merchant(), _create(), _extra_merchant_key(), _fresh_headers(), fixture, parametrize, P3 — finish CHALLENGE without rewriting its receipt. A merchant that gets…, Not an in-memory cache (P4a's rule for /v1/verify explicitly does not apply… (+30 more)

### Community 13 - "announce.py"
Cohesion: 0.12
Nodes (28): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+20 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (18): Directory, _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",… (+10 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (27): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+19 more)

### Community 17 - "Decision"
Cohesion: 0.16
Nodes (22): Decision, asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote(), _owner() (+14 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.11
Nodes (9): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., Same fix as the narrative: a bare grade name gets misread., test_a_model_failure_does_not_look_like_a_chain_failure(), test_no_model_configured_is_a_clean_503() (+1 more)

### Community 19 - "check_startup_posture"
Cohesion: 0.10
Nodes (35): clear(), check_startup_posture(), InsecureConfiguration, RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Refuse to start a billable deployment with no key or a published one. Only…, Settings (+27 more)

### Community 20 - "VaultSigner"
Cohesion: 0.12
Nodes (12): Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, Signs issued chains with Ed25519. The key is loaded from disk if present,…, _trusted_from_settings(), VaultSigner, _verify_with_key() (+4 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.07
Nodes (31): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+23 more)

### Community 23 - "retention.py"
Cohesion: 0.18
Nodes (13): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+5 more)

### Community 24 - "test_judge.py"
Cohesion: 0.16
Nodes (13): judge_page(), get, HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that… (+5 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (29): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, The two demo actions share state across runs. Resetting them locally prevents a…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the… (+21 more)

### Community 26 - "test_nac_provider.py"
Cohesion: 0.09
Nodes (31): _ClientWithNoNumberVerificationApi, _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeNumberVerificationBareToken, FakeNumberVerificationRejectsNonce, FakeReachability (+23 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.23
Nodes (14): create_session(), end_session(), get_session(), delete, get, post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.… (+6 more)

### Community 29 - "routes_registry.py"
Cohesion: 0.31
Nodes (9): _directory(), get, Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), One institution's claim on a number, with the basis for the claim., RegistryLookupResponse (+1 more)

### Community 30 - "test_outcomes_contract.py"
Cohesion: 0.15
Nodes (33): _as_the_merchant(), _extra_merchant_key(), _fresh_headers(), _get(), fixture, P5 — collect outcomes before calibrating scores. Merchants report what actually…, P3's own dimension is derived, not reported through this endpoint — reporting…, This file fires many requests against a couple of fixed keys; do not leak that… (+25 more)

### Community 31 - "ConsentStore"
Cohesion: 0.19
Nodes (9): ConsentRecord, ConsentStore, _now(), _owner_hash(), datetime, Drop terminal records once their retention window has passed. Caller holds the…, Lock-safe entry point for `app.retention`'s periodic sweeper., Claim this consent for exactly one callback. A true compare-and-swap. The old… (+1 more)

### Community 32 - "routes_consent.py"
Cohesion: 0.14
Nodes (25): _accept_quality(), complete_number_verification(), consent_complete_page(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), _prefers_html() (+17 more)

### Community 33 - "test_s2_stream_isolation.py"
Cohesion: 0.20
Nodes (12): subscriber_count(), asyncio, S2 — the SSE stream must be authenticated and must not cross tenants., End to end through the HTTP surface, not just the bus., A disconnect that is never noticed must not pin memory forever (S12)., The finding, verbatim: `curl -N /v1/console/stream` harvested everything., A background emit with no owner must not fan out to a real tenant., test_a_subscriber_never_sees_an_event_emitted_for_nobody() (+4 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.07
Nodes (57): Result, RequestContext, VerificationRequest, Receive the events emitted for `owner`, and only those., subscribe(), capability_for(), load_capabilities(), preflight() (+49 more)

### Community 35 - "store.py"
Cohesion: 0.12
Nodes (30): owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainAlreadyExists, ChainRecord, get(), get_async() (+22 more)

### Community 36 - "signing.py"
Cohesion: 0.19
Nodes (19): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+11 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 38 - "routes_verified_caller.py"
Cohesion: 0.23
Nodes (14): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+6 more)

### Community 39 - "challenges.py"
Cohesion: 0.13
Nodes (30): AttemptNotFound, AttemptNotPending, create_attempt(), _expire_if_due(), _finalize_or_replay(), IdempotencyKeyConflict, _now(), _owner() (+22 more)

### Community 40 - "rate_limit.py"
Cohesion: 0.16
Nodes (21): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+13 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.10
Nodes (17): ConsentCapacityExceeded, RuntimeError, A live consent cannot be retained without displacing another one., asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files., /docs, /redoc and /openapi.json all answered 200 unauthenticated. (+9 more)

### Community 42 - "NacProvider"
Cohesion: 0.12
Nodes (12): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., describe(), main() (+4 more)

### Community 43 - "test_fake_operator.py"
Cohesion: 0.21
Nodes (21): makes_billable_calls(), Can a request cause a real, paid CAMARA call to leave this process? Keyed on…, FakeNacProvider, Offline fake Number Verification provider (P4a, ISNAD_PROVIDER=nac_fake). Talks…, _decide(), _operator_client(), _patch_to_asgi(), AsyncClient (+13 more)

### Community 44 - "test_s7_quota_and_key_mode.py"
Cohesion: 0.15
Nodes (17): InsecureVaultKey, The signing key is readable by someone other than its owner., RuntimeError, This owner already has as many live sessions as it is allowed., SessionQuotaExceeded, asyncio, S7 — the two unbounded amplifiers: session quota, and the key file mode., `_sessions` was never pruned, so it grew for the life of the process. (+9 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.13
Nodes (22): Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The window is the spoofing opportunity: while an announcement stands, a call…, Matching the caller alone would let one genuine announcement verify a burst of…, The load-bearing test of this whole feature. Caller ID is spoofable, so a…, The mismatch that is real: this number is Demo Bank's, and the caller says they…, "Arab Bank" is not in the registry, so the registry knows nothing about whether…, The shape that broke: every extra honest word made condemnation more likely,…, Absence from a hand-curated registry is not evidence. Almost every number in… (+14 more)

### Community 47 - "test_proof_shares.py"
Cohesion: 0.17
Nodes (28): _as_the_merchant(), _create(), _extra_merchant_key(), _fresh_headers(), fixture, I13 — expiring reviewer links with explicit disclosure scope. A proof share is…, The token must be recoverable for a replay, but never sit in the database in…, _reset_limiters() (+20 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "test_merchant_pilot.py"
Cohesion: 0.14
Nodes (41): _challenge_handler(), _client(), _login(), _make_allowed_flow(), _make_challenged_flow(), _patch_isnad(), fixture, Request (+33 more)

### Community 50 - "MockProvider"
Cohesion: 0.08
Nodes (46): build_investigator(), Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, FaultInjectingProvider, ValueError, I4 — a lab-only fault-injecting provider wrapper. Wraps a real provider (the… (+38 more)

### Community 51 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 52 - "velocity.py"
Cohesion: 0.09
Nodes (25): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, ScreenEventRow, _owner(), purge_older_than() (+17 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "test_s5_subject_binding.py"
Cohesion: 0.18
Nodes (14): _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve., test_a_chain_issued_for_a_does_not_verify_against_b() (+6 more)

### Community 55 - "test_s6_vault_keys.py"
Cohesion: 0.12
Nodes (16): MissingVaultKey, RuntimeError, The signing key was expected on disk and was not there., S6 — verification must use the key that signed, and survive a restart., The finding, verbatim: config.py made vault_key_path CWD-relative. A process…, The acceptance criterion: issue, restart, verify., The route returned rec.public_key while verifying with its own., Otherwise a row with a self-consistent key and signature verifies. (+8 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.18
Nodes (11): A changed SIM should start an investigation., A receipt that can be challenged, too, Every check has a job, Evidence you can rerun, Isnad · إسناد, One integration, an explainable action, One warning. Two very different checkouts., Simulated answers. The same investigation. (+3 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "PolicyEngine"
Cohesion: 0.07
Nodes (10): PolicyEngine, Path, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain., Checks to attempt before this signal alone may carry a DECLINE. The counterpart… (+2 more)

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
Cohesion: 0.13
Nodes (24): Base, IdempotencyRecordRow, ProofShareRow, A durable record of one merchant write, keyed by owner + operation + the…, An expiring reviewer link onto one chain's separately issued attestation (I13)…, create_share(), _decrypt(), _encrypt() (+16 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (21): logodds_to_p(), BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy() (+13 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "fake_operator/app.py"
Cohesion: 0.12
Nodes (23): delete, get, Request, Response, Public, bounded, unauthenticated by design: the token in the path IS the…, read_proof_share(), revoke_proof_share(), _AccessToken (+15 more)

### Community 66 - "P4a implementation record"
Cohesion: 0.17
Nodes (12): A real defect found during browser verification, not just written to pass tests, Browser evidence, actually performed, Consent-contract defects fixed first (before the OAuth work), Contract decision, checked against the source before building, Files changed, ID-token validation, shared rather than duplicated, Known gaps, stated plainly, P4a implementation record (+4 more)

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (57): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, build_report(), EvidenceCase (+49 more)

### Community 68 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 69 - "Action"
Cohesion: 0.07
Nodes (35): deterministic(), The always-available narrative. No model, no key, no network., EvidenceLink, _now(), datetime, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA… (+27 more)

### Community 70 - "_directory"
Cohesion: 0.13
Nodes (15): _directory(), Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., Institutions own ranges, not single numbers. A registry of exact numbers alone…, test_a_published_inbound_only_line_is_flagged_as_never_outbound() (+7 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "_two_banks"
Cohesion: 0.18
Nodes (11): The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, test_a_bare_generic_word_is_not_a_match(), test_a_caller_who_describes_themselves_more_fully_still_matches(), test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution(), test_an_alias_is_matched_whole_and_not_merged_with_the_name() (+3 more)

### Community 73 - "vault.py"
Cohesion: 0.24
Nodes (9): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+1 more)

### Community 74 - "outcomes.py"
Cohesion: 0.16
Nodes (22): MerchantOutcomeEventRow, One merchant-reported outcome on an owned chain — order status or fraud…, challenge_execution_summary(), current_and_timeline(), _current_head(), DimensionAlreadyLabelled, _event_dict(), IdempotencyKeyConflict (+14 more)

### Community 75 - "emit"
Cohesion: 0.21
Nodes (19): events_after(), has_gap(), Persisted events for this owner's run, strictly newer than `after`, in order.…, True when a client's own cursor cannot be trusted: it claims to have already…, emit(), Deliver an event to the subscribers belonging to the current owner. Persisted…, _owner(), asyncio (+11 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "test_acts.py"
Cohesion: 0.27
Nodes (11): _investigator(), asyncio, End-to-end scenario tests — the demo's three acts run the real engine. These…, Act I — clean signup: one silent Number Verification clears them., Act II — SIM swapped 41 min ago, new device, wrong location -> DECLINE., Act III — no merchant history, but years of SIM tenure clear them -> ALLOW.…, The agent should not run all seven APIs when a verdict is reached cheaply., test_act1_kill_the_otp_allows_silently() (+3 more)

### Community 78 - "routes_proof_shares.py"
Cohesion: 0.15
Nodes (15): get_outcomes(), _owned_chain(), get, post, Ownership only — no decision gate. Unlike P3, an outcome may be reported on any…, report_outcome(), create_proof_share(), post (+7 more)

### Community 79 - "P5 implementation record"
Cohesion: 0.20
Nodes (10): Browser evidence (this session, real processes, not mocked), Contract decisions made explicit before writing code, Idempotency: durable, plus its own audit columns, Insert-then-single-transaction, not two-phase, Known gaps, Merchant pilot harness, P5 implementation record, Retention (+2 more)

### Community 80 - "test_s9_consent_replay.py"
Cohesion: 0.17
Nodes (15): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., The acceptance criterion: a replayed callback returns 409. The attacker's path:…, by_state() used to keep resolving after use. (+7 more)

### Community 81 - "P1 and P2 implementation records"
Cohesion: 0.67
Nodes (3): P1 and P2 implementation records, P2 implementation — 6 Sep (follow-up session), Preserved P1 implementation record

### Community 82 - "routes_verify.py"
Cohesion: 0.09
Nodes (16): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., _idempotency_state_response(), Replay a completed state or reject a conflicting/in-flight one. One cache entry…, The one call: 'Can I trust this interaction?' -> ALLOW / CHALLENGE / DECLINE…, verify() (+8 more)

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
Nodes (21): Choice, LLMPlanner, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as… (+13 more)

### Community 89 - "database.py"
Cohesion: 0.13
Nodes (13): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for (+5 more)

### Community 90 - "test_receipt_download.py"
Cohesion: 0.22
Nodes (11): CompletedProcess, chain_id(), fixture, Path, I7 — portable receipt verification. The existing GET /v1/receipts/{chain_id}…, _run_verify_script(), test_a_malformed_bundle_is_rejected_not_crashed(), test_the_offline_script_accepts_a_matching_trusted_key() (+3 more)

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 92 - "enums.py"
Cohesion: 0.11
Nodes (19): detail_for(), The only sentences an evidence link may carry, and where each one comes from.…, The age window this action's question covered, if it has one. Mirrors the…, The max_age the swap checks are actually called with., The sentence for a signal, derived from the response and our parameters., _window(), window_hours(), parametrize (+11 more)

### Community 101 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 110 - "get_chain"
Cohesion: 0.29
Nodes (7): get_chain(), get, Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, The public key anyone can use to independently verify a chain signature., vault_public_key(), verify_chain()

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 120 - "routes_privacy.py"
Cohesion: 0.22
Nodes (9): _human(), posture(), privacy_page(), get, HTMLResponse, Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page… (+1 more)

### Community 121 - "What the risk score means"
Cohesion: 0.50
Nodes (4): Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability

### Community 125 - "schemas.py"
Cohesion: 0.08
Nodes (40): create_challenge(), get_challenge_timeline(), _owned_challenged_chain(), get, post, The owned followup history for a chain. Available on any decision — empty on…, The chain this caller owns, or the same 404 a missing one gets (P3 mirrors…, Open a followup on a CHALLENGE decision. Refused on any other decision: a… (+32 more)

### Community 126 - "test_run_replay_endpoint.py"
Cohesion: 0.25
Nodes (8): _extra_merchant_key(), asyncio, fixture, I14's HTTP surface: GET /v1/console/runs/{run_id}/events. Authorized the same…, _reset_limiters(), _seed_run(), test_a_foreign_key_sees_nothing_for_someone_elses_run(), test_the_owner_can_replay_their_own_run()

### Community 127 - "InMemoryCache"
Cohesion: 0.16
Nodes (8): InMemoryCache, Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one., Drop what has expired; if nothing has, drop the oldest inserted., test_in_memory_cache_ttl(), Held entries for 24h and was swept only on a get of the same key., test_the_idempotency_cache_is_bounded()

### Community 128 - "run_reverse"
Cohesion: 0.17
Nodes (16): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), asyncio, REGISTRY_MATCH_UNANNOUNCED is zeroed in policy.yaml on purpose., Act IV must not regress: adding local evidence to the chain must not rescue a…, The combination that matters: the bank's real number, announced, but the…, Both tiers consume. A client uses Tier 1 OR Tier 2 for a given call, and…, The standalone reverse-verify path must keep working — it is a public API in… (+8 more)

### Community 129 - "run_events.py"
Cohesion: 0.31
Nodes (9): A durably persisted copy of one SSE event, keyed by (owner, run_id, sequence),…, RunEventRow, _allowlisted_body(), _now(), persist_event(), purge_older_than(), datetime, Durable event journal for one investigation run (I14). `persist_event()` is… (+1 more)

### Community 130 - "GreedyPlanner"
Cohesion: 0.09
Nodes (20): get_planner(), GreedyPlanner, Planner, Protocol, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, _engine() (+12 more)

### Community 132 - "test_false_decline_baseline.py"
Cohesion: 0.21
Nodes (11): _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and…, The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean line'.…, Guards against a baseline so blunt it declines everyone, which would make the…, The whole thesis is that these two rules disagree about an unanswered check. If…, test_a_clean_chain_declines_under_neither_baseline(), test_every_generated_case_differs_from_clean_in_exactly_one_check() (+3 more)

### Community 133 - "SessionManager"
Cohesion: 0.10
Nodes (28): SessionStatus, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, _csv(), Scripted evidence, except for the links deliberately made real. Every winner…, get_provider(), Select the evidence provider from config. ISNAD_PROVIDER=mock -> scripted… (+20 more)

### Community 134 - "counterfactual.py"
Cohesion: 0.31
Nodes (8): Alternative, Figure, A number that knows where it came from (T5). Provenance travels with the value…, What the same decision would have cost as one SMS OTP (T5)., compute(), country_for(), Longest-matching E.164 prefix, or DEFAULT., Build the counterfactual from the finished chain.

### Community 135 - "P3 implementation record"
Cohesion: 0.22
Nodes (9): Browser evidence (this session, real processes, not mocked), CHALLENGE followups, in their own tables, Idempotency, durable rather than in-memory, Insert-only `store.save` (step 1), Known gaps, Merchant pilot harness: "Continue merchant verification", P3 implementation record, Retention and posture (+1 more)

### Community 136 - "test_reverse.py"
Cohesion: 0.25
Nodes (6): asyncio, Reverse Isnad — verify an inbound caller to the customer (Act IV)., The real institution line is network-attested -> TRUST (ALLOW)., A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)., test_genuine_caller_is_trusted(), test_spoofed_caller_is_rejected()

### Community 137 - "verify_receipt.py"
Cohesion: 0.36
Nodes (8): BundleError, load_bundle(), load_trusted_keys(), main(), Path, ValueError, I7 — verify a downloaded Isnad receipt entirely offline. Verifies the exact…, verify()

### Community 138 - "test_consent_contract.py"
Cohesion: 0.17
Nodes (16): Create a keyed, domain-separated commitment to a request. A bare SHA-256 of…, request_commitment(), P4a — consent-contract defects fixed before building the live-consent journey.…, A record that times out without ever being touched must still get a…, _sweep() used to delete a terminal record the instant any create() ran. Pre-…, Retention is bounded, not indefinite: it must eventually go away., Before P4a, `state` was the only random value; nonce did not exist., A mutable request object must not change the subject/context after approval.… (+8 more)

### Community 139 - "_announce"
Cohesion: 0.13
Nodes (15): _announce(), The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call…, An institution announcing a call is telling this service who it is about to…, A non-spending read is for a party that already holds the use. Anyone else gets…, The cap is per announcement, not a lockout. A bank that really is calling twice…, test_a_published_inbound_only_number_cannot_be_announced_from() (+7 more)

### Community 140 - "build_evidence_comparison.py"
Cohesion: 0.46
Nodes (7): build_report(), _code_revision(), _load(), main(), _policy_digest(), Path, I3 — evidence budget and decision comparison, combined into one report. Reuses…

### Community 141 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 144 - "sonnet_review_regressions.py"
Cohesion: 0.29
Nodes (12): add_flow(), client_for(), asyncio, Offline review probes: assertions describe required behavior and fail on…, test_review_consent_owned_read_enforces_terminal_retention(), test_review_foreign_operator_session_cannot_read_flow(), test_review_harness_read_enforces_flow_retention(), test_review_invalid_context_returns_422_instead_of_500() (+4 more)

### Community 145 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 146 - "owner_hash"
Cohesion: 0.14
Nodes (18): owner_hash(), _as_the_merchant(), fixture, _as_the_merchant(), fixture, S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both. (+10 more)

### Community 147 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 148 - "6. MENA Ignite submission priorities — reviewed 6 September 2026"
Cohesion: 0.20
Nodes (10): 6. MENA Ignite submission priorities — reviewed 6 September 2026, H0 — Confirm the submission contract before building more, H1 — Make the AI contribution visible and measurable, H2 — Show verifiable Nokia NaC integration, with precise scope, H2a — Live API calls to Nokia's hosted simulator, H3 — Make one MENA customer problem specific, H4 — Demonstrate the benefit without hiding the tradeoff, H5 — Ship one coherent, remotely accessible demonstration (+2 more)

### Community 149 - "9. Sonnet code review — 6 September 2026"
Cohesion: 0.25
Nodes (8): 9. Sonnet code review — 6 September 2026, R1 — Bind merchant harness flows to their creating session (high), R2 — Recover completed verification after a lost response (high), R3 — Enforce harness flow retention on reads and while idle (medium), R4 — Enforce terminal consent retention without new traffic (medium), R5 — Remove the unvalidated SDK token-exchange branch (high, conditional), R6 — Freeze outcome operations for safe retries (high), R7 — Validate flow context before constructing upstream input (medium)

### Community 150 - "merchant_outcome_report.py"
Cohesion: 0.39
Nodes (7): build_report(), _business_impact_worksheet(), _evidence_cost(), _is_synthetic(), main(), Owner-scoped offline report: has anyone told us what actually happened? (P5)…, I12 step 3: merchant-entered assumptions only, never actual recovered revenue.…

### Community 151 - "test_outcome_report_review_metrics.py"
Cohesion: 0.54
Nodes (7): _owner(), I12 — review metrics and an optional business-impact worksheet, added on top of…, _seed(), test_a_worksheet_with_assumptions_is_report_only(), test_challenge_completion_time_is_averaged_over_completed_attempts(), test_manually_accepted_orders_are_counted(), test_no_worksheet_without_explicit_assumptions()

### Community 152 - "bound_key"
Cohesion: 0.29
Nodes (7): bound_key(), _no_leftover_announcements(), fixture, The suite shares one in-memory database, so an announcement made by one test…, demo-merchant-key, bound to the institution that owns BANK_NUMBER., A registry holding Demo Bank and one other institution. The shipped registry…, two_bank_registry()

### Community 153 - "SlidingWindowLimiter"
Cohesion: 0.20
Nodes (6): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, test_the_limiter_bucket_map_is_bounded(), test_the_window_actually_slides()

### Community 154 - "Isnad — compact handoff"
Cohesion: 0.33
Nodes (6): 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 4. Path to a live product, 5. Code map and working rules, 8. Latest session, Isnad — compact handoff

### Community 156 - "_verdict"
Cohesion: 0.29
Nodes (7): T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., The acceptance criterion: grounded in the chain, not in free text., test_a_question_containing_instructions_changes_no_stored_verdict(), test_the_answer_is_grounded_in_links_that_are_actually_in_the_chain(), test_the_prompt_carries_no_free_text_from_the_chain(), _verdict()

### Community 157 - "._tz_aware"
Cohesion: 0.53
Nodes (3): datetime, field_validator, _reject_naive()

### Community 158 - "test_evidence_comparison.py"
Cohesion: 0.47
Nodes (5): asyncio, I3 — the combined evidence/decision comparison report. Loaded from the script…, test_false_declines_are_counted_only_among_the_innocent_denominator(), test_the_report_carries_both_sources_and_named_denominators(), test_the_report_is_reproducible_across_two_runs()

### Community 161 - "explain_chain"
Cohesion: 0.40
Nodes (5): explain_chain(), post, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature…, verify_chain_subject()

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **137 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+132 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1176 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Action`, `SessionManager`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `IdTokenError`, `merchant_pilot/app.py`, `sonnet_review_regressions.py`, `test_nac_provider.py`, `NaC integration — observed, not assumed`, `enums.py`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `NaC integration — observed, not assumed`, `JUDGE_WALKTHROUGH.md`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `NaC integration — observed, not assumed` connect `NaC integration — observed, not assumed` to `console.html — live agent console`, `NacProvider`, `Phase 2 Agent Runbook`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 81 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 81 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 49 INFERRED edges - model-reasoned connections that need verification._
- **Are the 68 inferred relationships involving `Decision` (e.g. with `Investigator` and `create_challenge()`) actually correct?**
  _`Decision` has 68 INFERRED edges - model-reasoned connections that need verification._