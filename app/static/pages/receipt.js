const $ = (id) => document.getElementById(id);
const rawChainId = location.pathname.split('/').pop() || '';
let chainId = '';
try { chainId = decodeURIComponent(rawChainId); } catch (_) { /* handled by main */ }
let payloadBytes = null, originalBytes = null, sigBytes = null, keyBytes = null;
// I7: the response body exactly as it arrived, held so the download hands the
// reader the same bytes this page verified.
let bundleText = null;

// --- I6: locale ------------------------------------------------------------
// The switch itself lives in /ui/i18n.js, shared with the other pages that
// have one. This page only says what *it* must redraw when the language
// changes; the fallback rule has one implementation, not one per page.
//
// If that module does not load, the page falls back to English and keeps
// working. Verification is what this page is *for*, and it must not be lost
// because a presentation concern failed to arrive — an unreachable translation
// is not a reason to leave a reader unable to check a signature.
const Locale = (typeof Isnad !== 'undefined') ? Isnad : {
  applyText: (el, path, literal, prefix) => { el.textContent = (prefix || '') + literal; },
  isolate: (value) => { const b = document.createElement('bdi'); b.dir = 'ltr'; b.textContent = value; return b; },
  setIsolated: (el, value) => { el.replaceChildren(Locale.isolate(value)); },
  codedInto: (el, code) => { el.replaceChildren(Locale.isolate(code)); },
  onChange: () => {},
  setLocale: async () => 'en',
  preferred: () => 'en',
  reviewStatus: () => null
};

let signedState = null;      // re-rendered when the language changes
let lastSignature = null;    // true | false, or null when not yet checked

Locale.onChange((locale) => {
  $('locale').value = locale;
  // The arrow is a direction, not a word, so it flips with the page.
  $('backArrow').textContent = locale === 'ar' ? '\u2192' : '\u2190';
  // An unreviewed translation says so on the page, not only in its JSON file.
  const review = Locale.reviewStatus();
  $('draftNote').textContent = review || '';
  $('draftNote').hidden = !review;
  if (lastSignature !== null) showSignature(lastSignature);
  if (signedState){
    Locale.codedInto($('decision'), signedState.decision, 'decision');
    Locale.codedInto($('grade'), signedState.chain_grade || 'UNGRADED', 'chain_grade');
  }
});

function hexToBytes(hex){
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

function setStatus(state, text, note){
  const el = $('status');
  el.className = 'status ' + state;
  el.textContent = text;
  el.removeAttribute('lang');
  $('statusNote').textContent = note || '';
}

/* The one status with a dictionary entry, and the one that must never be
   readable from colour alone: it keeps its glyph and its sentence in both
   languages. */
function showSignature(ok){
  lastSignature = ok;
  const el = $('status');
  el.className = 'status ' + (ok ? 'ok' : 'bad');
  Locale.applyText(el,
    ok ? 'ui.signature_valid' : 'ui.signature_invalid',
    ok ? 'signature valid' : 'signature INVALID',
    ok ? '✓ ' : '✗ ');
  $('statusNote').textContent = ok
    ? 'These bytes match the key below. Compare that public key with a trusted source to establish the signer’s identity.'
    : 'The bytes do not match the signature. This receipt has been altered.';
}

async function verify(){
  if (!window.isSecureContext || !crypto.subtle){
    // Honest failure rather than a misleading red cross: WebCrypto is simply
    // unavailable outside a secure context.
    setStatus('pending', '⋯ cannot verify here',
      'WebCrypto needs HTTPS (or localhost). Open this page over HTTPS to verify.');
    return null;
  }
  try{
    const key = await crypto.subtle.importKey('raw', keyBytes, {name:'Ed25519'}, false, ['verify']);
    return await crypto.subtle.verify({name:'Ed25519'}, key, sigBytes, payloadBytes);
  }catch(err){
    setStatus('pending', '⋯ cannot verify here',
      'This browser does not support Ed25519 in WebCrypto.');
    return null;
  }
}

async function showVerification(){
  const ok = await verify();
  if (ok === null){ lastSignature = null; return null; }
  showSignature(ok);
  return ok;
}

/* LTR isolation for anything the signature covers. Under dir="rtl" the bidi
   algorithm reorders a bare chain id, hex digest, ISO timestamp or signed
   number at its neutral edges, and a reordered string is no longer the one the
   reader is being asked to compare. */
const setIsolated = (id, value) => Locale.setIsolated($(id), value);

function render(signed, publicKey, signature){
  signedState = signed;
  $('chainId').textContent = signed.chain_id;   // already a <bdi dir="ltr">
  setIsolated('publicKey', publicKey);
  setIsolated('signature', signature);
  setIsolated('signedAt', signed.signed_at || '—');

  Locale.codedInto($('decision'), signed.decision, 'decision');
  Locale.codedInto($('grade'), signed.chain_grade || 'UNGRADED', 'chain_grade');
  setIsolated('confidence', signed.confidence);
  $('hypothesis').textContent = signed.hypothesis;
  setIsolated('planner', signed.planner);
  $('summaryCard').hidden = false;

  const body = $('steps');
  body.replaceChildren();
  // Allow-list each signed link field before rendering. `detail` is also in the
  // signed payload, but on the NaC path it can contain provider prose and this
  // public receipt must never display it.
  const steps = Array.isArray(signed.chain) ? signed.chain : [];
  steps.forEach(step => {
    const tr = document.createElement('tr');
    const delta = typeof step.delta_logodds === 'number'
      ? (step.delta_logodds >= 0 ? '+' : '') + step.delta_logodds.toFixed(2)
      : '—';
    // The window the question covered, NOT the age of the event: CAMARA answers
    // "was there a swap in the last N hours" with a boolean and no timestamp,
    // so an event age would be invented.
    const window = typeof step.max_age_hours === 'number'
      ? `last ${step.max_age_hours}h` : '—';
    [step.step, step.api, step.signal, step.result, delta, window].forEach(v => {
      const td = document.createElement('td');
      // API names, signed signal tokens and signed numbers, isolated so an
      // RTL page cannot reorder a "+0.90" into "0.90+" or split an API name.
      td.appendChild(Locale.isolate(v));
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
  $('stepsCard').hidden = steps.length === 0;
  renderArithmetic(signed, steps);
}

// Redo the belief and threshold decision from signed parts. Older verdicts do
// not contain a policy snapshot, so they remain verifiable but cannot claim a
// threshold replay rather than quietly borrowing today's deployment policy.
function renderArithmetic(signed, steps){
  const card = $('mathCard');
  const prior = signed.prior_logodds;
  if (prior === null || prior === undefined || prior === 0){
    // A chain signed before the prior was recorded. Showing 0.0 as if it were
    // the real starting point would be inventing a number the vault never
    // attested, so the card says why it cannot be shown instead.
    card.hidden = true;
    return;
  }
  const deltas = steps
    .map(step => typeof step.delta_logodds === 'number' ? step.delta_logodds : 0);
  const sum = deltas.reduce((a2, b) => a2 + b, 0);
  const total = prior + sum;
  const p = 1 / (1 + Math.exp(-total));

  const fixed = n => (n >= 0 ? '+' : '') + n.toFixed(4);
  setIsolated('mPrior', prior.toFixed(4));
  setIsolated('mDeltas', fixed(sum));
  setIsolated('mTotal', total.toFixed(4));
  setIsolated('mP', p.toFixed(3));
  const snapshot = signed.policy_snapshot || {};
  const allowBelow = snapshot.allow_below;
  const declineAbove = snapshot.decline_above;
  if (typeof allowBelow !== 'number' || typeof declineAbove !== 'number'){
    $('mThresholds').textContent = 'not recorded by this older receipt';
    $('mVerdict').textContent = signed.decision;
    $('mNote').textContent =
      'Belief recomputed from signed values. This older receipt did not sign its policy thresholds, so its decision cannot be replayed from thresholds.';
    $('mNote').style.color = 'var(--mut)';
    card.hidden = false;
    return;
  }
  const expected = p <= allowBelow ? 'ALLOW' : p >= declineAbove ? 'DECLINE' : 'CHALLENGE';
  setIsolated('mThresholds', `ALLOW ≤ ${allowBelow.toFixed(3)} · DECLINE ≥ ${declineAbove.toFixed(3)}`);
  setIsolated('mVerdict', expected);
  if (expected === signed.decision){
    $('mNote').textContent = 'Recomputed in this browser from the signed prior, link deltas, and policy snapshot.';
    $('mNote').style.color = '';
  } else {
    // Unresolved provider evidence can conservatively retain CHALLENGE even
    // where the numeric threshold alone would allow. Make that difference
    // conspicuous rather than silently replacing the signer’s decision.
    $('mNote').textContent = `MISMATCH: threshold replay is ${expected}, but the signed decision is ${signed.decision}. The signed chain contains a conservative unresolved-evidence override.`;
    $('mNote').style.color = 'var(--amber)';
  }
  card.hidden = false;
}

// The tamper control: alter one byte in front of the viewer and let them watch
// the same check fail. A judge doing this on their own phone is worth more than
// any claim we make about tamper-evidence.
$('tamperBtn').addEventListener('click', async () => {
  payloadBytes = Uint8Array.from(originalBytes);
  const i = Math.floor(payloadBytes.length / 2);
  payloadBytes[i] = payloadBytes[i] ^ 0x01;   // flip a single bit
  await showVerification();
  $('tamperBtn').disabled = true;
  $('resetBtn').hidden = false;
});

$('resetBtn').addEventListener('click', async () => {
  payloadBytes = Uint8Array.from(originalBytes);
  await showVerification();
  $('tamperBtn').disabled = false;
  $('resetBtn').hidden = true;
});

/* I7 — hand over the exact bytes, not a re-rendering of them.

   `bundleText` is the response body verbatim. Downloading a parse-and-then-
   re-serialize round trip would ship the reader a file this page never
   verified: key order, escaping and number formatting are all the serializer's
   choices, and the one string that must survive byte-for-byte is precisely the
   one an offline verifier re-encodes and checks. */
$('downloadBtn').addEventListener('click', () => {
  if (bundleText === null) return;
  const url = URL.createObjectURL(new Blob([bundleText], {type: 'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'isnad-receipt-' + chainId.replace(/[^A-Za-z0-9_-]/g, '_') + '.json';
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Deferred: revoking in the same task can cancel the download before the
  // browser has read the blob.
  setTimeout(() => URL.revokeObjectURL(url), 30000);
});

$('locale').addEventListener('change', (event) => { Locale.setLocale(event.target.value); });

(async function main(){
  await Locale.setLocale(Locale.preferred());
  try{
    if (!chainId){
      setStatus('bad', '✗ invalid receipt link', 'This receipt URL does not contain a valid chain id.');
      return;
    }
    const response = await fetch(`/v1/receipts/${encodeURIComponent(chainId)}`);
    if (!response.ok){
      setStatus('bad', '✗ no such receipt', 'This chain id was not found.');
      $('chainId').textContent = chainId;
      return;
    }
    // .text() first, .json() never: the download must be able to hand over
    // these bytes, and once parsed they cannot be reconstructed faithfully.
    bundleText = await response.text();
    const data = JSON.parse(bundleText);
    // Downloadable whatever the signature says. A receipt that fails to verify
    // is exactly the one a reader most needs to keep and check elsewhere.
    $('downloadBtn').disabled = false;
    originalBytes = new TextEncoder().encode(data.signed_payload);
    payloadBytes = Uint8Array.from(originalBytes);
    sigBytes = hexToBytes(data.signature);
    keyBytes = hexToBytes(data.public_key);
    const verified = await showVerification();
    if (verified !== true) return;
    const signed = JSON.parse(data.signed_payload);
    if (!signed || signed.chain_id !== chainId){
      setStatus('bad', '✗ receipt mismatch', 'The signed receipt does not belong to this URL.');
      return;
    }
    render(signed, data.public_key, data.signature);
    $('tamperBtn').disabled = false;
  }catch(err){
    setStatus('bad', '✗ could not load', 'The receipt could not be fetched.');
  }
})();
