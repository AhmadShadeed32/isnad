'use strict';
// This page is intentionally a presentation client only.  It uses the reviewed
// console fixture endpoint and its authenticated event stream; it introduces no
// new provider-call or state-changing route.
const DEMO_TOKEN = document.querySelector('meta[name="isnad-demo-token"]')?.content || '';
const checkout = document.getElementById('checkout');
const cleanCheckout = document.getElementById('cleanCheckout');
const gapCheckout = document.getElementById('gapCheckout');
let activeScenario = 'replacement';
const mode = document.getElementById('mode');
const localeSelect = document.getElementById('locale');
const localeNote = document.getElementById('localeNote');
const planner = document.getElementById('planner');
const statusline = document.getElementById('statusline');
const trace = document.getElementById('trace');
const decision = document.getElementById('decision');
const reason = document.getElementById('reason');
const grade = document.getElementById('grade');
const presentationTitle = document.getElementById('presentationTitle');
const presentationSummary = document.getElementById('presentationSummary');
const presentationAction = document.getElementById('presentationAction');
const supportingGroup = document.getElementById('supportingGroup');
const supportingFacts = document.getElementById('supportingFacts');
const adverseGroup = document.getElementById('adverseGroup');
const adverseFacts = document.getElementById('adverseFacts');
const unresolvedGroup = document.getElementById('unresolvedGroup');
const unresolvedFacts = document.getElementById('unresolvedFacts');
const uncorroboratedGroup = document.getElementById('uncorroboratedGroup');
const uncorroboratedFacts = document.getElementById('uncorroboratedFacts');
const receipt = document.getElementById('receipt');
const receiptLink = document.getElementById('receiptLink');
const verifySignature = document.getElementById('verifySignature');
const vault = document.getElementById('vault');
const sessionBeat = document.getElementById('sessionBeat');
const sessionCopy = document.getElementById('sessionCopy');
const startTrust = document.getElementById('startTrust');
const simulateSwap = document.getElementById('simulateSwap');
const sessionState = document.getElementById('sessionState');
const fallback = document.getElementById('fallback');
const stepEls = [1,2,3,4].map(n => document.getElementById('s' + n));
// --- the judge's own evidence source ----------------------------------------
const esStatus = document.getElementById('esStatus');
const esMock = document.getElementById('esMock');
const esReal = document.getElementById('esReal');
const esExplain = document.getElementById('esExplain');
const esAccess = document.getElementById('esAccess');
const esAccessNote = document.getElementById('esAccessNote');
const esApplies = document.getElementById('esApplies');
const esAllowance = document.getElementById('esAllowance');
const accessCode = document.getElementById('accessCode');
const accessSubmit = document.getElementById('accessSubmit');
const scenarioSelect = document.getElementById('scenario');
const judgePlanner = document.getElementById('judgePlanner');
const runPaired = document.getElementById('runPaired');
const resultSource = document.getElementById('resultSource');
const reviewPanel = document.getElementById('reviewPanel');
const reviewWhy = document.getElementById('reviewWhy');
const reviewState = document.getElementById('reviewState');
const reviewOpen = document.getElementById('reviewOpen');
const reviewPassed = document.getElementById('reviewPassed');
const reviewFailed = document.getElementById('reviewFailed');
const reviewAbandoned = document.getElementById('reviewAbandoned');
const wireDetails = document.getElementById('wireDetails');
const wireProvenance = document.getElementById('wireProvenance');
const wireBody = document.getElementById('wireBody');
// The session is this browser's own tenant. It is minted on load, it is not a
// merchant key, and holding it authorizes nothing but the demonstration.
let judgeSession = null;
let capabilities = null;
// The source the *completed* result was produced with. Deliberately separate
// from whatever the radio currently says: changing the dropdown must never
// restate what an already-signed run was.
let completedSource = null;
let pairedRunning = false;
// One idempotency key per logical run, so a double click is the same request
// rather than a second paid investigation.
let pairedIdempotencyKey = null;
// The open merchant-review attempt on the CURRENT chain, if any. Server state
// decides whether it is still open; this only remembers which attempt to report
// against, and is cleared whenever a new run starts.
let reviewAttemptId = null;
let demoMode = false;
let configuredProvider = 'unknown';
let activeRunId = null;
// The run_id whose verdict has already been rendered from a persistence-
// confirmed response (the receipt is visible). A stream reconnect or a
// duplicate SSE 'verdict' delivery for that same run must not re-render over
// it with an earlier, not-yet-confirmed SSE-only snapshot.
let completedRunId = null;
let latestChainId = null;
let eventSource = null;
let streamCredential = null;
let streamReconnectTimer = null;
// Set once the exchange refuses this tab's credential outright. A refusal is
// not a blip: reconnecting cannot obtain another one, only a reload can.
let streamHalted = false;
let sessionId = null;
let streamedVerdict = null;

// --- I14: the trace is state, not the DOM ------------------------------------
//
// Every row used to be appended the moment its event arrived, which made the
// order of the trace the order of the network rather than the order of the
// investigation. Two things broke because of it: an event recovered from the
// journal after a reconnect landed *below* the later events that had already
// been drawn, and the same event delivered twice (I14 promises at least once)
// drew twice.
//
// So rows live here, keyed by the sequence the journal assigned, and the trace
// is rebuilt from this state in sequence order. An event with no `sequence`
// never reached the journal: it is live-only, unrecoverable, and cannot be
// deduplicated — it is still shown, in arrival order, after the numbered rows,
// because dropping a real observation is worse than showing it out of order.
let traceEntries = new Map();     // sequence -> {event, recovered, serverTime, at}
let traceLiveOnly = [];           // entries for events that never persisted
// Set only by a terminal 401/403 from the replay endpoint. Retrying then cannot
// mint a credential the server will honour; the reader has to reload.
let recoveryHalted = false;

// The one sentence this page is allowed to say when it cannot prove the trace
// is whole. `gap` is not that proof: `has_gap(after=0)` is always false, so a
// run whose journal writes failed outright would report "no gap" and a complete
// trace at the same time.
const INCOMPLETE_TRACE = 'Decision saved; some trace events are unavailable.';

function resetTraceState(){
  traceEntries = new Map();
  traceLiveOnly = [];
  recoveryHalted = false;
}

function key(){ return DEMO_TOKEN; }
function newRunId(){ return 'judge-' + Date.now() + '-' + Math.random().toString(16).slice(2); }
function clearSteps(){ stepEls.forEach(s => s.className = 'step'); }
function setStep(index, kind = 'active'){ if (stepEls[index]) stepEls[index].className = 'step ' + kind; }
function setStatus(text){ statusline.textContent = text; }
function safeError(err){ return err && err.message ? err.message : 'The demo request did not complete.'; }
function provenance(source){
  const normalized = String(source || 'unknown').toLowerCase();
  if (normalized === 'mock') return {label:'SIMULATOR · mock fixture', cls:'sim'};
  // A Nokia-shaped answer produced by the local contract transport. It is NOT
  // `mock` — an authored fixture — and it is NOT `nac`: the request is the real
  // serialized one, the response never left this process.
  if (normalized === 'nac_contract_mock') return {label:'MOCK · Nokia contract, answered locally', cls:'sim'};
  if (normalized === 'nac') return {label:'LIVE · Nokia NaC', cls:'live'};
  if (normalized === 'local') return {label:'LOCAL · Isnad state', cls:''};
  return {label:'PROVENANCE · ' + normalized, cls:''};
}
// Two clocks, and the difference between them is the point. A live row is
// stamped when it arrived; a recovered row is stamped with the `server_time`
// the journal recorded, because that is when it happened. Stamping a recovered
// row with `Date.now()` would date the whole missing stretch of a run to the
// moment the reader reconnected.
function traceClock(entry){
  const when = entry.recovered
    ? (entry.serverTime ? new Date(entry.serverTime) : null)
    : entry.at;
  if (!when || Number.isNaN(when.getTime())) return '';
  const pad = n => String(n).padStart(2, '0');
  return pad(when.getHours()) + ':' + pad(when.getMinutes()) + ':' + pad(when.getSeconds());
}
// The exact figures in a meta line — a risk score, a budget, a clock — are
// neutral-edged and get reordered by the bidi algorithm on an RTL page.
function metaLine(entry, meta){
  const side = document.createElement('div');
  side.className = 'trace-meta';
  const parts = [];
  if (meta) parts.push(meta);
  const stamp = traceClock(entry);
  if (stamp) parts.push(stamp);
  // Said in words, not by colour or position alone: this row was read back out
  // of the journal rather than watched happening.
  if (entry.recovered) parts.push('recovered');
  const text = parts.join(' · ');
  side.appendChild(window.Isnad ? window.Isnad.isolate(text) : document.createTextNode(text));
  return side;
}
// Builds one evidence/selection row. It returns the row rather than appending
// it: `renderTrace` decides where a row goes, because only the sequence order
// can decide that.
function appendTrace(entry, kind, title, detail, source, meta, detailKey){
  const row = document.createElement('div');
  row.className = 'trace-row ' + kind;
  const mark = document.createElement('div'); mark.className = 'mark'; mark.textContent = kind === 'pass' ? '✓' : kind === 'flag' ? '!' : '·';
  const body = document.createElement('div');
  const heading = document.createElement('div'); heading.className = 'trace-title'; heading.textContent = title;
  const copy = document.createElement('div'); copy.className = 'trace-detail';
  copy.textContent = detail || '';
  if (detailKey){
    // Falls back to the English sentence the server sent when a signal has no
    // authored copy — visibly, never to a raw key.
    copy.dataset.i18n = detailKey;
    if (window.Isnad) window.Isnad.applyDictionary(copy);
  } else {
    // A planner or model sentence. It is not authored product copy and is not
    // translated; marking it English keeps a screen reader from reading it with
    // Arabic phonetics, and keeps the untranslated part honest rather than
    // looking like a missing string.
    copy.lang = 'en';
    copy.dir = 'ltr';
  }
  body.append(heading, copy);
  if (source){ const p = provenance(source); const badge = document.createElement('span'); badge.className = 'provenance ' + p.cls; badge.textContent = p.label; body.appendChild(badge); }
  row.append(mark, body, metaLine(entry, meta));
  return row;
}
// The operator's date, rendered beside the check it explains — never merged
// into it. The two are separate observations and the operator's own answers can
// disagree, so both are shown with their own wording.
// Keyed, not resolved-once. A string written straight into textContent at
// insertion time never changes again: `setLocale` re-applies `[data-i18n]`, and
// these `ui.*` keys are not in the exact-text catalog the observer walks, so a
// switch after a result rendered would leave this row in the language it was
// born in.
function keyed(key, fallback, tag){
  const el = document.createElement(tag || 'span');
  el.dataset.i18n = 'ui.' + key;
  el.textContent = fallback;
  if (window.Isnad) window.Isnad.applyDictionary(el);
  return el;
}
function appendTiming(event, entry){
  const t = (key, fallback) => (window.Isnad ? window.Isnad.t('ui.' + key, fallback) : fallback);
  const row = document.createElement('div');
  row.className = 'trace-row info';
  const mark = document.createElement('div'); mark.className = 'mark'; mark.textContent = '·';
  const body = document.createElement('div');
  const heading = keyed('swap_date_heading', 'Operator change date', 'div');
  heading.className = 'trace-title';
  body.appendChild(heading);

  const copy = document.createElement('div'); copy.className = 'trace-detail';
  if (event.availability === 'available' && event.provider_time){
    copy.appendChild(keyed('swap_date_available', 'Operator reported the latest change at'));
    copy.append(document.createTextNode(' '));
    // A timestamp is a signed-adjacent exact value: isolated LTR so the bidi
    // algorithm cannot reorder it under an RTL page.
    copy.appendChild(window.Isnad ? window.Isnad.isolate(event.provider_time)
                                  : document.createTextNode(event.provider_time));
    if (typeof event.age_seconds === 'number'){
      const days = Math.floor(event.age_seconds / 86400);
      const hours = Math.floor((event.age_seconds % 86400) / 3600);
      copy.append(document.createTextNode(' · '));
      copy.appendChild(keyed('swap_date_age', 'Age at the moment of the check'));
      copy.append(document.createTextNode(' '));
      copy.appendChild(window.Isnad ? window.Isnad.isolate(days + 'd ' + hours + 'h')
                                    : document.createTextNode(days + 'd ' + hours + 'h'));
    }
  } else {
    // Keyed on the availability state, which the journal does keep, and never
    // on a provider sentence — the operator's own prose is not persisted and is
    // not invented here when it is missing.
    copy.appendChild(keyed('swap_date_' + (event.availability || 'unknown'),
                           event.reason || 'No date is available.'));
  }
  body.appendChild(copy);

  const notes = [];
  if (event.availability === 'available') notes.push('swap_date_may_be_activation');
  if (event.disagrees_with_window === true) notes.push('swap_date_disagrees');
  if (event.monitored_period_days === null || event.monitored_period_days === undefined){
    notes.push('swap_date_horizon_unknown');
  }
  notes.forEach(key => {
    const note = keyed(key, t(key, ''), 'div');
    note.className = 'trace-detail';
    note.style.opacity = '.75';
    body.appendChild(note);
  });

  const side = document.createElement('div'); side.className = 'trace-meta';
  side.appendChild(keyed('swap_date_separate_call', 'A separate operator call.'));
  if (typeof event.cost === 'number') side.append(document.createTextNode(' · cost ' + event.cost));
  const stamp = traceClock(entry);
  if (stamp) side.append(document.createTextNode(' · ' + stamp));
  if (entry.recovered) side.append(document.createTextNode(' · recovered'));
  row.append(mark, body, side);
  return row;
}
// The single place a stored event becomes a row. `renderTrace` calls it for
// every entry it holds, in sequence order, so the same function draws a live
// row and a recovered one and the two cannot drift apart.
function buildTraceRow(entry){
  const event = entry.event;
  if (event.type === 'decision'){
    const label = event.action === 'stop' ? 'Agent stops' : 'Agent selects ' + (event.api || event.action);
    return appendTrace(entry, 'info', label, event.rationale || 'No rationale returned.', null,
      (event.planner || 'policy') + ' · budget ' + event.budget_left);
  }
  if (event.type === 'evidence'){
    const kind = event.result === 'PASS' ? 'pass' : event.result === 'FLAG' ? 'flag' : 'info';
    const windowText = typeof event.max_age_hours === 'number' ? ' · window ' + event.max_age_hours + 'h' : '';
    // Keyed on the SIGNAL, not on the sentence. `event.detail` is authored
    // vocabulary with a window interpolated into it, so translating it by exact
    // text would break the moment the window changed. The signal is the stable
    // identity of what the network said — and it is also the only one of the
    // two the journal keeps, so a recovered row falls back to authored copy for
    // the signal rather than to a sentence written at replay time.
    return appendTrace(entry, kind, event.api || event.signal || 'Network evidence',
      event.detail || event.signal || '', event.source,
      'risk score ' + event.p_fraud + windowText,
      event.signal ? 'ui.signal_' + event.signal : null);
  }
  if (event.type === 'enrichment') return appendTiming(event, entry);
  // start, verdict and anything else: real journal rows, but not trace rows.
  return null;
}
// Stores one event. Returns whether the trace changed, so a duplicate delivery
// costs nothing and a redraw only happens when there is something new to draw.
function recordEvent(event, options){
  const opts = options || {};
  const recovered = opts.recovered === true;
  const entry = {
    event,
    recovered,
    serverTime: opts.serverTime || null,
    at: new Date(),
  };
  if (typeof event.sequence !== 'number'){
    traceLiveOnly.push(entry);
    return true;
  }
  const existing = traceEntries.get(event.sequence);
  // A live delivery supersedes a recovered one — the journal's allowlist drops
  // the operator's `detail`, so the live copy of the same event says more.
  // Anything else is the duplicate I14's at-least-once delivery promises.
  if (existing && !(existing.recovered && !recovered)) return false;
  traceEntries.set(event.sequence, entry);
  return true;
}
function renderTrace(){
  const rows = [];
  Array.from(traceEntries.keys()).sort((a, b) => a - b).forEach(sequence => {
    const row = buildTraceRow(traceEntries.get(sequence));
    if (!row) return;
    row.dataset.sequence = String(sequence);
    if (traceEntries.get(sequence).recovered) row.dataset.recovered = '1';
    rows.push(row);
  });
  traceLiveOnly.forEach(entry => {
    const row = buildTraceRow(entry);
    if (!row) return;
    // No sequence to order it by and no journal row to recover it from. Saying
    // so is more honest than giving it a number it never had.
    row.dataset.live = '1';
    rows.push(row);
  });
  trace.replaceChildren(...rows);
  trace.scrollTop = trace.scrollHeight;
}
async function apiJson(path, options = {}){
  // Both credentials travel, and each only when it exists. Sending
  // `Authorization: Bearer ` with nothing after it is worse than sending
  // nothing: the rate limiter buckets on "starts with Bearer", so outside demo
  // mode — where this page carries no demo token at all — every judge in the
  // world would have shared one 60-per-minute bucket. With the header absent,
  // the limiter falls through to the judge session, which is what actually
  // separates one judge from another here.
  const bearer = key();
  const authHeaders = bearer ? {'Authorization': 'Bearer ' + bearer} : {};
  // The judge session is this tab's own tenant and is what the server prefers
  // for reads, so a judge's chain, journal and receipt stay theirs; the demo
  // token still authorizes the legacy console fixtures.
  const judgeHeaders = judgeSession ? {'X-Judge-Session': judgeSession} : {};
  const response = await fetch(path, { ...options, headers:{...authHeaders, ...judgeHeaders, ...window.IsnadKey.headers(path), ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok){
    // The status rides on the error, the same way console.js carries it. A
    // retry loop that cannot tell a 503 from a 403 either abandons a failure
    // that would have healed on its own, or hammers one that never will.
    const failure = new Error(data.detail?.message || data.detail?.code || 'request failed (' + response.status + ')');
    failure.status = response.status;
    throw failure;
  }
  return data;
}
function setMode(data){
  demoMode = data.demo_mode === true;
  configuredProvider = data.provider || 'unknown';
  // "Configured", because this pill is about the DEPLOYMENT's default
  // provider, not about the run on screen. A judge who has just made a real
  // Nokia call should not read "mock provider" beside it as a claim about
  // their result — the result carries its own source, right under the decision.
  const providerLabel = configuredProvider === 'nac' ? 'LIVE PROVIDER · configured: Nokia NaC' : configuredProvider === 'mock' ? 'SIMULATOR · configured provider: mock' : 'PROVIDER · configured: ' + configuredProvider;
  mode.textContent = providerLabel + (demoMode ? ' · stage mode' : '');
  mode.className = 'mode ' + (configuredProvider === 'nac' && !demoMode ? 'live' : 'sim');
  planner.textContent = 'planner: ' + (data.planner || 'unknown');
  // Only the CUSTOM stories depend on demo mode: they run the console's own
  // authored fixtures. The two paired Nokia sources are a separate, scoped
  // path and stay available in a production posture, which is the whole point
  // of giving a judge their own session.
  if (!demoMode){ checkout.disabled = true; cleanCheckout.disabled = true; gapCheckout.disabled = true; document.getElementById('checkoutFoot').textContent = 'The custom mock stories are demo-mode fixtures and are disabled here. The paired Nokia scenarios above still run.'; }
}
// A tab is credentialed if it holds EITHER a demo token or a judge session.
// Outside demo mode there is no demo token, and gating on that alone left a
// production-posture judge with no live trace at all — the decision still
// arrived, but the reasoning the page exists to show did not.
function credentialed(){ return Boolean(key() || judgeSession); }
function scheduleStreamReconnect(){
  if (streamReconnectTimer || streamHalted || !credentialed()) return;
  streamReconnectTimer = setTimeout(() => {
    streamReconnectTimer = null;
    connectStream().catch(() => {});
  }, 5000);
}
async function connectStream(){
  if (!credentialed()) return;
  try{
    const token = await apiJson('/v1/console/stream-token', {method:'POST'});
    streamCredential = token.stream_token;
    if (!streamCredential) throw new Error('Could not start the evidence stream.');
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/v1/console/stream?stream_token=' + encodeURIComponent(streamCredential));
    // The moment the stream comes back is the moment recovery has a job: the
    // run kept going while this tab was not listening, and the journal already
    // holds what it missed. Reconciling here rather than only at the end is
    // what lets a reader watch the rest of a run they joined late.
    eventSource.onopen = () => {
      if (activeRunId) reconcileTrace(activeRunId).catch(() => {});
    };
    eventSource.onmessage = message => { try { onEvent(JSON.parse(message.data)); } catch (_) { /* Ignore a malformed stream frame. */ } };
    eventSource.onerror = () => {
      if (eventSource) eventSource.close();
      eventSource = null; streamCredential = null;
      if (activeRunId && decision.textContent === 'VERIFYING') setStatus('Connection interrupted; reconnecting to the evidence stream…');
      scheduleStreamReconnect();
    };
  }catch(err){
    // A credential the exchange refuses will be refused again in five seconds.
    // Looping on it leaves the reader watching a reconnect message that can
    // never resolve, so say what actually recovers it and stop.
    if (err && (err.status === 401 || err.status === 403)){
      streamHalted = true;
      setStatus('This demo session expired, so the live evidence stream stopped.'
        + ' Reload the page to start a new one. The checkout still runs; its'
        + ' trace is read back from the journal afterwards.');
    } else {
      scheduleStreamReconnect();
    }
    throw err;
  }
}
// True once the active run's decision has come back confirmed persisted. The
// trace keeps accepting events after that — a late or replayed one is still a
// real observation — but the status line and the progress steps belong to the
// finished result from then on.
function settled(){ return completedRunId !== null && completedRunId === activeRunId; }
function onEvent(event){
  if (event.type !== 'session' && (!activeRunId || event.run_id !== activeRunId)) return;
  if (event.type === 'session'){
    handleSessionEvent(event);
  } else if (event.type === 'start'){
    setStep(0); setStatus('Agent formed a ' + String(event.hypothesis || 'checkout') + ' hypothesis. Prior risk score: ' + event.prior_p_fraud + '.');
  } else if (event.type === 'decision'){
    // The row is always recorded; the running commentary only applies while
    // the run is still running. An event that lags the POST response would
    // otherwise walk the progress steps backwards and overwrite the sentence
    // describing the finished decision.
    if (!settled()) setStep(1);
    if (recordEvent(event)) renderTrace();
    if (event.phase === 'investigation' && event.planner) planner.textContent = 'planner: ' + event.planner;
    if (!settled()) setStatus('Agent selected the next check from the remaining evidence budget.');
  } else if (event.type === 'evidence'){
    if (!settled()) setStep(2);
    if (recordEvent(event)) renderTrace();
    if (!settled()) setStatus('Evidence received with its source and result.');
  } else if (event.type === 'enrichment'){
    if (recordEvent(event)) renderTrace();
  } else if (event.type === 'verdict'){
    if (event.run_id === completedRunId) return; // already rendered from a persistence-confirmed response
    stepEls.forEach((s, index) => s.className = 'step ' + (index === 3 ? (event.decision === 'DECLINE' ? 'bad' : 'good') : 'good'));
    streamedVerdict = event;
    // Not yet persisted: this event fires from inside the server's investigation,
    // before the caller has saved the chain. persisted stays false so the
    // receipt link does not appear before there is a receipt to open.
    renderVerdict(event, {persisted:false}); setStatus('Decision complete. Saving the signed evidence chain…');
  }
}
// --- I14: reconciling the trace with the journal -----------------------------
//
// Nothing below re-runs an investigation or buys a check again. It reads the
// journal the server wrote *before* each event was ever put on the stream, so a
// tab that missed the whole stream still ends up with the same trace as one
// that watched it — at zero extra cost to the operator.
//
// It also touches nothing but the trace. The verdict, the chain id, the receipt
// link and the signature result all come from the investigation POST, which is
// the only thing that confirms the chain was persisted, and a replay that
// arrives late or fails must not be able to disturb any of them.
const REPLAY_RETRY_DELAYS = [200, 500, 1000];
// The endpoint pages at `settings.run_replay_page_size` and returns no next
// cursor; sequences are contiguous per run, so the cursor is simply the highest
// sequence seen so far. The bound is here because a loop driven by a server
// response should always have one, not because a demo run approaches it.
const REPLAY_MAX_PAGES = 50;
function wait(ms){ return new Promise(resolve => setTimeout(resolve, ms)); }
async function replayPage(runId, after){
  let lastError = null;
  for (let attempt = 0; attempt <= REPLAY_RETRY_DELAYS.length; attempt++){
    try {
      return await apiJson('/v1/console/runs/' + encodeURIComponent(runId)
        + '/events?after=' + encodeURIComponent(after));
    } catch (err){
      // 401/403 is the server saying this demo credential will never be
      // honoured again — the process that minted it is gone. No number of
      // retries mints another. Every other 4xx is a request this client would
      // keep getting wrong. Only a transport failure (no status at all) or a
      // 5xx is worth asking again for.
      if (typeof err.status === 'number' && err.status < 500) throw err;
      lastError = err;
      if (attempt === REPLAY_RETRY_DELAYS.length) break;
      await wait(REPLAY_RETRY_DELAYS[attempt]);
      if (activeRunId !== runId) return null;
    }
  }
  throw lastError || new Error('the journal could not be read');
}
// Complete means the journal can prove it, and only two facts can: every
// sequence from 1 to the highest is present, and the run's verdict is among
// them. `gap` cannot stand in for this — `has_gap(after=0)` is always false, so
// a run whose writes failed outright reports no gap at all.
function journalIsComplete(sequences, sawVerdict){
  if (!sawVerdict) return false;
  const unique = Array.from(new Set(sequences)).sort((a, b) => a - b);
  if (!unique.length) return false;
  return unique[0] === 1 && unique[unique.length - 1] === unique.length;
}
async function reconcileTrace(runId, options){
  const final = (options || {}).final === true;
  if (!runId || !key() || recoveryHalted) return;
  const sequences = [];
  let sawVerdict = false;
  let changed = false;
  let after = 0;
  try {
    for (let page = 0; page < REPLAY_MAX_PAGES; page++){
      const data = await replayPage(runId, after);
      // A response for a run the reader has already left. A replay row carries
      // a sequence, an event type, a body and a server time — and no run_id, so
      // there is nothing inside it that could catch this mistake later. The
      // only binding available is the run this fetch asked about.
      if (data === null || activeRunId !== runId) return;
      const rows = Array.isArray(data.events) ? data.events : [];
      if (!rows.length) break;
      rows.forEach(row => {
        if (typeof row.sequence !== 'number') return;
        sequences.push(row.sequence);
        if (row.sequence > after) after = row.sequence;
        if (row.event_type === 'verdict'){
          // Counted, never rendered. The persisted verdict this page shows
          // comes from the POST response, which is what confirms the chain was
          // saved and the receipt exists; a journal row proves neither.
          sawVerdict = true;
          return;
        }
        if (recordEvent({...row.body, type: row.event_type, sequence: row.sequence},
                        {recovered: true, serverTime: row.server_time})){
          changed = true;
        }
      });
    }
  } catch (err){
    const terminal = err && (err.status === 401 || err.status === 403);
    if (terminal) recoveryHalted = true;
    if (changed) renderTrace();
    if (activeRunId !== runId) return;
    // A failed recovery may not hide a decision that was already saved. The
    // verdict, the receipt and the signature result are untouched above; all
    // that changes here is the sentence describing the trace.
    if (completedRunId === runId){
      setStatus(INCOMPLETE_TRACE + (terminal ? ' Reload the page to try again.' : ''));
    } else if (terminal){
      setStatus('This demo session expired. Reload the page to continue.');
    }
    return;
  }
  if (changed) renderTrace();
  if (activeRunId !== runId) return;
  // Only the reconciliation that follows a confirmed decision may speak about
  // completeness. One triggered by a mid-run reconnect has nothing to be
  // complete about yet, and saying so either way would be wrong.
  if (!final || completedRunId !== runId) return;
  if (!journalIsComplete(sequences, sawVerdict)) setStatus(INCOMPLETE_TRACE);
}

// The network-conditions panel moved to /console. It is a diagnostic about
// the NETWORK, not about a person, it never touches a verdict, and on this
// page it competed with the decision for attention and pushed the primary
// action below the first screen. Its markup, its subscription state and its
// listeners now live in console.js — one owner, not two that can disagree.
//
// Nothing is left behind here on purpose: the listeners were attached at
// module load against getElementById results, so removing the markup without
// removing this would have thrown on load and taken the whole page with it.

// `items` are the server's English sentences; `links` are the chain rows they
// were built from. When the chain is present each fact is rebuilt from the
// link's SIGNAL, which is stable and has authored copy in both languages, and
// the API name is kept verbatim beside it — a CAMARA product name is not
// something to translate. Without the chain the server's sentence stands.
function setFactGroup(group, list, items, links){
  const rows = Array.isArray(links) && links.length ? links : null;
  group.hidden = (rows ? rows.length : items.length) === 0;
  list.replaceChildren();
  if (rows){
    rows.forEach(link => {
      const li = document.createElement('li');
      const api = document.createElement('span');
      api.lang = 'en'; api.dir = 'ltr'; api.textContent = (link.api || '') + ': ';
      li.appendChild(api);
      li.appendChild(keyed('signal_' + link.signal, link.detail || link.signal || ''));
      list.appendChild(li);
    });
    return;
  }
  items.forEach(text => { const li = document.createElement('li'); li.textContent = text; list.appendChild(li); });
}
function applyPresentation(data){
  const p = data.presentation;
  if (p && typeof p === 'object'){
    presentationTitle.replaceChildren(
      keyed('decision_title_' + (data.decision || 'UNKNOWN'), p.title || (data.decision || '—'))
    );
    // The deterministic explanation is composed server-side from this chain's
    // own numbers and thresholds, so there is no fixed sentence to key. It is
    // marked English rather than left to look like a missing translation —
    // see docs/TESTING_GUIDE.md for this limit.
    presentationSummary.textContent = p.summary || '';
    presentationSummary.lang = 'en';
    presentationSummary.dir = 'ltr';
    presentationAction.replaceChildren(
      keyed('next_action_' + (data.decision || 'UNKNOWN'), p.next_action || '')
    );
    const chain = Array.isArray(data.chain) ? data.chain : [];
    const unresolvedSignals = ['CONSENT_REQUIRED', 'PROVIDER_UNAVAILABLE', 'EVIDENCE_UNAVAILABLE'];
    setFactGroup(supportingGroup, supportingFacts,
      Array.isArray(p.supporting_facts) ? p.supporting_facts : [],
      chain.filter(link => link.result === 'PASS'));
    setFactGroup(adverseGroup, adverseFacts,
      Array.isArray(p.adverse_facts) ? p.adverse_facts : [],
      chain.filter(link => link.result === 'FLAG'));
    setFactGroup(unresolvedGroup, unresolvedFacts,
      Array.isArray(p.unresolved_checks) ? p.unresolved_checks : [],
      chain.filter(link => unresolvedSignals.indexOf(link.signal) !== -1));
    // Distinct from "could not be checked": this names an adverse FINDING that
    // was never corroborated, which is the reason a CHALLENGE here is not the
    // DECLINE the raw score alone would have produced. Server-composed from
    // the signed gap, so it is marked English rather than left looking like a
    // missing translation.
    const gaps = Array.isArray(p.unmet_corroboration) ? p.unmet_corroboration : [];
    uncorroboratedGroup.hidden = gaps.length === 0;
    uncorroboratedFacts.replaceChildren();
    gaps.forEach(sentence => {
      const li = document.createElement('li');
      li.lang = 'en'; li.dir = 'ltr';
      li.textContent = sentence;
      uncorroboratedFacts.appendChild(li);
    });
    return;
  }
  // Backward-compatible fallback: an older cached response or an in-flight SSE
  // snapshot with no presentation attached yet. Falls back to the existing
  // reason text rather than showing nothing.
  presentationTitle.textContent = data.decision || '—';
  presentationSummary.textContent = data.reason || 'No evidence chain yet.';
  presentationAction.textContent = '';
  setFactGroup(supportingGroup, supportingFacts, []);
  setFactGroup(adverseGroup, adverseFacts, []);
  setFactGroup(unresolvedGroup, unresolvedFacts, []);
  uncorroboratedGroup.hidden = true;
  uncorroboratedFacts.replaceChildren();
}
function renderSourceBadge(data){
  // Bound to the run that produced this result, not to the current dropdown.
  // A judge who changes the selector afterwards must still see what THIS
  // decision rested on.
  const judge = data.judge || null;
  const sources = data.provider_sources || [];
  let text = '';
  if (judge){
    text = (judge.evidence_source === 'nokia_simulator'
      ? say('es_result_real', 'This result: actual requests to Nokia\u2019s hosted simulator')
      : say('es_result_mock', 'This result: Nokia-compatible responses answered locally · no requests were sent to Nokia'))
      + ' · contract ' + judge.contract_version;
  } else if (sources.length){
    text = say('es_result_fixture', 'This result: authored demonstration fixtures')
      + ' (' + sources.join(', ') + ')';
  }
  if (!text){ resultSource.hidden = true; resultSource.textContent = ''; return; }
  resultSource.hidden = false;
  resultSource.replaceChildren(window.Isnad ? window.Isnad.isolate(text) : document.createTextNode(text));
}
function renderVerdict(data, {persisted = true} = {}){
  latestChainId = data.chain_id;
  renderSourceBadge(data);
  decision.textContent = data.decision || '—'; decision.className = 'decision small ' + (data.decision || '');
  presentationTitle.className = 'decision ' + (data.decision || '');
  applyPresentation(data);
  reason.textContent = data.reason || '';
  const steps = data.evidence_steps ?? '—';
  // "Demo duration", not a latency claim: the console paces each check at
  // roughly 650 ms so the trace is readable on stage. It is presentational
  // pacing, never a measurement of real network latency.
  const duration = data.latency_ms ?? '—';
  // Isolated: a grade token, a count and a millisecond figure strung together
  // are reordered at their neutral edges by an RTL page.
  const gradeLine = document.createElement('bdi');
  gradeLine.dir = 'ltr';
  gradeLine.textContent = 'chain grade: ' + (data.chain_grade || 'not recorded') + ' · ' + steps + ' evidence steps · demo duration ' + duration + ' ms (paced ~650 ms per check for readability, not a latency measurement)';
  grade.replaceChildren(gradeLine);
  if (data.planner) planner.textContent = 'planner: ' + data.planner;
  vault.textContent = ''; lastSignatureOk = null;
  sessionId = null; simulateSwap.disabled = true;
  const isCleanAllow = activeScenario === 'clean' && data.decision === 'ALLOW';
  sessionBeat.classList.toggle('visible', isCleanAllow);
  const canSimulate = isCleanAllow && demoMode && configuredProvider === 'mock';
  startTrust.disabled = !canSimulate;
  sessionCopy.textContent = canSimulate
    ? 'Start a short trust session for this fixed checkout fixture, then simulate a SIM change. A live deployment waits for a real network signal instead.'
    : 'This continuity drill is intentionally disabled: simulated swaps are available only in demo mode with the mock provider. Live deployments wait for real network changes.';
  setSessionState(canSimulate ? 'Ready for a demo-only continuity check.' : 'Simulator continuity drill unavailable in this environment.');
  if (persisted && latestChainId){
    // Only now, confirmed saved by the server that returned this response,
    // does a receipt actually exist to open.
    receiptLink.href = '/r/' + encodeURIComponent(latestChainId);
    receipt.classList.add('visible');
    completedRunId = activeRunId;
    setStatus('Decision complete. The receipt below contains the signed evidence chain.');
    renderReviewPanel(data);
    // Recovers an attempt opened before a refresh: server state, not this
    // page's memory, decides whether one is still open.
    refreshReviewTimeline().catch(() => {});
  } else {
    reviewPanel.hidden = true;
  }
}
// --- the paired evidence-source controller -----------------------------------
//
// Everything below decides only what the NEXT run asks for. Nothing here
// rewrites a completed run's labels: a signed result keeps the source it was
// produced with, whatever the dropdown is showing when the reader looks at it.

function selectedSource(){ return esReal.checked ? 'nokia_simulator' : 'mock_nokia'; }

// Every sentence this controller writes is keyed, so an Arabic reader gets
// Arabic. `t` falls back to English visibly rather than to a raw key.
function say(key, fallback){ return window.Isnad ? window.Isnad.t('ui.' + key, fallback) : fallback; }
// Text AND key together: the shared MutationObserver re-applies `data-i18n`
// after any mutation, so an element that keeps a stale key has its new text
// overwritten the moment anything else on the page changes.
function setKeyed(el, key, fallback){
  el.setAttribute('data-i18n', 'ui.' + key);
  el.textContent = say(key, fallback);
}

function sourceCapability(id){
  return (capabilities?.sources || []).find(source => source.id === id) || null;
}

function describeSource(){
  // The exact required wording, one sentence per choice, always under the
  // selected one. Mock says plainly that Gemini is a separate choice, because
  // "mock" and "offline" are not the same claim.
  if (selectedSource() === 'nokia_simulator'){
    setKeyed(esExplain, 'es_real_explain', "Actual requests to Nokia's hosted simulator using test numbers.");
  } else {
    setKeyed(esExplain, 'es_mock_explain', 'Nokia-compatible responses simulated locally for demonstration. No requests are sent to Nokia. Gemini may still be used if selected.');
  }
}

function renderAllowance(){
  const allowance = capabilities?.allowance;
  if (!allowance || !allowance.nac_capability){ esAllowance.textContent = ''; return; }
  const line = say('es_allowance', 'Real NaC allowance') + ' · ' + allowance.session_attempts_left
    + ' / ' + allowance.deployment_attempts_left + ' · ' + allowance.attempts_per_run;
  esAllowance.replaceChildren(window.Isnad ? window.Isnad.isolate(line) : document.createTextNode(line));
}

function renderCapabilities(){
  if (!capabilities){
    setKeyed(esStatus, 'es_status_unavailable', 'Evidence source options unavailable. Reload to try again.');
    return;
  }
  const real = sourceCapability('nokia_simulator');
  const authorized = capabilities.allowance?.nac_capability === true;
  // Configuration readiness, never a connection claim. This badge must not be
  // readable as "a Nokia call succeeded"; only a completed run says that.
  if (!real?.available){
    setKeyed(esStatus, 'es_status_disabled', 'Real NaC is not enabled on this deployment. Mock evidence is unaffected.');
  } else if (authorized){
    setKeyed(esStatus, 'es_status_authorized', 'Real NaC configured and authorized for this session · Nokia connection not yet verified');
  } else {
    setKeyed(esStatus, 'es_status_needs_code', 'Real NaC configured · access code required · Nokia connection not yet verified');
  }
  esReal.disabled = !real?.available;
  // The access exchange is offered only when it would actually help.
  esAccess.hidden = !(real?.available && !authorized);
  if (!real?.available && esReal.checked){ esMock.checked = true; }
  const options = (capabilities.scenarios || []).map(scenario => {
    const option = document.createElement('option');
    option.value = scenario.id;
    option.textContent = (Locale && Locale.locale && Locale.locale() === 'ar' ? scenario.label_ar : scenario.label_en)
      + ' · ' + scenario.masked_number;
    return option;
  });
  const previous = scenarioSelect.value;
  scenarioSelect.replaceChildren(...options);
  if (previous && options.some(option => option.value === previous)) scenarioSelect.value = previous;
  describeSource();
  renderAllowance();
}

async function loadCapabilities(){
  capabilities = await apiJson('/v1/judge/capabilities');
  renderCapabilities();
}

async function startJudgeSession(){
  const data = await apiJson('/v1/judge/session', {method:'POST'});
  judgeSession = data.session;
  capabilities = data.capabilities;
  renderCapabilities();
}

async function unlockRealSource(){
  const code = (accessCode.value || '').trim();
  if (!code) return;
  accessSubmit.disabled = true;
  esAccessNote.hidden = false;
  setKeyed(esAccessNote, 'es_access_checking', 'Checking the access code…');
  try{
    const data = await apiJson('/v1/judge/access', {method:'POST', body:JSON.stringify({access_code: code})});
    capabilities = data.capabilities;
    // Never kept in the page after it has been exchanged.
    accessCode.value = '';
    setKeyed(esAccessNote, 'es_access_unlocked', 'Real NaC unlocked for this session.');
    renderCapabilities();
  }catch(err){
    // A server message, not a dictionary key: it is the specific refusal, and
    // paraphrasing it would lose which of several reasons applied.
    esAccessNote.removeAttribute('data-i18n');
    esAccessNote.textContent = safeError(err);
  }finally{
    accessSubmit.disabled = false;
  }
}

function renderWireDetails(judge){
  if (!judge){ wireDetails.hidden = true; return; }
  wireDetails.hidden = false;
  const hosted = judge.evidence_source === 'nokia_simulator';
  const line = (hosted ? say('es_wire_hosted', 'Hosted Nokia simulator') : say('es_wire_mock', 'Local Nokia-contract mock'))
    + ' · contract ' + judge.contract_version
    + ' · scenario ' + judge.scenario
    + ' · ' + judge.outbound_attempts + ' outbound attempt(s)'
    + (hosted ? '' : ' · ' + say('es_wire_synthetic', 'status and timing below are synthetic, not a measured Nokia latency'));
  wireProvenance.replaceChildren(window.Isnad ? window.Isnad.isolate(line) : document.createTextNode(line));
  // Method, path, status, duration. Deliberately no headers and no bodies:
  // an authorization header is a credential and a response body is the
  // operator's, and neither belongs on a page a stranger can open.
  const rows = (judge.attempts || []).map(attempt =>
    attempt.method + ' ' + attempt.path + '  →  ' + (attempt.status ?? attempt.error ?? 'no response')
    + '  (' + attempt.duration_ms + ' ms)');
  wireBody.textContent = rows.length ? rows.join('\n') : say('es_wire_none', 'No outbound attempt was made for this run.');
}

async function runPairedInvestigation(){
  if (pairedRunning || !judgeSession) return;
  const source = selectedSource();
  const scenario = scenarioSelect.value;
  if (!scenario) return;
  pairedRunning = true;
  runPaired.disabled = true;
  // The choice is frozen for the whole run on the server too; disabling the
  // controls here just stops the page disagreeing with it on screen.
  esMock.disabled = true; esReal.disabled = true; scenarioSelect.disabled = true; judgePlanner.disabled = true;
  esApplies.hidden = true;
  activeScenario = scenario;
  sessionBeat.classList.remove('visible'); fallback.classList.remove('visible');
  latestChainId = null; streamedVerdict = null; receipt.classList.remove('visible'); completedRunId = null;
  wireDetails.hidden = true;
  resetTraceState();
  trace.replaceChildren(); clearSteps();
  decision.textContent = 'VERIFYING'; decision.className = 'decision small';
  presentationTitle.textContent = 'VERIFYING'; presentationTitle.className = 'decision';
  presentationSummary.textContent = 'The agent is deciding what evidence it needs.';
  presentationAction.textContent = '';
  setFactGroup(supportingGroup, supportingFacts, []); setFactGroup(adverseGroup, adverseFacts, []); setFactGroup(unresolvedGroup, unresolvedFacts, []);
  uncorroboratedGroup.hidden = true; uncorroboratedFacts.replaceChildren();
  reason.textContent = 'The agent is deciding what evidence it needs.'; grade.textContent = '';
  activeRunId = newRunId();
  // One key per logical run. A second click while this is in flight is the
  // same request; it is never a second investigation.
  pairedIdempotencyKey = activeRunId;
  const runId = activeRunId;
  setStatus(source === 'nokia_simulator'
    ? say('es_running_real', 'Sending actual requests to Nokia\u2019s hosted simulator…')
    : say('es_running_mock', 'Running the Nokia-compatible contract locally. No requests are sent to Nokia.'));
  try{
    const data = await apiJson('/v1/judge/run', {
      method:'POST',
      headers:{'X-Console-Run-Id':runId, 'Idempotency-Key':pairedIdempotencyKey},
      body: JSON.stringify({evidence_source: source, scenario, planner: judgePlanner.value}),
    });
    // A response that arrived for a run the reader has already left is
    // discarded, not drawn over the run they are looking at now.
    if (activeRunId !== runId) return;
    completedSource = data.judge;
    renderVerdict({...data, ...(streamedVerdict && streamedVerdict.run_id === runId ? streamedVerdict : {})}, {persisted:true});
    renderWireDetails(data.judge);
    if (data.judge?.allowance){ capabilities = {...(capabilities || {}), allowance: data.judge.allowance}; renderAllowance(); }
    reconcileTrace(runId, {final:true}).catch(() => {});
  }catch(err){
    // A real failure stays a real failure. The page offers mock as a new run,
    // and never relabels this one.
    fallback.textContent = (source === 'nokia_simulator'
      ? say('es_failed_real', 'The real Nokia run did not complete:')
      : say('es_failed_mock', 'The mock run did not complete:')) + ' ' + safeError(err)
      + (source === 'nokia_simulator' ? ' ' + say('es_failed_real_retry', 'You can choose Mock and run again; that creates a separate run with its own receipt.') : '');
    fallback.classList.add('visible');
    setStatus('This run did not complete.');
  }finally{
    pairedRunning = false;
    runPaired.disabled = false;
    esMock.disabled = false;
    esReal.disabled = !sourceCapability('nokia_simulator')?.available;
    scenarioSelect.disabled = false; judgePlanner.disabled = false;
    loadCapabilities().catch(() => {});
  }
}

// --- the merchant's follow-up on a CHALLENGE ---------------------------------
//
// Three facts stay separate here, and the panel says so: Isnad's own CHALLENGE
// verdict, the merchant's reported review result, and whatever the merchant
// then does about the order. A passed review does not rewrite the verdict to
// ALLOW, does not establish that the customer is legitimate, and does not
// release anything. The original receipt is unchanged by all of it.

function setReviewState(key, fallback, suffix){
  reviewState.setAttribute('data-i18n', 'ui.' + key);
  reviewState.textContent = say(key, fallback) + (suffix ? ' · ' + suffix : '');
  if (suffix) reviewState.removeAttribute('data-i18n');
}

function showReviewActions({open}){
  reviewOpen.hidden = open;
  reviewPassed.hidden = !open;
  reviewFailed.hidden = !open;
  reviewAbandoned.hidden = !open;
}

function renderReviewPanel(data){
  // Only a CHALLENGE has a follow-up. On ALLOW or DECLINE there is nothing for
  // a merchant to review, and offering the control would imply otherwise.
  const challenged = data && data.decision === 'CHALLENGE';
  reviewPanel.hidden = !challenged;
  reviewAttemptId = null;
  if (!challenged) return;
  // What the agent could not settle, in its own words, so the panel explains
  // what a merchant would be checking rather than inventing a reason.
  const unresolved = (data.presentation && data.presentation.unresolved) || [];
  const gaps = (data.presentation && data.presentation.uncorroborated) || [];
  const lines = [...unresolved, ...gaps].map(item => (typeof item === 'string' ? item : item.text || ''))
    .filter(Boolean);
  reviewWhy.textContent = lines.length
    ? say('review_unresolved', 'What the merchant would check') + ': ' + lines.join(' · ')
    : '';
  setReviewState('review_not_started', 'Review not started.');
  showReviewActions({open:false});
}

async function refreshReviewTimeline(){
  if (!latestChainId) return;
  try{
    const data = await apiJson('/v1/chains/' + encodeURIComponent(latestChainId) + '/challenges');
    // The server's expiry decides whether an attempt is still open, not this
    // page's memory of having opened one.
    const open = (data.attempts || []).find(attempt => attempt.status === 'PENDING');
    if (open){
      reviewAttemptId = open.attempt_id;
      setReviewState('review_pending', 'Review open and awaiting a result',
        say('review_expires', 'expires') + ' ' + (open.expires_at || ''));
      showReviewActions({open:true});
      return;
    }
    const last = (data.attempts || [])[ (data.attempts || []).length - 1 ];
    if (last){
      reviewAttemptId = null;
      setReviewState('review_recorded', 'Merchant review recorded', last.status);
      showReviewActions({open:false});
      reviewOpen.hidden = false;
    }
  }catch(err){ /* a read failure leaves the last known state on screen */ }
}

async function openMerchantReview(){
  if (!latestChainId) return;
  reviewOpen.disabled = true;
  setReviewState('review_opening', 'Opening a manual review…');
  try{
    const attempt = await apiJson('/v1/chains/' + encodeURIComponent(latestChainId) + '/challenges', {
      method:'POST',
      // Stable per chain: a double click opens one review, not two.
      headers:{'Idempotency-Key':'review-open-' + latestChainId},
      body: JSON.stringify({method:'manual_review'}),
    });
    reviewAttemptId = attempt.attempt_id;
    setReviewState('review_pending', 'Review open and awaiting a result',
      say('review_expires', 'expires') + ' ' + (attempt.expires_at || ''));
    showReviewActions({open:true});
  }catch(err){
    reviewState.removeAttribute('data-i18n');
    reviewState.textContent = say('review_failed_to_open', 'The review could not be opened:') + ' ' + safeError(err);
  }finally{ reviewOpen.disabled = false; }
}

async function reportMerchantReview(result){
  if (!latestChainId || !reviewAttemptId) return;
  [reviewPassed, reviewFailed, reviewAbandoned].forEach(button => { button.disabled = true; });
  setReviewState('review_reporting', 'Recording the review result…');
  try{
    const event = await apiJson('/v1/chains/' + encodeURIComponent(latestChainId)
      + '/challenges/' + encodeURIComponent(reviewAttemptId) + '/events', {
      method:'POST',
      headers:{'Idempotency-Key':'review-' + reviewAttemptId + '-' + result},
      body: JSON.stringify({result}),
    });
    reviewAttemptId = null;
    setReviewState('review_recorded', 'Merchant review recorded', event.status);
    showReviewActions({open:false});
    reviewOpen.hidden = false;
  }catch(err){
    reviewState.removeAttribute('data-i18n');
    reviewState.textContent = safeError(err);
    await refreshReviewTimeline();
  }finally{
    [reviewPassed, reviewFailed, reviewAbandoned].forEach(button => { button.disabled = false; });
  }
}

reviewOpen.addEventListener('click', () => { openMerchantReview().catch(() => {}); });
reviewPassed.addEventListener('click', () => { reportMerchantReview('PASSED').catch(() => {}); });
reviewFailed.addEventListener('click', () => { reportMerchantReview('FAILED').catch(() => {}); });
reviewAbandoned.addEventListener('click', () => { reportMerchantReview('ABANDONED').catch(() => {}); });

esMock.addEventListener('change', () => { describeSource(); if (completedSource) esApplies.hidden = false; });
esReal.addEventListener('change', () => { describeSource(); if (completedSource) esApplies.hidden = false; });
accessSubmit.addEventListener('click', () => { unlockRealSource().catch(() => {}); });
accessCode.addEventListener('keydown', (event) => { if (event.key === 'Enter') unlockRealSource().catch(() => {}); });
runPaired.addEventListener('click', () => { runPairedInvestigation().catch(() => {}); });

const SCENARIO_COPY = {
  replacement: {
    title: 'New SIM. Same customer.',
    story: 'Her SIM was replaced, but her handset is unchanged. A rule that declines every SIM change loses her order. Isnad checks the surrounding evidence before deciding.',
    foot: 'Expected: CHALLENGE. Ask for the merchant’s step-up instead of automatically declining. Operator answers are simulated.',
    path: '/v1/console/run/act6',
  },
  clean: {
    title: 'A clean checkout.',
    story: 'A new customer has no merchant history. Supporting network evidence can let this checkout proceed without another step-up.',
    foot: 'Expected: ALLOW. Supporting evidence clears this fixed example. Operator answers are simulated.',
    path: '/v1/console/run/act3',
  },
  gap: {
    title: 'Consent withheld, one operator gone quiet.',
    story: 'The customer has not granted Number Verification consent, and one operator check comes back unavailable rather than pass or fail. The chain has a real gap in it, not a contradiction.',
    foot: 'Expected: CHALLENGE, evidence unresolved. This is "we could not check," not "the check failed."',
    path: '/v1/console/run/act5',
  },
};
async function runCheckout(scenario = 'replacement'){
  if (!demoMode || !key()) return;
  activeScenario = scenario;
  const copy = SCENARIO_COPY[scenario] || SCENARIO_COPY.replacement;
  document.getElementById('customerTitle').textContent = copy.title;
  document.getElementById('customerStory').textContent = copy.story;
  document.getElementById('checkoutFoot').textContent = copy.foot;
  checkout.disabled = true; cleanCheckout.disabled = true; gapCheckout.disabled = true;
  sessionBeat.classList.remove('visible'); fallback.classList.remove('visible');
  latestChainId = null; streamedVerdict = null; receipt.classList.remove('visible'); completedRunId = null;
  // Sequences restart at 1 for every run, so the previous run's state would
  // both suppress this run's events and draw the previous run's rows.
  resetTraceState();
  trace.replaceChildren(); clearSteps();
  decision.textContent = 'VERIFYING'; decision.className = 'decision small';
  presentationTitle.textContent = 'VERIFYING'; presentationTitle.className = 'decision';
  presentationSummary.textContent = 'The agent is deciding what evidence it needs.';
  presentationAction.textContent = '';
  setFactGroup(supportingGroup, supportingFacts, []); setFactGroup(adverseGroup, adverseFacts, []); setFactGroup(unresolvedGroup, unresolvedFacts, []);
  uncorroboratedGroup.hidden = true; uncorroboratedFacts.replaceChildren();
  reason.textContent = 'The agent is deciding what evidence it needs.'; grade.textContent = '';
  activeRunId = newRunId(); setStatus('Starting a deterministic, simulated checkout fixture…');
  // Captured, not read back from `activeRunId` later: by the time the POST
  // returns the reader may have started another case.
  const runId = activeRunId;
  try{
    const data = await apiJson(copy.path, {method:'POST', headers:{'X-Console-Run-Id':runId}});
    // The HTTP response returns only after the server has persisted the chain,
    // so this call, not the earlier SSE 'verdict' event, is what confirms a
    // receipt actually exists. SSE normally draws the outcome first for
    // responsiveness; merging its fields here just fills in anything the
    // slightly-earlier stream event carried that this response also confirms.
    if (activeRunId !== runId) return;
    renderVerdict({...data, ...(streamedVerdict && streamedVerdict.run_id === runId ? streamedVerdict : {})}, {persisted:true});
    // The decision is on screen and saved. Now, and only now, catch the trace
    // up with the journal: anything the stream dropped is still recoverable,
    // and this is the point where the journal is finished being written.
    //
    // Deliberately not awaited. The decision is already complete; holding the
    // checkout buttons hostage to a journal read would make the reader wait for
    // a record they can already see the outcome of. It also means a slow reply
    // can still be in flight when the next case starts, which is exactly why
    // `reconcileTrace` binds itself to `runId` and drops a response that
    // arrives for a run the reader has left.
    reconcileTrace(runId, {final:true}).catch(() => {});
  }catch(err){
    fallback.textContent = 'Checkout fixture could not run: ' + safeError(err) + '. Reload for a fresh demo session, then try again.';
    fallback.classList.add('visible'); setStatus('Checkout did not complete.');
  }finally{ checkout.disabled = !demoMode; cleanCheckout.disabled = !demoMode; gapCheckout.disabled = !demoMode; }
}
async function checkSignature(){
  if (!latestChainId) return;
  vault.textContent = 'Checking signed evidence…';
  try{
    const data = await apiJson('/v1/chains/' + encodeURIComponent(latestChainId) + '/verification');
    // Dictionary-covered, and never colour alone: the glyph and the sentence
    // both carry the answer.
    lastSignatureOk = Boolean(data.valid && data.key_trusted);
    renderSignatureResult();
  }catch(err){ vault.textContent = 'Signature check unavailable: ' + safeError(err); }
}
let lastSignatureOk = null;
function renderSignatureResult(){
  if (lastSignatureOk === null) return;
  if (typeof Locale.applyText === 'function'){
    Locale.applyText(vault,
      lastSignatureOk ? 'ui.signature_valid' : 'ui.signature_invalid',
      lastSignatureOk ? 'Ed25519 signature valid; signing key trusted' : 'Signature check did not pass',
      lastSignatureOk ? '✓ ' : '✗ ');
  } else {
    vault.textContent = lastSignatureOk
      ? '✓ Ed25519 signature valid; signing key trusted'
      : '✗ Signature check did not pass';
  }
}
function setSessionState(text, kind = ''){ sessionState.textContent = text; sessionState.className = 'session-state ' + kind; }
function handleSessionEvent(event){
  if (!sessionId || event.session_id !== sessionId) return;
  if (event.event === 'started'){
    setSessionState('ACTIVE · monitoring the trusted interaction for SIM/device changes.', 'ok');
    startTrust.disabled = true; simulateSwap.disabled = false;
  } else if (event.event === 'revoked'){
    setSessionState('REVOKED · ' + (event.reason || 'network evidence changed'), 'flag');
    simulateSwap.disabled = true; startTrust.disabled = false; sessionId = null;
  } else if (event.event === 'expired' || event.event === 'ended'){
    setSessionState((event.status || 'ENDED') + ' · ' + (event.reason || 'session complete'));
    simulateSwap.disabled = true; startTrust.disabled = false; sessionId = null;
  }
}
async function startTrustSession(){
  if (!demoMode || configuredProvider !== 'mock' || sessionId) return;
  startTrust.disabled = true; setSessionState('Starting a demo-only trust session…');
  try{
    // The number is the fixed Act III checkout subject.  There is no form field
    // or caller-selected target: this UI cannot create sessions for someone else.
    const data = await apiJson('/v1/sessions', {method:'POST', body:JSON.stringify({phone_number:'+99999991002'})});
    sessionId = data.session_id;
    handleSessionEvent({event:'started', session_id:data.session_id, status:data.status, reason:data.reason});
  }catch(err){ setSessionState('Could not start the continuity check: ' + safeError(err), 'flag'); startTrust.disabled = false; }
}
async function simulateTrustSwap(){
  if (!sessionId || !demoMode || configuredProvider !== 'mock') return;
  const id = sessionId; simulateSwap.disabled = true;
  setSessionState('SIM swap injected into the simulator; waiting for the monitor…');
  try{
    await apiJson('/v1/sessions/' + encodeURIComponent(id) + '/simulate-swap', {method:'POST'});
    // The SSE stream normally delivers revocation first. Polling the existing
    // session read route is a resilient fallback if a venue proxy reconnects it.
    for (let attempt = 0; attempt < 10 && sessionId === id; attempt++){
      await new Promise(resolve => setTimeout(resolve, 400));
      const data = await apiJson('/v1/sessions/' + encodeURIComponent(id));
      if (data.status !== 'ACTIVE'){
        handleSessionEvent({event:data.status === 'REVOKED' ? 'revoked' : 'ended', session_id:id, ...data});
        return;
      }
    }
    setSessionState('SIM change injected; monitor is still checking.', 'flag');
  }catch(err){ setSessionState('Could not simulate the change: ' + safeError(err), 'flag'); simulateSwap.disabled = false; }
}
checkout.addEventListener('click', () => runCheckout('replacement'));
cleanCheckout.addEventListener('click', () => runCheckout('clean'));
gapCheckout.addEventListener('click', () => runCheckout('gap'));
verifySignature.addEventListener('click', checkSignature);
startTrust.addEventListener('click', startTrustSession);
simulateSwap.addEventListener('click', simulateTrustSwap);

// --- I6: language ------------------------------------------------------------
//
// The module is loaded from this origin. If it does not arrive, the page keeps
// working in English: a checkout demonstration must not be lost because a
// presentation concern failed to load.
const Locale = (typeof Isnad !== 'undefined') ? Isnad : {
  applyDictionary: () => {}, onChange: () => {}, setLocale: async () => 'en',
  preferred: () => 'en', reviewStatus: () => null, locale: () => 'en'
};

Locale.onChange((active) => {
  localeSelect.value = active;
  const parts = [];
  const review = Locale.reviewStatus();
  if (review) parts.push(review);
  localeNote.textContent = parts.join(' ');
  localeNote.hidden = parts.length === 0;
  renderSignatureResult();
  // The scenario option text and every sentence this controller writes are
  // built in JavaScript, so the shared dictionary pass does not reach them.
  // Without this, switching to Arabic left the scenario names in English.
  if (capabilities) renderCapabilities();
});

localeSelect.addEventListener('change', (event) => { Locale.setLocale(event.target.value); });
Locale.setLocale(Locale.preferred());

(async function configure(){
  // Two independent failures, and they used to share one catch — so a stream
  // that would not open disabled all three checkout buttons and told the
  // reader "Could not read the secure demo mode", which was not what had
  // happened. The checkout does not need the stream: the investigation POST
  // returns the verdict, the chain and the presentation on its own, and the
  // trace is reconciled from the durable journal afterwards. Losing the live
  // stream costs liveness, never the decision.
  //
  // It is reachable without any server fault: stream credentials are capped
  // per owner, so a long session, several tabs, or a browser matrix runs the
  // pool down and the exchange starts refusing.
  // The judge session comes first: it is this tab's own tenant, and the stream,
  // the journal and every chain read below are scoped by it. Its failure does
  // not disable the page — it disables the paired sources and says so.
  try {
    await startJudgeSession();
  } catch (err) {
    esStatus.removeAttribute('data-i18n');
    esStatus.textContent = say('es_sources_unavailable', 'Evidence sources unavailable:') + ' ' + safeError(err);
    runPaired.disabled = true; esMock.disabled = true; esReal.disabled = true;
  }
  try {
    setMode(await apiJson('/v1/console/mode'));
  } catch (err) {
    mode.textContent = 'SERVER MODE UNKNOWN';
    mode.className = 'mode sim';
    checkout.disabled = true; cleanCheckout.disabled = true; gapCheckout.disabled = true;
    fallback.textContent = 'Could not read the secure demo mode: ' + safeError(err);
    fallback.classList.add('visible');
    return;
  }
  try {
    await connectStream();
  } catch (err) {
    // Said in the status line, not in the error banner: nothing the reader
    // wanted to do has been taken away from them. A refused credential has
    // already said something more specific — do not overwrite it.
    if (streamHalted) return;
    setStatus('Live evidence stream unavailable (' + safeError(err)
      + '). The checkout still runs; its trace is read back from the journal afterwards.');
  }
}());
