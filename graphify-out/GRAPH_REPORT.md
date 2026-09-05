# Graph Report - isnad  (2026-09-05)

## Corpus Check
- 167 files · ~131,184 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2040 nodes · 4576 edges · 123 communities (98 shown, 7 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 451 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `942dcc24`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_chain_grade.py
- test_t6_receipt.py
- Action
- main.py
- test_llm_planner.py
- Investigator
- test_registry.py
- test_velocity.py
- VerificationRequest
- routes_console.py
- Choice
- cache.py
- GreedyPlanner
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- RequestContext
- test_t4_ask_the_agent.py
- config.py
- SessionManager
- test_t5_counterfactual.py
- GeminiClient
- retention.py
- MockProvider
- test_act7.py
- NacProvider
- timeline.js
- routes_session.py
- test_reverse.py
- build_investigator
- ConsentStore
- routes_consent.py
- schemas.py
- investigator.py
- store.py
- signing.py
- policy.yaml — the single tuning surface
- test_judge.py
- rate_limit.py
- routes_verify.py
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- InMemoryCache
- Result
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- VaultSigner
- owner_hash
- UtcDateTime
- stream_token.py
- test_nac_contract.py
- purge_older_than
- test_s6_vault_keys.py
- Isnad · إسناد
- console.html — live agent console
- test_s9_consent_replay.py
- test_audit_low.py
- bound_key
- _directory
- false_decline_baseline.py
- Decision
- Project Brief
- events.py
- resolve_key_path
- evidence_pack.py
- Verdict
- mock.py
- test_hardening.py
- Phase 2 Agent Runbook
- _two_banks
- routes_verified_caller.py
- SlidingWindowLimiter
- test_a_tampered_registry_refuses_to_load
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
- t1_probe.py
- _secure_sqlite_files
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

## Communities (123 total, 7 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.06
Nodes (51): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, p_to_logodds(), Prior for Reverse Isnad: an unverified inbound caller starts uncertain., _engine(), _gate(), _investigator(), _link() (+43 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (36): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+28 more)

### Community 2 - "Action"
Cohesion: 0.07
Nodes (18): Planner, Protocol, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, PolicyEngine, Path, Expected information per unit cost, weighted by hypothesis relevance. (+10 more)

### Community 3 - "main.py"
Cohesion: 0.07
Nodes (26): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+18 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.10
Nodes (41): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop. (+33 more)

### Community 5 - "Investigator"
Cohesion: 0.15
Nodes (14): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+6 more)

### Community 6 - "test_registry.py"
Cohesion: 0.07
Nodes (31): The number registry — which published numbers belong to which institution. The…, Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and… (+23 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.13
Nodes (37): distinct_callees(), How many different people this number has been screened against lately.…, _as(), _burst(), _clean(), _engine(), _owner_of(), asyncio (+29 more)

### Community 8 - "VerificationRequest"
Cohesion: 0.15
Nodes (14): VerificationRequest, _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeReachability, FakeSimSwap, _provider() (+6 more)

### Community 9 - "routes_console.py"
Cohesion: 0.12
Nodes (30): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, key_from_bearer(), owner_for(), Merchant API-key auth: `Authorization: Bearer <key>`., The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., require_api_key() (+22 more)

### Community 10 - "Choice"
Cohesion: 0.14
Nodes (11): Choice, What the planner decided, and why, and who decided it., asyncio, parametrize, StopsImmediately, test_low_prior_allow_requires_a_supporting_fact_even_with_stop(), _StopsImmediately, The loop must end and still produce a signed verdict. (+3 more)

### Community 11 - "cache.py"
Cohesion: 0.12
Nodes (8): Cache, CacheCapacityExceeded, get_cache(), Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one., RedisCache

### Community 12 - "GreedyPlanner"
Cohesion: 0.13
Nodes (17): get_planner(), GreedyPlanner, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, _engine(), asyncio, LLM planner fallback + cache/idempotency., It used to, and `STEP_UP_OTP` is not a provider call — see… (+9 more)

### Community 13 - "announce.py"
Cohesion: 0.10
Nodes (31): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+23 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (18): Directory, _Institution, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",… (+10 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (27): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+19 more)

### Community 17 - "RequestContext"
Cohesion: 0.16
Nodes (18): Money, field_validator, RequestContext, main(), T1 — call every CAMARA action for real and record what came back. The runbook's…, Never write a real identifier to a file that gets committed., redact(), _investigator() (+10 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "config.py"
Cohesion: 0.13
Nodes (27): check_startup_posture(), InsecureConfiguration, makes_billable_calls(), RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Can a request cause a real, paid CAMARA call to leave this process? Keyed on…, Refuse to start a billable deployment with no key or a published one. Only… (+19 more)

### Community 20 - "SessionManager"
Cohesion: 0.14
Nodes (19): SessionStatus, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+11 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.11
Nodes (20): GeminiClient, GeminiError, Any, RuntimeError, The provider did not return usable candidate text., Minimal synchronous client for a single Gemini content-generation turn., Return a JSON object, or raise so the caller can use its fallback., Return candidate text for display-only explanation features. (+12 more)

### Community 23 - "retention.py"
Cohesion: 0.14
Nodes (16): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+8 more)

### Community 24 - "MockProvider"
Cohesion: 0.12
Nodes (24): Investigate an inbound caller with the impersonation hypothesis. Same engine as…, run_reverse(), MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, main(), Scenario, _verdict(), asyncio (+16 more)

### Community 25 - "test_act7.py"
Cohesion: 0.09
Nodes (24): _no_leftover_announcements(), fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not…, Act VII exercises several authenticated stage controls per test; their request… (+16 more)

### Community 26 - "NacProvider"
Cohesion: 0.15
Nodes (8): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., nac.py's _as_url returned any string the SDK provided., test_a_non_https_authorization_url_is_refused()

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.18
Nodes (17): get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., create_session(), end_session(), get_session(), post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.… (+9 more)

### Community 29 - "test_reverse.py"
Cohesion: 0.25
Nodes (6): asyncio, Reverse Isnad — verify an inbound caller to the customer (Act IV)., The real institution line is network-attested -> TRUST (ALLOW)., A spoofed 'bank officer' fails network attestation -> REJECT (DECLINE)., test_genuine_caller_is_trusted(), test_spoofed_caller_is_rejected()

### Community 30 - "build_investigator"
Cohesion: 0.15
Nodes (24): build_investigator(), asyncio, Parallel evidence gathering — latency bought with cost. Opt-in per request.…, On a chain that spends its budget anyway the two are equal — the takeover case…, Speed must not change the answer., Two runs over the same evidence must produce the same number regardless of…, Local evidence is applied before the batch; both must land in the chain., Two investigations in flight at once must not put each other's links in the… (+16 more)

### Community 31 - "ConsentStore"
Cohesion: 0.25
Nodes (4): ConsentRecord, ConsentStore, Claim this consent for exactly one callback. A true compare-and-swap. The old…, Short-lived consent state; tokens never leave this process or API response.

### Community 32 - "routes_consent.py"
Cohesion: 0.21
Nodes (18): complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent(), number_verification_callback(), HTTPException, post, Receive the provider redirect; the authorization code is never exposed. (+10 more)

### Community 33 - "schemas.py"
Cohesion: 0.12
Nodes (25): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), post, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify() (+17 more)

### Community 34 - "investigator.py"
Cohesion: 0.16
Nodes (11): form(), Read the request context and commit to a risk hypothesis. This is what makes…, get_engine(), Load the policy once and reuse it — avoids re-reading/parsing YAML per request., _install_retries(), main(), Measure how differently the LLM planner behaves from the greedy one. This…, Give the provider every chance to answer, for measurement runs only. The demo… (+3 more)

### Community 35 - "store.py"
Cohesion: 0.22
Nodes (18): owner_binding(), Bind a verdict to the merchant it was issued for. Peppered rather than the bare…, ChainRow, A persisted, signed evidence chain. Only chain evidence is stored — never raw…, ChainRecord, get_public_record(), get_public_record_async(), get_record() (+10 more)

### Community 36 - "signing.py"
Cohesion: 0.19
Nodes (19): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+11 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.15
Nodes (16): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP_CONFIRMED — reserved, nothing emits it, OTP counterfactual pricing block, REGISTRY_MATCH_UNANNOUNCED = 0.0 (+8 more)

### Community 38 - "test_judge.py"
Cohesion: 0.18
Nodes (12): judge_page(), HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the… (+4 more)

### Community 39 - "rate_limit.py"
Cohesion: 0.14
Nodes (21): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+13 more)

### Community 40 - "routes_verify.py"
Cohesion: 0.14
Nodes (19): explain_chain(), get_chain(), _idempotency_state_response(), post, Replayable evidence — for COD dispute / chargeback resolution., Evidence-vault check: recompute the signature over the stored chain and confirm…, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature… (+11 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.11
Nodes (16): asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Held entries for 24h and was swept only on a get of the same key., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files., /docs, /redoc and /openapi.json all answered 200 unauthenticated., It told an attacker whether calls cost money and whether demo was live., store.* is called from async handlers; SQLite writes block. Under any… (+8 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.18
Nodes (18): _cfg(), _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, `check_startup_posture` guarded `provider == "nac"` only. `hybrid` makes real,…, Both lists empty is a MockProvider with extra steps — no call can leave the…, Exactly ONE live link. The rest of the chain must stay deterministic, or the… (+10 more)

### Community 43 - "InMemoryCache"
Cohesion: 0.18
Nodes (6): InMemoryCache, Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one., Drop what has expired; if nothing has, drop the oldest inserted., test_in_memory_cache_ttl()

### Community 44 - "Result"
Cohesion: 0.11
Nodes (20): EvidenceLink, One attested link in the chain — the normalized result of one CAMARA call.…, Result, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, _csv(), HybridProvider (+12 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.09
Nodes (37): _announce(), Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call…, The window is the spoofing opportunity: while an announcement stands, a call…, Matching the caller alone would let one genuine announcement verify a burst of…, An institution announcing a call is telling this service who it is about to… (+29 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.21
Nodes (12): _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve., test_a_chain_issued_for_a_does_not_verify_against_b(), test_public_request_binding_is_not_an_offline_guessable_sha256_digest() (+4 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "VaultSigner"
Cohesion: 0.08
Nodes (26): InsecureVaultKey, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key is readable by someone other than its owner., Signs issued chains with Ed25519. The key is loaded from disk if present,…, _trusted_from_settings() (+18 more)

### Community 50 - "owner_hash"
Cohesion: 0.16
Nodes (16): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+8 more)

### Community 51 - "UtcDateTime"
Cohesion: 0.40
Nodes (3): A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, UtcDateTime, TypeDecorator

### Community 52 - "stream_token.py"
Cohesion: 0.16
Nodes (14): clear(), mint(), owner_for(), RuntimeError, Short-lived, stream-only credentials for browser EventSource connections.…, Minting must not displace another owner's live stream credential., Issue a credential that identifies one SSE owner and nothing else., Return the stream owner while the token is valid, otherwise ``None``. (+6 more)

### Community 53 - "test_nac_contract.py"
Cohesion: 0.21
Nodes (14): parametrize, Path, Contract tests over responses actually observed from Nokia Network as Code.…, Non-zero latency is the difference between an observation and a guess., Every action the agent can take against a NETWORK must have a recorded…, A fixture without a version and a timestamp is an assumption again., These are committed. Operating rule 0.1: no real identifier in the repo., The runbook forbids quietly promoting an API that was never exercised. (+6 more)

### Community 54 - "purge_older_than"
Cohesion: 0.38
Nodes (6): purge_older_than(), Drop events outside any window anyone will ask about. This table exists to…, console_token(), main(), Drive one number against many callees, so Act VII can show caller velocity. Run…, screen()

### Community 55 - "test_s6_vault_keys.py"
Cohesion: 0.14
Nodes (14): MissingVaultKey, RuntimeError, The signing key was expected on disk and was not there., S6 — verification must use the key that signed, and survive a restart., The acceptance criterion: issue, restart, verify., The route returned rec.public_key while verifying with its own., Otherwise a row with a self-consistent key and signature verifies., Silently generating is what turns a missing volume into a stage failure. (+6 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.18
Nodes (11): A changed SIM should start an investigation., A receipt that can be challenged, too, Every check has a job, Evidence you can rerun, Isnad · إسناد, One integration, an explainable action, One warning. Two very different checkouts., Simulated answers. The same investigation. (+3 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.16
Nodes (13): investigate(), console.html — live agent console, askTheAgent(), showReceiptQr(), judge.html — Judge Mode verified checkout, runCheckout(), receipt.html — public evidence receipt, renderArithmetic() (+5 more)

### Community 58 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.11
Nodes (18): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read…, policy.yaml says "opt in per request, never globally" and no route let anyone… (+10 more)

### Community 60 - "bound_key"
Cohesion: 0.29
Nodes (7): bound_key(), _no_leftover_announcements(), fixture, The suite shares one in-memory database, so an announcement made by one test…, demo-merchant-key, bound to the institution that owns BANK_NUMBER., A registry holding Demo Bank and one other institution. The shipped registry…, two_bank_registry()

### Community 61 - "_directory"
Cohesion: 0.13
Nodes (15): _directory(), Absence from the registry is not evidence of anything. Most numbers in the…, A hotline printed on the back of a card is a convenient thing to spoof,…, Same rule as the pricing block in policy.yaml: an entry here asserts that a…, The name reaches this from a copy-paste, a phone keyboard, or another system's…, The check is only worth having if it runs against the file that ships., Institutions own ranges, not single numbers. A registry of exact numbers alone…, test_a_published_inbound_only_line_is_flagged_as_never_outbound() (+7 more)

### Community 62 - "false_decline_baseline.py"
Cohesion: 0.33
Nodes (9): baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's…, The two rules being replaced, applied to a full evidence set. The baseline is…, Every single-signal case the policy vocabulary admits, plus a control., The operating curve, because the honest answer to "you allow some corroborated-…, run() (+1 more)

### Community 63 - "Decision"
Cohesion: 0.07
Nodes (41): Decision, logodds_to_p(), model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase (+33 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "events.py"
Cohesion: 0.14
Nodes (19): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), subscriber_count() (+11 more)

### Community 66 - "resolve_key_path"
Cohesion: 0.20
Nodes (11): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+3 more)

### Community 67 - "evidence_pack.py"
Cohesion: 0.06
Nodes (55): _add_missing_columns(), _assert_schema_current(), init_db(), Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, Prepare SQLite locally, or verify a migrated non-SQLite schema. SQLite remains…, Response, build_report() (+47 more)

### Community 68 - "Verdict"
Cohesion: 0.08
Nodes (31): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+23 more)

### Community 69 - "mock.py"
Cohesion: 0.11
Nodes (17): detail_for(), The only sentences an evidence link may carry, and where each one comes from.…, The age window this action's question covered, if it has one. Mirrors the…, The max_age the swap checks are actually called with., The sentence for a signal, derived from the response and our parameters., _window(), window_hours(), parametrize (+9 more)

### Community 70 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 71 - "Phase 2 Agent Runbook"
Cohesion: 0.25
Nodes (11): setPlannerBadge(), privacy.html — what we keep, CLAUDE.md — graphify agent instructions, EvidenceProvider adapter contract, Phase 2 Agent Runbook, Part 4 pre-deployment hardening gate, Runbook invariants (gather() seam, no raw signals, no logging), Prompt-injection boundary for the planner (+3 more)

### Community 72 - "_two_banks"
Cohesion: 0.18
Nodes (11): The bug this replaced: every word of the claim had to be indexed, so the more…, Name and aliases share one token index, so a merged subset test would reject…, The converse hole in the old comparison: "bank" alone matched every bank,…, A claim that contains the owner's name has named the owner. Order the checks…, test_a_bare_generic_word_is_not_a_match(), test_a_caller_who_describes_themselves_more_fully_still_matches(), test_a_mismatch_needs_the_claim_to_name_a_DIFFERENT_indexed_institution(), test_an_alias_is_matched_whole_and_not_merged_with_the_name() (+3 more)

### Community 73 - "routes_verified_caller.py"
Cohesion: 0.25
Nodes (13): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+5 more)

### Community 74 - "SlidingWindowLimiter"
Cohesion: 0.20
Nodes (6): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, test_the_limiter_bucket_map_is_bounded(), test_the_window_actually_slides()

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.15
Nodes (16): clear(), is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep() (+8 more)

### Community 79 - "LLMPlanner"
Cohesion: 0.11
Nodes (12): effective_planner(), LLMPlanner, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Asks a model to choose the next evidence step, given the belief state, the…, Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as… (+4 more)

### Community 80 - "consent.py"
Cohesion: 0.29
Nodes (7): ConsentCapacityExceeded, _now(), _owner_hash(), datetime, RuntimeError, A live consent cannot be retained without displacing another one., Drop expired and terminal records. Caller holds the lock.

### Community 81 - "velocity.py"
Cohesion: 0.16
Nodes (15): matches(), Bind a verdict to the number it was issued about., Whether a stored chain was really issued about this number., subject_hash(), is_high_velocity(), is_high_velocity_async(), _owner(), The tenant this request belongs to, set at the auth boundary (S2). (+7 more)

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

### Community 88 - "t1_probe.py"
Cohesion: 0.50
Nodes (4): describe(), main(), T1 — fire exactly ONE real CAMARA call and record what actually came back.…, Render an SDK response without assuming it is a dict or a pydantic model.

### Community 89 - "_secure_sqlite_files"
Cohesion: 0.29
Nodes (8): Path, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only., WAL and a busy timeout on every SQLite connection (S12). Without WAL a reader…, _secure_sqlite_files(), _sqlite_database_path(), _sqlite_pragmas(), listens_for

### Community 90 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 92 - "test_privacy.py"
Cohesion: 0.20
Nodes (7): The consent and retention posture, made checkable. §0.8.5 Q9 — *"you HMAC…, Hard-coded prose drifts from the running system the first time someone tunes a…, A page that hard-codes '1 hour' is a page that will one day be wrong., The consent trail is inside the signed bytes already. Showing it is what turns…, test_the_page_serves_and_pulls_its_numbers_from_the_endpoint(), test_the_posture_reports_the_retention_windows_actually_configured(), test_the_receipt_shows_the_consent_basis_of_every_link()

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

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **73 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 860 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `test_llm_planner.py`, `Investigator`, `VerificationRequest`, `Choice`, `GreedyPlanner`, `RequestContext`, `SessionManager`, `test_t5_counterfactual.py`, `MockProvider`, `NacProvider`, `build_investigator`, `routes_consent.py`, `schemas.py`, `investigator.py`, `test_hybrid_provider.py`, `Result`, `test_verified_caller.py`, `test_nac_contract.py`, `test_s9_consent_replay.py`, `test_audit_low.py`, `false_decline_baseline.py`, `Decision`, `evidence_pack.py`, `Verdict`, `mock.py`, `LLMPlanner`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `NacProvider` connect `NacProvider` to `Action`, `mock.py`, `Phase 2 Agent Runbook`, `VerificationRequest`, `test_s12_runtime_posture.py`, `Result`, `RequestContext`, `t1_probe.py`, `NaC integration — observed, not assumed`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `CURRENT_STATE.md`, `NaC integration — observed, not assumed`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 56 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 56 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 34 INFERRED edges - model-reasoned connections that need verification._