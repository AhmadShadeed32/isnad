# Graph Report - isnad  (2026-09-05)

## Corpus Check
- 167 files · ~117,637 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2032 nodes · 4568 edges · 109 communities (86 shown, 5 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 451 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `568a8289`
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
- routes_registry.py
- InMemoryCache
- GreedyPlanner
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- RequestContext
- test_t4_ask_the_agent.py
- config.py
- MockProvider
- test_t5_counterfactual.py
- GeminiClient
- retention.py
- resolve_key_path
- test_act7.py
- NacProvider
- timeline.js
- Signal → log-odds vocabulary
- schemas.py
- test_parallel_gather.py
- routes_consent.py
- routes_verify.py
- VerificationRequest
- investigator.py
- store.py
- signing.py
- policy.yaml — the single tuning surface
- test_judge.py
- rate_limit.py
- explain_chain
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- routes_session.py
- test_false_decline_baseline.py
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- VaultSigner
- owner_hash
- UtcDateTime
- stream_token.py
- test_nac_contract.py
- velocity.py
- Isnad · إسناد
- console.html — live agent console
- test_s9_consent_replay.py
- test_audit_low.py
- test_registry.py
- Decision
- independent_evaluation.py
- Project Brief
- test_s2_stream_isolation.py
- init_db
- Verdict
- Action
- events.py
- Phase 2 Agent Runbook
- _two_banks
- routes_verified_caller.py
- test_s14_no_tracked_secrets.py
- demo_token.py
- LLMPlanner
- test_privacy.py
- test_vault.py
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- t1_probe.py
- _secure_sqlite_files
- NaC integration — observed, not assumed
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_s4_demo_mode.py
- get
- isnad
- Isnad (إسناد) — project brief

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

## Communities (109 total, 5 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.07
Nodes (47): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, _engine(), _investigator(), asyncio, chain_grade — what the chain itself was worth, beside what the caller should…, Belief cleared overall, but one check pushed toward fraud — that chain is not…, The gate exists so a stolen key is not an instant pass. It counted network… (+39 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (34): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+26 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.07
Nodes (11): p_to_logodds(), PolicyEngine, Path, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain. (+3 more)

### Community 3 - "main.py"
Cohesion: 0.08
Nodes (25): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+17 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.11
Nodes (40): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+32 more)

### Community 5 - "Investigator"
Cohesion: 0.10
Nodes (19): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+11 more)

### Community 6 - "_written"
Cohesion: 0.10
Nodes (21): Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and…, An institution may publish a block inside a block — a branch range carved out… (+13 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.12
Nodes (39): distinct_callees(), is_high_velocity(), How many different people this number has been screened against lately.…, (over_threshold, observed, threshold). Threshold 0 disables the check., _as(), _burst(), _clean(), _engine() (+31 more)

### Community 8 - "test_nac_provider.py"
Cohesion: 0.15
Nodes (13): _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeReachability, FakeSimSwap, _provider(), asyncio (+5 more)

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
Cohesion: 0.08
Nodes (25): get_planner(), GreedyPlanner, Planner, Protocol, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, The loop must end and still produce a signed verdict. (+17 more)

### Community 13 - "announce.py"
Cohesion: 0.10
Nodes (29): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+21 more)

### Community 14 - "Directory"
Cohesion: 0.08
Nodes (25): Directory, get_directory(), _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside. (+17 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (25): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+17 more)

### Community 17 - "RequestContext"
Cohesion: 0.15
Nodes (20): form(), Read the request context and commit to a risk hypothesis. This is what makes…, Money, field_validator, RequestContext, _investigator(), asyncio, End-to-end scenario tests — the demo's three acts run the real engine. These… (+12 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "config.py"
Cohesion: 0.11
Nodes (33): check_startup_posture(), InsecureConfiguration, makes_billable_calls(), RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Can a request cause a real, paid CAMARA call to leave this process? Keyed on…, Refuse to start a billable deployment with no key or a published one. Only… (+25 more)

### Community 20 - "MockProvider"
Cohesion: 0.12
Nodes (22): SessionStatus, MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned. (+14 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.10
Nodes (21): GeminiClient, GeminiError, Any, RuntimeError, Small Gemini REST adapter shared by Isnad's optional AI features. The hackathon…, The provider did not return usable candidate text., Minimal synchronous client for a single Gemini content-generation turn., Return a JSON object, or raise so the caller can use its fallback. (+13 more)

### Community 23 - "retention.py"
Cohesion: 0.14
Nodes (16): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+8 more)

### Community 24 - "resolve_key_path"
Cohesion: 0.18
Nodes (12): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+4 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (27): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not… (+19 more)

### Community 26 - "NacProvider"
Cohesion: 0.16
Nodes (8): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., nac.py's _as_url returned any string the SDK provided., test_a_non_https_authorization_url_is_refused()

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "Signal → log-odds vocabulary"
Cohesion: 0.18
Nodes (10): OTP_CONFIRMED — reserved, nothing emits it, REGISTRY_MATCH_UNANNOUNCED = 0.0, Signal → log-odds vocabulary, registry.yaml — institution number registry, Nothing in the registry is a real bank number, Inbound-only hotline as a spoof signal, Registry provenance is mandatory (basis / source / verified_on), showReceiptQr() (+2 more)

### Community 29 - "schemas.py"
Cohesion: 0.09
Nodes (30): post, Investigate an inbound caller with the impersonation hypothesis. Same engine as…, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), run_reverse(), Alternative, Area, ExplainRequest (+22 more)

### Community 30 - "test_parallel_gather.py"
Cohesion: 0.16
Nodes (21): asyncio, Parallel evidence gathering — latency bought with cost. Opt-in per request.…, On a chain that spends its budget anyway the two are equal — the takeover case…, Speed must not change the answer., Two runs over the same evidence must produce the same number regardless of…, Local evidence is applied before the batch; both must land in the chain., Nothing changes for existing callers. The policy default is sequential., The whole point. Three 300ms calls should take about 300ms, not 900ms. (+13 more)

### Community 31 - "routes_consent.py"
Cohesion: 0.10
Nodes (30): get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), HTTPException (+22 more)

### Community 32 - "routes_verify.py"
Cohesion: 0.10
Nodes (30): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, console_run(), Trigger a demo act server-side (paced), emitting to the live stream. Demo-only,…, _idempotency_state_response(), Replay a completed state or reject a conflicting/in-flight one. One cache entry…, The one call: 'Can I trust this interaction?' -> ALLOW / CHALLENGE / DECLINE…, verify() (+22 more)

### Community 33 - "VerificationRequest"
Cohesion: 0.16
Nodes (14): VerificationRequest, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, _csv(), HybridProvider, Scripted evidence, except for the links deliberately made real. Every winner…, Delegate to `fallback`, except for `actions` on `numbers`, which are real. (+6 more)

### Community 34 - "investigator.py"
Cohesion: 0.16
Nodes (12): build_investigator(), get_engine(), Load the policy once and reuse it — avoids re-reading/parsing YAML per request., _install_retries(), main(), Measure how differently the LLM planner behaves from the greedy one. This…, Give the provider every chance to answer, for measurement runs only. The demo…, _verdict() (+4 more)

### Community 35 - "store.py"
Cohesion: 0.21
Nodes (17): owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord, get_public_record(), get_public_record_async(), get_record_async() (+9 more)

### Community 36 - "signing.py"
Cohesion: 0.19
Nodes (19): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+11 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.25
Nodes (9): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP counterfactual pricing block, step_up_otp — priced, never selected, Caller velocity — the cross-subscriber signal (+1 more)

### Community 38 - "test_judge.py"
Cohesion: 0.24
Nodes (9): _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the…, _reset_limiters(), test_judge_page_is_a_checkout_to_signed_receipt_story(), test_judge_page_mints_a_short_lived_token_only_in_demo_mode() (+1 more)

### Community 39 - "rate_limit.py"
Cohesion: 0.18
Nodes (16): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+8 more)

### Community 40 - "explain_chain"
Cohesion: 0.40
Nodes (5): explain_chain(), post, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature…, verify_chain_subject()

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.08
Nodes (19): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files. (+11 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.25
Nodes (13): _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, Exactly ONE live link. The rest of the chain must stay deterministic, or the…, The whole point. On stage, an exception here is a dead demo., The resting state is fully scripted: someone who sets ISNAD_PROVIDER without…, _Stub (+5 more)

### Community 43 - "routes_session.py"
Cohesion: 0.21
Nodes (15): create_session(), end_session(), get_session(), post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.…, simulate_swap(), _to_response() (+7 more)

### Community 44 - "test_false_decline_baseline.py"
Cohesion: 0.36
Nodes (7): _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and…, The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean line'.…, test_every_generated_case_differs_from_clean_in_exactly_one_check(), test_the_corroborated_group_holds_two_distinct_checks(), test_the_population_comes_from_the_policy_not_from_a_hand_picked_list()

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.06
Nodes (56): _announce(), bound_key(), _no_leftover_announcements(), asyncio, fixture, Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it… (+48 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.21
Nodes (15): get_record(), _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve. (+7 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "VaultSigner"
Cohesion: 0.06
Nodes (38): InsecureVaultKey, MissingVaultKey, RuntimeError, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key was expected on disk and was not there. (+30 more)

### Community 50 - "owner_hash"
Cohesion: 0.19
Nodes (14): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+6 more)

### Community 51 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 52 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "velocity.py"
Cohesion: 0.14
Nodes (17): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), _owner(), purge_older_than(), The tenant this request belongs to, set at the auth boundary (S2)., Note that this caller was screened against this callee, for this tenant. (+9 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.05
Nodes (38): Isnad — start here, Inputs still needed for a live handset proof, Live procedure, Number Verification handset validation, Pass criteria, Safe local proof (no operator, handset, or network call), What “handset consent” and “callback” mean, Cases (+30 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.24
Nodes (10): investigate(), console.html — live agent console, askTheAgent(), judge.html — Judge Mode verified checkout, runCheckout(), Trust with a TTL (session revocation), 90-second judge demo script, Video script — rendered cut and live take (+2 more)

### Community 58 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.10
Nodes (20): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read… (+12 more)

### Community 61 - "test_registry.py"
Cohesion: 0.08
Nodes (26): _directory(), The number registry — which published numbers belong to which institution. The…, Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., "Not found" is only readable next to the size of the thing that failed to find… (+18 more)

### Community 62 - "Decision"
Cohesion: 0.11
Nodes (22): Decision, Enum, baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's…, The two rules being replaced, applied to a full evidence set. The baseline is…, Every single-signal case the policy vocabulary admits, plus a control. (+14 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (21): logodds_to_p(), model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec (+13 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "test_s2_stream_isolation.py"
Cohesion: 0.20
Nodes (12): subscriber_count(), asyncio, S2 — the SSE stream must be authenticated and must not cross tenants., End to end through the HTTP surface, not just the bus., A disconnect that is never noticed must not pin memory forever (S12)., The finding, verbatim: `curl -N /v1/console/stream` harvested everything., A background emit with no owner must not fan out to a real tenant., test_a_subscriber_never_sees_an_event_emitted_for_nobody() (+4 more)

### Community 67 - "init_db"
Cohesion: 0.09
Nodes (41): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, Response, _assert_status() (+33 more)

### Community 68 - "Verdict"
Cohesion: 0.11
Nodes (22): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+14 more)

### Community 69 - "Action"
Cohesion: 0.08
Nodes (36): EvidenceLink, One attested link in the chain — the normalized result of one CAMARA call.…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, Result, detail_for(), The only sentences an evidence link may carry, and where each one comes from.…, The age window this action's question covered, if it has one. Mirrors the… (+28 more)

### Community 70 - "events.py"
Cohesion: 0.14
Nodes (13): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), asyncio (+5 more)

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "_two_banks"
Cohesion: 0.18
Nodes (11): The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, test_a_bare_generic_word_is_not_a_match(), test_a_caller_who_describes_themselves_more_fully_still_matches(), test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution(), test_an_alias_is_matched_whole_and_not_merged_with_the_name() (+3 more)

### Community 73 - "routes_verified_caller.py"
Cohesion: 0.24
Nodes (12): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+4 more)

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.13
Nodes (19): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+11 more)

### Community 79 - "LLMPlanner"
Cohesion: 0.12
Nodes (12): effective_planner(), LLMPlanner, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as… (+4 more)

### Community 81 - "test_privacy.py"
Cohesion: 0.18
Nodes (8): The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC…, Hard-coded prose drifts from the running system the first time someone tunes a…, A page that hard-codes '1 hour' is a page that will one day be wrong., The consent trail is inside the signed bytes already. Showing it is what turns…, test_caller_numbers_are_hashed_before_they_reach_retained_rows(), test_the_page_serves_and_pulls_its_numbers_from_the_endpoint(), test_the_posture_reports_the_retention_windows_actually_configured(), test_the_receipt_shows_the_consent_basis_of_every_link()

### Community 82 - "test_vault.py"
Cohesion: 0.43
Nodes (5): _make_chain(), Evidence vault — signed, tamper-evident chains., test_chain_persists_and_round_trips(), test_fresh_chain_verifies(), test_tampered_chain_fails_verification()

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

### Community 89 - "_secure_sqlite_files"
Cohesion: 0.29
Nodes (8): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 110 - "get"
Cohesion: 0.12
Nodes (21): verify_consent_chain(), privacy_page(), HTMLResponse, HTMLResponse, Request, The page a judge opens from the QR code., Give the QR a viewBox so it scales with its container., An inline SVG QR for this receipt's public URL. Generated server-side and… (+13 more)

### Community 116 - "Isnad (إسناد) — project brief"
Cohesion: 0.29
Nodes (6): How it works, Isnad (إسناد) — project brief, Measured, State, The problem, What it is

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **66 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 853 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_nac_provider.py`, `GreedyPlanner`, `RequestContext`, `MockProvider`, `test_t5_counterfactual.py`, `NacProvider`, `test_parallel_gather.py`, `routes_consent.py`, `VerificationRequest`, `investigator.py`, `test_hybrid_provider.py`, `test_verified_caller.py`, `test_nac_contract.py`, `test_s9_consent_replay.py`, `test_audit_low.py`, `Decision`, `independent_evaluation.py`, `init_db`, `Verdict`, `LLMPlanner`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Action`, `Phase 2 Agent Runbook`, `test_nac_provider.py`, `test_s12_runtime_posture.py`, `t1_probe.py`, `NaC integration — observed, not assumed`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `Isnad · إسناد`, `NaC integration — observed, not assumed`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 34 INFERRED edges - model-reasoned connections that need verification._