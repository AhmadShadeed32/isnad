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
let sessionId = null;
let streamedVerdict = null;

function key(){ return DEMO_TOKEN; }
function newRunId(){ return 'judge-' + Date.now() + '-' + Math.random().toString(16).slice(2); }
function clearSteps(){ stepEls.forEach(s => s.className = 'step'); }
function setStep(index, kind = 'active'){ if (stepEls[index]) stepEls[index].className = 'step ' + kind; }
function setStatus(text){ statusline.textContent = text; }
function safeError(err){ return err && err.message ? err.message : 'The demo request did not complete.'; }
function provenance(source){
  const normalized = String(source || 'unknown').toLowerCase();
  if (normalized === 'mock') return {label:'SIMULATOR · mock fixture', cls:'sim'};
  if (normalized === 'nac') return {label:'LIVE · Nokia NaC', cls:'live'};
  if (normalized === 'local') return {label:'LOCAL · Isnad state', cls:''};
  return {label:'PROVENANCE · ' + normalized, cls:''};
}
function appendTrace(kind, title, detail, source, meta, detailKey){
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
  const side = document.createElement('div'); side.className = 'trace-meta'; side.textContent = meta || '';
  row.append(mark, body, side); trace.appendChild(row); trace.scrollTop = trace.scrollHeight;
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
function appendTiming(event){
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
    copy.appendChild(keyed('swap_date_' + event.availability,
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
  row.append(mark, body, side);
  trace.appendChild(row); trace.scrollTop = trace.scrollHeight;
}
async function apiJson(path, options = {}){
  const response = await fetch(path, { ...options, headers:{'Authorization':'Bearer ' + key(), ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail?.message || data.detail?.code || 'request failed (' + response.status + ')');
  return data;
}
function setMode(data){
  demoMode = data.demo_mode === true;
  configuredProvider = data.provider || 'unknown';
  const providerLabel = configuredProvider === 'nac' ? 'LIVE PROVIDER · Nokia NaC' : configuredProvider === 'mock' ? 'SIMULATOR · mock provider' : 'PROVIDER · ' + configuredProvider;
  mode.textContent = providerLabel + (demoMode ? ' · stage mode' : '');
  mode.className = 'mode ' + (configuredProvider === 'nac' && !demoMode ? 'live' : 'sim');
  planner.textContent = 'planner: ' + (data.planner || 'unknown');
  if (!demoMode){ checkout.disabled = true; cleanCheckout.disabled = true; gapCheckout.disabled = true; document.getElementById('checkoutFoot').textContent = 'Stage checkout is disabled outside demo mode. Use the authenticated production API for live customer requests.'; }
}
function scheduleStreamReconnect(){
  if (streamReconnectTimer || !key()) return;
  streamReconnectTimer = setTimeout(() => {
    streamReconnectTimer = null;
    connectStream().catch(() => {});
  }, 5000);
}
async function connectStream(){
  if (!key()) return;
  try{
    const token = await apiJson('/v1/console/stream-token', {method:'POST'});
    streamCredential = token.stream_token;
    if (!streamCredential) throw new Error('Could not start the evidence stream.');
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/v1/console/stream?stream_token=' + encodeURIComponent(streamCredential));
    eventSource.onmessage = message => { try { onEvent(JSON.parse(message.data)); } catch (_) { /* Ignore a malformed stream frame. */ } };
    eventSource.onerror = () => {
      if (eventSource) eventSource.close();
      eventSource = null; streamCredential = null;
      if (activeRunId && decision.textContent === 'VERIFYING') setStatus('Connection interrupted; reconnecting to the evidence stream…');
      scheduleStreamReconnect();
    };
  }catch(err){
    scheduleStreamReconnect();
    throw err;
  }
}
function onEvent(event){
  if (event.type !== 'session' && (!activeRunId || event.run_id !== activeRunId)) return;
  if (event.type === 'session'){
    handleSessionEvent(event);
  } else if (event.type === 'start'){
    setStep(0); setStatus('Agent formed a ' + String(event.hypothesis || 'checkout') + ' hypothesis. Prior risk score: ' + event.prior_p_fraud + '.');
  } else if (event.type === 'decision'){
    setStep(1); const label = event.action === 'stop' ? 'Agent stops' : 'Agent selects ' + (event.api || event.action);
    appendTrace('info', label, event.rationale || 'No rationale returned.', null, (event.planner || 'policy') + ' · budget ' + event.budget_left);
    if (event.phase === 'investigation' && event.planner) planner.textContent = 'planner: ' + event.planner;
    setStatus('Agent selected the next check from the remaining evidence budget.');
  } else if (event.type === 'evidence'){
    setStep(2); const kind = event.result === 'PASS' ? 'pass' : event.result === 'FLAG' ? 'flag' : 'info';
    const windowText = typeof event.max_age_hours === 'number' ? ' · window ' + event.max_age_hours + 'h' : '';
    // Keyed on the SIGNAL, not on the sentence. `event.detail` is authored
    // vocabulary with a window interpolated into it, so translating it by exact
    // text would break the moment the window changed. The signal is the stable
    // identity of what the network said.
    appendTrace(kind, event.api || event.signal || 'Network evidence',
      event.detail || event.signal || '', event.source,
      'risk score ' + event.p_fraud + windowText,
      event.signal ? 'ui.signal_' + event.signal : null);
    setStatus('Evidence received with its source and result.');
  } else if (event.type === 'enrichment'){
    appendTiming(event);
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
// --- network conditions ------------------------------------------------------
//
// Every provider request here starts from a click. Rendering this page, or
// switching language, must never cause one: a passive surface that calls an
// operator is a bill the reader did not agree to.
const ncEls = {
  subscribe: document.getElementById('ncSubscribe'),
  forecast: document.getElementById('ncForecast'),
  history: document.getElementById('ncHistory'),
  remove: document.getElementById('ncDelete'),
  state: document.getElementById('ncState'),
  result: document.getElementById('ncResult')
};
let ncSubscription = null;
function currentPhoneNumber(){
  return (SCENARIO_COPY[activeScenario] || SCENARIO_COPY.replacement).phone;
}
function ncSetState(key, fallback, suffix){
  ncEls.state.replaceChildren(keyed(key, fallback));
  if (suffix) ncEls.state.append(document.createTextNode(' '),
    window.Isnad ? window.Isnad.isolate(suffix) : document.createTextNode(suffix));
}
function ncButtons(busy){
  const live = ncSubscription && !ncSubscription.terminal;
  // Same gate the checkout buttons use. Without demo mode and a console token
  // every one of these calls is a 401 the reader cannot act on.
  if (!demoMode || !key()){
    [ncEls.subscribe, ncEls.forecast, ncEls.history, ncEls.remove]
      .forEach(button => { button.disabled = true; });
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
  span.appendChild(keyed('network_conditions_level_' + String(level || 'unknown').toLowerCase(),
                         level || 'unknown'));
  return span;
}
function ncRenderQuery(body){
  ncEls.result.replaceChildren();
  const header = document.createElement('div');
  header.appendChild(keyed('network_conditions_mode_' + body.mode, body.mode));
  header.append(document.createTextNode(' · '));
  header.appendChild(keyed('network_conditions_provenance', 'source'));
  header.append(document.createTextNode(': ' + body.provenance));
  ncEls.result.appendChild(header);
  if (body.empty){
    // Explicitly not "Low": the operator returned nothing at all.
    const empty = keyed('network_conditions_empty',
      'The operator returned no reading. The condition is unknown.', 'div');
    empty.className = 'nc-note';
    ncEls.result.appendChild(empty);
  }
  (body.intervals || []).forEach(interval => {
    const row = document.createElement('div');
    row.className = 'nc-interval';
    row.appendChild(ncLevelNode(interval.level));
    row.append(document.createTextNode(' '));
    row.appendChild(window.Isnad ? window.Isnad.isolate(interval.start + ' → ' + interval.stop)
                                 : document.createTextNode(interval.start + ' → ' + interval.stop));
    const confidence = document.createElement('span');
    confidence.className = 'nc-note';
    confidence.append(document.createTextNode(' · '));
    if (interval.confidence === null || interval.confidence === undefined){
      confidence.appendChild(keyed('network_conditions_confidence_unknown', 'confidence not reported'));
    } else {
      confidence.appendChild(keyed('network_conditions_confidence', 'confidence'));
      confidence.append(document.createTextNode(' ' + interval.confidence + '%'));
    }
    row.appendChild(confidence);
    ncEls.result.appendChild(row);
  });
  const stamp = document.createElement('div');
  stamp.className = 'nc-note';
  stamp.appendChild(keyed('network_conditions_updated', 'Updated at'));
  stamp.append(document.createTextNode(' '));
  stamp.appendChild(window.Isnad ? window.Isnad.isolate(body.observed_at)
                                 : document.createTextNode(body.observed_at));
  ncEls.result.appendChild(stamp);
}
async function ncCall(run, busyKey){
  ncButtons(true);
  ncSetState(busyKey, 'Working…');
  try {
    await run();
  } catch (error){
    // The order, the form and any previous reading stay exactly as they were:
    // a failed network-condition request must never cost the reader their work.
    ncSetState('network_conditions_failed', 'The request did not complete.', error.message);
  } finally {
    ncButtons(false);
  }
}
ncEls.subscribe.addEventListener('click', () => ncCall(async () => {
  ncSubscription = await apiJson('/v1/network-conditions/subscriptions', {
    method: 'POST', body: JSON.stringify({phone_number: currentPhoneNumber()})
  });
  ncSetState('network_conditions_active', 'Subscription active until', ncSubscription.expires_at);
}, 'network_conditions_working'));
ncEls.forecast.addEventListener('click', () => ncCall(async () => {
  ncRenderQuery(await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}/query`, {
    method: 'POST', body: JSON.stringify({phone_number: currentPhoneNumber()})
  }));
  ncSetState('network_conditions_read', 'Reading complete.');
}, 'network_conditions_working'));
ncEls.history.addEventListener('click', () => ncCall(async () => {
  const end = new Date();
  const start = new Date(end.getTime() - 3600000);
  ncRenderQuery(await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}/query`, {
    method: 'POST',
    body: JSON.stringify({phone_number: currentPhoneNumber(), start: start.toISOString(), end: end.toISOString()})
  }));
  ncSetState('network_conditions_read', 'Reading complete.');
}, 'network_conditions_working'));
ncEls.remove.addEventListener('click', () => ncCall(async () => {
  ncSubscription = await apiJson(`/v1/network-conditions/subscriptions/${ncSubscription.subscription_id}`, {method: 'DELETE'});
  ncSetState('network_conditions_deleted', 'Subscription deleted at the operator.');
}, 'network_conditions_working'));

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
}
function renderVerdict(data, {persisted = true} = {}){
  latestChainId = data.chain_id;
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
  }
}
const SCENARIO_COPY = {
  replacement: {
    title: 'New SIM. Same customer.',
    story: 'Her SIM was replaced, but her handset is unchanged. A rule that declines every SIM change loses her order. Isnad checks the surrounding evidence before deciding.',
    foot: 'Expected: CHALLENGE. Ask for the merchant’s step-up instead of automatically declining. Operator answers are simulated.',
    path: '/v1/console/run/act6',
    // The fixture's own subscriber number, so the network-condition panel asks
    // about the same device the checkout was about.
    phone: '+962790000002',
  },
  clean: {
    title: 'A clean checkout.',
    story: 'A new customer has no merchant history. Supporting network evidence can let this checkout proceed without another step-up.',
    foot: 'Expected: ALLOW. Supporting evidence clears this fixed example. Operator answers are simulated.',
    path: '/v1/console/run/act3',
    phone: '+962790000001',
  },
  gap: {
    title: 'Consent withheld, one operator gone quiet.',
    story: 'The customer has not granted Number Verification consent, and one operator check comes back unavailable rather than pass or fail. The chain has a real gap in it, not a contradiction.',
    foot: 'Expected: CHALLENGE, evidence unresolved. This is "we could not check," not "the check failed."',
    path: '/v1/console/run/act5',
    phone: '+962790000005',
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
  trace.replaceChildren(); clearSteps();
  decision.textContent = 'VERIFYING'; decision.className = 'decision small';
  presentationTitle.textContent = 'VERIFYING'; presentationTitle.className = 'decision';
  presentationSummary.textContent = 'The agent is deciding what evidence it needs.';
  presentationAction.textContent = '';
  setFactGroup(supportingGroup, supportingFacts, []); setFactGroup(adverseGroup, adverseFacts, []); setFactGroup(unresolvedGroup, unresolvedFacts, []);
  reason.textContent = 'The agent is deciding what evidence it needs.'; grade.textContent = '';
  activeRunId = newRunId(); setStatus('Starting a deterministic, simulated checkout fixture…');
  try{
    const data = await apiJson(copy.path, {method:'POST', headers:{'X-Console-Run-Id':activeRunId}});
    // The HTTP response returns only after the server has persisted the chain,
    // so this call, not the earlier SSE 'verdict' event, is what confirms a
    // receipt actually exists. SSE normally draws the outcome first for
    // responsiveness; merging its fields here just fills in anything the
    // slightly-earlier stream event carried that this response also confirms.
    renderVerdict({...data, ...(streamedVerdict && streamedVerdict.run_id === activeRunId ? streamedVerdict : {})}, {persisted:true});
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
});

localeSelect.addEventListener('change', (event) => { Locale.setLocale(event.target.value); });
Locale.setLocale(Locale.preferred());

(async function configure(){
  try { setMode(await apiJson('/v1/console/mode')); await connectStream(); }
  catch(err){ mode.textContent = 'SERVER MODE UNKNOWN'; mode.className = 'mode sim'; checkout.disabled = true; cleanCheckout.disabled = true; gapCheckout.disabled = true; fallback.textContent = 'Could not read the secure demo mode: ' + safeError(err); fallback.classList.add('visible'); }
}());
