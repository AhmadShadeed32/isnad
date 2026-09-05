# Graph Report - isnad  (2026-09-05)

## Corpus Check
- 168 files · ~132,225 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2066 nodes · 4682 edges · 130 communities (105 shown, 7 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 494 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cb4c57d3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_chain_grade.py
- test_t6_receipt.py
- PolicyEngine
- main.py
- test_llm_planner.py
- Investigator
- _written
- test_velocity.py
- test_nac_provider.py
- routes_console.py
- Choice
- cache.py
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
- run_reverse
- test_act7.py
- NacProvider
- timeline.js
- routes_session.py
- test_reverse.py
- MockProvider
- ConsentStore
- routes_consent.py
- schemas.py
- VerificationRequest
- store.py
- signing.py
- policy.yaml — the single tuning surface
- test_judge.py
- rate_limit.py
- get
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- InMemoryCache
- Action
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- owner_hash
- test_s11_claimed_identity.py
- db/models.py
- stream_token.py
- test_nac_contract.py
- purge_older_than
- VaultSigner
- Isnad · إسناد
- console.html — live agent console
- test_s9_consent_replay.py
- test_audit_low.py
- bound_key
- _directory
- .create
- independent_evaluation.py
- Project Brief
- events.py
- vault.py
- evidence_pack.py
- Verdict
- test_provider_vocabulary.py
- test_hardening.py
- Phase 2 Agent Runbook
- test_registry.py
- routes_verified_caller.py
- SlidingWindowLimiter
- test_retention.py
- test_s14_no_tracked_secrets.py
- demo_token.py
- test_an_unreadable_signature_is_tampering_not_absence
- LLMPlanner
- consent.py
- velocity.py
- test_vault.py
- CURRENT_STATE.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- routes_receipt.py
- database.py
- 3. Recommended app work — not implemented in this documentation pass
- NaC integration — observed, not assumed
- test_privacy.py
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_s4_demo_mode.py
- routes_privacy.py
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- Isnad — compact handoff
- What the risk score means
- routes_registry.py
- Signal → log-odds vocabulary
- .trusts
- test_independent_evaluation.py
- .__call__
- _as_the_merchant
- test_a_clean_prior_still_records_the_policy_required_network_check

## God Nodes (most connected - your core abstractions)
1. `Action` - 130 edges
2. `VerificationRequest` - 81 edges
3. `MockProvider` - 74 edges
4. `Result` - 65 edges
5. `Decision` - 62 edges
6. `PolicyEngine` - 57 edges
7. `Hypothesis` - 56 edges
8. `RequestContext` - 48 edges
9. `EvidenceLink` - 46 edges
10. `Verdict` - 42 edges

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

## Communities (130 total, 7 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.06
Nodes (52): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, Money, field_validator, p_to_logodds(), _engine(), _gate(), _investigator() (+44 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (34): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+26 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.07
Nodes (11): PolicyEngine, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain., Checks to attempt before this signal alone may carry a DECLINE. The counterpart…, How many actions to fire at once in parallel mode. Bounded: a batch larger than… (+3 more)

### Community 3 - "main.py"
Cohesion: 0.09
Nodes (23): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+15 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.11
Nodes (38): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+30 more)

### Community 5 - "Investigator"
Cohesion: 0.18
Nodes (10): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+2 more)

### Community 6 - "_written"
Cohesion: 0.10
Nodes (21): Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and…, An institution may publish a block inside a block — a branch range carved out… (+13 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.07
Nodes (51): get_engine(), Path, Load the policy once and reuse it — avoids re-reading/parsing YAML per request., distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., Regression tests for audit fixes: engine caching + auth hardening. (+43 more)

### Community 8 - "test_nac_provider.py"
Cohesion: 0.15
Nodes (13): _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeReachability, FakeSimSwap, _provider(), asyncio (+5 more)

### Community 9 - "routes_console.py"
Cohesion: 0.18
Nodes (18): act7_announce(), _act7_emit(), _act7_key(), act7_screen(), console_stream_token(), post, Exchange a normal bearer key for a short-lived SSE-only credential. Browser…, Same gate as console_run: demo mode, plus a valid console token. (+10 more)

### Community 10 - "Choice"
Cohesion: 0.12
Nodes (10): Choice, Planner, Protocol, What the planner decided, and why, and who decided it., StopsImmediately, _StopsImmediately, The loop must end and still produce a signed verdict., A run that started on the model and fell back must not read as pure llm. (+2 more)

### Community 11 - "cache.py"
Cohesion: 0.12
Nodes (8): Cache, CacheCapacityExceeded, get_cache(), Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one., RedisCache

### Community 12 - "GreedyPlanner"
Cohesion: 0.12
Nodes (19): get_planner(), GreedyPlanner, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, test_the_factory_still_selects_by_config(), _engine(), asyncio (+11 more)

### Community 13 - "announce.py"
Cohesion: 0.21
Nodes (15): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+7 more)

### Community 14 - "Directory"
Cohesion: 0.09
Nodes (21): Directory, get_directory(), _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside. (+13 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (27): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+19 more)

### Community 17 - "Decision"
Cohesion: 0.09
Nodes (32): Decision, Area, A claimed location — never a tracked coordinate. Used only for yes/no verify., Enum, baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's… (+24 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "check_startup_posture"
Cohesion: 0.11
Nodes (32): clear(), check_startup_posture(), InsecureConfiguration, makes_billable_calls(), RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Can a request cause a real, paid CAMARA call to leave this process? Keyed on… (+24 more)

### Community 20 - "SessionManager"
Cohesion: 0.24
Nodes (14): SessionStatus, trip_swap(), Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, SessionManager, _clean_trips(), asyncio, fixture, Trust-with-a-TTL: live session revocation. (+6 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.11
Nodes (20): GeminiClient, GeminiError, Any, RuntimeError, The provider did not return usable candidate text., Minimal synchronous client for a single Gemini content-generation turn., Return a JSON object, or raise so the caller can use its fallback., Return candidate text for display-only explanation features. (+12 more)

### Community 23 - "retention.py"
Cohesion: 0.18
Nodes (13): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+5 more)

### Community 24 - "run_reverse"
Cohesion: 0.14
Nodes (19): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), asyncio, The whole point of the act, in one assertion: the registry resolves it, the…, test_the_landline_is_known_by_name_but_not_by_the_network(), asyncio, REGISTRY_MATCH_UNANNOUNCED is zeroed in policy.yaml on purpose., Act IV must not regress: adding local evidence to the chain must not rescue a… (+11 more)

### Community 25 - "test_act7.py"
Cohesion: 0.09
Nodes (26): _no_leftover_announcements(), fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, The two demo actions share state across runs. Resetting them locally prevents a…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not… (+18 more)

### Community 26 - "NacProvider"
Cohesion: 0.09
Nodes (16): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., main(), T1 — call every CAMARA action for real and record what came back. The runbook's… (+8 more)

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.16
Nodes (21): get_live_provider(), key_from_bearer(), owner_for(), Merchant API-key auth: `Authorization: Bearer <key>`., The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., Resolve the configured provider as an API-level 503 when unavailable., require_api_key() (+13 more)

### Community 29 - "test_reverse.py"
Cohesion: 0.25
Nodes (6): asyncio, Reverse Isnad — verify an inbound caller to the customer (Act IV)., The real institution line is network-attested -> TRUST (ALLOW)., A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)., test_genuine_caller_is_trusted(), test_spoofed_caller_is_rejected()

### Community 30 - "MockProvider"
Cohesion: 0.13
Nodes (29): build_investigator(), console_run(), Trigger a demo act server-side (paced), emitting to the live stream. Demo-only,…, MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, Scenario, asyncio, Parallel evidence gathering — latency bought with cost. Opt-in per request.… (+21 more)

### Community 31 - "ConsentStore"
Cohesion: 0.25
Nodes (4): ConsentRecord, ConsentStore, Claim this consent for exactly one callback. A true compare-and-swap. The old…, Short-lived consent state; tokens never leave this process or API response.

### Community 32 - "routes_consent.py"
Cohesion: 0.08
Nodes (46): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), HTTPException (+38 more)

### Community 33 - "schemas.py"
Cohesion: 0.13
Nodes (17): post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), _now(), datetime, ReverseVerificationRequest, ReverseVerificationResponse, ScreenResponse (+9 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.17
Nodes (22): Result, RequestContext, VerificationRequest, _FailingLocationVerify, _FakeClient, _FakeLocationVerify, _nac_provider(), asyncio (+14 more)

### Community 35 - "store.py"
Cohesion: 0.22
Nodes (18): owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord, get_public_record(), get_public_record_async(), get_record() (+10 more)

### Community 36 - "signing.py"
Cohesion: 0.17
Nodes (21): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+13 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 38 - "test_judge.py"
Cohesion: 0.18
Nodes (12): judge_page(), HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the… (+4 more)

### Community 39 - "rate_limit.py"
Cohesion: 0.28
Nodes (11): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+3 more)

### Community 40 - "get"
Cohesion: 0.20
Nodes (11): verify_consent_chain(), console_mode(), What the console needs to label the run honestly. Behind a key because /health…, get_chain(), Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, The public key anyone can use to independently verify a chain signature., vault_public_key() (+3 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.11
Nodes (16): asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Held entries for 24h and was swept only on a get of the same key., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files., /docs, /redoc and /openapi.json all answered 200 unauthenticated., It told an attacker whether calls cost money and whether demo was live., store.* is called from async handlers; SQLite writes block. Under any… (+8 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.18
Nodes (18): _cfg(), _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, `check_startup_posture` guarded `provider == "nac"` only. `hybrid` makes real,…, Both lists empty is a MockProvider with extra steps — no call can leave the…, Exactly ONE live link. The rest of the chain must stay deterministic, or the… (+10 more)

### Community 43 - "InMemoryCache"
Cohesion: 0.18
Nodes (6): InMemoryCache, Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one., Drop what has expired; if nothing has, drop the oldest inserted., test_in_memory_cache_ttl()

### Community 44 - "Action"
Cohesion: 0.09
Nodes (23): EvidenceLink, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, HybridProvider, Delegate to `fallback`, except for `actions` on `numbers`, which are real., get_provider(), Select the evidence provider from config. ISNAD_PROVIDER=mock -> scripted… (+15 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.09
Nodes (37): _announce(), Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call…, The window is the spoofing opportunity: while an announcement stands, a call…, Matching the caller alone would let one genuine announcement verify a burst of…, An institution announcing a call is telling this service who it is about to… (+29 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.16
Nodes (16): _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., An old row must parse, and must never claim to be about a number., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve. (+8 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "owner_hash"
Cohesion: 0.16
Nodes (16): owner_hash(), RuntimeError, This owner already has as many live sessions as it is allowed., SessionQuotaExceeded, asyncio, S7 — the two unbounded amplifiers: session quota, and the key file mode., `_sessions` was never pruned, so it grew for the life of the process., The acceptance criterion: stat the key -> 600, the directory -> 700. It was… (+8 more)

### Community 50 - "test_s11_claimed_identity.py"
Cohesion: 0.27
Nodes (10): S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge(), test_ordinary_organisation_names_still_pass() (+2 more)

### Community 51 - "db/models.py"
Cohesion: 0.18
Nodes (7): Base, AnnouncementUseRow, A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, One subscriber's single use of one announcement. A global counter was worse…, UtcDateTime, DeclarativeBase, TypeDecorator

### Community 52 - "stream_token.py"
Cohesion: 0.13
Nodes (17): console_stream(), Server-Sent Events stream of the live agent console. Each verification emits:…, clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential. (+9 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "purge_older_than"
Cohesion: 0.38
Nodes (6): purge_older_than(), Drop events outside any window anyone will ask about. This table exists to…, console_token(), main(), Drive one number against many callees, so Act VII can show caller velocity. Run…, screen()

### Community 55 - "VaultSigner"
Cohesion: 0.10
Nodes (22): InsecureVaultKey, MissingVaultKey, RuntimeError, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key was expected on disk and was not there., The signing key is readable by someone other than its owner., Signs issued chains with Ed25519. The key is loaded from disk if present,…, VaultSigner (+14 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.18
Nodes (11): A changed SIM should start an investigation., A receipt that can be challenged, too, Every check has a job, Evidence you can rerun, Isnad · إسناد, One integration, an explainable action, One warning. Two very different checkouts., Simulated answers. The same investigation. (+3 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "test_s9_consent_replay.py"
Cohesion: 0.21
Nodes (13): S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., The acceptance criterion: a replayed callback returns 409. The attacker's path:…, by_state() used to keep resolving after use., _start_consent(), test_a_denied_consent_also_burns_its_state() (+5 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.11
Nodes (18): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read…, policy.yaml says "opt in per request, never globally" and no route let anyone… (+10 more)

### Community 60 - "bound_key"
Cohesion: 0.29
Nodes (7): bound_key(), _no_leftover_announcements(), fixture, The suite shares one in-memory database, so an announcement made by one test…, demo-merchant-key, bound to the institution that owns BANK_NUMBER., A registry holding Demo Bank and one other institution. The shipped registry…, two_bank_registry()

### Community 61 - "_directory"
Cohesion: 0.13
Nodes (15): _directory(), Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., Institutions own ranges, not single numbers. A registry of exact numbers alone…, test_a_published_inbound_only_line_is_flagged_as_never_outbound() (+7 more)

### Community 62 - ".create"
Cohesion: 0.26
Nodes (5): _now(), datetime, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionRecord

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (21): logodds_to_p(), model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec (+13 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "events.py"
Cohesion: 0.14
Nodes (19): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), subscriber_count() (+11 more)

### Community 66 - "vault.py"
Cohesion: 0.20
Nodes (11): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+3 more)

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (57): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, Response, build_report() (+49 more)

### Community 68 - "Verdict"
Cohesion: 0.12
Nodes (19): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+11 more)

### Community 69 - "test_provider_vocabulary.py"
Cohesion: 0.16
Nodes (12): detail_for(), The sentence for a signal, derived from the response and our parameters., parametrize, A fixture may only say what a CAMARA API can return. This is the test that…, No Nokia adapter exists, so no scenario may return a reputation., CAMARA answers a boolean against max_age. It cannot date the swap., The signal vocabulary is the one the real captures came back with., test_device_intelligence_is_never_a_verdict() (+4 more)

### Community 70 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "test_registry.py"
Cohesion: 0.08
Nodes (23): The number registry — which published numbers belong to which institution. The…, The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, "Not found" is only readable next to the size of the thing that failed to find…, S11 — caller-controlled text is compared, never rendered. The response says…, Guards the one mistake that would matter: a demo fixture shipping as a… (+15 more)

### Community 73 - "routes_verified_caller.py"
Cohesion: 0.33
Nodes (8): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse

### Community 74 - "SlidingWindowLimiter"
Cohesion: 0.20
Nodes (6): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, test_the_limiter_bucket_map_is_bounded(), test_the_window_actually_slides()

### Community 75 - "test_retention.py"
Cohesion: 0.24
Nodes (11): _age_announcements(), _counts(), asyncio, Retention — the sweeper that finally has a caller. `announce.purge_expired()`…, A transient database error must not end the loop. Nothing else in the process…, The whole point of this file: the purges have a caller now. The boot sweep…, `announcement_uses` has no foreign key, so deleting the announcements alone…, test_one_sweep_clears_both_tables() (+3 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.21
Nodes (11): is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep(), console_page() (+3 more)

### Community 79 - "LLMPlanner"
Cohesion: 0.08
Nodes (23): form(), Read the request context and commit to a risk hypothesis. This is what makes…, effective_planner(), LLMPlanner, Observation, PlannerResponse, BaseModel, The only shape the model is allowed to answer in. (+15 more)

### Community 80 - "consent.py"
Cohesion: 0.29
Nodes (7): ConsentCapacityExceeded, _now(), _owner_hash(), datetime, RuntimeError, A live consent cannot be retained without displacing another one., Drop expired and terminal records. Caller holds the lock.

### Community 81 - "velocity.py"
Cohesion: 0.23
Nodes (11): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, ScreenEventRow, _owner(), The tenant this request belongs to, set at the auth boundary (S2). (+3 more)

### Community 82 - "test_vault.py"
Cohesion: 0.43
Nodes (5): _make_chain(), Evidence vault — signed, tamper-evident chains., test_chain_persists_and_round_trips(), test_fresh_chain_verifies(), test_tampered_chain_fails_verification()

### Community 83 - "CURRENT_STATE.md"
Cohesion: 0.40
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

### Community 88 - "routes_receipt.py"
Cohesion: 0.24
Nodes (10): HTMLResponse, Request, The page a judge opens from the QR code., Give the QR a viewBox so it scales with its container., An inline SVG QR for this receipt's public URL. Generated server-side and…, The exact signed bytes, the signature, and the key that signed them. Public and…, receipt_data(), receipt_page() (+2 more)

### Community 89 - "database.py"
Cohesion: 0.27
Nodes (8): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for

### Community 90 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 92 - "test_privacy.py"
Cohesion: 0.18
Nodes (8): The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC…, Hard-coded prose drifts from the running system the first time someone tunes a…, A page that hard-codes '1 hour' is a page that will one day be wrong., The consent trail is inside the signed bytes already. Showing it is what turns…, test_caller_numbers_are_hashed_before_they_reach_retained_rows(), test_the_page_serves_and_pulls_its_numbers_from_the_endpoint(), test_the_posture_reports_the_retention_windows_actually_configured(), test_the_receipt_shows_the_consent_basis_of_every_link()

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 110 - "routes_privacy.py"
Cohesion: 0.22
Nodes (8): _human(), posture(), privacy_page(), HTMLResponse, Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page…, What this deployment keeps, for how long, and what it never holds.

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

### Community 117 - "Number Verification handset validation"
Cohesion: 0.33
Nodes (6): Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean

### Community 119 - "Fixed synthetic evaluation"
Cohesion: 0.33
Nodes (6): Cases, Fixed synthetic evaluation, Limits, Measured result, Reproduce it, What it compares

### Community 120 - "Isnad — compact handoff"
Cohesion: 0.33
Nodes (6): 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 4. Path to a live product, 5. Code map and working rules, 6. Latest session, Isnad — compact handoff

### Community 121 - "What the risk score means"
Cohesion: 0.50
Nodes (4): Correlation is an open evaluation concern, How it is calculated, What the risk score means, What would establish a useful probability

### Community 123 - "routes_registry.py"
Cohesion: 0.29
Nodes (10): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), One institution's claim on a number, with the basis for the claim., RegistryInstitution, RegistryLookupResponse (+2 more)

### Community 124 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 125 - ".trusts"
Cohesion: 0.20
Nodes (6): Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, _trusted_from_settings(), _verify_with_key(), Ed25519PublicKey

### Community 126 - "test_independent_evaluation.py"
Cohesion: 0.22
Nodes (6): asyncio, The fixed synthetic evaluation must expose disagreements, not hide them., test_corroboration_baseline_does_not_double_count_one_change_event(), test_fixed_cases_cover_the_risky_shapes_the_report_claims(), test_report_accounts_for_every_case_call_and_disagreement(), test_unavailable_evidence_is_a_gap_and_never_an_adverse_vote()

### Community 127 - ".__call__"
Cohesion: 0.50
Nodes (3): Receive, Scope, Send

### Community 128 - "_as_the_merchant"
Cohesion: 0.67
Nodes (3): _as_the_merchant(), fixture, Read chains directly as the key that created them. store.get_record() is scoped…

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **73 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 869 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_velocity.py`, `test_nac_provider.py`, `Choice`, `GreedyPlanner`, `Directory`, `Decision`, `SessionManager`, `test_t5_counterfactual.py`, `run_reverse`, `NacProvider`, `MockProvider`, `routes_consent.py`, `schemas.py`, `VerificationRequest`, `test_hybrid_provider.py`, `test_verified_caller.py`, `test_nac_contract.py`, `test_s9_consent_replay.py`, `test_audit_low.py`, `independent_evaluation.py`, `evidence_pack.py`, `Verdict`, `test_provider_vocabulary.py`, `LLMPlanner`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `NacProvider` connect `NacProvider` to `schemas.py`, `VerificationRequest`, `Phase 2 Agent Runbook`, `test_nac_provider.py`, `test_s12_runtime_posture.py`, `Action`, `NaC integration — observed, not assumed`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `MockProvider` connect `MockProvider` to `test_chain_grade.py`, `test_velocity.py`, `routes_console.py`, `test_console.py`, `Decision`, `SessionManager`, `run_reverse`, `test_act7.py`, `test_reverse.py`, `schemas.py`, `VerificationRequest`, `Action`, `test_verified_caller.py`, `owner_hash`, `independent_evaluation.py`, `Project Brief`, `evidence_pack.py`, `Verdict`, `Phase 2 Agent Runbook`, `LLMPlanner`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 38 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 38 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 39 INFERRED edges - model-reasoned connections that need verification._