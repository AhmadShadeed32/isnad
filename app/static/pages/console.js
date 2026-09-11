const log = document.getElementById('log');
const dot = document.getElementById('dot');
const statusText = document.getElementById('statusText');
const sessionLabel = document.getElementById('sessionLabel');
const verdictEl = document.getElementById('verdict');
const gradeEl = document.getElementById('grade');
const reasonEl = document.getElementById('reason');
const fill = document.getElementById('fill');
const pval = document.getElementById('pval');
const buttons = [...document.querySelectorAll('.btn[data-act]')];
const demoNotice = document.getElementById('demoNotice');
const liveConsentCard = document.getElementById('liveConsentCard');
const consentPhone = document.getElementById('consentPhone');
const startConsentBtn = document.getElementById('startConsent');
const consentLink = document.getElementById('consentLink');
const resumeConsentBtn = document.getElementById('resumeConsent');
const consentState = document.getElementById('consentState');
const modePill = document.getElementById('modePill');
const askInput = document.getElementById('askInput');
const askBtn = document.getElementById('askBtn');
const askAnswer = document.getElementById('askAnswer');
const cfEl = document.getElementById('counterfactual');
const qrBox = document.getElementById('qrBox');
const qrCode = document.getElementById('qrCode');
const qrLink = document.getElementById('qrLink');
const plannerPill = document.getElementById('plannerPill');
const runbookStatus = document.getElementById('runbookStatus');
const runbookButtons = [...document.querySelectorAll('.scenario')];
const runStageSuiteBtn = document.getElementById('runStageSuite');
const runLiveSuiteBtn = document.getElementById('runLiveSuite');
const runAct7Btn = document.getElementById('runAct7');
const resetStageBtn = document.getElementById('resetStage');
const runVelocityDemoBtn = document.getElementById('runVelocityDemo');
const runLiveConsentBtn = document.getElementById('runLiveConsent');
const runReverseCheckBtn = document.getElementById('runReverseCheck');
const runSessionDemoBtn = document.getElementById('runSessionDemo');
const runIdempotencyBtn = document.getElementById('runIdempotency');
const verifyChainRunBtn = document.getElementById('verifyChainRun');
const runForwardCheckBtn = document.getElementById('runForwardCheck');
const clearBtn = document.getElementById('clearBtn');

let t0 = 0;
let latestChainId = null;
let providerMode = 'mock';
let suiteRunning = false;
let activeRunId = null;
const recoverBtn = document.getElementById('recoverBtn');
const recoverNote = document.getElementById('recoverNote');
// Separate from recoverNote on purpose: that note is about the journal and is
// wiped by resetRecovery() the moment the presenter starts another run, which
// is exactly what they do while wondering why nothing is happening.
const streamNotice = document.getElementById('streamNotice');
// Elapsed time since this run started — except for a recovered row, which did
// not happen now and has a real recorded time of its own, and except before a
// run has started at all, where an elapsed figure would be measured from the
// epoch. Neither case gets a made-up number.
let replayTime = null;
const clock = () => {
  if (replayTime) return replayTime;
  if (!t0) return '--.--';
  return ((Date.now() - t0) / 1000).toFixed(2).padStart(5, '0');
};
function journalTime(iso){
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? '--.--' : at.toISOString().slice(11, 19);
}
const cursor = () => '<span class="cursor">▌</span>';
function newRunId(){
  // A new run starts a new journal, so nothing seen for the previous one may
  // suppress or be attributed to this one.
  const id = `run-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  resetRecovery();
  // The handler still refuses to act without an active run, so enabling here
  // — a tick before the caller assigns it — costs nothing.
  recoverBtn.disabled = false;
  return id;
}

function setRunbookStatus(text, tone){
  runbookStatus.textContent = text;
  runbookStatus.className = 'runbook-status' + (tone ? ' ' + tone : '');
}
function setLatestChain(chainId){
  if (!chainId) return;
  latestChainId = chainId;
  verifyChainRunBtn.disabled = false;
  askInput.disabled = false;
  askBtn.disabled = false;
  askAnswer.textContent = '';
  showReceiptQr(chainId);
}

// T4 — ask the agent. textContent throughout: the answer is model output and the
// question is whatever a judge typed (S10).
async function askTheAgent(){
  const question = (askInput.value || '').trim();
  if (!question || !latestChainId) return;
  askBtn.disabled = true;
  askAnswer.textContent = 'thinking…';
  try{
    const data = await apiJson(`/v1/chains/${latestChainId}/explain`, {
      method: 'POST',
      body: JSON.stringify({question})
    });
    askAnswer.textContent = data.answer;
    addRow(clock(), 'ask', question, 'pfrag');
    addRow(clock(), 'agent', data.answer, 'info');
  }catch(err){
    askAnswer.textContent = err.message;
  }finally{
    askBtn.disabled = false;
  }
}
function wait(ms){ return new Promise(resolve => setTimeout(resolve, ms)); }
// Substituted server-side at render time. Empty when demo mode is off, in
// which case the presenter supplies a real merchant key at run time. No
// credential is ever hardcoded here — view-source used to hand out a working
// merchant key (S1).
const CONSOLE_TOKEN = document.querySelector('meta[name="isnad-demo-token"]')?.content || '';
const TOKEN_KEY = 'isnad.apiKey';
function apiKey(){
  if (CONSOLE_TOKEN) return CONSOLE_TOKEN;
  try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch (err) { return ''; }
}
function setApiKey(value){
  // sessionStorage, not localStorage: the key dies with the tab rather than
  // outliving the demo on a shared machine.
  try { sessionStorage.setItem(TOKEN_KEY, value); } catch (err) { /* private mode */ }
  // A freshly supplied key is the one way out of a halted stream that is not a
  // reload. In demo mode nothing calls this, so the halt correctly sticks.
  resumeStream();
}
// Never defined here, but called on the journal-read failure path since I14
// (line ~560) — so the one branch that exists to explain a failed recovery
// threw a ReferenceError of its own instead of showing the message. Defined
// once, with the same wording judge.js uses.
function safeError(err){
  return err && err.message ? err.message : 'The request did not complete.';
}
function requireApiKey(){
  const key = apiKey();
  if (key) return key;
  const entered = (window.prompt('Merchant API key') || '').trim();
  if (entered){
    setApiKey(entered);
    // The stream could not be opened before a key existed; open it now.
    connectStream().catch(() => {});
  }
  return entered;
}
async function apiJson(path, options = {}){
  const headers = {
    ...window.IsnadKey.headers(path),
    ...(options.auth === false ? {} : {'Authorization':'Bearer ' + requireApiKey()}),
    ...(options.body ? {'Content-Type':'application/json'} : {}),
    ...(options.headers || {})
  };
  const request = {...options, headers};
  delete request.auth;
  const response = await fetch(path, request);
  const data = await response.json().catch(() => ({}));
  if (!response.ok){
    // The status rides along on the error: to a caller, a rejected credential
    // and a transient failure are the same rejected promise otherwise, and the
    // stream has to tell them apart to know whether retrying is worth anything.
    const failure = response.status === 401 || response.status === 403
      ? new Error(authFailureMessage(response.status))
      : new Error(data.detail?.message || data.detail?.code || `request failed (${response.status})`);
    failure.status = response.status;
    throw failure;
  }
  return data;
}
// A 401 here is almost never "you forgot to supply a key" — the page was
// rendered with a working one. Demo tokens are held in memory server-side with
// a 900s TTL, so a restart or a console left open past the TTL invalidates the
// token baked into this HTML. The server's honest generic message ("Bearer API
// key required") is then actively misleading on stage: the fix is to reload,
// not to hunt for a key.
function authFailureMessage(status){
  if (CONSOLE_TOKEN){
    return status === 401
      ? 'demo session expired — reload the page for a fresh token'
      : 'demo token was rejected — reload the page';
  }
  // An operator-typed merchant key is wrong or revoked. Drop it, or apiKey()
  // keeps returning the same bad value and requireApiKey() never prompts again,
  // which wedges the tab until it is closed.
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (err) { /* private mode */ }
  return status === 401
    ? 'API key rejected — cleared it, the next action will ask again'
    : 'that API key is not permitted to do this';
}
function setRunbookBusy(busy){
  suiteRunning = busy;
  buttons.forEach(button => { button.disabled = busy || !demoMode; });
  runbookButtons.forEach(button => {
    if (button.id === 'verifyChainRun') button.disabled = busy || !latestChainId;
    else button.disabled = busy;
  });
  if (!busy) configureMode();
}

function stripCursor(){ const c = log.querySelector('.cursor'); if(c) c.remove(); }
function cursorNode(){
  const el = document.createElement('span');
  el.className = 'cursor';
  return el;
}
// Every field this renders — ev.detail, ev.reason, ev.rationale, ev.api,
// ev.source, err.message — reaches it from the network or from a server error
// string, and it used to be interpolated into innerHTML unescaped (S10). Built
// from nodes now: nothing here can parse a string as markup. `meta` is a
// separate argument because two callers used to append their own <span>.
function addRow(ts, api, msg, cls, meta){
  stripCursor();
  const row = document.createElement('div');
  row.className = 'row';
  row.appendChild(span('ts', ts));
  row.appendChild(span('api', api));
  const message = span('msg' + (cls ? ' ' + cls : ''), msg);
  if (meta) message.appendChild(span('meta', meta));
  row.appendChild(message);
  log.appendChild(row);
  log.appendChild(cursorNode());
  log.scrollTop = log.scrollHeight;
}
function span(className, text){
  const el = document.createElement('span');
  el.className = className;
  el.textContent = text == null ? '' : String(text);
  return el;
}
function setMeter(p){
  const pct = Math.max(4, Math.min(100, p * 100));
  fill.style.width = pct + '%';
  fill.style.background = p >= 0.80 ? 'var(--red)' : p <= 0.15 ? 'var(--green)' : 'var(--amber)';
  pval.textContent = 'risk score = ' + p.toFixed(3);
}
const GRADE_NOTE = {
  ATTESTED_FULL:    'every link resolved and corroborating',
  ATTESTED_PARTIAL: 'resolved, corroboration below the full bar',
  UNRESOLVED:       'a required link could not be obtained, or none was gathered at all — not a failed check',
  DEGRADED:         'all links resolved, one or more adverse',
  REFUTED:          'a link directly contradicts the claim'
};
// T5 — render the counterfactual. Built from nodes and textContent (S10), and
// every value carries its basis so an estimate is never shown as a measurement.
function fmt(fig, suffix){
  if (!fig || fig.value === null || fig.value === undefined) return '—';
  const n = fig.value;
  const shown = Number.isInteger(n) ? String(n) : n.toFixed(n < 1 ? 4 : 2);
  return shown + (suffix || '');
}
function unpriced(fig, label){
  return fig && fig.value === null && fig.basis === 'unpriced' ? label : fmt(fig);
}
function countryLabel(country){
  return {
    JO:'Jordan', AE:'United Arab Emirates', SA:'Saudi Arabia',
    DEFAULT:'regional default list price'
  }[country] || country;
}
function cfRow(label, isnad, otp){
  const tr = document.createElement('tr');
  [label, isnad, otp].forEach((text, i) => {
    const td = document.createElement(i === 0 ? 'th' : 'td');
    td.textContent = text;
    tr.appendChild(td);
  });
  return tr;
}
function renderCounterfactual(alt){
  cfEl.replaceChildren();
  if (!alt){ cfEl.hidden = true; return; }
  cfEl.hidden = false;

  const table = document.createElement('table');
  const head = document.createElement('tr');
  ['', 'Isnad', 'one SMS OTP'].forEach(t => {
    const th = document.createElement('th');
    th.textContent = t;
    head.appendChild(th);
  });
  table.appendChild(head);
  table.appendChild(cfRow('network calls', fmt(alt.isnad_calls), fmt(alt.otp_messages) + ' SMS'));
  table.appendChild(cfRow('time', fmt(alt.isnad_latency_ms, ' ms'), fmt(alt.otp_seconds, ' s')));
  table.appendChild(cfRow('cost (' + alt.currency + ')',
    unpriced(alt.isnad_cost_usd, 'not priced — operator contract'),
    unpriced(alt.otp_cost_usd, 'not priced — merchant-specific')));
  table.appendChild(cfRow('expected drop-off', 'not measured',
    alt.otp_dropoff_rate.value === null ? '—'
      : Math.round(alt.otp_dropoff_rate.value * 100) + '%'));
  // The price of getting it wrong. Both are null unless the merchant has
  // priced them, and an em dash is the honest rendering of "we do not know".
  table.appendChild(cfRow('cost of abandonment', '—',
    unpriced(alt.otp_dropoff_cost_usd, 'not priced — merchant-specific')));
  table.appendChild(cfRow('cost of one false decline',
    unpriced(alt.false_decline_cost_usd, 'not priced — merchant-specific'),
    unpriced(alt.false_decline_cost_usd, 'not priced — merchant-specific')));
  cfEl.appendChild(table);

  const foot = document.createElement('div');
  foot.className = 'foot';
  // Say what each number is. An estimate presented as a measurement is the
  // failure mode this whole block exists to avoid.
  foot.textContent =
    `${countryLabel(alt.country)} · OTP price: ${alt.otp_cost_usd.basis.replace('_', ' ')} · ` +
    `OTP time and drop-off: estimates · ${alt.note}`;
  cfEl.appendChild(foot);
}

const SVG_NS = 'http://www.w3.org/2000/svg';

// T6 — render the receipt QR. The SVG is generated server-side and embedded
// here, because console.html must keep zero external origins: no CDN QR library,
// no image host. It is the only place this page assigns markup, and the source
// is our own /v1/receipts/{id}/qr, not anything a caller controls.
async function showReceiptQr(chainId){
  if (!chainId){ qrBox.hidden = true; return; }
  try{
    const data = await apiJson(`/v1/receipts/${chainId}/qr`, {auth:false});
    qrCode.replaceChildren();
    // segno's svg_inline() omits xmlns on purpose — it is meant to be dropped
    // into HTML, where the parser infers the namespace. Parsed as XML instead,
    // an undeclared root lands in the *null* namespace: nodeName is still 'svg',
    // so this passed its own check and got appended, but the browser laid it out
    // as an unknown inline element and drew nothing. The QR never rendered.
    // Declaring the namespace keeps the strict XML parse (and keeps the server's
    // markup free of any 'http://', which a test asserts on).
    const markup = data.svg.replace('<svg ', '<svg xmlns="' + SVG_NS + '" ');
    const parsed = new DOMParser().parseFromString(markup, 'image/svg+xml');
    const svg = parsed.documentElement;
    if (svg && svg.namespaceURI === SVG_NS && svg.localName === 'svg'){
      qrCode.appendChild(document.importNode(svg, true));
      qrLink.textContent = data.url;
      qrLink.href = data.url;
      qrBox.hidden = false;
    }
  }catch(err){
    qrBox.hidden = true;
  }
}

// planner: llm | greedy | llm+greedy. Framed as reliability engineering the
// fallback is a strength; hidden, it looks like a bluff — so it is always shown.
function setPlannerBadge(planner){
  if (!planner) return;
  plannerPill.textContent = 'planner: ' + planner;
  plannerPill.className = 'mode-pill ' + (planner === 'llm' ? 'live' : 'sim');
}
function setVerdict(d, reason, grade){
  verdictEl.textContent = d;
  verdictEl.className = 'verdict ' + d;
  reasonEl.textContent = reason || '';
  if (grade){
    gradeEl.className = 'grade ' + grade;
    // Nodes, not innerHTML: `grade` arrives on the SSE stream (S10).
    gradeEl.textContent = 'chain_grade ';
    const strong = document.createElement('b');
    strong.textContent = grade;
    gradeEl.appendChild(strong);
    const note = GRADE_NOTE[grade];
    if (note){
      const span = document.createElement('span');
      span.className = 'note';
      span.textContent = note;   // still a node, never innerHTML (S10)
      gradeEl.appendChild(span);
    }
  } else {
    gradeEl.className = 'grade';
    gradeEl.textContent = '';
  }
}

// ---- live stream ----
// EventSource cannot set an Authorization header. It therefore receives a
// short-lived, stream-only credential minted through the normal header-authenticated
// endpoint below — never the merchant key itself. The stream is still isolated
// per owner (S2), but proxy and browser request logs cannot replay it as API auth.
let es = null;
let esKey = null;
let streamCredential = null;
let streamCredentialKey = null;
let streamCredentialExpiresAt = 0;
let streamConnectPromise = null;
let streamReconnectTimer = null;

// A rejected credential is terminal for this tab: the token was minted by a
// process that is gone, and no number of retries brings that process back.
// Retrying regardless is what turned a restarted server into a console that
// looked dead on stage while it quietly logged a 403 every five seconds.
let streamHalted = false;
let streamRetryAttempt = 0;

function invalidateStreamCredential(){
  streamCredential = null;
  streamCredentialKey = null;
  streamCredentialExpiresAt = 0;
}
// Backed off, because the failures worth retrying are the ones that clear on
// their own — a 5xx, a lost connection, a server still coming up. A flat five
// seconds did not make those recover any sooner; it only made the hopeless
// case louder.
function scheduleStreamReconnect(){
  if (streamHalted || streamReconnectTimer) return;
  const delay = Math.min(5000 * 2 ** streamRetryAttempt, 60000);
  streamRetryAttempt += 1;
  streamReconnectTimer = setTimeout(() => {
    streamReconnectTimer = null;
    connectStream().catch(() => {});
  }, delay);
}
// Stop, and say why. A stream that has given up must not keep reading
// "reconnecting…" — that is the state the presenter trusts to mean "wait".
function haltStream(message){
  streamHalted = true;
  if (streamReconnectTimer){ clearTimeout(streamReconnectTimer); streamReconnectTimer = null; }
  if (es){ es.close(); es = null; esKey = null; }
  invalidateStreamCredential();
  dot.classList.remove('live');
  dot.classList.add('attention');
  statusText.textContent = 'stream stopped';
  streamNotice.textContent = message;
}
function resumeStream(){
  if (!streamHalted) return;
  streamHalted = false;
  streamRetryAttempt = 0;
  dot.classList.remove('attention');
  streamNotice.textContent = '';
}
async function getStreamCredential(key){
  if (streamCredential && streamCredentialKey === key && Date.now() < streamCredentialExpiresAt){
    return streamCredential;
  }
  const data = await apiJson('/v1/console/stream-token', {method:'POST'});
  if (!data.stream_token) throw new Error('Could not start the evidence stream');
  streamCredential = data.stream_token;
  streamCredentialKey = key;
  streamCredentialExpiresAt = Date.now() + Math.max(1, Number(data.expires_in_seconds) || 0) * 1000;
  return streamCredential;
}
async function connectStream(){
  const key = apiKey();
  if (streamHalted || !key || key === esKey) return;
  if (streamConnectPromise) return streamConnectPromise;
  streamConnectPromise = (async () => {
    try{
      const credential = await getStreamCredential(key);
      // The operator may have supplied another key while the exchange was in
      // flight; do not attach that key's stream to this tab.
      if (apiKey() !== key) return;
      if (es) es.close();
      esKey = key;
      es = new EventSource('/v1/console/stream?stream_token=' + encodeURIComponent(credential));
      es.onopen = () => { streamRetryAttempt = 0; dot.classList.add('live'); statusText.textContent = 'live'; };
      es.onerror = () => {
        dot.classList.remove('live'); statusText.textContent = 'reconnecting…';
        // The moment the stream drops is the moment recovery has a job. The
        // console does not do it automatically: re-reading the journal is the
        // operator's call, and a silent backfill would hide that the live
        // stream broke at all.
        if (activeRunId){
          recoverNote.className = 'recover-note gap';
          recoverNote.textContent = 'The evidence stream dropped. Anything that happened while it was down is in the journal — use "Recover missed events" to read it back. No check is bought again.';
        }
        if (es) es.close();
        es = null; esKey = null;
        // The EventSource error itself says nothing about why it fired, so the
        // credential is dropped and the retry re-earns it. That retry is where
        // the two cases separate: the exchange is a plain fetch, and a 401/403
        // from it halts the stream rather than starting this over.
        invalidateStreamCredential();
        scheduleStreamReconnect();
      };
      es.onmessage = onStreamMessage;
    }catch(err){
      // The credential exchange is a plain fetch, so unlike the EventSource
      // error that may have sent us here, its rejection is legible: a 401/403
      // is the server saying this token will never be honoured again. Strict
      // equality on purpose — a fetch against a server that has not finished
      // restarting rejects with a TypeError carrying no status at all, and that
      // one has to keep retrying.
      if (err.status === 401 || err.status === 403){
        haltStream(err.message);
        throw err;
      }
      dot.classList.remove('live'); statusText.textContent = 'stream unavailable';
      scheduleStreamReconnect();
      throw err;
    }finally{
      streamConnectPromise = null;
    }
  })();
  return streamConnectPromise;
}
function onStreamMessage(e){
  const ev = JSON.parse(e.data);
  if (activeRunId && ev.type !== 'session' && ev.run_id !== activeRunId) return;
  // I14 delivers at least once: the same event legitimately arrives twice —
  // once live, once replayed after a reconnect — and the journal sequence is
  // the key the two deliveries share. An event with no sequence never reached
  // the journal, so it is live-only and cannot be deduplicated or recovered.
  if (typeof ev.sequence === 'number'){
    if (seenSequences.has(ev.sequence)) return;
    seenSequences.add(ev.sequence);
    if (ev.sequence > highestSequence) highestSequence = ev.sequence;
  }
  renderStreamEvent(ev);
}

// ---- I14: recovery after a disconnect ----
//
// Nothing here re-runs an investigation or buys a check again: it reads the
// journal the server wrote before each event was ever sent live. Recovery
// resumes the *record* of a run, never the run — an interrupted investigation
// stays interrupted, and that is reported separately from a completed one.
let seenSequences = new Set();
let highestSequence = 0;

function resetRecovery(){
  seenSequences = new Set();
  highestSequence = 0;
  recoverBtn.disabled = true;
  recoverNote.textContent = '';
  recoverNote.className = 'recover-note';
}

async function recoverMissedEvents(){
  if (!activeRunId){ return; }
  recoverBtn.disabled = true;
  recoverNote.className = 'recover-note';
  recoverNote.textContent = 'reading the journal…';
  try{
    const data = await apiJson('/v1/console/runs/' + encodeURIComponent(activeRunId)
      + '/events?after=' + encodeURIComponent(highestSequence));
    let recovered = 0;
    for (const row of data.events || []){
      if (seenSequences.has(row.sequence)) continue;   // in order, and only once
      seenSequences.add(row.sequence);
      if (row.sequence > highestSequence) highestSequence = row.sequence;
      // Stamped with the server time the journal recorded, not with now.
      replayTime = journalTime(row.server_time);
      try{
        renderStreamEvent({...row.body, type: row.event_type, sequence: row.sequence, replayed: true});
      }finally{
        replayTime = null;
      }
      recovered++;
    }
    if (data.gap){
      // An explicit gap signal, not a silent smooth continuation: the events
      // before this point are past their retention window or were never
      // stored, and this console will not invent them.
      recoverNote.className = 'recover-note gap';
      recoverNote.textContent = recovered
        ? `Recovered ${recovered} event(s), but earlier ones are missing from the journal — retention or a failed write. The trace above is incomplete and nothing here reconstructs the absent events.`
        : 'Earlier events are missing from the journal — retention or a failed write. The trace above is incomplete and nothing here reconstructs the absent events.';
    } else {
      recoverNote.textContent = recovered
        ? `Recovered ${recovered} event(s) from the journal. No provider call was made.`
        : 'Nothing missing: the journal holds no events this console has not already shown.';
    }
  }catch(err){
    recoverNote.className = 'recover-note gap';
    recoverNote.textContent = 'Could not read the journal: ' + safeError(err);
  }finally{
    recoverBtn.disabled = !activeRunId;
  }
}

/* A recovered event carries only what the journal allowlist stores. Printing
   "undefined" for the rest would be a bug; filling them in would be worse. */
function val(v, absent){
  return (v === undefined || v === null) ? (absent || '(not journalled)') : v;
}

function renderStreamEvent(ev){
  if (ev.type === 'start'){
    t0 = Date.now();
    sessionLabel.textContent = `isnad-agent · hypothesis: ${ev.hypothesis}`;
    addRow(clock(), 'hypothesis', `${ev.hypothesis} — prior risk score=${ev.prior_p_fraud}`, 'pfrag');
    setMeter(ev.prior_p_fraud);
  } else if (ev.type === 'evidence'){
    const cls = ev.result === 'PASS' ? 'pass' : ev.result === 'FLAG' ? 'flag' : 'info';
    const mark = ev.result === 'PASS' ? '✓' : ev.result === 'FLAG' ? '✗' : '·';
    // `asked over` is the window the question covered, not the age of the
    // event — CAMARA returns a boolean with no timestamp.
    const asked = typeof ev.max_age_hours === 'number' ? ` · asked over last ${ev.max_age_hours}h` : '';
    // A replayed event carries no `detail`: the journal's allowlist excludes
    // provider prose on purpose, so the normalized signal stands in rather
    // than a sentence invented at replay time.
    // A recovered row has no `detail`: the journal's allowlist excludes
    // provider prose on purpose, so the normalized signal stands in rather
    // than a sentence invented at replay time.
    const said = ev.detail || ev.signal || '(not journalled)';
    addRow(clock(), ev.api, `[${mark}] ${said}  `, cls,
      `→ risk score=${ev.p_fraud} · ${ev.source||'provider'}${asked}${ev.replayed ? ' · recovered' : ''}`);
    setMeter(ev.p_fraud);
  } else if (ev.type === 'decision'){
    // The rationale is whoever decided's own sentence, rendered verbatim as
    // text (S10 rebuilt addRow so it cannot be markup). The planner tag makes a
    // greedy fallback visible rather than letting it read as model reasoning.
    const who = ev.planner ? `[${ev.planner}] ` : '';
    if (ev.action === 'stop'){
      addRow(clock(), 'agent', `${who}stop → ${ev.rationale}`, 'pfrag');
    } else {
      addRow(clock(), 'agent', `${who}select → ${ev.api} · ${ev.rationale} · cost=${ev.cost}`, 'pfrag');
    }
    // Only the investigation phase reflects the planner. The step-up and the
    // corroboration checks are policy choreography carrying planner:'policy',
    // and badging those made the pill read "planner: policy" mid-run.
    if (ev.phase === 'investigation') setPlannerBadge(ev.planner);
  } else if (ev.type === 'enrichment'){
    // A separate priced operator call, on its own row so the cost story stays
    // readable: the boolean and the date were two calls, not one.
    const t = (key, fallback) => (window.Isnad ? window.Isnad.t('ui.' + key, fallback) : fallback);
    const said = ev.availability === 'available'
      ? `${t('swap_date_available','latest change')} ${ev.provider_time}`
      : t('swap_date_' + ev.availability, ev.reason || ev.availability);
    const flags = [];
    if (ev.disagrees_with_window === true) flags.push('disagrees-with-window');
    if (ev.monitored_period_days === null || ev.monitored_period_days === undefined){
      flags.push('horizon-unknown');
    } else { flags.push(`horizon=${ev.monitored_period_days}d`); }
    addRow(clock(), ev.operation || 'retrieve-date', `[date] ${said}`, 'info',
      `· ${flags.join(' · ')} · cost=${ev.cost}`);
  } else if (ev.type === 'announce'){
    // The calling number is deliberately absent from a recovered row: it is a
    // subscriber number and the journal does not keep one.
    addRow(clock(), 'Verified Caller',
      `pre-announce → ${val(ev.institution)}` + (ev.calling_participant ? ` from ${ev.calling_participant}` : ''),
      'pass', `· ${val(ev.announcement_id)} · valid ${val(ev.ttl_seconds, '—')}s${ev.replayed ? ' · recovered' : ''}`);
  } else if (ev.type === 'screen'){
    // Tier 1 is local-only, so the microsecond figure is the point: this ran
    // before the phone would have finished its first ring.
    const cls = ev.label === 'VERIFIED_INSTITUTION' ? 'pass'
              : ev.label === 'SUSPECTED_SPOOF' ? 'flag' : 'info';
    addRow(clock(), 'Tier 1 screen', `${val(ev.label)} — ${val(ev.reason)}`, cls,
      `· ${val(ev.basis)} · ${val(ev.elapsed_us, '—')}µs${ev.replayed ? ' · recovered' : ''}`);
    setVerdict(val(ev.label), val(ev.reason));
  } else if (ev.type === 'velocity'){
    const cls = ev.label === 'SUSPECTED_SPOOF' ? 'flag' : 'info';
    addRow(clock(), 'caller velocity',
      `${val(ev.label)} — ${val(ev.reason)}`, cls,
      `· ${val(ev.calls, '—')} distinct callees · threshold ${val(ev.threshold, '—')}${ev.replayed ? ' · recovered' : ''}`);
    setVerdict(val(ev.label), val(ev.reason));
  } else if (ev.type === 'verdict'){
    const cls = ev.decision === 'DECLINE' ? 'flag' : ev.decision === 'ALLOW' ? 'pass' : 'info';
    addRow(clock(), 'VERDICT', `${ev.decision} / ${ev.chain_grade || '—'} — ${val(ev.reason)} · ${val(ev.evidence_steps, '—')} checks · cost=${val(ev.evidence_cost, '—')}${ev.replayed ? ' · recovered' : ''}`, cls);
    setVerdict(ev.decision, val(ev.reason), ev.chain_grade);
    setPlannerBadge(ev.planner);
    setLatestChain(ev.chain_id);
    if (!suiteRunning) buttons.forEach(b => b.disabled = !demoMode);
  } else if (ev.type === 'session'){
    handleSession(ev);
  }
}

// ---- session (trust with a TTL) ----
const sessState = document.getElementById('sessState');
const startSessBtn = document.getElementById('startSess');
const swapSessBtn = document.getElementById('swapSess');
const endSessBtn = document.getElementById('endSess');
let sessionId = null;
let sessionStarting = false;
let demoMode = true;
let modeReady = false;
let consentId = null;
let consentPoll = null;

function setSess(text, color){ sessState.textContent = text; sessState.style.color = color; }
function canUseDemoSession(){ return modeReady && demoMode && providerMode === 'mock'; }
function syncSessionControls(){
  startSessBtn.disabled = sessionStarting || Boolean(sessionId) || !canUseDemoSession();
  swapSessBtn.disabled = !sessionId || !canUseDemoSession();
  endSessBtn.disabled = !sessionId;
}
function handleSession(ev){
  if (ev.session_id !== sessionId) return;
  if (ev.event === 'started'){
    setSess('session: ACTIVE — watching SIM', 'var(--green)');
    addRow(clock(), 'session', `ACTIVE · ${ev.phone_number} · monitoring SIM + device`, 'pass');
    syncSessionControls();
  } else if (ev.event === 'revoked'){
    setSess('session: REVOKED', 'var(--red)');
    addRow(clock(), 'session', `REVOKED — ${ev.reason}`, 'flag');
    sessionId = null;
    syncSessionControls();
  } else if (ev.event === 'expired' || ev.event === 'ended'){
    setSess('session: ' + ev.status, 'var(--mut)');
    addRow(clock(), 'session', ev.status.toLowerCase() + (ev.reason ? ' — ' + ev.reason : ''), 'info');
    sessionId = null;
    syncSessionControls();
  }
}
async function startSession(){
  if (sessionStarting || sessionId || !canUseDemoSession()){
    if (!canUseDemoSession()) setSess('session: demo-only continuity checks require the mock provider', 'var(--mut)');
    return;
  }
  sessionStarting = true;
  syncSessionControls();
  if (!t0) t0 = Date.now();
  setSess('session: starting…', 'var(--mut)');
  try{
    const data = await apiJson('/v1/sessions', {
      method:'POST', body: JSON.stringify({ phone_number: '+99999991001' })
    });
    sessionId = data.session_id;
    handleSession({
      event: 'started', session_id: sessionId, status: data.status,
      phone_number: data.phone_number, reason: data.reason
    });
    return data;
  }catch(err){
    setSess('session: error', 'var(--red)');
    addRow(clock(), 'session', err.message, 'flag');
    throw err;
  }
  finally{
    sessionStarting = false;
    syncSessionControls();
  }
}
startSessBtn.addEventListener('click', () => startSession().catch(() => {}));
async function waitForSessionTerminal(id, attempts = 10){
  for (let attempt = 0; attempt < attempts && sessionId === id; attempt++){
    await wait(400);
    const data = await apiJson(`/v1/sessions/${id}`);
    if (data.status !== 'ACTIVE'){
      handleSession({event:data.status === 'REVOKED' ? 'revoked' : 'ended', session_id:id, ...data});
      return data;
    }
  }
  // SSE may have updated the page while the polling wait was asleep. Read once
  // more so the caller receives the actual terminal status rather than treating
  // a successful stream update as an indeterminate session.
  if (sessionId !== id){
    try { return await apiJson(`/v1/sessions/${id}`); }
    catch(err){ return null; }
  }
  return null;
}
async function injectSwap(){
  if (!sessionId || !canUseDemoSession()) return null;
  const id = sessionId;
  swapSessBtn.disabled = true;
  addRow(clock(), 'attack', 'SIM swap injected — monitor will catch it…', 'flag');
  try{
    await apiJson(`/v1/sessions/${id}/simulate-swap`, {method:'POST'});
    // SSE is the fast path. Polling reconciles the manual control as well, so
    // a dropped stream cannot leave the page claiming this trust is still active.
    const terminal = await waitForSessionTerminal(id);
    if (!terminal && sessionId === id) setSess('session: SIM change injected; monitor is still checking.', 'var(--amber)');
    return terminal;
  }catch(err){
    addRow(clock(), 'session', err.message, 'info');
    syncSessionControls();
    throw err;
  }
}
swapSessBtn.addEventListener('click', () => injectSwap().catch(() => {}));
endSessBtn.addEventListener('click', async () => {
  if (!sessionId) return;
  endSessBtn.disabled = true;
  const id = sessionId;
  try{
    const data = await apiJson(`/v1/sessions/${id}`, {method:'DELETE'});
    handleSession({
    event:'ended', session_id:id, status:data.status,
    phone_number:data.phone_number, reason:data.reason
    });
  }catch(err){
    addRow(clock(), 'session', err.message, 'flag');
    endSessBtn.disabled = false;
  }
});

async function runSessionDemo(){
  if (!canUseDemoSession()) throw new Error('session simulation requires demo mode with the mock provider');
  setRunbookStatus('Starting trust session…');
  await startSession();
  const id = sessionId;
  await wait(250);
  const terminal = await injectSwap();
  if (terminal){
    setRunbookStatus(`Trust session finished: ${terminal.status} (${terminal.reason || 'no reason'})`, terminal.status === 'REVOKED' ? 'ok' : 'warn');
    return terminal;
  }
  setRunbookStatus('SIM swap was injected; session monitor is still checking.', 'warn');
  return {status:'ACTIVE'};
}

function setConsentState(text, color = 'var(--mut)'){
  consentState.textContent = 'consent: ' + text;
  consentState.style.color = color;
}
function stopConsentPolling(){
  if (consentPoll) clearInterval(consentPoll);
  consentPoll = null;
}
function resetConsentControls(){
  stopConsentPolling();
  consentId = null;
  startConsentBtn.disabled = false;
  resumeConsentBtn.disabled = true;
  consentLink.hidden = true;
  consentLink.removeAttribute('href');
}
async function pollConsent(){
  if (!consentId) return;
  let data;
  try{ data = await apiJson(`/v1/consents/${consentId}`); }
  catch(err){
    setConsentState('could not refresh — start a new consent request or reload', 'var(--red)');
    resetConsentControls();
    return;
  }
  setConsentState(data.status, data.status === 'AUTHORIZED' ? 'var(--green)' : 'var(--mut)');
  if (data.status === 'AUTHORIZED'){
    stopConsentPolling();
    resumeConsentBtn.disabled = false;
  } else if (['DENIED','FAILED','EXPIRED','COMPLETED'].includes(data.status)){
    resetConsentControls();
  }
}
startConsentBtn.addEventListener('click', async () => {
  stopConsentPolling();
  consentId = null;
  consentLink.hidden = true;
  startConsentBtn.disabled = true;
  setConsentState('starting…');
  activeRunId = newRunId();
  try{
    const data = await apiJson('/v1/consents/number-verification', {
      method:'POST',
      body:JSON.stringify({phone_number:consentPhone.value, context:{event:'signup',account_age_days:0}})
    });
    consentId = data.consent_id;
    consentLink.href = data.authorization_url;
    consentLink.hidden = false;
    resumeConsentBtn.disabled = true;
    setConsentState('PENDING — open the consent screen');
    window.open(data.authorization_url, '_blank', 'noopener');
    stopConsentPolling();
    consentPoll = setInterval(pollConsent, 1500);
  }catch(err){
    setConsentState(err.message, 'var(--red)');
    resetConsentControls();
  }
});
resumeConsentBtn.addEventListener('click', async () => {
  if (!consentId) return;
  resumeConsentBtn.disabled = true;
  setConsentState('verifying…');
  try{
    const data = await apiJson(`/v1/consents/${consentId}/verify`, {
      method:'POST', headers:{'X-Console-Run-Id':activeRunId || newRunId()}
    });
    setConsentState(`${data.decision} · chain ${data.chain_id}`, 'var(--green)');
    setVerdict(data.decision, data.reason);
    setLatestChain(data.chain_id);
    setRunbookStatus(`Real consent verification completed: ${data.decision}.`, 'ok');
    resetConsentControls();
  }catch(err){
    setConsentState(err.message || 'verification failed', 'var(--red)');
    resumeConsentBtn.disabled = false;
  }
});

async function configureMode(){
  try{
    // /health is liveness only now (S13); the mode a run should be labelled
    // with is behind a key.
    const health = await apiJson('/v1/console/mode');
    demoMode = health.demo_mode !== false;
    providerMode = health.provider || 'mock';
    modeReady = true;
    setPlannerBadge(health.planner);
    liveConsentCard.hidden = providerMode !== 'nac';
    modePill.textContent = providerMode === 'nac'
      ? (demoMode ? 'HYBRID · NaC + simulator' : 'LIVE · NaC sandbox')
      : 'SIMULATOR · mock provider';
    modePill.className = 'mode-pill ' + (providerMode === 'nac' ? 'live' : 'sim');
    if (providerMode === 'nac' && demoMode){
      demoNotice.textContent = 'Hybrid mode: scripted stage acts are enabled; the fixed continuity drill stays disabled because NaC checks remain live.';
    } else if (providerMode === 'nac'){
      demoNotice.textContent = 'Live NaC mode: real checks enabled; scripted acts and SIM-swap injection are disabled.';
    } else {
      demoNotice.textContent = 'Simulator mode: scripted network signals are deterministic and safe for stage testing.';
    }
    if (!suiteRunning){
      buttons.forEach(b => b.disabled = !demoMode);
      runStageSuiteBtn.disabled = !demoMode;
      resetStageBtn.disabled = !demoMode;
      runVelocityDemoBtn.disabled = !demoMode;
      runSessionDemoBtn.disabled = !canUseDemoSession();
      runLiveConsentBtn.disabled = providerMode !== 'nac';
      syncSessionControls();
      verifyChainRunBtn.disabled = !latestChainId;
      // Gate the network-condition controls the moment the mode is known.
      // Reading the mode is not a provider call; nothing here asks the
      // operator anything until somebody clicks.
      ncButtons(false);
    }
  }catch(err){
    modeReady = false;
    demoMode = false;
    syncSessionControls();
    ncButtons(false);
    demoNotice.textContent = 'Could not read server mode';
    modePill.textContent = 'SERVER MODE UNKNOWN';
    modePill.className = 'mode-pill sim';
  }
}
configureMode();
// A no-op until a key exists: in demo mode the render-time token is already
// here, otherwise this reconnects once the presenter supplies one.
connectStream().catch(() => {});

// ---- triggers ----
async function run(act, {reset = true} = {}){
  buttons.forEach(b => b.disabled = true);
  if (reset) clearConsole(false);
  activeRunId = newRunId();
  sessionLabel.textContent = 'isnad-agent · investigating…';
  try{
    // auth:false was left here when S4 put this endpoint behind a key. The
    // server has required a bearer token since d90d268, so every Act button and
    // the full-stage run had been 401ing before the investigator ever started —
    // which also left the ask-the-agent box permanently disabled, because
    // setLatestChain() below never ran on this path.
    const data = await apiJson(`/v1/console/run/${act}`, {
      method:'POST', headers:{'X-Console-Run-Id':activeRunId}
    });
    // The stream normally paints this first. The endpoint result remains the
    // authoritative fallback when an intermediary drops or delays SSE.
    setVerdict(data.decision, data.reason, data.chain_grade);
    if (typeof data.confidence === 'number') setMeter(data.confidence);
    setLatestChain(data.chain_id);
    renderCounterfactual(data.alternative);
    return data;
  }catch(err){
    addRow('--.--', 'error', err.message, 'flag');
    if (!suiteRunning) buttons.forEach(b => b.disabled = !demoMode);
    throw err;
  }finally{
    if (!suiteRunning) buttons.forEach(b => b.disabled = !demoMode);
  }
}

async function runForwardCheck({reset = true} = {}){
  if (reset) clearConsole(false);
  if (!t0) t0 = Date.now();
  activeRunId = newRunId();
  sessionLabel.textContent = 'isnad-agent · live forward verification…';
  setRunbookStatus('Calling forward verification through the configured provider…');
  const data = await apiJson('/v1/verify', {
    method:'POST',
    headers:{'X-Console-Run-Id':activeRunId},
    body:JSON.stringify({
      phone_number:'+99999991000',
      context:{event:'checkout',payment_method:'cod',account_age_days:0,amount:{value:4200}},
      options:{return_chain:true}
    })
  });
  setLatestChain(data.chain_id);
  setVerdict(data.decision, data.reason, data.chain_grade);
  if (typeof data.confidence === 'number') setMeter(data.confidence);
  setPlannerBadge(data.planner);
  renderCounterfactual(data.alternative);   // T5
  addRow(clock(), 'merchant API', `${data.decision} · chain=${data.chain_id} · source=${(data.provider_sources || []).join(',') || 'unknown'}`, data.decision === 'DECLINE' ? 'flag' : data.decision === 'ALLOW' ? 'pass' : 'info');
  setRunbookStatus(`Forward verification completed: ${data.decision}.`, data.decision === 'DECLINE' ? 'warn' : 'ok');
  return data;
}

async function runReverseCheck({reset = true} = {}){
  if (reset) clearConsole(false);
  if (!t0) t0 = Date.now();
  activeRunId = newRunId();
  sessionLabel.textContent = 'isnad-agent · Reverse Isnad…';
  setRunbookStatus('Checking the claimed bank caller through the configured provider…');
  const data = await apiJson('/v1/reverse-verify', {
    method:'POST',
    headers:{'X-Console-Run-Id':activeRunId},
    body:JSON.stringify({caller_number:'+96279999999',claimed_identity:'Bank of Jordan',options:{return_chain:true}})
  });
  setLatestChain(data.chain_id);
  setVerdict(data.trust, data.reason, data.chain_grade);
  addRow(clock(), 'reverse API', `${data.trust} · chain=${data.chain_id}`, data.trust === 'REJECT_CALLER' ? 'flag' : 'pass');
  setRunbookStatus(`Reverse Isnad completed: ${data.trust}.`, data.trust === 'REJECT_CALLER' ? 'warn' : 'ok');
  return data;
}

async function runIdempotencyCheck({reset = true} = {}){
  if (reset) clearConsole(false);
  if (!t0) t0 = Date.now();
  activeRunId = newRunId();
  setRunbookStatus('Sending the same request twice with one Idempotency-Key…');
  const key = `console-${Date.now()}`;
  const request = {
    method:'POST',
    headers:{'Idempotency-Key':key,'X-Console-Run-Id':activeRunId},
    body:JSON.stringify({
      phone_number:'+99999991002',
      context:{event:'signup',account_age_days:0},
      options:{return_chain:true}
    })
  };
  const first = await apiJson('/v1/verify', request);
  const second = await apiJson('/v1/verify', request);
  const same = first.chain_id === second.chain_id;
  setLatestChain(second.chain_id);
  addRow(clock(), 'idempotency', same ? `PASS · replayed chain ${second.chain_id}` : 'FAIL · second request created a different chain', same ? 'pass' : 'flag');
  setRunbookStatus(same ? 'Idempotency replay passed: both responses share one chain.' : 'Idempotency replay failed.', same ? 'ok' : 'err');
  return {first, second, same};
}

async function verifyLatestChain(){
  if (!latestChainId) throw new Error('run a verification first so there is a chain to verify');
  const data = await apiJson(`/v1/chains/${latestChainId}/verification`);
  addRow(clock(), 'evidence vault', `${data.valid ? 'PASS' : 'FAIL'} · ${data.algorithm} signature · chain=${data.chain_id}`, data.valid ? 'pass' : 'flag');
  setRunbookStatus(data.valid ? 'Evidence vault passed: latest chain signature is valid.' : 'Evidence vault failed: signature is invalid.', data.valid ? 'ok' : 'err');
  return data;
}

async function runStageSuite(){
  if (!demoMode || suiteRunning) return;
  setRunbookBusy(true);
  clearConsole(true);
  setRunbookStatus('Running Act I…');
  const acts = [
    ['Act I', 'act1'], ['Act II', 'act2'], ['Act III', 'act3'], ['Act IV', 'act4']
  ];
  try{
    for (const [label, act] of acts){
      setRunbookStatus(`Running ${label}…`);
      const data = await run(act, {reset:false});
      addRow(clock(), 'runbook', `${label} complete · ${data.decision} · ${data.chain_id}`, data.decision === 'DECLINE' ? 'flag' : 'pass');
      await wait(300);
    }
    if (canUseDemoSession()){
      await runSessionDemo();
      setRunbookStatus('Full stage demo complete: four acts plus live session revocation.', 'ok');
    } else {
      addRow(clock(), 'runbook', 'continuity drill skipped: it is available only with the mock provider', 'info');
      setRunbookStatus('Full stage demo complete: four acts. The mock-only continuity drill was skipped.', 'ok');
    }
  }catch(err){
    addRow(clock(), 'runbook', err.message, 'flag');
    setRunbookStatus(`Stage demo stopped: ${err.message}`, 'err');
  }finally{
    setRunbookBusy(false);
  }
}

// Act VII — three calls, one number, three answers. Paced deliberately: the
// checks themselves take microseconds, and a sequence that finishes before the
// audience has read the first line demonstrates nothing.
async function runAct7(){
  if (!demoMode || suiteRunning) return;
  setRunbookBusy(true);
  clearConsole(true);
  activeRunId = newRunId();
  try{
    setRunbookStatus('A call arrives from Demo Bank\u2019s real switchboard number\u2026');
    addRow(clock(), 'scenario', 'An unannounced call presenting Demo Bank\u2019s switchboard number', 'info');
    await apiJson('/v1/console/act7/screen/spoofed', {method:'POST', headers:{'X-Console-Run-Id':activeRunId}});
    await wait(1600);

    setRunbookStatus('Now the bank announces the call it is about to place\u2026');
    await apiJson('/v1/console/act7/announce', {method:'POST', headers:{'X-Console-Run-Id':activeRunId}});
    await wait(1200);

    setRunbookStatus('The same number, the same call \u2014 now announced.');
    addRow(clock(), 'scenario', 'The same number, this time announced in advance', 'info');
    await apiJson('/v1/console/act7/screen/announced', {method:'POST', headers:{'X-Console-Run-Id':activeRunId}});
    await wait(1600);

    setRunbookStatus('And the hotline printed on the back of the card.');
    addRow(clock(), 'scenario', 'The published hotline \u2014 a number the bank never calls from', 'info');
    await apiJson('/v1/console/act7/screen/hotline', {method:'POST', headers:{'X-Console-Run-Id':activeRunId}});

    setRunbookStatus('Act VII complete: a registry hit is not trust \u2014 only the announced call verified.', 'ok');
  }catch(err){
    addRow(clock(), 'runbook', err.message, 'flag');
    setRunbookStatus(`Act VII stopped: ${err.message}`, 'err');
  }finally{
    setRunbookBusy(false);
  }
}

async function resetStageState(){
  if (!demoMode || suiteRunning) return;
  const data = await apiJson('/v1/console/reset-stage', {method:'POST'});
  addRow(clock(), 'stage reset',
    `cleared ${data.cleared_velocity_events} velocity event${data.cleared_velocity_events === 1 ? '' : 's'} and simulated SIM swaps`,
    'pass');
  setRunbookStatus('Stage state reset. Act I and Act VII will start clean.', 'ok');
  return data;
}

async function runVelocityDemo(){
  if (!demoMode || suiteRunning) return;
  activeRunId = newRunId();
  setRunbookStatus('Building the caller-velocity signal from Tier 1 screens…');
  const data = await apiJson('/v1/console/velocity-demo', {
    method:'POST', headers:{'X-Console-Run-Id':activeRunId}
  });
  setRunbookStatus(
    `Caller velocity complete: ${data.label} after ${data.calls} distinct callees.`,
    data.label === 'SUSPECTED_SPOOF' ? 'ok' : 'warn'
  );
  return data;
}

async function runLiveSuite(){
  if (suiteRunning) return;
  setRunbookBusy(true);
  clearConsole(true);
  const failures = [];
  const steps = [
    ['health', async () => {
      const data = await apiJson('/v1/console/mode');
      addRow(clock(), 'health', `PASS · provider=${data.provider} · demo_mode=${data.demo_mode}`, 'pass');
    }],
    ['forward verification', () => runForwardCheck({reset:false})],
    ['Reverse Isnad', () => runReverseCheck({reset:false})],
    ['idempotency', () => runIdempotencyCheck({reset:false})],
    ['vault', () => verifyLatestChain()]
  ];
  try{
    for (const [label, action] of steps){
      setRunbookStatus(`Live check: ${label}…`);
      try{ await action(); }
      catch(err){
        failures.push(label);
        addRow(clock(), label, `FAIL · ${err.message}`, 'flag');
      }
    }
    setRunbookStatus(failures.length ? `Live checks finished with failures: ${failures.join(', ')}.` : 'All live API checks passed.', failures.length ? 'warn' : 'ok');
  }finally{
    setRunbookBusy(false);
  }
}

async function launchSingle(action){
  if (suiteRunning) return;
  setRunbookBusy(true);
  try{ await action(); }
  catch(err){
    addRow(clock(), 'runbook', err.message, 'flag');
    setRunbookStatus(`Scenario failed: ${err.message}`, 'err');
  }finally{
    setRunbookBusy(false);
  }
}

runStageSuiteBtn.addEventListener('click', runStageSuite);
runLiveSuiteBtn.addEventListener('click', runLiveSuite);
runAct7Btn.addEventListener('click', runAct7);
resetStageBtn.addEventListener('click', () => launchSingle(resetStageState));
runVelocityDemoBtn.addEventListener('click', () => launchSingle(runVelocityDemo));
runLiveConsentBtn.addEventListener('click', () => {
  if (providerMode !== 'nac') return;
  liveConsentCard.hidden = false;
  liveConsentCard.scrollIntoView({behavior:'smooth', block:'center'});
  setRunbookStatus('Consent panel opened. Start consent, approve NaC, then resume verification.');
  startConsentBtn.focus();
});
runReverseCheckBtn.addEventListener('click', () => launchSingle(() => runReverseCheck()));
runSessionDemoBtn.addEventListener('click', () => launchSingle(runSessionDemo));
recoverBtn.addEventListener('click', recoverMissedEvents);
runIdempotencyBtn.addEventListener('click', () => launchSingle(() => runIdempotencyCheck()));
verifyChainRunBtn.addEventListener('click', () => launchSingle(verifyLatestChain));
runForwardCheckBtn.addEventListener('click', () => launchSingle(() => runForwardCheck()));

function clearConsole(idle = true){
  latestChainId = null;
  verifyChainRunBtn.disabled = true;
  askInput.disabled = true;
  askBtn.disabled = true;
  log.replaceChildren();
  if (idle) log.appendChild(span('meta', 'Ready. Trigger an act to watch the agent investigate.'));
  log.appendChild(cursorNode());
  setVerdict('—', '', null);
  renderCounterfactual(null);
  qrBox.hidden = true;
  askAnswer.textContent = '';
  verdictEl.className = 'verdict';
  fill.style.width = '8%'; fill.style.background = 'var(--green)'; pval.textContent = '—';
  if (idle) sessionLabel.textContent = 'isnad-agent · idle';
}
askBtn.addEventListener('click', askTheAgent);
askInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') askTheAgent(); });
buttons.forEach(b => b.addEventListener('click', () => run(b.dataset.act)));
clearBtn.addEventListener('click', () => clearConsole(true));

// --- network conditions ------------------------------------------------------
//
// Moved here from /judge. Same routes, same isolation, same rule: every
// operator request starts from a click. Rendering this page, switching
// language, or running an act must never cause one — a passive surface that
// calls an operator is a bill the reader did not agree to.
//
// Subscription state lives only here; the judge page no longer holds any, so
// there is one owner of it rather than two that can disagree.
const ncEls = {
  phone: document.getElementById('ncPhone'),
  subscribe: document.getElementById('ncSubscribe'),
  forecast: document.getElementById('ncForecast'),
  history: document.getElementById('ncHistory'),
  remove: document.getElementById('ncDelete'),
  state: document.getElementById('ncState'),
  result: document.getElementById('ncResult')
};
let ncSubscription = null;

// Keyed, not resolved once: `setLocale` re-applies `[data-i18n]`, so a string
// written straight into textContent would stay in the language it was born in.
function ncKeyed(key, fallback, tag){
  const el = document.createElement(tag || 'span');
  el.dataset.i18n = 'ui.' + key;
  el.textContent = fallback;
  if (window.Isnad) window.Isnad.applyDictionary(el);
  return el;
}
function ncIsolate(value){
  return window.Isnad ? window.Isnad.isolate(value) : document.createTextNode(String(value));
}
function ncSetState(key, fallback, suffix){
  ncEls.state.replaceChildren(ncKeyed(key, fallback));
  if (suffix) ncEls.state.append(document.createTextNode(' '), ncIsolate(suffix));
}
function ncButtons(busy){
  const live = ncSubscription && !ncSubscription.terminal;
  const all = [ncEls.subscribe, ncEls.forecast, ncEls.history, ncEls.remove];
  // Without demo mode every one of these calls is a 401 the reader cannot act
  // on, so the controls say so by being disabled rather than by failing.
  if (!demoMode){
    all.forEach(button => { button.disabled = true; });
    return;
  }
  // Disabled while in flight so a second click cannot start a second call.
  ncEls.subscribe.disabled = busy || !!live;
  ncEls.forecast.disabled = busy || !live;
  ncEls.history.disabled = busy || !live;
  ncEls.remove.disabled = busy || !live;
}
function ncLevelNode(level){
  const span = document.createElement('span');
  span.className = 'nc-level ' + String(level || 'unknown').toLowerCase();
  // A glyph as well as a colour: colour alone is not a state.
  const glyph = level === 'High' ? '▲ ' : level === 'Medium' ? '◆ ' : level === 'Low' ? '● ' : '? ';
  span.append(document.createTextNode(glyph));
  span.appendChild(ncKeyed('network_conditions_level_' + String(level || 'unknown').toLowerCase(),
                           level || 'unknown'));
  return span;
}
function ncRenderQuery(body){
  ncEls.result.replaceChildren();
  const header = document.createElement('div');
  header.appendChild(ncKeyed('network_conditions_mode_' + body.mode, body.mode));
  header.append(document.createTextNode(' · '));
  header.appendChild(ncKeyed('network_conditions_provenance', 'source'));
  header.append(document.createTextNode(': ' + body.provenance));
  ncEls.result.appendChild(header);
  if (body.empty){
    // Explicitly not "Low": the operator returned nothing at all.
    const empty = ncKeyed('network_conditions_empty',
      'The operator returned no reading. The condition is unknown.', 'div');
    empty.className = 'nc-note';
    ncEls.result.appendChild(empty);
  }
  (body.intervals || []).forEach(interval => {
    const row = document.createElement('div');
    row.className = 'nc-interval';
    row.appendChild(ncLevelNode(interval.level));
    row.append(document.createTextNode(' '));
    row.appendChild(ncIsolate(interval.start + ' → ' + interval.stop));
    const confidence = document.createElement('span');
    confidence.className = 'nc-note';
    confidence.append(document.createTextNode(' · '));
    if (interval.confidence === null || interval.confidence === undefined){
      confidence.appendChild(ncKeyed('network_conditions_confidence_unknown', 'confidence not reported'));
    } else {
      confidence.appendChild(ncKeyed('network_conditions_confidence', 'confidence'));
      confidence.append(document.createTextNode(' ' + interval.confidence + '%'));
    }
    row.appendChild(confidence);
    ncEls.result.appendChild(row);
  });
  const stamp = document.createElement('div');
  stamp.className = 'nc-note';
  stamp.appendChild(ncKeyed('network_conditions_updated', 'Updated at'));
  stamp.append(document.createTextNode(' '));
  stamp.appendChild(ncIsolate(body.observed_at));
  ncEls.result.appendChild(stamp);
}
function ncPhoneNumber(){
  return (ncEls.phone.value || '').trim();
}
async function ncCall(run, busyKey){
  ncButtons(true);
  ncSetState(busyKey, 'Working…');
  try {
    await run();
  } catch (error){
    // The form and any previous reading stay exactly as they were: a failed
    // network-condition request must never cost the reader their work.
    ncSetState('network_conditions_failed', 'The request did not complete.', safeError(error));
  } finally {
    ncButtons(false);
  }
}
ncEls.subscribe.addEventListener('click', () => ncCall(async () => {
  ncSubscription = await apiJson('/v1/network-conditions/subscriptions', {
    method: 'POST', body: JSON.stringify({phone_number: ncPhoneNumber()})
  });
  ncSetState('network_conditions_active', 'Subscription active until', ncSubscription.expires_at);
}, 'network_conditions_working'));
ncEls.forecast.addEventListener('click', () => ncCall(async () => {
  ncRenderQuery(await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}/query`, {
    method: 'POST', body: JSON.stringify({phone_number: ncPhoneNumber()})
  }));
  ncSetState('network_conditions_read', 'Reading complete.');
}, 'network_conditions_working'));
ncEls.history.addEventListener('click', () => ncCall(async () => {
  const end = new Date();
  const start = new Date(end.getTime() - 3600000);
  ncRenderQuery(await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}/query`, {
    method: 'POST',
    body: JSON.stringify({phone_number: ncPhoneNumber(), start: start.toISOString(), end: end.toISOString()})
  }));
  ncSetState('network_conditions_read', 'Reading complete.');
}, 'network_conditions_working'));
ncEls.remove.addEventListener('click', () => ncCall(async () => {
  ncSubscription = await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}`, {method: 'DELETE'});
  ncSetState('network_conditions_deleted', 'Subscription deleted at the operator.');
}, 'network_conditions_working'));
