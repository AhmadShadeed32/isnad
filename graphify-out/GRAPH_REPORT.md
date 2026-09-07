# Graph Report - isnad  (2026-09-07)

## Corpus Check
- 269 files · ~947,244 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4048 nodes · 8898 edges · 215 communities (178 shown, 11 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 748 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0f7fb95d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_chain_grade.py
- test_t6_receipt.py
- compare_missing_location_claim
- request_limits.py
- Hypothesis
- Investigator
- _written
- test_velocity.py
- test_presentation.py
- routes_console.py
- IdTokenError
- merchant_pilot/app.py
- test_challenge_contract.py
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- test_outcome_report.py
- test_t4_ask_the_agent.py
- Settings
- VaultSigner
- test_t5_counterfactual.py
- GeminiClient
- velocity.py
- test_judge.py
- test_act7.py
- test_nac_provider.py
- timeline.js
- routes_session.py
- routes_proof_shares.py
- test_outcomes_contract.py
- ConsentStore
- routes_verify.py
- events.py
- VerificationRequest
- Verdict
- signing.py
- test_lab_page.py
- schemas.py
- challenges.py
- main.py
- test_s12_runtime_posture.py
- test_run_replay_endpoint.py
- Action
- SessionManager
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_proof_shares.py
- test_s10_xss_and_headers.py
- test_merchant_pilot.py
- MockProvider
- db/models.py
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
- Result
- test_registry.py
- Phase 2 Agent Runbook
- policy.yaml — the single tuning surface
- routes_lab.py
- outcomes.py
- emit
- test_s14_no_tracked_secrets.py
- get
- 11. UI review and implementation plan — 6 September 2026
- P5 implementation record
- test_s9_consent_replay.py
- P1 and P2 implementation records
- test_nac_demo_probe.py
- PHASE2_HANDOFF.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- LLMPlanner
- database.py
- test_receipt_download.py
- shot
- FlowRecord
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- Recorder
- test_network_conditions.py
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- config.py
- What the risk score means
- routes_reverse.py
- stream_token.py
- InMemoryCache
- network_conditions.py
- run_events.py
- GreedyPlanner
- get_engine
- nac_demo_probe.py
- test_number_recycling.py
- P3 implementation record
- test_consent_contract.py
- verify_receipt.py
- build_investigator
- routes_consent.py
- build_evidence_comparison.py
- test_hardening.py
- test_hybrid_provider.py
- owner_hash
- test_s4_demo_mode.py
- `device_status`
- 3. Recommended app work — not implemented in this documentation pass
- 6. MENA Ignite submission priorities — reviewed 6 September 2026
- 9. Sonnet code review — 6 September 2026
- NaC installed SDK: complete operation index
- test_outcome_report_review_metrics.py
- Isnad: implementation and release runbook
- Decision
- Isnad — implementation handoff
- test_i18n.py
- normalize_level
- test_hypothesis_relevance.py
- test_evidence_comparison.py
- Open findings and concrete fixes
- runner.py
- _delivered
- test_gemini_primary.py
- timing.py
- LoginThrottle
- resolve_key_path
- Code review and hackathon readiness — 6 September 2026
- test_session.py
- build_judge_lab.py
- test_pilot_polling.py
- test_s5_subject_binding.py
- Money
- codebase_review_2026_09_07.py
- _configured_for_llm
- i18n.js
- sonnet_review_regressions.py
- Recording
- validate_period
- get_provider
- `slice`
- 12. Active user requests and implementation plan — 6 September 2026
- SlidingWindowLimiter
- _callback
- Signal → log-odds vocabulary
- `qod`
- Session record — 6–7 September 2026 (runbook gates 0 to 9)
- Checkpoint log
- Nokia API additions and demo call plan
- Isnad user test guide
- fixture
- planner_divergence.py
- Nokia Network as Code contract matrix
- Hosted simulator observations
- ._tz_aware
- `congestion_insights`
- test_low_prior_allow_requires_a_supporting_fact_even_with_stop
- 7. Add the relevant identity extensions, in this order
- `geofencing`
- `kyc`
- `number_verification`
- _check_registry_signature
- NaC integration — observed, not assumed
- `well_known_metadata`
- Current code review — 7 September 2026
- _poll_and_maybe_complete
- `sim_swap`
- test_injection_in_every_free_text_field_changes_no_verdict
- test_a_verification_never_calls_the_congestion_provider
- test_a_level_carries_a_glyph_as_well_as_a_colour
- test_the_panel_never_requests_anything_on_load
- test_the_receipt_reports_the_window_asked_about_not_an_event_age

## God Nodes (most connected - your core abstractions)
1. `Action` - 196 edges
2. `VerificationRequest` - 129 edges
3. `MockProvider` - 110 edges
4. `Decision` - 102 edges
5. `Result` - 102 edges
6. `Hypothesis` - 74 edges
7. `RequestContext` - 73 edges
8. `Verdict` - 71 edges
9. `EvidenceLink` - 70 edges
10. `PolicyEngine` - 70 edges

## Surprising Connections (you probably didn't know these)
- `Demo/production parity — only the provider differs` --references--> `MockProvider`  [EXTRACTED]
  docs/02_API_Build_Plan.md → app/providers/mock.py
- `T3 — rebuild the planner so the agent actually reasons` --references--> `LLMPlanner`  [EXTRACTED]
  docs/PHASE2_AGENT_RUNBOOK.md → app/agent/planner.py
- `test_an_old_receipt_reads_back_with_no_timing_rather_than_a_default_date()` --uses--> `Verdict`  [INFERRED]
  tests/test_swap_timestamps.py → app/chain/models.py
- `test_settings_default_to_gemini()` --uses--> `Settings`  [INFERRED]
  tests/test_gemini_primary.py → app/config.py
- `MockProvider` --implements--> `EvidenceProvider adapter contract`  [EXTRACTED]
  app/providers/mock.py → docs/02_API_Build_Plan.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pitch Video Render Pipeline (narration to encoded cut)** — docs_video_readme_video_build_pipeline, docs_video_timings_spine, docs_video_scene_scenes, docs_video_encode_pipeline, docs_video_readme_narration_anchored_timing [EXTRACTED 1.00]
- **Supply-Chain Pinning and Audit Flow (S8)** — requirements_runtime_pins, requirements_lock_runtime_closure, requirements_dev_toolchain, github_workflows_ci_verify, requirements_network_as_code_pip_defect, setup_bootstrap_venv [EXTRACTED 1.00]
- **Nokia NaC / CAMARA Evidence Capture Catalogue** — docs_nac_sim_swap_capture, docs_nac_device_swap_capture, docs_nac_location_verify_capture, docs_nac_number_verify_capture, docs_nac_reachability_capture, docs_nac_roaming_capture, docs_nac_device_intelligence_capture, docs_nac_step_up_otp_capture, docs_nac_sim_swap_normalized_envelope [INFERRED 0.95]

## Communities (215 total, 11 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.06
Nodes (54): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Is this a clean verdict resting on local evidence alone — or on local evidence…, Chain, ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, logodds_to_p(), p_to_logodds() (+46 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (32): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+24 more)

### Community 2 - "compare_missing_location_claim"
Cohesion: 0.24
Nodes (13): compare_missing_location_claim(), Comparison, NoClaimedLocation, ValueError, I2 — one-fact counterfactual explorer. Changes exactly one input on an existing…, The base scenario has no claimed_location to remove, so there is no single-fact…, asyncio, I2 — one-fact counterfactual explorer. The only supported variant is removing… (+5 more)

### Community 3 - "request_limits.py"
Cohesion: 0.13
Nodes (11): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+3 more)

### Community 4 - "Hypothesis"
Cohesion: 0.08
Nodes (51): _facts(), narrate(), Everything the narrator may see. Enums, numbers, booleans., A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, An offline greedy run and a Gemini run that fell back must not read alike., test_a_no_answer_fallback_names_the_condition_that_allowed_greedy(), test_a_response_or_internal_error_is_not_no_response() (+43 more)

### Community 5 - "Investigator"
Cohesion: 0.22
Nodes (8): Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Attach the operator's date to a swap link. Returns what it cost. Kept out of…, A separate trace row, because it was a separate call. Labelled `enrichment`,…, Which planner produced this run. "llm+greedy" when the run fell back partway…, The event the console renders as the agent's reasoning. The rationale is…

### Community 6 - "_written"
Cohesion: 0.10
Nodes (21): Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and…, An institution may publish a block inside a block — a branch range carved out… (+13 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.13
Nodes (37): distinct_callees(), How many different people this number has been screened against lately.…, _as(), _burst(), _clean(), _engine(), _owner_of(), asyncio (+29 more)

### Community 8 - "test_presentation.py"
Cohesion: 0.08
Nodes (43): present(), Presentation, BaseModel, Project a signed Verdict into a plain-language Presentation. Pure function:…, What a first-time visitor sees. Never signed, never part of `Verdict`, safe to…, _facts_known_to_the_chain(), asyncio, parametrize (+35 more)

### Community 9 - "routes_console.py"
Cohesion: 0.07
Nodes (46): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token. (+38 more)

### Community 10 - "IdTokenError"
Cohesion: 0.09
Nodes (50): fetch_jwks(), IdTokenError, Any, AsyncClient, RuntimeError, ID-token validation shared by every OIDC-based Number Verification path (P4a).…, The id_token is missing, malformed, or fails contract validation. Deliberately…, Validate signature, iss, aud, exp/iat and nonce. Returns the claims. Fails… (+42 more)

### Community 11 - "merchant_pilot/app.py"
Cohesion: 0.13
Nodes (33): ChallengeEventBody, _client_is_private(), create_flow(), create_flow_challenge(), get_capabilities(), lifespan(), logout(), NewFlowRequest (+25 more)

### Community 12 - "test_challenge_contract.py"
Cohesion: 0.13
Nodes (38): _as_the_merchant(), _create(), _extra_merchant_key(), _fresh_headers(), fixture, parametrize, P3 — finish CHALLENGE without rewriting its receipt. A merchant that gets…, Not an in-memory cache (P4a's rule for /v1/verify explicitly does not apply… (+30 more)

### Community 13 - "announce.py"
Cohesion: 0.10
Nodes (32): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+24 more)

### Community 14 - "Directory"
Cohesion: 0.08
Nodes (23): Directory, _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",… (+15 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (27): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+19 more)

### Community 17 - "test_outcome_report.py"
Cohesion: 0.32
Nodes (13): _as_the_merchant(), _owner(), fixture, P5's offline report: denominators and unknowns must stay honest. Loaded from…, A challenge PASS is not a fraud label. Only an explicit CONFIRMED_LEGITIMATE…, _report(), _seed(), test_a_passed_challenge_alone_does_not_count_as_a_false_decline_fix() (+5 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (17): The sentence a merchant reads. It has to name the links the decision actually…, chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for. (+9 more)

### Community 19 - "Settings"
Cohesion: 0.10
Nodes (35): clear(), check_startup_posture(), InsecureConfiguration, RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Refuse to start a billable deployment with no key or a published one. Only…, Settings (+27 more)

### Community 20 - "VaultSigner"
Cohesion: 0.07
Nodes (30): InsecureVaultKey, MissingVaultKey, RuntimeError, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key was expected on disk and was not there. (+22 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.08
Nodes (29): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+21 more)

### Community 23 - "velocity.py"
Cohesion: 0.09
Nodes (24): is_high_velocity(), is_high_velocity_async(), _owner(), purge_older_than(), The tenant this request belongs to, set at the auth boundary (S2)., Note that this caller was screened against this callee, for this tenant., (over_threshold, observed, threshold). Threshold 0 disables the check., Drop events outside any window anyone will ask about. This table exists to… (+16 more)

### Community 24 - "test_judge.py"
Cohesion: 0.16
Nodes (13): judge_page(), get, HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that… (+5 more)

### Community 25 - "test_act7.py"
Cohesion: 0.09
Nodes (24): _no_leftover_announcements(), fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not…, Act VII exercises several authenticated stage controls per test; their request… (+16 more)

### Community 26 - "test_nac_provider.py"
Cohesion: 0.09
Nodes (31): _ClientWithNoNumberVerificationApi, _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeNumberVerificationBareToken, FakeNumberVerificationRejectsNonce, FakeReachability (+23 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.30
Nodes (11): create_session(), end_session(), get_session(), get, post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.…, simulate_swap() (+3 more)

### Community 29 - "routes_proof_shares.py"
Cohesion: 0.11
Nodes (21): get_outcomes(), _owned_chain(), get, post, Ownership only — no decision gate. Unlike P3, an outcome may be reported on any…, report_outcome(), create_proof_share(), get (+13 more)

### Community 30 - "test_outcomes_contract.py"
Cohesion: 0.15
Nodes (33): _as_the_merchant(), _extra_merchant_key(), _fresh_headers(), _get(), fixture, P5 — collect outcomes before calibrating scores. Merchants report what actually…, P3's own dimension is derived, not reported through this endpoint — reporting…, This file fires many requests against a couple of fixed keys; do not leak that… (+25 more)

### Community 31 - "ConsentStore"
Cohesion: 0.19
Nodes (9): ConsentRecord, ConsentStore, _now(), _owner_hash(), datetime, Drop terminal records once their retention window has passed. Caller holds the…, Lock-safe entry point for `app.retention`'s periodic sweeper., Claim this consent for exactly one callback. A true compare-and-swap. The old… (+1 more)

### Community 32 - "routes_verify.py"
Cohesion: 0.08
Nodes (32): explain_chain(), get_chain(), _idempotency_state_response(), get, post, Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, Ask the agent about a decision it already made (T4). Grounded in the stored… (+24 more)

### Community 33 - "events.py"
Cohesion: 0.16
Nodes (15): mask_phone(), Keep console events useful without broadcasting a full phone number., _redact(), subscriber_count(), asyncio, S2 — the SSE stream must be authenticated and must not cross tenants., End to end through the HTTP surface, not just the bus., A disconnect that is never noticed must not pin memory forever (S12). (+7 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.08
Nodes (44): RequestContext, VerificationRequest, capability_for(), load_capabilities(), preflight(), I10 — provider capability and consent readiness. Reads the authored…, Local-only readiness: {"ready": bool, "reason": str | None}., main() (+36 more)

### Community 35 - "Verdict"
Cohesion: 0.11
Nodes (33): Verdict, owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainAlreadyExists, ChainRecord, get() (+25 more)

### Community 36 - "signing.py"
Cohesion: 0.19
Nodes (19): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+11 more)

### Community 37 - "test_lab_page.py"
Cohesion: 0.04
Nodes (23): fixture, The judge lab page (I1/I2/I3/I4/I9) — a reader for recorded runs. The page's…, The escaping the page does to survive the HTML parser must be invisible to…, I9's bound: the only input is which recording to show. If a POST, or a…, Not just the router — nothing reachable under /lab accepts a body., Replay is a local scrub over an embedded list. A fetch here would be the first…, I1 step 2: a heuristic described as reasoning is worse than a heuristic., P2's receipt-table lesson, applied before it can be repeated here. (+15 more)

### Community 38 - "schemas.py"
Cohesion: 0.07
Nodes (52): create_challenge(), get_challenge_timeline(), _owned_challenged_chain(), get, post, The owned followup history for a chain. Available on any decision — empty on…, The chain this caller owns, or the same 404 a missing one gets (P3 mirrors…, Open a followup on a CHALLENGE decision. Refused on any other decision: a… (+44 more)

### Community 39 - "challenges.py"
Cohesion: 0.14
Nodes (28): AttemptNotFound, AttemptNotPending, create_attempt(), _expire_if_due(), _finalize_or_replay(), IdempotencyKeyConflict, _now(), _owner() (+20 more)

### Community 40 - "main.py"
Cohesion: 0.06
Nodes (44): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+36 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.08
Nodes (24): ConsentCapacityExceeded, RuntimeError, A live consent cannot be retained without displacing another one., database_ready(), A readiness probe that performs a real round trip to the database., create_app(), lifespan(), FastAPI (+16 more)

### Community 42 - "test_run_replay_endpoint.py"
Cohesion: 0.08
Nodes (18): _extra_merchant_key(), fixture, I14's HTTP surface: GET /v1/console/runs/{run_id}/events. Authorized the same…, Sequences restart per run, so a previous run's numbers must not suppress this…, I14's bound: the journal resumes the record of a run, never the run., The journal's allowlist excludes provider prose on purpose, so a replayed…, Every field the journal may not hold goes through `val`, which names the…, `detail` is the one field on an evidence event that an operator writes.… (+10 more)

### Community 43 - "Action"
Cohesion: 0.06
Nodes (63): deterministic(), The always-available narrative. No model, no key, no network., Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, normalize(), Record whether the operator's two answers agree, without resolving it. The…, Turn one raw provider value into metadata, or into an explicit unknown. Every…, with_window_agreement() (+55 more)

### Community 44 - "SessionManager"
Cohesion: 0.12
Nodes (20): _now(), datetime, RuntimeError, This owner already has as many live sessions as it is allowed., Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+12 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.06
Nodes (60): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), _announce(), bound_key(), _no_leftover_announcements(), asyncio, fixture, Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA… (+52 more)

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
Cohesion: 0.10
Nodes (25): Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, The mock's own `retrieve-date`, with the same contract as the real one. It is a…, A scripted reading, including the two shapes a UI most often gets wrong:…, FaultInjectingProvider, ValueError (+17 more)

### Community 51 - "db/models.py"
Cohesion: 0.12
Nodes (15): Base, ChallengeAttemptRow, ChallengeEventRow, ProofShareRow, One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, One CHALLENGE followup: a merchant re-verifying a customer out of band after a…, One merchant-reported result against a `ChallengeAttemptRow`. Append-only. A… (+7 more)

### Community 52 - "run_case"
Cohesion: 0.19
Nodes (15): ValueError, I9 — judge-controlled scenario challenge. A small, versioned, authored case set…, The requested case id is not in the authored set — reject before doing any…, A reproducible shuffle of the case set — same seed, same order, always., run_case(), seeded_order(), UnknownCase, asyncio (+7 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "test_review_regressions.py"
Cohesion: 0.13
Nodes (29): asyncio, parametrize, Idle retention and one trust-session binding per merchant order., test_completed_phone_expires_without_a_request(), test_idle_cleanup_and_shutdown(), test_retention_must_be_positive(), test_terminal_reads_remove_authorization_material(), test_trust_session_binding_is_not_replaced() (+21 more)

### Community 55 - "run_scenario"
Cohesion: 0.14
Nodes (27): ValueError, Run the named scenario's fixture, or `request_override` (a full…, run_scenario(), UnknownScenario, asyncio, I1's shared runner: deterministic, isolated, offline investigation replays. No…, `detail` on the NaC path is operator-supplied text, and these artifacts are…, The offline guarantee is the lab's whole claim: its comparisons are only… (+19 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.25
Nodes (8): API example, Deployment boundaries and next work, Features and integration status, How the engine works, Isnad · إسناد, Quick start, Repository and configuration, Testing and reproducible evidence

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "PolicyEngine"
Cohesion: 0.07
Nodes (11): PolicyEngine, What one extra provider operation costs, in the same budget units. Missing…, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., The checks that can move this hypothesis, in either direction. Empty for…, What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain. (+3 more)

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
Cohesion: 0.18
Nodes (18): create_share(), _decrypt(), _encrypt(), _fernet(), IdempotencyKeyConflict, _now(), _owner(), purge_expired_shares() (+10 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.16
Nodes (20): BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy(), load_dataset() (+12 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "test_fake_operator.py"
Cohesion: 0.11
Nodes (36): makes_billable_calls(), Can a request cause a real, paid CAMARA call to leave this process? Keyed on…, FakeNacProvider, _AccessToken, _AuthCode, authorize(), authorize_decide(), discovery() (+28 more)

### Community 66 - "P4a implementation record"
Cohesion: 0.17
Nodes (12): A real defect found during browser verification, not just written to pass tests, Browser evidence, actually performed, Consent-contract defects fixed first (before the OAuth work), Contract decision, checked against the source before building, Files changed, ID-token validation, shared rather than duplicated, Known gaps, stated plainly, P4a implementation record (+4 more)

### Community 67 - "init_db"
Cohesion: 0.05
Nodes (66): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, build_report(), EvidenceCase (+58 more)

### Community 68 - "NacProvider"
Cohesion: 0.09
Nodes (18): _bounded(), NacProvider, Any, Exception, One extra operator call: `retrieve-date` for a swap that was checked. Separate…, A 4xx is the operator refusing; anything else is not a refusal., One create. Returns the operator's own id, which get/delete take., Both bounds absent asks for the forecast; both present asks history. (+10 more)

### Community 69 - "Result"
Cohesion: 0.07
Nodes (41): EvidenceLink, _now(), datetime, One attested link in the chain — the normalized result of one CAMARA call.…, Result, _fact(), A deterministic, plain-language projection of an already-signed Verdict. P2…, One human sentence for a link, traceable to that exact link. `link.api` and… (+33 more)

### Community 70 - "test_registry.py"
Cohesion: 0.07
Nodes (35): _directory(), The number registry — which published numbers belong to which institution. The…, Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., The bug this replaced: every word of the claim had to be indexed, so the more… (+27 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 73 - "routes_lab.py"
Cohesion: 0.13
Nodes (23): _embed(), lab_bundle(), lab_page(), _live_identity(), get, HTMLResponse, JSONResponse, Request (+15 more)

### Community 74 - "outcomes.py"
Cohesion: 0.16
Nodes (22): MerchantOutcomeEventRow, One merchant-reported outcome on an owned chain — order status or fraud…, challenge_execution_summary(), current_and_timeline(), _current_head(), DimensionAlreadyLabelled, _event_dict(), IdempotencyKeyConflict (+14 more)

### Community 75 - "emit"
Cohesion: 0.21
Nodes (19): events_after(), has_gap(), Persisted events for this owner's run, strictly newer than `after`, in order.…, True when a client's own cursor cannot be trusted: it claims to have already…, emit(), Deliver an event to the subscribers belonging to the current owner. Persisted…, _owner(), asyncio (+11 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "get"
Cohesion: 0.39
Nodes (9): capabilities_page(), dashboard(), flow_page(), login(), login_page(), get, HTMLResponse, RedirectResponse (+1 more)

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

### Community 82 - "test_nac_demo_probe.py"
Cohesion: 0.08
Nodes (54): Client, _configured_key(), output(), fixture, parametrize, Request, Response, Offline tests for the bounded simulator runner. Nothing here makes an external… (+46 more)

### Community 83 - "PHASE2_HANDOFF.md"
Cohesion: 0.31
Nodes (3): Isnad — start here, Answers worth rehearsing, The 90-second Isnad demo

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

### Community 88 - "LLMPlanner"
Cohesion: 0.08
Nodes (21): GeminiNoResponse, No model answer arrived, as distinct from a returned invalid answer., Choice, effective_planner(), LLMPlanner, Observation, Planner, PlannerResponse (+13 more)

### Community 89 - "database.py"
Cohesion: 0.16
Nodes (13): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for (+5 more)

### Community 90 - "test_receipt_download.py"
Cohesion: 0.12
Nodes (17): CompletedProcess, Path, I7 — portable receipt verification. The existing GET /v1/receipts/{chain_id}…, The one mistake that would make an honestly-signed receipt look tampered:…, A download assembled from the rendered summary would omit exactly the fields…, The receipt a reader most needs to keep and check elsewhere is the one that did…, I7 step 4: pseudonymous is not anonymous, and a downloaded file cannot be…, _run_verify_script() (+9 more)

### Community 91 - "shot"
Cohesion: 0.06
Nodes (55): browser(), _free_port(), judge(), page(), problems(), fixture, Path, A real browser against a real server, in an isolated instance. These tests… (+47 more)

### Community 92 - "FlowRecord"
Cohesion: 0.15
Nodes (7): FlowRecord, FlowStore, _now(), datetime, Internal, unauthorized lookup — background completion polling only. Every…, R1 + R3: sweeps expired flows first (retention enforced on every read, not only…, SessionStore

### Community 101 - "Recorder"
Cohesion: 0.08
Nodes (45): api(), no_backoff(), fixture, parametrize, Request, Response, Wire-contract tests over the *installed* Network as Code SDK.…, `null` means no date was returned, not "never swapped". (+37 more)

### Community 110 - "test_network_conditions.py"
Cohesion: 0.07
Nodes (42): Network conditions: information beside a decision, never inside one. The tests…, A reading produced by MockProvider is a fixture this repository wrote.…, The portal says Simulator. Nothing about a 200 changes that., A 4xx is an answer: nothing was created, so nothing needs reconciling., An id we cannot read, delete or match a callback to is not one to activate:…, Nokia documents the subscription as a prerequisite for a query., The host is ours and only ours — a destination supplied by a request would let…, Owner isolation was enforced and this was not, so one merchant could subscribe… (+34 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 120 - "config.py"
Cohesion: 0.15
Nodes (21): _directory(), get, Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), _directory(), pre_announce() (+13 more)

### Community 121 - "What the risk score means"
Cohesion: 0.50
Nodes (4): Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability

### Community 125 - "routes_reverse.py"
Cohesion: 0.25
Nodes (10): get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), Any, Create a keyed, domain-separated commitment to a request. A bare SHA-256 of…, request_commitment() (+2 more)

### Community 126 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 127 - "InMemoryCache"
Cohesion: 0.09
Nodes (11): Cache, get_cache(), InMemoryCache, Protocol, Redis-backed cache for token caching + idempotency across instances., Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one. (+3 more)

### Community 128 - "network_conditions.py"
Cohesion: 0.10
Nodes (42): NetworkConditionEventRow, NetworkConditionSubscriptionRow, One congestion subscription this service owns at the operator (gate 6). Network…, One congestion notification delivered to our callback. Deduplicated by…, accept_event(), _active_counts(), as_public(), callback_url_for() (+34 more)

### Community 129 - "run_events.py"
Cohesion: 0.13
Nodes (20): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, _allowlisted_body(), _now(), persist_event(), purge_older_than(), datetime, Durable event journal for one investigation run (I14). `persist_event()` is… (+12 more)

### Community 130 - "GreedyPlanner"
Cohesion: 0.08
Nodes (25): get_planner(), GreedyPlanner, Deterministic evidence selection: pick the highest information-per-cost action…, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Gemini by default; explicit greedy mode is for offline runs., A planner that opens on the SIM swap, as the LLM planner is free to do. This is…, _SwapFirstPlanner, The loop must end and still produce a signed verdict. (+17 more)

### Community 132 - "get_engine"
Cohesion: 0.12
Nodes (16): get_engine(), Path, Load the policy once and reuse it — avoids re-reading/parsing YAML per request., Regression tests for audit fixes: engine caching + auth hardening., test_engine_is_cached(), _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and… (+8 more)

### Community 133 - "nac_demo_probe.py"
Cohesion: 0.08
Nodes (39): NetworkAsCodeApi, main(), Export the installed SDK's public contracts without making network requests.…, schema_for(), short(), wire_contract(), build_client(), _error_code() (+31 more)

### Community 134 - "test_number_recycling.py"
Cohesion: 0.08
Nodes (36): date, _engine(), _link(), fixture, parametrize, Number Recycling: continuity checked before stored trust is reused. The check…, It is a definite answer, not a hole in the chain: the receipt must not say the…, No prior verification is a reason not to ask, not a reason to guess a date. A… (+28 more)

### Community 135 - "P3 implementation record"
Cohesion: 0.22
Nodes (9): Browser evidence (this session, real processes, not mocked), CHALLENGE followups, in their own tables, Idempotency, durable rather than in-memory, Insert-only `store.save` (step 1), Known gaps, Merchant pilot harness: "Continue merchant verification", P3 implementation record, Retention and posture (+1 more)

### Community 136 - "test_consent_contract.py"
Cohesion: 0.19
Nodes (14): P4a — consent-contract defects fixed before building the live-consent journey.…, A record that times out without ever being touched must still get a…, _sweep() used to delete a terminal record the instant any create() ran. Pre-…, Retention is bounded, not indefinite: it must eventually go away., Before P4a, `state` was the only random value; nonce did not exist., A mutable request object must not change the subject/context after approval.…, Every terminal transition must clear the token; deny() did not. deny() only…, _request() (+6 more)

### Community 137 - "verify_receipt.py"
Cohesion: 0.36
Nodes (8): BundleError, load_bundle(), load_trusted_keys(), main(), Path, ValueError, I7 — verify a downloaded Isnad receipt entirely offline. Verifies the exact…, verify()

### Community 138 - "build_investigator"
Cohesion: 0.11
Nodes (31): build_investigator(), Receive the events emitted for `owner`, and only those., subscribe(), asyncio, I1 shared contract, step 6: Investigator accepts an injectable planner and…, Unchanged behavior for every existing caller that does not inject one., test_a_custom_event_sink_receives_every_emission_instead_of_the_bus(), test_the_default_sink_is_still_the_shared_event_bus() (+23 more)

### Community 139 - "routes_consent.py"
Cohesion: 0.15
Nodes (25): accept_quality(), prefers_html(), Whether a caller is a browser navigating or a script fetching. Extracted from…, The q-value Accept assigns to an exact media type (no wildcard credit). A `*/*`…, Whether a browser's Accept header prefers text/html over JSON. Absent,…, complete_number_verification(), consent_complete_page(), _consent_response() (+17 more)

### Community 140 - "build_evidence_comparison.py"
Cohesion: 0.46
Nodes (7): build_report(), _code_revision(), _load(), main(), _policy_digest(), Path, I3 — evidence budget and decision comparison, combined into one report. Reuses…

### Community 141 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 142 - "test_hybrid_provider.py"
Cohesion: 0.13
Nodes (17): _csv(), HybridProvider, Delegate to `fallback`, except for `actions` on `numbers`, which are real., Route the date the same way the boolean was routed. Enriching a scripted…, _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of… (+9 more)

### Community 144 - "owner_hash"
Cohesion: 0.19
Nodes (14): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+6 more)

### Community 145 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 146 - "`device_status`"
Cohesion: 0.08
Nodes (25): `device_status`, `device_status.check_connectivity`, `device_status.check_roaming`, `device_status.create_reachability_subscription`, `device_status.create_reachability_subscription_v08`, `device_status.create_roaming_subscription`, `device_status.create_roaming_subscription_v08`, `device_status.create_subscription` (+17 more)

### Community 147 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 148 - "6. MENA Ignite submission priorities — reviewed 6 September 2026"
Cohesion: 0.20
Nodes (10): 6. MENA Ignite submission priorities — reviewed 6 September 2026, H0 — Confirm the submission contract before building more, H1 — Make the AI contribution visible and measurable, H2 — Show verifiable Nokia NaC integration, with precise scope, H2a — Live API calls to Nokia's hosted simulator, H3 — Make one MENA customer problem specific, H4 — Demonstrate the benefit without hiding the tradeoff, H5 — Ship one coherent, remotely accessible demonstration (+2 more)

### Community 149 - "9. Sonnet code review — 6 September 2026"
Cohesion: 0.25
Nodes (8): 9. Sonnet code review — 6 September 2026, R1 — Bind merchant harness flows to their creating session (high), R2 — Recover completed verification after a lost response (high), R3 — Enforce harness flow retention on reads and while idle (medium), R4 — Enforce terminal consent retention without new traffic (medium), R5 — Remove the unvalidated SDK token-exchange branch (high, conditional), R6 — Freeze outcome operations for safe retries (high), R7 — Validate flow context before constructing upstream input (medium)

### Community 150 - "NaC installed SDK: complete operation index"
Cohesion: 0.09
Nodes (21): `call_forwarding_signal`, `call_forwarding_signal.retrieve_call_forwarding`, `call_forwarding_signal.retrieve_unconditional_call_forwarding`, `consent_info`, `consent_info.retrieve`, `device_swap`, `device_swap.check`, `device_swap.retrieve_date` (+13 more)

### Community 151 - "test_outcome_report_review_metrics.py"
Cohesion: 0.38
Nodes (9): _as_the_merchant(), _owner(), fixture, I12 — review metrics and an optional business-impact worksheet, added on top of…, _seed(), test_a_worksheet_with_assumptions_is_report_only(), test_challenge_completion_time_is_averaged_over_completed_attempts(), test_manually_accepted_orders_are_counted() (+1 more)

### Community 152 - "Isnad: implementation and release runbook"
Cohesion: 0.11
Nodes (18): 0. Establish the exact starting point, 10. Re-audit core behavior while integrating additions, 11. Run a bounded end-to-end demo rehearsal, 12. Publish a complete user test guide and improve README, 13. Final offline release gate, 14. Commit, push and confirm the actual release, 15. Final handover format, 1. Freeze the baseline and protect reproducibility (+10 more)

### Community 153 - "Decision"
Cohesion: 0.09
Nodes (26): Decision, _degraded_context(), The one extra, still-derived-not-invented sentence for the DEGRADED CHALLENGE…, _summary(), baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's… (+18 more)

### Community 154 - "Isnad — implementation handoff"
Cohesion: 0.18
Nodes (11): 10. Follow-up code review — 6 September 2026, 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 4. Path to a live product, 5. Code map and working rules, 8. Latest session, F1 — Keep polling while a completed receipt is still missing (high; R2), F2 — Finish idle cleanup and terminal data minimization (medium; R3) (+3 more)

### Community 155 - "test_i18n.py"
Cohesion: 0.05
Nodes (32): I6 — locale dictionaries served through one explicit, allowlisted route. Locale…, The Arabic dictionary is machine-assisted and unreviewed; a reader of the page,…, The translation is a gloss beside the signed token. Replacing CHALLENGE with an…, Chain ids, hex keys, ISO timestamps, API names and signed numbers are reordered…, I6 step 1's hard rule: locale is UI-only. The only request that may carry it is…, Verification is what the receipt is *for*. An unreachable presentation module…, Zero external origins is the rule these pages keep; a shared module must not be…, A reader who cannot distinguish the green from the red must still get the… (+24 more)

### Community 156 - "normalize_level"
Cohesion: 0.15
Nodes (17): Interval, normalize_confidence(), _normalize_intervals(), normalize_level(), Any, The operator's word, or `unknown`. Never a guess in either direction., A percentage the operator actually gave, or None. Turning a missing confidence…, Validate every interval before it becomes a response. A provider list is not… (+9 more)

### Community 157 - "test_hypothesis_relevance.py"
Cohesion: 0.12
Nodes (24): _act_one(), asyncio, Every check a hypothesis may buy has to be able to move that hypothesis. The…, The sentence is what a merchant reads. Naming only the orthogonal check was the…, `grade` reads adverse_delta as "at least"; the explanation used a strict hard-…, The general form, so the next hypothesis added cannot repeat this., A check listed for a hypothesis must have a signal that can move it. `gain`…, `legit` lists nothing, and that has to mean "no hypothesis-driven check", not… (+16 more)

### Community 158 - "test_evidence_comparison.py"
Cohesion: 0.47
Nodes (5): asyncio, I3 — the combined evidence/decision comparison report. Loaded from the script…, test_false_declines_are_counted_only_among_the_innocent_denominator(), test_the_report_carries_both_sources_and_named_denominators(), test_the_report_is_reproducible_across_two_runs()

### Community 159 - "Open findings and concrete fixes"
Cohesion: 0.12
Nodes (17): Open findings and concrete fixes, R01 · P1 — Subscription queries are not bound to the subscribed device, R02 · P1 — Registered callback URLs cannot identify a newly created subscription, R03 · P1 — Subscription quotas and query pacing do not bound concurrent spend, R04 · P1 — Uncertain creates lose recovery and empty provider IDs become active, R05 · P1 — Trust sessions stay active and perform checks after their TTL, R06 · P2 — Mock congestion data is falsely labeled hosted-simulator data, R07 · P2 — Network-condition records have no terminal retention (+9 more)

### Community 161 - "runner.py"
Cohesion: 0.24
Nodes (6): LabRun, Versioned artifacts for the judge lab (I1's shared contract). A `LabRun` is a…, TraceEvent, _fixture_digest(), _planner_source(), Offline, deterministic investigation runs for the judge lab (I1). Reuses the…

### Community 164 - "_delivered"
Cohesion: 0.16
Nodes (16): _delivered(), asyncio, At-least-once means the same event legitimately arrives twice — once live, once…, Numbering a live-only event as if it were in the journal would promise a…, Most emissions carry no run_id and are not replayable at all., The two deliveries have to agree, or deduplication is meaningless., The Verified Caller act emits the calling number. A journal outlives the…, Emit each event and return what a subscriber actually received. `emit` redacts… (+8 more)

### Community 165 - "test_gemini_primary.py"
Cohesion: 0.18
Nodes (14): parametrize, Gemini responses must never be silently replaced by greedy selection., Run a real investigation on the real LLMPlanner with a stubbed client., The ALLOW gate's choreographed network check is `policy`, not `llm`., _run_with(), test_a_completed_investigation_after_a_model_stop_is_still_signed(), test_a_completed_investigation_records_llm_when_gemini_answered(), test_a_missing_key_reports_an_explicit_unavailable_status() (+6 more)

### Community 166 - "timing.py"
Cohesion: 0.22
Nodes (12): EvidenceTiming, BaseModel, When the operator says the change happened, and how sure that is. A versioned,…, Optional: when the operator says the change in `signal` happened. A SEPARATE…, failure(), not_attempted(), now_utc(), datetime (+4 more)

### Community 168 - "resolve_key_path"
Cohesion: 0.20
Nodes (11): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+3 more)

### Community 169 - "Code review and hackathon readiness — 6 September 2026"
Cohesion: 0.40
Nodes (5): Code review and hackathon readiness — 6 September 2026, Fixes delivered, Outcome, Suggestions for MENA Ignite, Verification

### Community 170 - "test_session.py"
Cohesion: 0.29
Nodes (12): SessionStatus, trip_swap(), _clean_trips(), asyncio, fixture, Trust-with-a-TTL: live session revocation., Start a clean session, inject a SIM swap, monitor must revoke it., test_manual_end() (+4 more)

### Community 171 - "build_judge_lab.py"
Cohesion: 0.67
Nodes (3): _build_all(), main(), Build LabRun artifacts for every judge-lab scenario (I1). Fully offline: mock…

### Community 172 - "test_pilot_polling.py"
Cohesion: 0.50
Nodes (3): skipif, Execute the shipped poll loop with controlled HTTP replies and a tiny DOM., test_poll_recovers_after_http_error_and_missing_receipt()

### Community 173 - "test_s5_subject_binding.py"
Cohesion: 0.18
Nodes (17): get_record(), _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., An old row must parse, and must never claim to be about a number., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature. (+9 more)

### Community 174 - "Money"
Cohesion: 0.27
Nodes (12): Money, _investigator(), asyncio, End-to-end scenario tests — the demo's three acts run the real engine. These…, Act I — clean signup: one silent Number Verification clears them., Act II — SIM swapped 41 min ago, new device, wrong location -> DECLINE., Act III — no merchant history, but years of SIM tenure clear them -> ALLOW.…, The agent should not run all seven APIs when a verdict is reached cheaply. (+4 more)

### Community 175 - "codebase_review_2026_09_07.py"
Cohesion: 0.18
Nodes (5): EmptyID, Offline reproductions for handoff R01–R06/R08/R12, 7 September 2026. Run from…, Recorder, session_probe(), TimeoutRecorder

### Community 176 - "_configured_for_llm"
Cohesion: 0.67
Nodes (3): _configured_for_llm(), fixture, Global config asking for the model, with a credential present.

### Community 178 - "sonnet_review_regressions.py"
Cohesion: 0.29
Nodes (12): add_flow(), client_for(), asyncio, Offline review probes: assertions describe required behavior and fail on…, test_review_consent_owned_read_enforces_terminal_retention(), test_review_foreign_operator_session_cannot_read_flow(), test_review_harness_read_enforces_flow_retention(), test_review_invalid_context_returns_422_instead_of_500() (+4 more)

### Community 179 - "Recording"
Cohesion: 0.15
Nodes (9): A timeout is not a refusal. The subscription may exist at the operator, so the…, A provider that counts its calls, so "no request was made" is assertable., Counting and inserting were separate steps, and the routes run in worker…, A missing key or a null timestamp used to escape normalization and surface as a…, Recording, test_a_malformed_interval_is_dropped_rather_than_crashing_the_response(), test_an_uncertain_create_stays_non_terminal_so_it_must_be_reconciled(), test_one_subscriptions_token_does_not_authenticate_anothers_events() (+1 more)

### Community 180 - "validate_period"
Cohesion: 0.17
Nodes (12): Decide forecast vs history, and refuse an unusable historical window. Both…, validate_period(), Two ordered bounds are not a historical window just because they are ordered.…, One bound implies a fifteen-minute interval on the other side that the caller…, test_a_backwards_window_is_refused(), test_a_naive_bound_is_refused(), test_a_window_entirely_in_the_future_is_not_history(), test_a_window_starting_within_clock_skew_is_still_accepted() (+4 more)

### Community 181 - "get_provider"
Cohesion: 0.21
Nodes (6): get_provider(), Select the evidence provider from config. ISNAD_PROVIDER=mock -> scripted…, FakeConsentProvider, A consent-specific completion must spend the consent on Number Verification.…, test_authorized_number_verification_runs_even_when_the_planner_stops(), test_number_verification_consent_callback_and_resume()

### Community 182 - "`slice`"
Cohesion: 0.17
Nodes (12): `slice`, `slice.activate`, `slice.attach_device`, `slice.create_slice`, `slice.deactivate`, `slice.delete_device_attachment`, `slice.delete_slice`, `slice.get_device_attachment` (+4 more)

### Community 183 - "12. Active user requests and implementation plan — 6 September 2026"
Cohesion: 0.17
Nodes (12): 12. Active user requests and implementation plan — 6 September 2026, API review checkpoint — user requested before resuming app changes, Delivery order and gates, Exact current state at this planning checkpoint, N1 — Gemini is primary; greedy only when no answer arrives, N2 — Arabic everywhere, including changing state, N3 — Reconcile the NaC docs with the installed SDK, N4 — Use real SIM/device change times (+4 more)

### Community 184 - "SlidingWindowLimiter"
Cohesion: 0.20
Nodes (6): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, test_the_limiter_bucket_map_is_bounded(), test_the_window_actually_slides()

### Community 185 - "_callback"
Cohesion: 0.27
Nodes (11): latest_event(), The newest delivered notification for one of this owner's subscriptions., _callback(), _owner(), The wiring the old test could not see: it called the handler with an id it…, Existence is not something to leak through a status code., test_a_delivered_event_is_accepted_and_readable(), test_a_forged_token_is_rejected() (+3 more)

### Community 186 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 187 - "`qod`"
Cohesion: 0.18
Nodes (11): `qod`, `qod.create_session`, `qod.create_session_v1`, `qod.delete_session`, `qod.delete_session_v1`, `qod.extend_session`, `qod.extend_session_v1`, `qod.get_session` (+3 more)

### Community 188 - "Session record — 6–7 September 2026 (runbook gates 0 to 9)"
Cohesion: 0.18
Nodes (11): Commits, in order, Dead ends worth not repeating, Defects found in this session's own code, Documented consequences a future run will see, Exact commands, Session record — 6–7 September 2026 (runbook gates 0 to 9), Still open, Three findings that changed the implementation (+3 more)

### Community 189 - "Checkpoint log"
Cohesion: 0.20
Nodes (9): 2026-09-06 — gate 0/1 complete, 2026-09-06 — gate 4 complete, 2026-09-06 — gate 5 complete, 2026-09-06 — gate 6 complete offline; hosted lifecycle is an external limit, 2026-09-06 — gates 2 and 3 complete, 2026-09-07 — gate 8 complete, with limits stated, 2026-09-07 — gates 9 and 10, and a review of this session's own work, Checkpoint log (+1 more)

### Community 190 - "Nokia API additions and demo call plan"
Cohesion: 0.20
Nodes (9): Congestion callback acceptance, Contract corrections to implement before demo calls, First bounded simulator matrix, How to test the calls, Important story limitation, Nokia API additions and demo call plan, Proposed five-minute demo, Recommended additions (+1 more)

### Community 191 - "Isnad user test guide"
Cohesion: 0.22
Nodes (8): Consent, merchant journey and the rest, Isnad user test guide, Network conditions (Congestion Insights), Network evidence, Receipts, proof and sessions, Setup, The agent and its decision, What this release does not do

### Community 192 - "fixture"
Cohesion: 0.22
Nodes (9): _callback_configured(), _clean_tables(), client(), provider(), fixture, This file makes far more requests than the per-key minute limit allows, and a…, The suite shares one in-memory database, and this feature's whole point is that…, _two_tenants() (+1 more)

### Community 193 - "planner_divergence.py"
Cohesion: 0.32
Nodes (7): form(), Read the request context and commit to a risk hypothesis. This is what makes…, _install_retries(), main(), Measure how differently the LLM planner behaves from the greedy one. This…, Give the provider every chance to answer, for measurement runs only. The demo…, _verdict()

### Community 194 - "Nokia Network as Code contract matrix"
Cohesion: 0.25
Nodes (7): Account and transport facts, Explicitly deferred, with reason, Nokia Network as Code contract matrix, Operations added or shortlisted by the API review, Operations Isnad calls today, The contradiction the demo must not hide, Unknowns recorded as unknown

### Community 195 - "Hosted simulator observations"
Cohesion: 0.25
Nodes (7): 2026-09-06-hosted-simulator.jsonl, 2026-09-06, second batch: Number Recycling, Hosted simulator observations, Two corrections to the 2026-09-06 file itself, What remains unobserved, What these observations contradicted, What these observations settled

### Community 196 - "._tz_aware"
Cohesion: 0.53
Nodes (3): datetime, field_validator, _reject_naive()

### Community 197 - "`congestion_insights`"
Cohesion: 0.33
Nodes (6): `congestion_insights`, `congestion_insights.create_subscription`, `congestion_insights.delete_subscription`, `congestion_insights.get_subscription`, `congestion_insights.list_subscriptions`, `congestion_insights.query`

### Community 198 - "test_low_prior_allow_requires_a_supporting_fact_even_with_stop"
Cohesion: 0.33
Nodes (4): asyncio, parametrize, StopsImmediately, test_low_prior_allow_requires_a_supporting_fact_even_with_stop()

### Community 199 - "7. Add the relevant identity extensions, in this order"
Cohesion: 0.40
Nodes (5): 7. Add the relevant identity extensions, in this order, 7a. Number Recycling, 7b. Network SIM Swap subscriptions, 7c. Consent Info, 7d. Optional after required gates: forwarding and tenure

### Community 200 - "`geofencing`"
Cohesion: 0.40
Nodes (5): `geofencing`, `geofencing.create_subscription`, `geofencing.delete_subscription`, `geofencing.get_subscription`, `geofencing.list_subscriptions`

### Community 201 - "`kyc`"
Cohesion: 0.40
Nodes (5): `kyc`, `kyc.check_tenure`, `kyc.fill_in`, `kyc.match`, `kyc.verify_age`

### Community 202 - "`number_verification`"
Cohesion: 0.40
Nodes (5): `number_verification`, `number_verification.get_device_phone_number`, `number_verification.get_device_phone_number_v2`, `number_verification.verify`, `number_verification.verify_v2`

### Community 203 - "_check_registry_signature"
Cohesion: 0.50
Nodes (4): _check_registry_signature(), Verify the number registry before serving anything. The Directory verifies…, The unsigned path must stay viable, or the fix for the above is a different…, test_startup_survives_a_deployment_that_has_no_signature()

### Community 204 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 205 - "`well_known_metadata`"
Cohesion: 0.50
Nodes (4): `well_known_metadata`, `well_known_metadata.get_oauth_authorization_server`, `well_known_metadata.get_openid_configuration`, `well_known_metadata.get_security_txt`

### Community 206 - "Current code review — 7 September 2026"
Cohesion: 0.50
Nodes (4): Current code review — 7 September 2026, Recommended implementation order, Reproduce the review locally, Validation of this checkout

### Community 207 - "_poll_and_maybe_complete"
Cohesion: 0.67
Nodes (3): get_flow(), _poll_and_maybe_complete(), Best-effort: Isnad being briefly unreachable must surface as "still polling",…

### Community 208 - "`sim_swap`"
Cohesion: 0.67
Nodes (3): `sim_swap`, `sim_swap.check`, `sim_swap.retrieve_date`

### Community 210 - "test_injection_in_every_free_text_field_changes_no_verdict"
Cohesion: 0.67
Nodes (3): parametrize, The runbook's required test, end to end through the API. claimed_identity is…, test_injection_in_every_free_text_field_changes_no_verdict()

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **320 isolated node(s):** `Isnad`, `encode.sh script`, `L`, `TOTAL`, `SCENES` (+315 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1709 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Result`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `IdTokenError`, `Action`, `NaC integration — observed, not assumed`, `sonnet_review_regressions.py`, `get_provider`, `test_review_regressions.py`, `test_nac_provider.py`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `PHASE2_HANDOFF.md`, `NaC integration — observed, not assumed`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `NaC integration — observed, not assumed` connect `NaC integration — observed, not assumed` to `console.html — live agent console`, `NacProvider`, `Phase 2 Agent Runbook`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 114 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 114 INFERRED edges - model-reasoned connections that need verification._
- **Are the 50 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 50 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 52 INFERRED edges - model-reasoned connections that need verification._