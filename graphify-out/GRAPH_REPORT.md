# Graph Report - isnad  (2026-09-05)

## Corpus Check
- 166 files · ~150,490 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2033 nodes · 4638 edges · 116 communities (93 shown, 7 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 468 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `09463b11`
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
- test_verified_caller.py
- routes_console.py
- routes_registry.py
- InMemoryCache
- GreedyPlanner
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- Decision
- test_t4_ask_the_agent.py
- check_startup_posture
- SessionManager
- test_t5_counterfactual.py
- GeminiClient
- retention.py
- start_number_verification_consent
- test_act7.py
- NacProvider
- timeline.js
- build_investigator
- Action
- routes_verify.py
- ConsentStore
- velocity.py
- schemas.py
- test_s2_stream_isolation.py
- test_provider_vocabulary.py
- signing.py
- console.html — live agent console
- test_judge.py
- rate_limit.py
- store.py
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- routes_session.py
- test_s7_quota_and_key_mode.py
- test_s3_tenant_isolation.py
- test_retention.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- VaultSigner
- owner_hash
- routes_receipt.py
- stream_token.py
- test_nac_contract.py
- _directory
- routes_privacy.py
- README — Isnad, network-verified trust decisions
- Phase 2 session handoff
- test_s9_consent_replay.py
- test_audit_low.py
- config.py
- get
- false_decline_baseline.py
- Result
- Project Brief
- events.py
- SecurityHeadersMiddleware
- evidence_pack.py
- subject.py
- VerificationRequest
- Ed25519-signed verifiable receipt
- Phase 2 Agent Runbook
- Planner
- routes_verified_caller.py
- .__call__
- UtcDateTime
- test_s14_no_tracked_secrets.py
- demo_token.py
- test_a_clean_prior_still_records_the_policy_required_network_check
- Choice
- test_independent_evaluation.py
- purge_older_than
- test_vault.py
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- database.py
- 90-second judge demo script
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- Isnad mentorship brief (one-pager)
- test_s4_demo_mode.py
- isnad
- Isnad (إسناد) — project brief
- request_commitment
- Number Verification handset validation
- Fixed synthetic evaluation
- Isnad — current state

## God Nodes (most connected - your core abstractions)
1. `Action` - 120 edges
2. `VerificationRequest` - 71 edges
3. `MockProvider` - 71 edges
4. `Decision` - 62 edges
5. `PolicyEngine` - 57 edges
6. `Hypothesis` - 56 edges
7. `Result` - 55 edges
8. `EvidenceLink` - 46 edges
9. `Verdict` - 42 edges
10. `NacProvider` - 41 edges

## Surprising Connections (you probably didn't know these)
- `An invariant is never a question to a planner` --references--> `GreedyPlanner`  [EXTRACTED]
  docs/PHASE2_HANDOFF.md → app/agent/planner.py
- `T3 — rebuild the planner so the agent actually reasons` --references--> `LLMPlanner`  [EXTRACTED]
  docs/PHASE2_AGENT_RUNBOOK.md → app/agent/planner.py
- `An invariant is never a question to a planner` --references--> `LLMPlanner`  [EXTRACTED]
  docs/PHASE2_HANDOFF.md → app/agent/planner.py
- `test_corroboration_baseline_does_not_double_count_one_change_event()` --uses--> `Decision`  [INFERRED]
  tests/test_independent_evaluation.py → app/domain/enums.py
- `test_fixed_cases_cover_the_risky_shapes_the_report_claims()` --uses--> `Decision`  [INFERRED]
  tests/test_independent_evaluation.py → app/domain/enums.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **The two choreographed invariants, in policy and in the orchestrator** — readme_corroborate_before_declining, readme_allow_rests_on_network_fact, app_agent_investigator_investigate, app_policy_policy_corroboration, app_policy_policy_min_network_links_for_allow, docs_phase2_handoff_choreography_not_planner [EXTRACTED 1.00]
- **Pitch Video Render Pipeline (narration to encoded cut)** — docs_video_readme_video_build_pipeline, docs_video_timings_spine, docs_video_scene_scenes, docs_video_encode_pipeline, docs_video_readme_narration_anchored_timing [EXTRACTED 1.00]
- **Supply-Chain Pinning and Audit Flow (S8)** — requirements_runtime_pins, requirements_lock_runtime_closure, requirements_dev_toolchain, github_workflows_ci_verify, requirements_network_as_code_pip_defect, setup_bootstrap_venv [EXTRACTED 1.00]
- **The honesty discipline — sourced, null, or not said** — docs_phase2_handoff_never_invent_a_number, app_policy_policy_pricing, app_registry_registry_provenance_rule, app_registry_registry_demo_fixture, docs_phase2_handoff_do_not_say, docs_implementation_status_nac_observed, docs_video_script_render_seam [INFERRED 0.85]
- **The false-decline thesis and the measurements that carry it** — readme_false_decline_thesis, readme_false_decline_baseline, readme_planner_divergence, app_policy_policy_thresholds, docs_video_script, docs_mentorship_isnad_mentorship_brief [INFERRED 0.85]
- **Nokia NaC / CAMARA Evidence Capture Catalogue** — docs_nac_sim_swap_capture, docs_nac_device_swap_capture, docs_nac_location_verify_capture, docs_nac_number_verify_capture, docs_nac_reachability_capture, docs_nac_roaming_capture, docs_nac_device_intelligence_capture, docs_nac_step_up_otp_capture, docs_nac_sim_swap_normalized_envelope [INFERRED 0.95]

## Communities (116 total, 7 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.06
Nodes (51): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, p_to_logodds(), Prior for Reverse Isnad: an unverified inbound caller starts uncertain., _engine(), _gate(), _investigator(), _link() (+43 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (34): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+26 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.08
Nodes (8): PolicyEngine, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Checks to attempt before this signal alone may carry a DECLINE. The counterpart…, How many actions to fire at once in parallel mode. Bounded: a batch larger than…, Distinct callees in the window before a number counts as a campaign. 0 disables…

### Community 3 - "main.py"
Cohesion: 0.11
Nodes (18): ASGIApp, Exception, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _RequestBodyTooLarge, RequestLimitsMiddleware, database_ready(), A readiness probe that performs a real round trip to the database. (+10 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.11
Nodes (38): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+30 more)

### Community 5 - "Investigator"
Cohesion: 0.14
Nodes (14): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+6 more)

### Community 6 - "test_registry.py"
Cohesion: 0.06
Nodes (42): The number registry — which published numbers belong to which institution. The…, Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and… (+34 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.07
Nodes (51): get_engine(), Path, Load the policy once and reuse it — avoids re-reading/parsing YAML per request., distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., Regression tests for audit fixes: engine caching + auth hardening. (+43 more)

### Community 8 - "test_verified_caller.py"
Cohesion: 0.06
Nodes (60): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), _announce(), bound_key(), _no_leftover_announcements(), asyncio, fixture, Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA… (+52 more)

### Community 9 - "routes_console.py"
Cohesion: 0.12
Nodes (27): key_from_bearer(), owner_for(), The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., act7_announce(), _act7_emit(), _act7_key(), act7_screen() (+19 more)

### Community 10 - "routes_registry.py"
Cohesion: 0.29
Nodes (10): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), One institution's claim on a number, with the basis for the claim., RegistryInstitution, RegistryLookupResponse (+2 more)

### Community 11 - "InMemoryCache"
Cohesion: 0.07
Nodes (16): Cache, CacheCapacityExceeded, get_cache(), InMemoryCache, Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one. (+8 more)

### Community 12 - "GreedyPlanner"
Cohesion: 0.08
Nodes (32): effective_planner(), get_planner(), GreedyPlanner, LLMPlanner, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Asks a model to choose the next evidence step, given the belief state, the…, Select the planner from config: greedy (default, demo-safe) or llm., The planner that will actually choose, not the one config asked for.… (+24 more)

### Community 13 - "announce.py"
Cohesion: 0.21
Nodes (15): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+7 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (17): Directory, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",…, The institution that published this number, or None. None means "not in the… (+9 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (25): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+17 more)

### Community 17 - "Decision"
Cohesion: 0.11
Nodes (27): form(), Read the request context and commit to a risk hypothesis. This is what makes…, Decision, RequestContext, logodds_to_p(), Enum, _investigator(), asyncio (+19 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "check_startup_posture"
Cohesion: 0.10
Nodes (35): check_startup_posture(), InsecureConfiguration, makes_billable_calls(), RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Can a request cause a real, paid CAMARA call to leave this process? Keyed on…, Refuse to start a billable deployment with no key or a published one. Only… (+27 more)

### Community 20 - "SessionManager"
Cohesion: 0.14
Nodes (19): SessionStatus, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+11 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.08
Nodes (29): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+21 more)

### Community 23 - "retention.py"
Cohesion: 0.18
Nodes (13): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+5 more)

### Community 24 - "start_number_verification_consent"
Cohesion: 0.31
Nodes (10): complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), HTTPException, post, Receive the provider redirect; the authorization code is never exposed. (+2 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (29): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, The two demo actions share state across runs. Resetting them locally prevents a…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the… (+21 more)

### Community 26 - "NacProvider"
Cohesion: 0.12
Nodes (12): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., describe(), main() (+4 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "build_investigator"
Cohesion: 0.14
Nodes (26): build_investigator(), A run must emit a 'start' first and a 'verdict' last to any subscriber., test_event_bus_streams_start_and_verdict(), asyncio, Parallel evidence gathering — latency bought with cost. Opt-in per request.…, On a chain that spends its budget anyway the two are equal — the takeover case…, Speed must not change the answer., Two runs over the same evidence must produce the same number regardless of… (+18 more)

### Community 29 - "Action"
Cohesion: 0.09
Nodes (29): EvidenceLink, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, _csv() (+21 more)

### Community 30 - "routes_verify.py"
Cohesion: 0.19
Nodes (15): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, _verification_response(), explain_chain(), _idempotency_state_response(), post, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature… (+7 more)

### Community 31 - "ConsentStore"
Cohesion: 0.15
Nodes (11): ConsentCapacityExceeded, ConsentRecord, ConsentStore, _now(), _owner_hash(), datetime, RuntimeError, Claim this consent for exactly one callback. A true compare-and-swap. The old… (+3 more)

### Community 32 - "velocity.py"
Cohesion: 0.13
Nodes (15): One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, ScreenEventRow, _owner(), The tenant this request belongs to, set at the auth boundary (S2)., Note that this caller was screened against this callee, for this tenant., record(), record_async(), The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC… (+7 more)

### Community 33 - "schemas.py"
Cohesion: 0.07
Nodes (40): deterministic(), _facts(), Everything the narrator may see. Enums, numbers, booleans., The always-available narrative. No model, no key, no network., Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), _now(), BaseModel (+32 more)

### Community 34 - "test_s2_stream_isolation.py"
Cohesion: 0.18
Nodes (13): subscriber_count(), asyncio, S2 — the SSE stream must be authenticated and must not cross tenants., End to end through the HTTP surface, not just the bus., A disconnect that is never noticed must not pin memory forever (S12)., The finding, verbatim: `curl -N /v1/console/stream` harvested everything., A background emit with no owner must not fan out to a real tenant., test_a_stream_token_cannot_authorize_a_normal_api_call() (+5 more)

### Community 35 - "test_provider_vocabulary.py"
Cohesion: 0.13
Nodes (15): detail_for(), The only sentences an evidence link may carry, and where each one comes from.…, The max_age the swap checks are actually called with., The sentence for a signal, derived from the response and our parameters., _window(), parametrize, A fixture may only say what a CAMARA API can return. This is the test that…, No Nokia adapter exists, so no scenario may return a reputation. (+7 more)

### Community 36 - "signing.py"
Cohesion: 0.15
Nodes (23): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+15 more)

### Community 37 - "console.html — live agent console"
Cohesion: 0.18
Nodes (17): investigate(), policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected (+9 more)

### Community 38 - "test_judge.py"
Cohesion: 0.16
Nodes (13): judge_page(), HTMLResponse, Read-only entry point for the concise, judge-facing product demonstration. The…, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that… (+5 more)

### Community 39 - "rate_limit.py"
Cohesion: 0.35
Nodes (10): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+2 more)

### Community 40 - "store.py"
Cohesion: 0.26
Nodes (14): ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord, get_public_record(), get_public_record_async(), _owned(), _owner(), Read a chain WITHOUT the owner check, for the public receipt page (T6). A… (+6 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.09
Nodes (18): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files. (+10 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.25
Nodes (13): _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, Exactly ONE live link. The rest of the chain must stay deterministic, or the…, The whole point. On stage, an exception here is a dead demo., The resting state is fully scripted: someone who sets ISNAD_PROVIDER without…, _Stub (+5 more)

### Community 43 - "routes_session.py"
Cohesion: 0.15
Nodes (20): get_live_provider(), Merchant API-key auth: `Authorization: Bearer <key>`., Resolve the configured provider as an API-level 503 when unavailable., require_api_key(), _valid_key(), create_session(), end_session(), get_session() (+12 more)

### Community 44 - "test_s7_quota_and_key_mode.py"
Cohesion: 0.14
Nodes (18): InsecureVaultKey, RuntimeError, The signing key is readable by someone other than its owner., asyncio, S7 — the two unbounded amplifiers: session quota, and the key file mode., `_sessions` was never pruned, so it grew for the life of the process., The acceptance criterion: stat the key -> 600, the directory -> 700. It was…, The acceptance criterion: ttl_seconds 86400 -> 422. One such request polled SIM… (+10 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_retention.py"
Cohesion: 0.24
Nodes (11): _age_announcements(), _counts(), asyncio, Retention — the sweeper that finally has a caller. `announce.purge_expired()`…, A transient database error must not end the loop. Nothing else in the process…, The whole point of this file: the purges have a caller now. The boot sweep…, `announcement_uses` has no foreign key, so deleting the announcements alone…, test_one_sweep_clears_both_tables() (+3 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.21
Nodes (15): get_record(), _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve. (+7 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "VaultSigner"
Cohesion: 0.10
Nodes (16): Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, Signs issued chains with Ed25519. The key is loaded from disk if present,…, _trusted_from_settings(), VaultSigner, _verify_with_key() (+8 more)

### Community 50 - "owner_hash"
Cohesion: 0.19
Nodes (14): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+6 more)

### Community 51 - "routes_receipt.py"
Cohesion: 0.24
Nodes (10): HTMLResponse, Request, The page a judge opens from the QR code., Give the QR a viewBox so it scales with its container., An inline SVG QR for this receipt's public URL. Generated server-side and…, The exact signed bytes, the signature, and the key that signed them. Public and…, receipt_data(), receipt_page() (+2 more)

### Community 52 - "stream_token.py"
Cohesion: 0.18
Nodes (13): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+5 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "_directory"
Cohesion: 0.13
Nodes (15): _directory(), Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., Institutions own ranges, not single numbers. A registry of exact numbers alone…, test_a_published_inbound_only_line_is_flagged_as_never_outbound() (+7 more)

### Community 55 - "routes_privacy.py"
Cohesion: 0.22
Nodes (8): _human(), posture(), privacy_page(), HTMLResponse, Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page…, What this deployment keeps, for how long, and what it never holds.

### Community 56 - "README — Isnad, network-verified trust decisions"
Cohesion: 0.24
Nodes (7): Answers worth rehearsing, The 90-second Isnad demo, Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability, README — Isnad, network-verified trust decisions

### Community 57 - "Phase 2 session handoff"
Cohesion: 0.26
Nodes (12): judge.html — Judge Mode verified checkout, provenance(), Trust with a TTL (session revocation), Phase 2 session handoff, The Act VI false decline (declined instead of degrading), An invariant is never a question to a planner, The greedy-suite / llm-console trap, Hybrid provider — one genuinely live link (+4 more)

### Community 58 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.10
Nodes (20): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read… (+12 more)

### Community 60 - "config.py"
Cohesion: 0.15
Nodes (17): _key_passphrase(), MissingVaultKey, Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, The signing key was expected on disk and was not there., Load the configured signer into this stable module-level instance. Modules… (+9 more)

### Community 61 - "get"
Cohesion: 0.24
Nodes (10): verify_consent_chain(), get_chain(), Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, The public key anyone can use to independently verify a chain signature., vault_public_key(), verify_chain(), get() (+2 more)

### Community 62 - "false_decline_baseline.py"
Cohesion: 0.33
Nodes (9): baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's…, The two rules being replaced, applied to a full evidence set. The baseline is…, Every single-signal case the policy vocabulary admits, plus a control., The operating curve, because the honest answer to "you allow some corroborated-…, run() (+1 more)

### Community 63 - "Result"
Cohesion: 0.13
Nodes (25): Result, model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec (+17 more)

### Community 64 - "Project Brief"
Cohesion: 0.31
Nodes (9): Project Brief, CAMARA — open network API standard, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Tazkiya (تزكية) — human vouching, Wakala (وكالة) — agent delegation, Mentorship outreach email (stc), Competitive position — a searched absence (+1 more)

### Community 65 - "events.py"
Cohesion: 0.14
Nodes (13): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), asyncio (+5 more)

### Community 66 - "SecurityHeadersMiddleware"
Cohesion: 0.22
Nodes (6): ASGIApp, Receive, Scope, Send, Attach security headers to every response. Written against the raw ASGI…, SecurityHeadersMiddleware

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (57): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, Response, build_report() (+49 more)

### Community 68 - "subject.py"
Cohesion: 0.25
Nodes (8): matches(), owner_binding(), Bind a verdict to the number it was issued about., Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, Whether a stored chain was really issued about this number., subject_hash(), An old row must parse, and must never claim to be about a number., test_an_unbound_pre_s5_chain_reads_back_as_unbound_not_as_matching()

### Community 69 - "VerificationRequest"
Cohesion: 0.11
Nodes (18): VerificationRequest, main(), T1 — call every CAMARA action for real and record what came back. The runbook's…, Never write a real identifier to a file that gets committed., redact(), _consent_provider(), FakeClient, FakeDeviceStatus (+10 more)

### Community 70 - "Ed25519-signed verifiable receipt"
Cohesion: 0.18
Nodes (13): OTP_CONFIRMED — reserved, nothing emits it, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr(), receipt.html — public evidence receipt (+5 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner, T3 — rebuild the planner so the agent actually reasons (+3 more)

### Community 73 - "routes_verified_caller.py"
Cohesion: 0.23
Nodes (13): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), ScreenResponse, get_directory() (+5 more)

### Community 74 - ".__call__"
Cohesion: 0.50
Nodes (4): Receive, Scope, Send, _reject()

### Community 75 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.19
Nodes (13): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+5 more)

### Community 79 - "Choice"
Cohesion: 0.10
Nodes (13): Choice, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as…, What the planner decided, and why, and who decided it., StopsImmediately (+5 more)

### Community 80 - "test_independent_evaluation.py"
Cohesion: 0.22
Nodes (6): asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()

### Community 81 - "purge_older_than"
Cohesion: 0.38
Nodes (6): purge_older_than(), Drop events outside any window anyone will ask about. This table exists to…, console_token(), main(), Drive one number against many callees, so Act VII can show caller velocity. Run…, screen()

### Community 82 - "test_vault.py"
Cohesion: 0.43
Nodes (5): _make_chain(), Evidence vault — signed, tamper-evident chains., test_chain_persists_and_round_trips(), test_fresh_chain_verifies(), test_tampered_chain_fails_verification()

### Community 85 - "verify_runtime_lock.py"
Cohesion: 0.60
Nodes (5): _canonical(), _locked(), main(), _project_dependencies(), Validate the committed runtime lock without contacting a package index. The…

### Community 86 - "test_evidence_pack.py"
Cohesion: 0.29
Nodes (5): evidence_pack_module(), asyncio, fixture, Focused contract tests for the offline, judge-reviewable evidence pack., test_evidence_pack_is_offline_and_verifies_the_stored_chain()

### Community 87 - "test_mock_scenarios.py"
Cohesion: 0.47
Nodes (5): Guards on the demo fixture table itself. A dict literal with a repeated key is…, Read the keys from the SOURCE, not the dict. By the time the module is imported…, _scenario_keys(), test_every_scenario_number_is_e164(), test_no_scenario_number_is_defined_twice()

### Community 89 - "database.py"
Cohesion: 0.16
Nodes (12): Base, Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas() (+4 more)

### Community 91 - "90-second judge demo script"
Cohesion: 0.29
Nodes (8): API Build Plan (Python / FastAPI), Demo/production parity — only the provider differs, Nokia Network as Code (NaC), 90-second judge demo script, Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses, Evidence pack (reproducible scripted proof)

### Community 100 - "Isnad mentorship brief (one-pager)"
Cohesion: 0.22
Nodes (9): REGISTRY_MATCH_UNANNOUNCED = 0.0, Decision thresholds (allow_below / decline_above), Cash-on-delivery fraud as the market wedge, Reverse Isnad — verifying the caller to the customer, Isnad mentorship brief (one-pager), Three-index number registry design, Chain grading (ATTESTED_FULL / PARTIAL / UNRESOLVED / DEGRADED / REFUTED), False-decline baseline measurement (+1 more)

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "request_commitment"
Cohesion: 0.33
Nodes (6): post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), Any, Create a keyed, domain-separated commitment to a request. A bare SHA-256 of…, request_commitment()

### Community 118 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 120 - "Isnad — current state"
Cohesion: 0.40
Nodes (5): Isnad — current state, Navigation, Open evidence gaps, Product and demo, What changed in this review

## Ambiguous Edges - Review These
- `The Act VI false decline (declined instead of degrading)` → `Hybrid provider — one genuinely live link`  [AMBIGUOUS]
  docs/PHASE2_HANDOFF.md · relation: conceptually_related_to
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **45 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 827 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `The Act VI false decline (declined instead of degrading)` and `Hybrid provider — one genuinely live link`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_velocity.py`, `test_verified_caller.py`, `GreedyPlanner`, `Decision`, `SessionManager`, `test_t5_counterfactual.py`, `start_number_verification_consent`, `NacProvider`, `build_investigator`, `schemas.py`, `test_provider_vocabulary.py`, `test_hybrid_provider.py`, `test_nac_contract.py`, `test_s9_consent_replay.py`, `test_audit_low.py`, `false_decline_baseline.py`, `Result`, `evidence_pack.py`, `VerificationRequest`, `Planner`, `Choice`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `MockProvider` connect `Action` to `test_chain_grade.py`, `schemas.py`, `evidence_pack.py`, `VerificationRequest`, `test_velocity.py`, `test_verified_caller.py`, `routes_console.py`, `GreedyPlanner`, `test_s7_quota_and_key_mode.py`, `test_console.py`, `Decision`, `SessionManager`, `README — Isnad, network-verified trust decisions`, `test_act7.py`, `90-second judge demo script`, `build_investigator`, `false_decline_baseline.py`, `Result`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `PolicyEngine` connect `PolicyEngine` to `test_chain_grade.py`, `schemas.py`, `velocity.py`, `test_llm_planner.py`, `Investigator`, `test_velocity.py`, `routes_verified_caller.py`, `GreedyPlanner`, `Decision`, `test_audit_low.py`, `Action`, `routes_verify.py`, `Result`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 29 INFERRED edges - model-reasoned connections that need verification._