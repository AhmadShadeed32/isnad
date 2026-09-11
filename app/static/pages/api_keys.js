/* The judge's merchant-key page: one session, one code exchange, one key shown once. */
const mintForm = document.getElementById('mintForm');
const accessCode = document.getElementById('accessCode');
const mintButton = document.getElementById('mintButton');
const mintNote = document.getElementById('mintNote');
const issued = document.getElementById('issued');
const apiKeyEl = document.getElementById('apiKey');
const keyExpires = document.getElementById('keyExpires');
const keyList = document.getElementById('keyList');
const factNote = document.getElementById('factNote');

let judgeSession = null;
let capabilities = null;
let currentKey = null;

function say(key, fallback){ return window.Isnad ? window.Isnad.t('ui.' + key, fallback) : fallback; }
function el(tag, cls, text){
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;   // never markup assignment: S10
  return n;
}
function safeError(err){ return err && err.message ? err.message : say('ak_failed', 'The request did not complete.'); }
function setNote(node, key, fallback){ node.setAttribute('data-i18n', 'ui.' + key); node.textContent = say(key, fallback); node.removeAttribute('lang'); }
function plainNote(node, text){ node.removeAttribute('data-i18n'); node.textContent = text; }

async function apiJson(path, options = {}){
  // Only the judge session travels. This page carries no demo token and no
  // merchant key: the one it mints is handed to the reader, not kept.
  const judgeHeaders = judgeSession ? {'X-Judge-Session': judgeSession} : {};
  const response = await fetch(path, { ...options, headers:{...judgeHeaders, ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers || {})} });
  const data = await response.json().catch(() => ({}));
  if (!response.ok){
    const failure = new Error(data.detail?.message || data.detail?.code || 'request failed (' + response.status + ')');
    failure.status = response.status;
    throw failure;
  }
  return data;
}

function humanDuration(seconds){
  if (seconds >= 3600) return Math.round(seconds / 360) / 10 + ' h';
  if (seconds >= 60) return Math.round(seconds / 60) + ' min';
  return seconds + ' s';
}

function renderFacts(){
  const keys = (capabilities && capabilities.api_keys) || {};
  const provider = keys.provider || '—';
  document.getElementById('factProvider').textContent = provider === 'mock'
    ? say('ak_provider_mock', 'mock · Nokia-compatible demo. Nothing is sent to Nokia.')
    : provider;
  const planner = keys.planner_default || '—';
  document.getElementById('factPlanner').textContent = planner === 'llm'
    ? say('ak_planner_llm', 'Gemini · LLM. Add the X-Isnad-Planner: greedy header (already in the commands below) to reproduce the guide’s numbers.')
    : say('ak_planner_greedy', 'greedy · deterministic. Results match the guide as written.');
  document.getElementById('factTtl').textContent = keys.ttl_seconds ? humanDuration(keys.ttl_seconds) : '—';
  if (keys.available === false){
    factNote.hidden = false;
    setNote(factNote, 'ak_unavailable', 'This deployment does not issue keys from a page: its default provider makes billable calls. Use a configured merchant key.');
    mintButton.disabled = true; accessCode.disabled = true;
  }
}

function origin(){ return location.origin; }

function commands(key){
  const bearer = "  -H 'Authorization: Bearer " + key + "'";
  const verify = [
    'curl ' + origin() + '/v1/verify \\',
    bearer + ' \\',
    "  -H 'Content-Type: application/json' \\",
    "  -H 'X-Isnad-Planner: greedy' \\",
    "  -H 'Idempotency-Key: judge-test-1' \\",
    "  -d '{",
    '    "phone_number": "+99999991006",',
    '    "context": {',
    '      "event": "checkout",',
    '      "payment_method": "cod",',
    '      "account_age_days": 0,',
    '      "amount": {"value": 1500, "currency": "USD"},',
    '      "claimed_location": {"lat": 31.9539, "lon": 35.9106, "radius_m": 2000}',
    '    }',
    "  }'",
  ].join('\n');
  const chain = ['curl ' + origin() + '/v1/chains/CHAIN_ID \\', bearer].join('\n');
  const signature = ['curl ' + origin() + '/v1/chains/CHAIN_ID/verification \\', bearer].join('\n');
  return {verify, chain, signature};
}

function renderIssued(data){
  currentKey = data.api_key;
  apiKeyEl.textContent = data.api_key;
  keyExpires.textContent = humanDuration(data.expires_in_seconds);
  const cmd = commands(data.api_key);
  document.getElementById('cmdVerify').textContent = cmd.verify;
  document.getElementById('cmdChain').textContent = cmd.chain;
  document.getElementById('cmdSignature').textContent = cmd.signature;
  issued.hidden = false;
  issued.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function renderList(keys){
  keyList.textContent = '';
  if (!keys.length){
    keyList.appendChild(el('p', 'why', say('ak_list_empty', 'None yet.')));
    return;
  }
  keys.forEach(k => {
    const row = el('div', 'kv');
    row.appendChild(el('code', 'prefix', k.prefix));
    row.appendChild(el('span', null, say('ak_expires', 'Expires in') + ' ' + humanDuration(k.expires_in_seconds)));
    keyList.appendChild(row);
  });
}

async function refreshList(){
  try{
    const data = await apiJson('/v1/judge/api-keys');
    renderList(data.keys || []);
  }catch(_){ /* the list is a convenience; the key on screen is the deliverable */ }
}

async function mint(event){
  event.preventDefault();
  const code = (accessCode.value || '').trim();
  if (!code) return;
  mintButton.disabled = true;
  setNote(mintNote, 'ak_checking', 'Checking the access code…');
  try{
    const data = await apiJson('/v1/judge/api-keys', {method:'POST', body:JSON.stringify({access_code: code})});
    // Never kept in the page after it has been exchanged.
    accessCode.value = '';
    capabilities = data.capabilities;
    setNote(mintNote, 'ak_minted', 'Key issued. It is shown once, below.');
    renderIssued(data);
    await refreshList();
  }catch(err){
    // The server's refusal, verbatim: which of several reasons applied matters.
    plainNote(mintNote, safeError(err));
  }finally{
    mintButton.disabled = false;
  }
}

async function copyText(text, button){
  const original = button.textContent;
  try{
    await navigator.clipboard.writeText(text);
    button.textContent = say('ak_copied', 'Copied');
  }catch(_){
    button.textContent = say('ak_copy_failed', 'Select and copy manually');
  }
  setTimeout(() => { button.textContent = original; }, 1800);
}

mintForm.addEventListener('submit', mint);
document.getElementById('copyKey').addEventListener('click', (e) => { if (currentKey) copyText(currentKey, e.currentTarget); });
document.querySelectorAll('button.copy').forEach(button => {
  button.addEventListener('click', () => copyText(document.getElementById(button.dataset.for).textContent, button));
});

(async function configure(){
  try{
    const data = await apiJson('/v1/judge/session', {method:'POST'});
    judgeSession = data.session;
    capabilities = data.capabilities;
    renderFacts();
    await refreshList();
  }catch(err){
    plainNote(factNote, say('ak_session_failed', 'Could not start a judge session:') + ' ' + safeError(err));
    factNote.hidden = false;
    mintButton.disabled = true; accessCode.disabled = true;
  }
}());
