# Graph Report - isnad  (2026-09-06)

## Corpus Check
- 185 files · ~157,133 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2383 nodes · 5460 edges · 125 communities (95 shown, 10 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 585 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5a63912`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_chain_grade.py
- test_t6_receipt.py
- PolicyEngine
- main.py
- test_llm_planner.py
- Investigator
- test_registry.py
- test_velocity.py
- test_presentation.py
- routes_console.py
- IdTokenError
- merchant_pilot/app.py
- GreedyPlanner
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- test_independent_evaluation.py
- test_t4_ask_the_agent.py
- config.py
- VaultSigner
- test_t5_counterfactual.py
- GeminiClient
- test_retention.py
- test_judge.py
- test_act7.py
- NacProvider
- timeline.js
- routes_session.py
- schemas.py
- MockProvider
- ConsentStore
- routes_consent.py
- owner_hash
- VerificationRequest
- store.py
- signing.py
- policy.yaml — the single tuning surface
- rate_limit.py
- Verdict
- routes_verified_caller.py
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- test_fake_operator.py
- SessionManager
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- InMemoryCache
- test_merchant_pilot.py
- UtcDateTime
- velocity.py
- test_nac_contract.py
- purge_once
- test_s7_quota_and_key_mode.py
- Isnad · إسناد
- console.html — live agent console
- LLMPlanner
- test_audit_low.py
- test_consent_html_redirect.py
- 7. Competition feature implementation plan
- Decision
- independent_evaluation.py
- Project Brief
- test_hardening.py
- P4a implementation record
- evidence_pack.py
- Signal → log-odds vocabulary
- Action
- _directory
- Phase 2 Agent Runbook
- _two_banks
- routes_registry.py
- database.py
- get
- test_s14_no_tracked_secrets.py
- demo_token.py
- test_vault.py
- Choice
- test_s9_consent_replay.py
- P1 and P2 implementation records
- _reset_limiters
- CURRENT_STATE.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- test_a_clean_prior_still_records_the_policy_required_network_check
- test_the_grade_legend_covers_every_grade
- test_the_refuted_legend_says_fraud_is_supported
- NaC integration — observed, not assumed
- test_privacy.py
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_s4_demo_mode.py
- test_a_tampered_registry_refuses_to_load
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- test_an_unreadable_signature_is_tampering_not_absence
- What the risk score means

## God Nodes (most connected - your core abstractions)
1. `Action` - 146 edges
2. `VerificationRequest` - 93 edges
3. `Result` - 83 edges
4. `MockProvider` - 77 edges
5. `Decision` - 73 edges
6. `EvidenceLink` - 61 edges
7. `PolicyEngine` - 57 edges
8. `Hypothesis` - 56 edges
9. `Verdict` - 55 edges
10. `RequestContext` - 53 edges

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

## Communities (125 total, 10 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.08
Nodes (44): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, p_to_logodds(), _engine(), _gate(), _investigator(), _link(), asyncio (+36 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (32): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+24 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.08
Nodes (9): PolicyEngine, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain., Checks to attempt before this signal alone may carry a DECLINE. The counterpart…, How many actions to fire at once in parallel mode. Bounded: a batch larger than… (+1 more)

### Community 3 - "main.py"
Cohesion: 0.08
Nodes (26): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+18 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.11
Nodes (38): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+30 more)

### Community 5 - "Investigator"
Cohesion: 0.13
Nodes (15): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+7 more)

### Community 6 - "test_registry.py"
Cohesion: 0.06
Nodes (33): The number registry — which published numbers belong to which institution. The…, Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and… (+25 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.07
Nodes (51): get_engine(), Path, Load the policy once and reuse it — avoids re-reading/parsing YAML per request., distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., Regression tests for audit fixes: engine caching + auth hardening. (+43 more)

### Community 8 - "test_presentation.py"
Cohesion: 0.09
Nodes (39): present(), Presentation, BaseModel, Project a signed Verdict into a plain-language Presentation. Pure function:…, What a first-time visitor sees. Never signed, never part of `Verdict`, safe to…, _facts_known_to_the_chain(), asyncio, parametrize (+31 more)

### Community 9 - "routes_console.py"
Cohesion: 0.09
Nodes (35): key_from_bearer(), owner_for(), Merchant API-key auth: `Authorization: Bearer <key>`., The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., require_api_key(), _valid_key(), act7_announce() (+27 more)

### Community 10 - "IdTokenError"
Cohesion: 0.09
Nodes (50): fetch_jwks(), IdTokenError, Any, AsyncClient, RuntimeError, ID-token validation shared by every OIDC-based Number Verification path (P4a).…, The id_token is missing, malformed, or fails contract validation. Deliberately…, Validate signature, iss, aud, exp/iat and nonce. Returns the claims. Fails… (+42 more)

### Community 11 - "merchant_pilot/app.py"
Cohesion: 0.08
Nodes (32): _client_is_private(), create_flow(), dashboard(), flow_page(), FlowRecord, FlowStore, get_flow(), login() (+24 more)

### Community 12 - "GreedyPlanner"
Cohesion: 0.12
Nodes (19): get_planner(), GreedyPlanner, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, test_the_factory_still_selects_by_config(), _engine(), asyncio (+11 more)

### Community 13 - "announce.py"
Cohesion: 0.12
Nodes (22): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+14 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (18): Directory, _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",… (+10 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.08
Nodes (22): asyncio, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the…, An em dash looks like a rendering defect in a live demo, not the deliberate… (+14 more)

### Community 17 - "test_independent_evaluation.py"
Cohesion: 0.22
Nodes (6): asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "config.py"
Cohesion: 0.12
Nodes (30): check_startup_posture(), InsecureConfiguration, RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Refuse to start a billable deployment with no key or a published one. Only…, Settings, BaseSettings (+22 more)

### Community 20 - "VaultSigner"
Cohesion: 0.06
Nodes (40): InsecureVaultKey, _key_passphrase(), MissingVaultKey, Path, RuntimeError, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any… (+32 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.09
Nodes (27): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+19 more)

### Community 22 - "GeminiClient"
Cohesion: 0.07
Nodes (33): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+25 more)

### Community 23 - "test_retention.py"
Cohesion: 0.16
Nodes (17): purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0)., run_forever(), start(), Task, _age_announcements() (+9 more)

### Community 24 - "test_judge.py"
Cohesion: 0.18
Nodes (12): judge_page(), HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the… (+4 more)

### Community 25 - "test_act7.py"
Cohesion: 0.09
Nodes (24): _no_leftover_announcements(), fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not…, Act VII exercises several authenticated stage controls per test; their request… (+16 more)

### Community 26 - "NacProvider"
Cohesion: 0.06
Nodes (37): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., describe(), main() (+29 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.21
Nodes (15): create_session(), end_session(), get_session(), post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.…, simulate_swap(), _to_response() (+7 more)

### Community 29 - "schemas.py"
Cohesion: 0.11
Nodes (31): explain_chain(), _idempotency_state_response(), post, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature…, Replay a completed state or reject a conflicting/in-flight one. One cache entry…, The one call: 'Can I trust this interaction?' -> ALLOW / CHALLENGE / DECLINE…, verify() (+23 more)

### Community 30 - "MockProvider"
Cohesion: 0.07
Nodes (48): build_investigator(), Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), Area, Money, field_validator, A claimed location — never a tracked coordinate. Used only for yes/no verify., MockProvider (+40 more)

### Community 31 - "ConsentStore"
Cohesion: 0.09
Nodes (28): Any, Create a keyed, domain-separated commitment to a request. A bare SHA-256 of…, request_commitment(), ConsentCapacityExceeded, ConsentRecord, ConsentStore, _now(), _owner_hash() (+20 more)

### Community 32 - "routes_consent.py"
Cohesion: 0.19
Nodes (21): get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., _accept_quality(), complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback() (+13 more)

### Community 33 - "owner_hash"
Cohesion: 0.09
Nodes (31): Receive the events emitted for `owner`, and only those., subscribe(), subscriber_count(), owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore… (+23 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.12
Nodes (31): Result, RequestContext, VerificationRequest, main(), T1 — call every CAMARA action for real and record what came back. The runbook's…, Never write a real identifier to a file that gets committed., redact(), asyncio (+23 more)

### Community 35 - "store.py"
Cohesion: 0.17
Nodes (20): post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord (+12 more)

### Community 36 - "signing.py"
Cohesion: 0.19
Nodes (19): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+11 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 38 - "rate_limit.py"
Cohesion: 0.10
Nodes (27): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+19 more)

### Community 39 - "Verdict"
Cohesion: 0.15
Nodes (13): Verdict, A chain signed before grading existed must never be served a grade the vault…, test_a_pre_grading_chain_reads_back_as_ungraded_not_as_a_grade(), If metadata cannot establish exactly why the engine stopped (thin…, grade() checks `unresolved` before `decline_above` (see app/policy/engine.py),…, The signed model itself was never touched. `presentation` lives only on…, test_decline_with_an_unresolved_link_does_not_claim_direct_contradiction(), test_missing_support_without_any_unresolved_signal_does_not_name_a_check() (+5 more)

### Community 40 - "routes_verified_caller.py"
Cohesion: 0.25
Nodes (13): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+5 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.08
Nodes (20): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files. (+12 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.25
Nodes (13): _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, Exactly ONE live link. The rest of the chain must stay deterministic, or the…, The whole point. On stage, an exception here is a dead demo., The resting state is fully scripted: someone who sets ISNAD_PROVIDER without…, _Stub (+5 more)

### Community 43 - "test_fake_operator.py"
Cohesion: 0.13
Nodes (32): FakeNacProvider, _AccessToken, _AuthCode, authorize(), authorize_decide(), discovery(), _issuer(), jwks() (+24 more)

### Community 44 - "SessionManager"
Cohesion: 0.12
Nodes (24): SessionStatus, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, get_provider(), Select the evidence provider from config. ISNAD_PROVIDER=mock -> scripted…, trip_swap(), _now() (+16 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.05
Nodes (63): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), asyncio, The whole point of the act, in one assertion: the registry resolves it, the…, test_the_landline_is_known_by_name_but_not_by_the_network(), _announce(), bound_key(), _no_leftover_announcements() (+55 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.21
Nodes (15): get_record(), _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve. (+7 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.08
Nodes (24): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+16 more)

### Community 49 - "InMemoryCache"
Cohesion: 0.07
Nodes (16): Cache, CacheCapacityExceeded, get_cache(), InMemoryCache, Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one. (+8 more)

### Community 50 - "test_merchant_pilot.py"
Cohesion: 0.19
Nodes (20): TestClient, _client(), _login(), _patch_isnad(), fixture, P4a — demo/merchant_pilot, the single-merchant reference harness. The harness…, Found during P4a's browser verification: restarting the Isnad server mid-poll…, _reset_login_throttle() (+12 more)

### Community 51 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 52 - "velocity.py"
Cohesion: 0.17
Nodes (14): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, ScreenEventRow, is_high_velocity_async(), _owner() (+6 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "purge_once"
Cohesion: 0.20
Nodes (11): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), One sweep of everything past its window. Returns what it deleted., purge_older_than(), Drop events outside any window anyone will ask about. This table exists to…, retention_seconds(), console_token() (+3 more)

### Community 55 - "test_s7_quota_and_key_mode.py"
Cohesion: 0.17
Nodes (14): RuntimeError, This owner already has as many live sessions as it is allowed., SessionQuotaExceeded, asyncio, S7 — the two unbounded amplifiers: session quota, and the key file mode., `_sessions` was never pruned, so it grew for the life of the process., The acceptance criterion: ttl_seconds 86400 -> 422. One such request polled SIM…, test_a_days_ttl_is_rejected() (+6 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.18
Nodes (11): A changed SIM should start an investigation., A receipt that can be challenged, too, Every check has a job, Evidence you can rerun, Isnad · إسناد, One integration, an explainable action, One warning. Two very different checkouts., Simulated answers. The same investigation. (+3 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "LLMPlanner"
Cohesion: 0.10
Nodes (17): effective_planner(), LLMPlanner, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as… (+9 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.11
Nodes (18): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, policy.yaml says "opt in per request, never globally" and no route let anyone… (+10 more)

### Community 60 - "test_consent_html_redirect.py"
Cohesion: 0.24
Nodes (9): FakeConsentProvider, _patched(), P4a step 8 — a browser-preferring callback gets a generic HTML redirect. The…, _start(), test_a_browser_preferring_callback_is_redirected_even_when_denied(), test_a_browser_preferring_callback_is_redirected_to_the_generic_page(), test_a_script_client_with_no_accept_header_still_gets_json(), test_a_tied_preference_keeps_json() (+1 more)

### Community 61 - "7. Competition feature implementation plan"
Cohesion: 0.05
Nodes (44): 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 3. Recommended app work — not implemented in this documentation pass, 4. Path to a live product, 5. Code map and working rules, 6. MENA Ignite submission priorities — reviewed 6 September 2026, 7. Competition feature implementation plan, 8. Latest session (+36 more)

### Community 62 - "Decision"
Cohesion: 0.08
Nodes (30): form(), Read the request context and commit to a risk hypothesis. This is what makes…, Decision, logodds_to_p(), _degraded_context(), _fact(), A deterministic, plain-language projection of an already-signed Verdict. P2…, One human sentence for a link, traceable to that exact link. `link.api` and… (+22 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (20): model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy() (+12 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 66 - "P4a implementation record"
Cohesion: 0.17
Nodes (12): A real defect found during browser verification, not just written to pass tests, Browser evidence, actually performed, Consent-contract defects fixed first (before the OAuth work), Contract decision, checked against the source before building, Files changed, ID-token validation, shared rather than duplicated, Known gaps, stated plainly, P4a implementation record (+4 more)

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (59): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains… (+51 more)

### Community 68 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 69 - "Action"
Cohesion: 0.06
Nodes (41): EvidenceLink, _now(), datetime, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, Offline fake Number Verification provider (P4a, ISNAD_PROVIDER=nac_fake). Talks…, _csv() (+33 more)

### Community 70 - "_directory"
Cohesion: 0.13
Nodes (15): _directory(), Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., Institutions own ranges, not single numbers. A registry of exact numbers alone…, test_a_published_inbound_only_line_is_flagged_as_never_outbound() (+7 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "_two_banks"
Cohesion: 0.18
Nodes (11): The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, test_a_bare_generic_word_is_not_a_match(), test_a_caller_who_describes_themselves_more_fully_still_matches(), test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution(), test_an_alias_is_matched_whole_and_not_merged_with_the_name() (+3 more)

### Community 73 - "routes_registry.py"
Cohesion: 0.36
Nodes (8): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), RegistryInstitution, RegistryLookupResponse, RegistryNumber

### Community 74 - "database.py"
Cohesion: 0.27
Nodes (8): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for

### Community 75 - "get"
Cohesion: 0.17
Nodes (13): consent_complete_page(), HTMLResponse, Generic same-origin landing page for a subscriber's phone browser. Carries no…, privacy_page(), HTMLResponse, get_chain(), Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm… (+5 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.20
Nodes (13): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+5 more)

### Community 78 - "test_vault.py"
Cohesion: 0.43
Nodes (5): _make_chain(), Evidence vault — signed, tamper-evident chains., test_chain_persists_and_round_trips(), test_fresh_chain_verifies(), test_tampered_chain_fails_verification()

### Community 79 - "Choice"
Cohesion: 0.12
Nodes (10): Choice, Planner, Protocol, What the planner decided, and why, and who decided it., StopsImmediately, _StopsImmediately, The loop must end and still produce a signed verdict., A run that started on the model and fell back must not read as pure llm. (+2 more)

### Community 80 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 81 - "P1 and P2 implementation records"
Cohesion: 0.67
Nodes (3): P1 and P2 implementation records, P2 implementation — 6 Sep (follow-up session), Preserved P1 implementation record

### Community 82 - "_reset_limiters"
Cohesion: 0.67
Nodes (3): fixture, These console checks deliberately make authenticated requests. Keep their…, _reset_limiters()

### Community 83 - "CURRENT_STATE.md"
Cohesion: 0.35
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

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 92 - "test_privacy.py"
Cohesion: 0.20
Nodes (7): The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC…, Hard-coded prose drifts from the running system the first time someone tunes a…, A page that hard-codes '1 hour' is a page that will one day be wrong., The consent trail is inside the signed bytes already. Showing it is what turns…, test_the_page_serves_and_pulls_its_numbers_from_the_endpoint(), test_the_posture_reports_the_retention_windows_actually_configured(), test_the_receipt_shows_the_consent_basis_of_every_link()

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 121 - "What the risk score means"
Cohesion: 0.50
Nodes (4): Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **112 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+107 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 996 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Action`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `IdTokenError`, `SessionManager`, `NaC integration — observed, not assumed`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_velocity.py`, `test_presentation.py`, `GreedyPlanner`, `test_t5_counterfactual.py`, `GeminiClient`, `NacProvider`, `MockProvider`, `routes_consent.py`, `VerificationRequest`, `Verdict`, `test_hybrid_provider.py`, `test_fake_operator.py`, `SessionManager`, `test_verified_caller.py`, `test_nac_contract.py`, `LLMPlanner`, `test_audit_low.py`, `test_consent_html_redirect.py`, `Decision`, `independent_evaluation.py`, `evidence_pack.py`, `Choice`, `test_s9_consent_replay.py`?**
  _High betweenness centrality (0.142) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `CURRENT_STATE.md`, `NaC integration — observed, not assumed`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 76 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 44 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `Result` (e.g. with `EvidenceLink` and `present()`) actually correct?**
  _`Result` has 52 INFERRED edges - model-reasoned connections that need verification._