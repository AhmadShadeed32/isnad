# Graph Report - isnad  (2026-09-05)

## Corpus Check
- 167 files · ~117,051 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2030 nodes · 4566 edges · 120 communities (94 shown, 8 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 451 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `faf467ff`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_chain_grade.py
- test_t6_receipt.py
- PolicyEngine
- request_limits.py
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
- VerificationRequest
- test_t4_ask_the_agent.py
- test_s5_subject_binding.py
- SessionManager
- test_t5_counterfactual.py
- GeminiClient
- test_retention.py
- start_number_verification_consent
- test_act7.py
- Action
- timeline.js
- test_parallel_gather.py
- routes_consent.py
- routes_verify.py
- ConsentStore
- test_privacy.py
- Decision
- investigator.py
- mock.py
- signing.py
- policy.yaml — the single tuning surface
- test_judge.py
- rate_limit.py
- store.py
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- routes_session.py
- run_reverse
- test_s3_tenant_isolation.py
- _announce
- get_record
- test_s10_xss_and_headers.py
- VaultSigner
- owner_hash
- receipt_qr
- stream_token.py
- test_nac_contract.py
- test_false_decline_baseline.py
- config.py
- Isnad · إسناد
- console.html — live agent console
- test_s9_consent_replay.py
- test_audit_low.py
- resolve_key_path
- explain_chain
- false_decline_baseline.py
- independent_evaluation.py
- Project Brief
- events.py
- .__call__
- evidence_pack.py
- velocity.py
- Result
- Signal → log-odds vocabulary
- Phase 2 Agent Runbook
- _two_banks
- routes_verified_caller.py
- test_reverse.py
- db/models.py
- test_s14_no_tracked_secrets.py
- demo_token.py
- bound_key
- Choice
- test_independent_evaluation.py
- purge_older_than
- test_vault.py
- test_low_prior_allow_requires_a_supporting_fact_even_with_stop
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- t1_probe.py
- database.py
- _reset_limiters
- NaC integration — observed, not assumed
- console_mode
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_s4_demo_mode.py
- privacy_page
- isnad
- Isnad (إسناد) — project brief
- vault_public_key

## God Nodes (most connected - your core abstractions)
1. `Action` - 120 edges
2. `VerificationRequest` - 71 edges
3. `MockProvider` - 68 edges
4. `Decision` - 62 edges
5. `PolicyEngine` - 57 edges
6. `Hypothesis` - 56 edges
7. `Result` - 55 edges
8. `EvidenceLink` - 46 edges
9. `Verdict` - 42 edges
10. `NacProvider` - 39 edges

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

## Communities (120 total, 8 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.06
Nodes (51): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, p_to_logodds(), Prior for Reverse Isnad: an unverified inbound caller starts uncertain., _engine(), _gate(), _investigator(), _link() (+43 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (34): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+26 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.08
Nodes (9): PolicyEngine, Path, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Checks to attempt before this signal alone may carry a DECLINE. The counterpart…, How many actions to fire at once in parallel mode. Bounded: a batch larger than… (+1 more)

### Community 3 - "request_limits.py"
Cohesion: 0.13
Nodes (11): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+3 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.11
Nodes (40): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+32 more)

### Community 5 - "Investigator"
Cohesion: 0.18
Nodes (10): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+2 more)

### Community 6 - "test_registry.py"
Cohesion: 0.05
Nodes (48): _directory(), The number registry — which published numbers belong to which institution. The…, Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Unknown must not read as "yes, they call from here" — that is precisely the…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, Intersection, not union: "arab bank" must not return every institution with…, The name reaches this from a copy-paste, a phone keyboard, or another system's… (+40 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.12
Nodes (39): distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., _as(), _burst(), _clean(), _engine() (+31 more)

### Community 8 - "test_verified_caller.py"
Cohesion: 0.13
Nodes (22): Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The window is the spoofing opportunity: while an announcement stands, a call…, Matching the caller alone would let one genuine announcement verify a burst of…, The load-bearing test of this whole feature. Caller ID is spoofable, so a…, The mismatch that is real: this number is Demo Bank's, and the caller says they…, "Arab Bank" is not in the registry, so the registry knows nothing about whether…, The shape that broke: every extra honest word made condemnation more likely,…, Absence from a hand-curated registry is not evidence. Almost every number in… (+14 more)

### Community 9 - "routes_console.py"
Cohesion: 0.12
Nodes (28): key_from_bearer(), owner_for(), Merchant API-key auth: `Authorization: Bearer <key>`., The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., require_api_key(), _valid_key(), act7_announce() (+20 more)

### Community 10 - "routes_registry.py"
Cohesion: 0.29
Nodes (10): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), One institution's claim on a number, with the basis for the claim., RegistryInstitution, RegistryLookupResponse (+2 more)

### Community 11 - "InMemoryCache"
Cohesion: 0.07
Nodes (16): Cache, CacheCapacityExceeded, get_cache(), InMemoryCache, Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one. (+8 more)

### Community 12 - "GreedyPlanner"
Cohesion: 0.09
Nodes (23): get_planner(), GreedyPlanner, Planner, Protocol, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, The loop must end and still produce a signed verdict. (+15 more)

### Community 13 - "announce.py"
Cohesion: 0.24
Nodes (13): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+5 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (17): Directory, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",…, The institution that published this number, or None. None means "not in the… (+9 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.08
Nodes (21): Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the…, An em dash looks like a rendering defect in a live demo, not the deliberate…, Behind a TLS-terminating tunnel, receipt_qr must see the forwarded scheme or it… (+13 more)

### Community 17 - "VerificationRequest"
Cohesion: 0.11
Nodes (29): form(), Read the request context and commit to a risk hypothesis. This is what makes…, Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), Money, field_validator, RequestContext, VerificationRequest (+21 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "test_s5_subject_binding.py"
Cohesion: 0.10
Nodes (32): check_startup_posture(), InsecureConfiguration, RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Refuse to start a billable deployment with no key or a published one. Only…, Settings, BaseSettings (+24 more)

### Community 20 - "SessionManager"
Cohesion: 0.14
Nodes (19): SessionStatus, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+11 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.08
Nodes (28): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+20 more)

### Community 23 - "test_retention.py"
Cohesion: 0.11
Nodes (26): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+18 more)

### Community 24 - "start_number_verification_consent"
Cohesion: 0.36
Nodes (10): _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), HTTPException, post, Receive the provider redirect; the authorization code is never exposed., Create a short-lived Number Verification authorization request. (+2 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (29): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, The two demo actions share state across runs. Resetting them locally prevents a…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the… (+21 more)

### Community 26 - "Action"
Cohesion: 0.11
Nodes (14): Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool. (+6 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "test_parallel_gather.py"
Cohesion: 0.16
Nodes (21): asyncio, Parallel evidence gathering — latency bought with cost. Opt-in per request.…, On a chain that spends its budget anyway the two are equal — the takeover case…, Speed must not change the answer., Two runs over the same evidence must produce the same number regardless of…, Local evidence is applied before the batch; both must land in the chain., Nothing changes for existing callers. The policy default is sequential., The whole point. Three 300ms calls should take about 300ms, not 900ms. (+13 more)

### Community 29 - "routes_consent.py"
Cohesion: 0.18
Nodes (10): build_investigator(), complete_number_verification(), _verification_response(), VerificationResponse, get_provider(), Select the evidence provider from config. ISNAD_PROVIDER=mock -> scripted…, FakeConsentProvider, A consent-specific completion must spend the consent on Number Verification.… (+2 more)

### Community 30 - "routes_verify.py"
Cohesion: 0.17
Nodes (14): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), _idempotency_state_response() (+6 more)

### Community 31 - "ConsentStore"
Cohesion: 0.15
Nodes (12): ConsentCapacityExceeded, ConsentRecord, ConsentStore, _now(), _owner_hash(), datetime, RuntimeError, Claim this consent for exactly one callback. A true compare-and-swap. The old… (+4 more)

### Community 32 - "test_privacy.py"
Cohesion: 0.18
Nodes (8): The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC…, Hard-coded prose drifts from the running system the first time someone tunes a…, A page that hard-codes '1 hour' is a page that will one day be wrong., The consent trail is inside the signed bytes already. Showing it is what turns…, test_caller_numbers_are_hashed_before_they_reach_retained_rows(), test_the_page_serves_and_pulls_its_numbers_from_the_endpoint(), test_the_posture_reports_the_retention_windows_actually_configured(), test_the_receipt_shows_the_consent_basis_of_every_link()

### Community 33 - "Decision"
Cohesion: 0.07
Nodes (43): deterministic(), _facts(), Everything the narrator may see. Enums, numbers, booleans., The always-available narrative. No model, no key, no network., EvidenceLink, _now(), BaseModel, datetime (+35 more)

### Community 34 - "investigator.py"
Cohesion: 0.12
Nodes (15): Small Gemini REST adapter shared by Isnad's optional AI features. The hackathon…, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., get_engine(), logodds_to_p(), Load the policy once and reuse it — avoids re-reading/parsing YAML per request., _install_retries() (+7 more)

### Community 35 - "mock.py"
Cohesion: 0.11
Nodes (19): detail_for(), The only sentences an evidence link may carry, and where each one comes from.…, The age window this action's question covered, if it has one. Mirrors the…, The max_age the swap checks are actually called with., The sentence for a signal, derived from the response and our parameters., _window(), window_hours(), parametrize (+11 more)

### Community 36 - "signing.py"
Cohesion: 0.15
Nodes (23): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+15 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 38 - "test_judge.py"
Cohesion: 0.18
Nodes (12): judge_page(), HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the… (+4 more)

### Community 39 - "rate_limit.py"
Cohesion: 0.35
Nodes (10): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+2 more)

### Community 40 - "store.py"
Cohesion: 0.18
Nodes (20): get_chain(), Replayable evidence — for COD dispute / chargeback resolution., owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord, get() (+12 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.08
Nodes (19): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files. (+11 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.19
Nodes (15): HybridProvider, Delegate to `fallback`, except for `actions` on `numbers`, which are real., _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, Exactly ONE live link. The rest of the chain must stay deterministic, or the…, The whole point. On stage, an exception here is a dead demo. (+7 more)

### Community 43 - "routes_session.py"
Cohesion: 0.21
Nodes (15): create_session(), end_session(), get_session(), post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.…, simulate_swap(), _to_response() (+7 more)

### Community 44 - "run_reverse"
Cohesion: 0.17
Nodes (16): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), asyncio, REGISTRY_MATCH_UNANNOUNCED is zeroed in policy.yaml on purpose., Act IV must not regress: adding local evidence to the chain must not rescue a…, The combination that matters: the bank's real number, announced, but the…, Both tiers consume. A client uses Tier 1 OR Tier 2 for a given call, and…, The standalone reverse-verify path must keep working — it is a public API in… (+8 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "_announce"
Cohesion: 0.13
Nodes (15): _announce(), The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call…, An institution announcing a call is telling this service who it is about to…, A non-spending read is for a party that already holds the use. Anyone else gets…, The cap is per announcement, not a lockout. A bank that really is calling twice…, test_a_published_inbound_only_number_cannot_be_announced_from() (+7 more)

### Community 47 - "get_record"
Cohesion: 0.20
Nodes (14): get_record(), _chain_for(), It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve., test_a_chain_issued_for_a_does_not_verify_against_b() (+6 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "VaultSigner"
Cohesion: 0.06
Nodes (33): InsecureVaultKey, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key is readable by someone other than its owner., Signs issued chains with Ed25519. The key is loaded from disk if present,…, _trusted_from_settings() (+25 more)

### Community 50 - "owner_hash"
Cohesion: 0.19
Nodes (14): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+6 more)

### Community 51 - "receipt_qr"
Cohesion: 0.20
Nodes (10): HTMLResponse, Request, The page a judge opens from the QR code., Give the QR a viewBox so it scales with its container., An inline SVG QR for this receipt's public URL. Generated server-side and…, The exact signed bytes, the signature, and the key that signed them. Public and…, receipt_data(), receipt_page() (+2 more)

### Community 52 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "test_false_decline_baseline.py"
Cohesion: 0.21
Nodes (11): _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and…, The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean line'.…, Guards against a baseline so blunt it declines everyone, which would make the…, The whole thesis is that these two rules disagree about an unanswered check. If…, test_a_clean_chain_declines_under_neither_baseline(), test_every_generated_case_differs_from_clean_in_exactly_one_check() (+3 more)

### Community 55 - "config.py"
Cohesion: 0.12
Nodes (19): Read-only entry point for the concise, judge-facing product demonstration. The…, _human(), posture(), Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page…, What this deployment keeps, for how long, and what it never holds., ASGIApp (+11 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.06
Nodes (36): Isnad — start here, Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean, Cases (+28 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.10
Nodes (20): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read… (+12 more)

### Community 60 - "resolve_key_path"
Cohesion: 0.13
Nodes (17): _key_passphrase(), MissingVaultKey, Path, RuntimeError, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, The signing key was expected on disk and was not there. (+9 more)

### Community 61 - "explain_chain"
Cohesion: 0.18
Nodes (11): verify_consent_chain(), explain_chain(), post, Evidence-vault check: recompute the signature over the stored chain and confirm…, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature…, verify_chain(), verify_chain_subject() (+3 more)

### Community 62 - "false_decline_baseline.py"
Cohesion: 0.33
Nodes (9): baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's…, The two rules being replaced, applied to a full evidence set. The baseline is…, Every single-signal case the policy vocabulary admits, plus a control., The operating curve, because the honest answer to "you allow some corroborated-…, run() (+1 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (20): model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy() (+12 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "events.py"
Cohesion: 0.09
Nodes (25): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), subscriber_count() (+17 more)

### Community 66 - ".__call__"
Cohesion: 0.50
Nodes (3): Receive, Scope, Send

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (57): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, Response, build_report() (+49 more)

### Community 68 - "velocity.py"
Cohesion: 0.19
Nodes (13): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, ScreenEventRow, _owner(), The tenant this request belongs to, set at the auth boundary (S2). (+5 more)

### Community 69 - "Result"
Cohesion: 0.14
Nodes (15): Result, str, _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeReachability, FakeSimSwap (+7 more)

### Community 70 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "_two_banks"
Cohesion: 0.18
Nodes (11): The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, test_a_bare_generic_word_is_not_a_match(), test_a_caller_who_describes_themselves_more_fully_still_matches(), test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution(), test_an_alias_is_matched_whole_and_not_merged_with_the_name() (+3 more)

### Community 73 - "routes_verified_caller.py"
Cohesion: 0.20
Nodes (15): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+7 more)

### Community 74 - "test_reverse.py"
Cohesion: 0.25
Nodes (6): asyncio, Reverse Isnad — verify an inbound caller to the customer (Act IV)., The real institution line is network-attested -> TRUST (ALLOW)., A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)., test_genuine_caller_is_trusted(), test_spoofed_caller_is_rejected()

### Community 75 - "db/models.py"
Cohesion: 0.18
Nodes (7): Base, AnnouncementUseRow, A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, One subscriber's single use of one announcement. A global counter was worse…, UtcDateTime, DeclarativeBase, TypeDecorator

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.15
Nodes (16): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+8 more)

### Community 78 - "bound_key"
Cohesion: 0.29
Nodes (7): bound_key(), _no_leftover_announcements(), fixture, The suite shares one in-memory database, so an announcement made by one test…, demo-merchant-key, bound to the institution that owns BANK_NUMBER., A registry holding Demo Bank and one other institution. The shipped registry…, two_bank_registry()

### Community 79 - "Choice"
Cohesion: 0.09
Nodes (18): Choice, effective_planner(), LLMPlanner, Observation, Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as…, The planner that will actually choose, not the one config asked for.… (+10 more)

### Community 80 - "test_independent_evaluation.py"
Cohesion: 0.22
Nodes (6): asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()

### Community 81 - "purge_older_than"
Cohesion: 0.38
Nodes (6): purge_older_than(), Drop events outside any window anyone will ask about. This table exists to…, console_token(), main(), Drive one number against many callees, so Act VII can show caller velocity. Run…, screen()

### Community 82 - "test_vault.py"
Cohesion: 0.43
Nodes (5): _make_chain(), Evidence vault — signed, tamper-evident chains., test_chain_persists_and_round_trips(), test_fresh_chain_verifies(), test_tampered_chain_fails_verification()

### Community 83 - "test_low_prior_allow_requires_a_supporting_fact_even_with_stop"
Cohesion: 0.33
Nodes (4): asyncio, parametrize, StopsImmediately, test_low_prior_allow_requires_a_supporting_fact_even_with_stop()

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

### Community 88 - "t1_probe.py"
Cohesion: 0.50
Nodes (4): describe(), main(), T1 — fire exactly ONE real CAMARA call and record what actually came back.…, Render an SDK response without assuming it is a dict or a pydantic model.

### Community 89 - "database.py"
Cohesion: 0.27
Nodes (8): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for

### Community 90 - "_reset_limiters"
Cohesion: 0.67
Nodes (3): fixture, These console checks deliberately make authenticated requests. Keep their…, _reset_limiters()

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **64 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 851 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_verified_caller.py`, `GreedyPlanner`, `VerificationRequest`, `SessionManager`, `test_t5_counterfactual.py`, `test_parallel_gather.py`, `routes_consent.py`, `Decision`, `investigator.py`, `mock.py`, `test_hybrid_provider.py`, `run_reverse`, `test_nac_contract.py`, `test_s9_consent_replay.py`, `test_audit_low.py`, `false_decline_baseline.py`, `independent_evaluation.py`, `evidence_pack.py`, `Result`, `Choice`, `test_low_prior_allow_requires_a_supporting_fact_even_with_stop`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `NacProvider` connect `Action` to `Decision`, `mock.py`, `Result`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `VerificationRequest`, `t1_probe.py`, `NaC integration — observed, not assumed`, `routes_consent.py`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `NaC integration — observed, not assumed` connect `NaC integration — observed, not assumed` to `console.html — live agent console`, `Action`, `Phase 2 Agent Runbook`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 34 INFERRED edges - model-reasoned connections that need verification._