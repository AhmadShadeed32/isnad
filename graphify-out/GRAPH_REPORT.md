# Graph Report - isnad  (2026-09-06)

## Corpus Check
- 170 files · ~140,062 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2132 nodes · 4882 edges · 120 communities (97 shown, 5 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 536 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a0ef5f65`
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
- test_nac_provider.py
- InMemoryCache
- GreedyPlanner
- announce.py
- Directory
- Normalized Evidence Envelope (result/signal/detail/source/consent)
- test_console.py
- Decision
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
- events.py
- VerificationRequest
- store.py
- signing.py
- policy.yaml — the single tuning surface
- rate_limit.py
- Verdict
- routes_verified_caller.py
- test_s12_runtime_posture.py
- test_hybrid_provider.py
- Money
- SessionManager
- test_s3_tenant_isolation.py
- test_verified_caller.py
- test_s5_subject_binding.py
- test_s10_xss_and_headers.py
- cache.py
- owner_hash
- db/models.py
- stream_token.py
- test_nac_contract.py
- purge_older_than
- test_s6_vault_keys.py
- Isnad · إسناد
- console.html — live agent console
- LLMPlanner
- test_audit_low.py
- resolve_key_path
- 3. Recommended app work — not implemented in this documentation pass
- investigator.py
- independent_evaluation.py
- Project Brief
- test_hardening.py
- 6. MENA Ignite submission priorities — reviewed 6 September 2026
- evidence_pack.py
- _verdict
- Action
- _directory
- Phase 2 Agent Runbook
- _two_banks
- routes_registry.py
- Isnad — compact handoff
- routes_privacy.py
- test_s14_no_tracked_secrets.py
- demo_token.py
- Result
- Choice
- test_s9_consent_replay.py
- presentation.py
- CURRENT_STATE.md
- Q: What changed in the 5 September review and what remains unproven?
- verify_runtime_lock.py
- test_evidence_pack.py
- test_mock_scenarios.py
- SlidingWindowLimiter
- NaC integration — observed, not assumed
- velocity.py
- tts.py
- app/__init__.py
- encode.sh
- setup.sh
- test_s4_demo_mode.py
- consent.py
- isnad
- Isnad (إسناد) — project brief
- Number Verification handset validation
- Fixed synthetic evaluation
- What the risk score means
- t1_probe.py

## God Nodes (most connected - your core abstractions)
1. `Action` - 136 edges
2. `VerificationRequest` - 82 edges
3. `MockProvider` - 77 edges
4. `Result` - 75 edges
5. `Decision` - 73 edges
6. `PolicyEngine` - 57 edges
7. `Hypothesis` - 56 edges
8. `Verdict` - 55 edges
9. `EvidenceLink` - 53 edges
10. `RequestContext` - 49 edges

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

## Communities (120 total, 5 thin omitted)

### Community 0 - "test_chain_grade.py"
Cohesion: 0.09
Nodes (40): ChainGrade, How much the evidence chain itself was worth, independent of the decision. The…, p_to_logodds(), _engine(), _gate(), _investigator(), _link(), asyncio (+32 more)

### Community 1 - "test_t6_receipt.py"
Cohesion: 0.04
Nodes (32): chain_id(), fixture, T6 — the public, independently verifiable receipt., S11's rule carried into T6: the reason is not part of the receipt., What the browser does, done here: import the key, verify the bytes., The tamper control, and the reason it is worth putting on stage., Verifying a re-serialization is the detail most implementations get wrong., The rendered summary must not be able to disagree with what was signed. (+24 more)

### Community 2 - "PolicyEngine"
Cohesion: 0.07
Nodes (10): PolicyEngine, Path, Expected information per unit cost, weighted by hypothesis relevance., Network facts required before a clean belief may stop the agent., What the chain itself was worth. Ordered so the strongest claim about the…, Loads policy.yaml and answers every question the agent asks of policy., Prior for Reverse Isnad: an unverified inbound caller starts uncertain., Checks to attempt before this signal alone may carry a DECLINE. The counterpart… (+2 more)

### Community 3 - "main.py"
Cohesion: 0.06
Nodes (33): ASGIApp, Exception, Receive, Scope, Send, Small ASGI guards that run before FastAPI parses a request body. Pydantic…, Reject oversized bodies and shed excess concurrent HTTP work. The in-flight…, _reject() (+25 more)

### Community 4 - "test_llm_planner.py"
Cohesion: 0.12
Nodes (33): Hypothesis, _engine(), FakeClient, _planner(), T3 — the LLM planner, its fallbacks, and its prompt-injection boundary. Every…, step_up_otp is never in the affordable set for the gather loop., The acceptance criterion: ISNAD_PLANNER=llm with no key == greedy., Without a ceiling one request can burn unbounded model budget. (+25 more)

### Community 5 - "Investigator"
Cohesion: 0.19
Nodes (10): Belief, The agent's running policy risk score. Configured weights add in log-odds…, Investigator, The orchestrator. Forms a hypothesis, gathers the cheapest useful evidence,…, Fire a batch of affordable actions concurrently. Chosen with the deterministic…, Is this a clean verdict resting on local evidence alone — or on local evidence…, The next outstanding exculpatory check, or None. Only ever gates the DECLINE…, Which planner produced this run. "llm+greedy" when the run fell back partway… (+2 more)

### Community 6 - "test_registry.py"
Cohesion: 0.07
Nodes (31): The number registry — which published numbers belong to which institution. The…, Unknown must not read as "yes, they call from here" — that is precisely the…, Intersection, not union: "arab bank" must not return every institution with…, Silently, the second one won — the later write to `_exact` replaced the…, EXACT beats PREFIX, so this silently took one number out of a range somebody…, Longest prefix wins, so the inner block silently took the range — whichever…, The case that must NOT be rejected: a switchboard listed explicitly inside the…, It did not merge, it corrupted: the second block took `_institutions` and… (+23 more)

### Community 7 - "test_velocity.py"
Cohesion: 0.13
Nodes (37): distinct_callees(), How many different people this number has been screened against lately.…, _as(), _burst(), _clean(), _engine(), _owner_of(), asyncio (+29 more)

### Community 8 - "test_presentation.py"
Cohesion: 0.08
Nodes (43): present(), Presentation, BaseModel, Project a signed Verdict into a plain-language Presentation. Pure function:…, What a first-time visitor sees. Never signed, never part of `Verdict`, safe to…, _facts_known_to_the_chain(), asyncio, parametrize (+35 more)

### Community 9 - "routes_console.py"
Cohesion: 0.11
Nodes (30): key_from_bearer(), owner_for(), Merchant API-key auth: `Authorization: Bearer <key>`., The tenant a validated key belongs to., Extract a validated key from an Authorization header, or None., require_api_key(), _valid_key(), act7_announce() (+22 more)

### Community 10 - "test_nac_provider.py"
Cohesion: 0.15
Nodes (13): _consent_provider(), FakeClient, FakeDeviceStatus, FakeNumberVerification, FakeReachability, FakeSimSwap, _provider(), asyncio (+5 more)

### Community 11 - "InMemoryCache"
Cohesion: 0.18
Nodes (6): InMemoryCache, Process-local cache with TTL. Default backend; fine for a single instance. For…, Atomically reserve ``key`` if no non-expired value exists. Idempotency uses…, Release an unfinished reservation without deleting a newer one., Drop what has expired; if nothing has, drop the oldest inserted., test_in_memory_cache_ttl()

### Community 12 - "GreedyPlanner"
Cohesion: 0.08
Nodes (23): get_planner(), GreedyPlanner, Planner, Protocol, For CHALLENGE: the cheapest low-friction network check that could resolve the…, Select the planner from config: greedy (default, demo-safe) or llm., Deterministic evidence selection: pick the highest information-per-cost action…, A planner that opens on the SIM swap, as the LLM planner is free to do. This is… (+15 more)

### Community 13 - "announce.py"
Cohesion: 0.16
Nodes (19): find(), find_async(), _owner(), datetime, A live announcement matching this call, or None. Scoped to the reader. Matches…, The window an announcement stays usable. Bounded because the window IS the…, Store one pre-announcement. Returns (id, expires_at)., The tenant this request belongs to, set at the auth boundary (S2). (+11 more)

### Community 14 - "Directory"
Cohesion: 0.10
Nodes (17): Directory, _matched(), NumberEntry, Path, Refuse to load a file where two institutions can claim one number. An entry…, Every published block this value sits strictly inside., Normalized words for the name index. Case- and accent-folded so "Arab Bank",…, The institution that published this number, or None. None means "not in the… (+9 more)

### Community 15 - "Normalized Evidence Envelope (result/signal/detail/source/consent)"
Cohesion: 0.11
Nodes (31): Device Intelligence NaC Capture, Device Swap NaC Capture, Location Verification NaC Capture, Number Verification NaC Capture, Consent-Gated Evidence (requires_consent / consent_basis), Device Reachability Status NaC Capture, Device Roaming Status NaC Capture, SIM Swap NaC Capture (+23 more)

### Community 16 - "test_console.py"
Cohesion: 0.07
Nodes (27): asyncio, fixture, Console page, demo-trigger endpoint, and the live event bus., The message above is only reachable if the server actually rejects a stale…, apiKey() reads sessionStorage, and requireApiKey() only prompts when the stored…, S4 put /v1/console/run/{act} behind a key, but the console kept calling it with…, Reverse Isnad returns TRUST_CALLER / CAUTION / REJECT_CALLER, not the forward…, Until the first verdict, the pill read `planner: —` even though the… (+19 more)

### Community 17 - "Decision"
Cohesion: 0.11
Nodes (20): Decision, _deltas(), The false-decline harness has to be trustworthy before its number is quoted.…, If cases were chosen by hand the number would mean nothing. Every adverse and…, The ADVERSE-1/UNKNOWN-1 claim is 'one bad reading on an otherwise clean line'.…, Guards against a baseline so blunt it declines everyone, which would make the…, The whole thesis is that these two rules disagree about an unanswered check. If…, test_a_clean_chain_declines_under_neither_baseline() (+12 more)

### Community 18 - "test_t4_ask_the_agent.py"
Cohesion: 0.09
Nodes (16): chain_id(), fake(), FakeClient, fixture, T4 — ask the agent about a decision it already made., T3's boundary applies here too: signals go in, details do not., The acceptance criterion, and the test the runbook asks for., Same fix as the narrative: a bare grade name gets misread. (+8 more)

### Community 19 - "config.py"
Cohesion: 0.09
Nodes (37): clear(), check_startup_posture(), InsecureConfiguration, makes_billable_calls(), RuntimeError, Runtime configuration. Everything is overridable via environment variables…, Raised at startup for a configuration that cannot be safely exposed., Can a request cause a real, paid CAMARA call to leave this process? Keyed on… (+29 more)

### Community 20 - "VaultSigner"
Cohesion: 0.08
Nodes (26): InsecureVaultKey, Verify against the key this process is holding., Verify against the key that actually signed the record (S6). The route used to…, Whether a public key is one this deployment vouches for. The live key, plus any…, The secret a subject binding is computed under (S5). Configured explicitly in…, The signing key is readable by someone other than its owner., Signs issued chains with Ed25519. The key is loaded from disk if present,…, _trusted_from_settings() (+18 more)

### Community 21 - "test_t5_counterfactual.py"
Cohesion: 0.10
Nodes (25): parametrize, T5 — the OTP counterfactual, and the honesty rules around it., A figure a judge checks and finds invented is worse than no figure., No public list price exists for CAMARA calls, so none is claimed., The rule the runbook states: every figure carries a source comment., IDlayr sells a competing product. Say so before a judge finds it., The cited range is 20-30%; claiming 30% would be the flattering read., policy.yaml is the tuning surface — the invariant the runbook states. (+17 more)

### Community 22 - "GeminiClient"
Cohesion: 0.11
Nodes (20): GeminiClient, GeminiError, Any, RuntimeError, The provider did not return usable candidate text., Minimal synchronous client for a single Gemini content-generation turn., Return a JSON object, or raise so the caller can use its fallback., Return candidate text for display-only explanation features. (+12 more)

### Community 23 - "test_retention.py"
Cohesion: 0.11
Nodes (24): purge_expired(), Drop announcements past their window, and the use rows that belonged to them.…, purge_once(), purge_once_async(), Deleting what no longer answers a question. Two tables here record who was in…, One sweep of everything past its window. Returns what it deleted., Sweep on a timer until cancelled. A failed sweep must not end the loop. A…, Start the sweeper, or None when it is disabled (interval <= 0). (+16 more)

### Community 24 - "test_judge.py"
Cohesion: 0.18
Nodes (12): judge_page(), HTMLResponse, Serve the on-stage checkout journey with a short-lived demo token. This uses…, _page_body(), fixture, The judge page is a safe presentation client over existing demo APIs., The public page is address-limited; do not leak this traffic to tests that…, Judge Mode is not a second route for arbitrary provider calls. It must use the… (+4 more)

### Community 25 - "test_act7.py"
Cohesion: 0.08
Nodes (27): _no_leftover_announcements(), asyncio, fixture, Act VII — the bank that wasn't. Three calls, one institution, three answers.…, The console mints a token to ANY visitor while demo mode is on, and that token…, Caller velocity is the one cross-call signal in the product. It needs a demo…, Reverse Isnad shipped answering TRUST_CALLER/CAUTION/REJECT_CALLER while the…, A PBX trunk has no SIM, so every mobile CAMARA API is inapplicable — not… (+19 more)

### Community 26 - "NacProvider"
Cohesion: 0.15
Nodes (8): NacProvider, Any, Exception, Nokia Network-as-Code adapter. The current Python SDK exposes synchronous…, Any URL from the SDK reaches window.open() in the console (S13). The SDK is an…, Run a blocking SDK call on the dedicated pool., nac.py's _as_url returned any string the SDK provided., test_a_non_https_authorization_url_is_refused()

### Community 27 - "timeline.js"
Cohesion: 0.13
Nodes (25): A(), app(), B, buildRow(), capEl, cl(), ease(), easeIO() (+17 more)

### Community 28 - "routes_session.py"
Cohesion: 0.21
Nodes (15): create_session(), end_session(), get_session(), post, Open a trust session: keep watching SIM/device after the verdict., Demo control: inject a mid-session SIM swap on this session's number.…, simulate_swap(), _to_response() (+7 more)

### Community 29 - "schemas.py"
Cohesion: 0.07
Nodes (38): post, Investigate an inbound caller with the impersonation hypothesis. Same engine as…, Reverse Isnad: 'Is this caller really who they say they are?' -> TRUST_CALLER /…, reverse_verify(), run_reverse(), Alternative, ExplainRequest, ExplainResponse (+30 more)

### Community 30 - "MockProvider"
Cohesion: 0.11
Nodes (34): build_investigator(), Render a verdict's chain as the human-readable 'isnad' — the ordered,…, render_text(), Area, A claimed location — never a tracked coordinate. Used only for yes/no verify., MockProvider, Deterministic, scriptable provider for tests and the on-stage demo. Runs the…, main() (+26 more)

### Community 31 - "ConsentStore"
Cohesion: 0.25
Nodes (4): ConsentRecord, ConsentStore, Claim this consent for exactly one callback. A true compare-and-swap. The old…, Short-lived consent state; tokens never leave this process or API response.

### Community 32 - "routes_consent.py"
Cohesion: 0.15
Nodes (26): build_engine_for_pricing(), The same cached policy the agent ran on, for the T5 counterfactual. Read at…, get_live_provider(), Resolve the configured provider as an API-level 503 when unavailable., complete_number_verification(), _consent_response(), _consent_unavailable(), get_number_verification_consent() (+18 more)

### Community 33 - "events.py"
Cohesion: 0.14
Nodes (19): emit(), mask_phone(), Keep console events useful without broadcasting a full phone number., Deliver an event to the subscribers belonging to the current owner., Receive the events emitted for `owner`, and only those., _redact(), subscribe(), subscriber_count() (+11 more)

### Community 34 - "VerificationRequest"
Cohesion: 0.10
Nodes (33): form(), Read the request context and commit to a risk hypothesis. This is what makes…, RequestContext, VerificationRequest, main(), T1 — call every CAMARA action for real and record what came back. The runbook's…, Never write a real identifier to a file that gets committed., redact() (+25 more)

### Community 35 - "store.py"
Cohesion: 0.11
Nodes (29): verify_consent_chain(), explain_chain(), post, Evidence-vault check: recompute the signature over the stored chain and confirm…, Ask the agent about a decision it already made (T4). Grounded in the stored…, Settle a dispute: is this chain evidence about *this* number? The signature…, The public key anyone can use to independently verify a chain signature., vault_public_key() (+21 more)

### Community 36 - "signing.py"
Cohesion: 0.15
Nodes (23): payload_for(), Exception, Path, A signature is present and does not match the file. Deliberately fatal. A…, Check the registry against its signature. Returns None when a signature is…, RegistryTampered, sign_bytes(), signature_path() (+15 more)

### Community 37 - "policy.yaml — the single tuning surface"
Cohesion: 0.15
Nodes (16): policy.yaml — the single tuning surface, Evidence budget and cheapest-evidence-first, corroboration: SIM_SWAPPED → [device_swap, location_verify], gather.mode — sequential vs parallel, grading.min_network_links_for_allow, OTP_CONFIRMED — reserved, nothing emits it, OTP counterfactual pricing block, REGISTRY_MATCH_UNANNOUNCED = 0.0 (+8 more)

### Community 38 - "rate_limit.py"
Cohesion: 0.14
Nodes (21): _client_ip(), limit_per_ip(), limit_per_key(), limit_screen(), HTTPException, Request, Dependency for routes reachable without a key., Dependency for Tier 1 screening. Same bucketing as limit_per_key, a different… (+13 more)

### Community 39 - "Verdict"
Cohesion: 0.09
Nodes (26): answer(), chain_facts(), ExplainUnavailable, _maybe_client(), RuntimeError, No model is configured to answer questions., Everything the answerer may see. Structured, never free text., Answer `question` about `verdict`, grounded in its chain. (+18 more)

### Community 40 - "routes_verified_caller.py"
Cohesion: 0.27
Nodes (11): _directory(), pre_announce(), post, Tier 1 — the pre-ring check. Local state only, no network call. This exists…, An institution declaring a call it is about to place. Two things are checked,…, screen(), PreAnnounceRequest, PreAnnounceResponse (+3 more)

### Community 41 - "test_s12_runtime_posture.py"
Cohesion: 0.12
Nodes (14): asyncio, S12 / S13 — runtime posture: docs, blocking writes, limits, bounds, leaks., No add_middleware call existed anywhere in the tree., Held entries for 24h and was swept only on a get of the same key., Harmless in memory; under Redis it lands in KEYS, MONITOR and RDB files., It told an attacker whether calls cost money and whether demo was live., store.* is called from async handlers; SQLite writes block. Under any…, test_a_key_is_rate_limited() (+6 more)

### Community 42 - "test_hybrid_provider.py"
Cohesion: 0.25
Nodes (13): _hybrid(), _link(), asyncio, One real CAMARA call inside an otherwise-scripted chain. Every winner found of…, Exactly ONE live link. The rest of the chain must stay deterministic, or the…, The whole point. On stage, an exception here is a dead demo., The resting state is fully scripted: someone who sets ISNAD_PROVIDER without…, _Stub (+5 more)

### Community 43 - "Money"
Cohesion: 0.22
Nodes (13): Money, field_validator, _investigator(), asyncio, End-to-end scenario tests — the demo's three acts run the real engine. These…, Act I — clean signup: one silent Number Verification clears them., Act II — SIM swapped 41 min ago, new device, wrong location -> DECLINE., Act III — no merchant history, but years of SIM tenure clear them -> ALLOW.… (+5 more)

### Community 44 - "SessionManager"
Cohesion: 0.14
Nodes (19): SessionStatus, trip_swap(), _now(), datetime, Trust-with-a-TTL. After a verdict, keep watching the SIM/device; if either…, Drop terminal records. `_sessions` was never pruned., A session the current caller owns, or None. None rather than a distinct error,…, SessionManager (+11 more)

### Community 45 - "test_s3_tenant_isolation.py"
Cohesion: 0.15
Nodes (14): _chain_id_for(), _console_token(), S3 — one key must not be able to read another key's chain or session., A token is minted per render; the tenant it maps to must be stable. Owning by…, The finding, verbatim: store.get() was called with no ownership check., The vault route reads the same row and leaked the same way., 404, not 403: an id must not be probeable for existence., The isolation must not have broken the ordinary path. (+6 more)

### Community 46 - "test_verified_caller.py"
Cohesion: 0.07
Nodes (48): _announce(), bound_key(), _no_leftover_announcements(), fixture, Verified Caller — the PBX/SIP answer, and the two tiers around it. No CAMARA…, The binding IS the mechanism. Without it anyone holding any key could announce…, The institution's own entry says it never originates calls there. Accepting it…, The window IS the spoofing opportunity: while an announcement stands, a call… (+40 more)

### Community 47 - "test_s5_subject_binding.py"
Cohesion: 0.21
Nodes (15): get_record(), _chain_for(), S5 — a signature must say what it is evidence *of*., It used to be a sibling column, outside the signed bytes., The payload becomes public on the receipt page (T6)., The finding, verbatim: a clean chain for any other number used to verify. This…, Not a sibling column: it has to be covered by the signature., The binding must not cost the no-PII property it exists to preserve. (+7 more)

### Community 48 - "test_s10_xss_and_headers.py"
Cohesion: 0.12
Nodes (13): S10 — DOM XSS sinks in the console, and the missing CSP., addRow built rows with innerHTML from ev.detail, ev.reason, ev.rationale,…, The acceptance criterion, verbatim. routes_verify.py reflected a raw path…, A constant message cannot carry an injected payload., console.html has zero external origins; the policy must keep it that way., The invariant the runbook says to keep: a venue may be offline., The middleware must not have been written in a way that buffers SSE.…, test_a_missing_chain_error_does_not_reflect_the_path() (+5 more)

### Community 49 - "cache.py"
Cohesion: 0.12
Nodes (8): Cache, CacheCapacityExceeded, get_cache(), Protocol, RuntimeError, Redis-backed cache for token caching + idempotency across instances., A new idempotency reservation cannot displace an existing one., RedisCache

### Community 50 - "owner_hash"
Cohesion: 0.19
Nodes (14): owner_hash(), S11 — caller-supplied text must not be spliced into an unsigned reason., routes_reverse built reason=f"Claimed identity: {…}. {verdict.reason}". Not…, Nothing was lost: the caller can still render both., A character class cannot catch an attack made of ordinary words. "Ignore…, _reverse(), test_an_injection_string_is_accepted_as_a_name_but_goes_nowhere(), test_markup_in_the_identity_is_rejected_at_the_edge() (+6 more)

### Community 51 - "db/models.py"
Cohesion: 0.16
Nodes (9): Base, AnnouncementUseRow, One Tier 1 screen, kept so velocity can be seen across subscribers. Every other…, A datetime column that is timezone-aware UTC on both sides. SQLite's DATETIME…, One subscriber's single use of one announcement. A global counter was worse…, ScreenEventRow, UtcDateTime, DeclarativeBase (+1 more)

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
Cohesion: 0.12
Nodes (16): MissingVaultKey, RuntimeError, The signing key was expected on disk and was not there., S6 — verification must use the key that signed, and survive a restart., The finding, verbatim: config.py made vault_key_path CWD-relative. A process…, The acceptance criterion: issue, restart, verify., The route returned rec.public_key while verifying with its own., Otherwise a row with a self-consistent key and signature verifies. (+8 more)

### Community 56 - "Isnad · إسناد"
Cohesion: 0.18
Nodes (11): A changed SIM should start an investigation., A receipt that can be challenged, too, Every check has a job, Evidence you can rerun, Isnad · إسناد, One integration, an explainable action, One warning. Two very different checkouts., Simulated answers. The same investigation. (+3 more)

### Community 57 - "console.html — live agent console"
Cohesion: 0.16
Nodes (13): investigate(), console.html — live agent console, askTheAgent(), showReceiptQr(), judge.html — Judge Mode verified checkout, runCheckout(), receipt.html — public evidence receipt, renderArithmetic() (+5 more)

### Community 58 - "LLMPlanner"
Cohesion: 0.15
Nodes (12): effective_planner(), LLMPlanner, Asks a model to choose the next evidence step, given the belief state, the…, The planner that will actually choose, not the one config asked for.…, _install_retries(), main(), Measure how differently the LLM planner behaves from the greedy one. This…, Give the provider every chance to answer, for measurement runs only. The demo… (+4 more)

### Community 59 - "test_audit_low.py"
Cohesion: 0.10
Nodes (20): institution_for_key(), Which institution this key may speak for, or None. Fails closed and is unset by…, _engine(), parametrize, The LOW cluster from the 31 Aug security audit. Individually small. Together…, policy.yaml prices no `actions:` entry for them — they are answered from local…, Free is the price of local evidence, not a blanket default. A network action…, SQLite's DATETIME ignores tzinfo, so an aware UTC value was written and read… (+12 more)

### Community 60 - "resolve_key_path"
Cohesion: 0.24
Nodes (9): _key_passphrase(), Path, Encrypt the key at rest when a passphrase is configured., Refuse to load a signing key that anyone else can read (S7b). File mode is not…, Make the key path absolute (S6). The default is CWD-relative, so the same…, Load the configured signer into this stable module-level instance. Modules…, _require_owner_only(), resolve_key_path() (+1 more)

### Community 61 - "3. Recommended app work — not implemented in this documentation pass"
Cohesion: 0.20
Nodes (10): 3. Recommended app work — not implemented in this documentation pass, Before implementation, Execution order and completion ledger, P1 — Fix location evidence at the provider boundary, P2 — Show the merchant what to do and why, P3 — Finish CHALLENGE without rewriting its receipt, P4a — Build the live-consent journey locally, P4b — Prove one supported handset end to end (+2 more)

### Community 62 - "investigator.py"
Cohesion: 0.15
Nodes (14): get_engine(), logodds_to_p(), Load the policy once and reuse it — avoids re-reading/parsing YAML per request., baselines(), main(), population(), What does the agent actually save, against the stack it replaces? Isnad's…, The two rules being replaced, applied to a full evidence set. The baseline is… (+6 more)

### Community 63 - "independent_evaluation.py"
Cohesion: 0.15
Nodes (19): model_validator, BaselineResult, corroboration_aware(), Dataset, evaluate(), EvaluationCase, EvidenceSpec, full_evidence_same_policy() (+11 more)

### Community 64 - "Project Brief"
Cohesion: 0.22
Nodes (13): Decision thresholds (allow_below / decline_above), Project Brief, CAMARA — open network API standard, Cash-on-delivery fraud as the market wedge, Isnad — the hadith chain of transmission, GSMA MENA Ignite / Open Gateway Hackathon 2026, Reverse Isnad — verifying the caller to the customer, Tazkiya (تزكية) — human vouching (+5 more)

### Community 65 - "test_hardening.py"
Cohesion: 0.20
Nodes (6): asyncio, A developer's .env must not be able to point the suite at real CAMARA calls.…, A developer's .env must not be able to point the suite at a paid model. The…, test_event_bus_masks_phone_numbers(), test_suite_never_calls_a_live_model(), test_suite_never_runs_against_a_billable_provider()

### Community 66 - "6. MENA Ignite submission priorities — reviewed 6 September 2026"
Cohesion: 0.22
Nodes (9): 6. MENA Ignite submission priorities — reviewed 6 September 2026, H0 — Confirm the submission contract before building more, H1 — Make the AI contribution visible and measurable, H2 — Show verifiable Nokia NaC integration, with precise scope, H3 — Make one MENA customer problem specific, H4 — Demonstrate the benefit without hiding the tradeoff, H5 — Ship one coherent, remotely accessible demonstration, Recommended time allocation, not the official rubric (+1 more)

### Community 67 - "evidence_pack.py"
Cohesion: 0.05
Nodes (65): _add_missing_columns(), _assert_schema_current(), init_db(), Path, Fail closed when a non-SQLite database was not migrated to this model., Add columns that exist on the model but not yet in the table. `create_all`…, The SQLite data file for permission hardening, if this URL has one., Keep the database and its WAL siblings owner-readable only. (+57 more)

### Community 68 - "_verdict"
Cohesion: 0.27
Nodes (11): narrate(), A sentence-level account of the finished chain. Falls back to the deterministic…, Display-only output must still respect the boundary., A bare enum name gets misread, and the misreading is self-contradictory.…, test_the_narrative_falls_back_to_a_deterministic_sentence(), test_the_narrative_is_generated_from_the_finished_chain(), test_the_narrative_is_told_what_the_grade_means(), test_the_narrative_never_changes_the_verdict() (+3 more)

### Community 69 - "Action"
Cohesion: 0.09
Nodes (30): Action, The evidence-gathering moves available to the agent. Each maps to one CAMARA…, EvidenceProvider, Protocol, Uniform contract for every source of network evidence. The agent calls…, _csv(), HybridProvider, Scripted evidence, except for the links deliberately made real. Every winner… (+22 more)

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
Cohesion: 0.24
Nodes (11): _directory(), Which institution published this number, if any. Read this response the right…, The numbers an institution publishes — the call-back question. "Hang up and…, registry_institution(), registry_lookup(), RegistryInstitution, RegistryLookupResponse, RegistryNumber (+3 more)

### Community 74 - "Isnad — compact handoff"
Cohesion: 0.25
Nodes (8): 1. Current product and evidence, 2. Mock parity — exact wording to preserve, 4. Path to a live product, 5. Code map and working rules, 7. Latest session, Isnad — compact handoff, P2 implementation — 6 Sep (follow-up session), Preserved P1 implementation record

### Community 75 - "routes_privacy.py"
Cohesion: 0.22
Nodes (8): _human(), posture(), privacy_page(), HTMLResponse, Request, The consent and retention posture, published. §0.8.5 Q9 is the sharpest…, Format the window where the number lives, not in the page. The page…, What this deployment keeps, for how long, and what it never holds.

### Community 76 - "test_s14_no_tracked_secrets.py"
Cohesion: 0.28
Nodes (8): parametrize, No credential may be tracked in the repository. This is Operating Rule 0.1…, `.env` as an exact ignore rule is not enough — the leak was `.env.bak-194200`., git check-ignore, so the rule is verified rather than eyeballed., test_no_dotenv_variant_is_tracked_except_the_example(), test_no_tracked_file_contains_a_credential(), test_the_ignore_rule_actually_covers_editor_backups(), _tracked_files()

### Community 77 - "demo_token.py"
Cohesion: 0.21
Nodes (11): is_valid(), mint(), owner_for(), The owner a console token belongs to, or None if it is not one., Issue a console token. Only callable while demo mode is on., True while `candidate` is an unexpired console token., _sweep(), console_page() (+3 more)

### Community 78 - "Result"
Cohesion: 0.10
Nodes (20): EvidenceLink, BaseModel, One attested link in the chain — the normalized result of one CAMARA call.…, Result, gather(), _link(), Registry and Verified Caller evidence for an inbound call. Ordered…, Enum (+12 more)

### Community 79 - "Choice"
Cohesion: 0.10
Nodes (16): Choice, Observation, PlannerResponse, BaseModel, The only shape the model is allowed to answer in., Exact equality against the affordable set, or greedy., Build the prompt. Every value here is an enum, a number or a bool. Rendered as…, One piece of evidence already gathered, as the planner is allowed to see it.… (+8 more)

### Community 80 - "test_s9_consent_replay.py"
Cohesion: 0.12
Nodes (17): provider(), fixture, S9 — an OAuth state must be single-use (authorization-code injection)., The 409 guard the old code could never reach. begin_callback() returned…, Whichever lands first used to win; both used to proceed., The fix must not have cost the flow it protects., Counts token exchanges so a second one cannot pass unnoticed., The acceptance criterion: a replayed callback returns 409. The attacker's path:… (+9 more)

### Community 81 - "presentation.py"
Cohesion: 0.33
Nodes (6): _degraded_context(), _fact(), A deterministic, plain-language projection of an already-signed Verdict. P2…, One human sentence for a link, traceable to that exact link. `link.api` and…, The one extra, still-derived-not-invented sentence for the DEGRADED CHALLENGE…, _summary()

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

### Community 88 - "SlidingWindowLimiter"
Cohesion: 0.20
Nodes (6): (allowed, retry_after_seconds)., Bound the bucket map. Drops windows that are entirely in the past., SlidingWindowLimiter, _Window, test_the_limiter_bucket_map_is_bounded(), test_the_window_actually_slides()

### Community 91 - "NaC integration — observed, not assumed"
Cohesion: 0.50
Nodes (4): Nokia Network as Code (NaC), Implementation Status, NaC integration — observed, not assumed, T1 — observed CAMARA responses

### Community 92 - "velocity.py"
Cohesion: 0.11
Nodes (18): is_high_velocity(), is_high_velocity_async(), _owner(), The tenant this request belongs to, set at the auth boundary (S2)., Note that this caller was screened against this callee, for this tenant., (over_threshold, observed, threshold). Threshold 0 disables the check., record(), record_async() (+10 more)

### Community 101 - "test_s4_demo_mode.py"
Cohesion: 0.15
Nodes (10): asyncio, S4 — demo mode must default off, and the session provider must not follow it., On, it opens unauthenticated write endpoints. Off is the safe rest state., Open, a stranger could fire acts into the judges' console mid-demo., Verified-good behaviour the runbook says to keep: acts hard-code the mock., The separate bug in the same flag. routes_session.py forced MockProvider…, test_console_acts_still_cannot_reach_a_billable_provider(), test_demo_endpoints_require_a_key_with_the_flag_on() (+2 more)

### Community 110 - "consent.py"
Cohesion: 0.29
Nodes (7): ConsentCapacityExceeded, _now(), _owner_hash(), datetime, RuntimeError, A live consent cannot be retained without displacing another one., Drop expired and terminal records. Caller holds the lock.

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

### Community 125 - "t1_probe.py"
Cohesion: 0.50
Nodes (4): describe(), main(), T1 — fire exactly ONE real CAMARA call and record what actually came back.…, Render an SDK response without assuming it is a dict or a pydantic model.

## Ambiguous Edges - Review These
- `S14 — committed secrets in .env.bak` → `Runbook invariants (gather() seam, no raw signals, no logging)`  [AMBIGUOUS]
  docs/PHASE2_AUDIT.md · relation: references

## Knowledge Gaps
- **82 isolated node(s):** `encode.sh script`, `L`, `TOTAL`, `SCENES`, `SCENE_START` (+77 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 900 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `S14 — committed secrets in .env.bak` and `Runbook invariants (gather() seam, no raw signals, no logging)`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `Action` connect `Action` to `test_chain_grade.py`, `test_t6_receipt.py`, `PolicyEngine`, `test_llm_planner.py`, `Investigator`, `test_presentation.py`, `test_nac_provider.py`, `GreedyPlanner`, `test_t5_counterfactual.py`, `NacProvider`, `MockProvider`, `routes_consent.py`, `VerificationRequest`, `Verdict`, `test_hybrid_provider.py`, `Money`, `SessionManager`, `test_verified_caller.py`, `test_nac_contract.py`, `LLMPlanner`, `test_audit_low.py`, `investigator.py`, `independent_evaluation.py`, `evidence_pack.py`, `_verdict`, `Result`, `Choice`, `test_s9_consent_replay.py`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `NacProvider` connect `NacProvider` to `VerificationRequest`, `Action`, `Phase 2 Agent Runbook`, `test_s12_runtime_posture.py`, `test_nac_provider.py`, `Result`, `NaC integration — observed, not assumed`, `t1_probe.py`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Why does `Video script — rendered cut and live take` connect `console.html — live agent console` to `CURRENT_STATE.md`, `NaC integration — observed, not assumed`, `Normalized Evidence Envelope (result/signal/detail/source/consent)`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 70 inferred relationships involving `Action` (e.g. with `Investigator` and `deterministic()`) actually correct?**
  _`Action` has 70 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `VerificationRequest` (e.g. with `Investigator` and `start_number_verification_consent()`) actually correct?**
  _`VerificationRequest` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 40 inferred relationships involving `MockProvider` (e.g. with `console_run()` and `EvidenceLink`) actually correct?**
  _`MockProvider` has 40 INFERRED edges - model-reasoned connections that need verification._