'use strict';
/* Deterministic renderer: setT(t) fully describes the frame. No CSS transitions,
   no requestAnimationFrame — the capture script steps time by hand.

   Every beat is ANCHORED TO A NARRATION LINE, never to a hardcoded second, so
   changing the voice, the speed or the wording of a line re-times the whole
   video from timings.json. Anchor grammar, used in `data-*` attributes and in
   A() below:

     s5b        the moment line s5b starts
     s5b+1.2    1.2 s after it starts
     s5b-0.3    0.3 s before it starts
     s5b@0.55   55% of the way through it
     s5b$0.4    0.4 s after it ends   (s5b$-2 = 2 s before it ends)
*/

const $ = id => document.getElementById(id);
const cl = (x, a, b) => Math.max(a, Math.min(b, x));
const ease = x => 1 - Math.pow(1 - cl(x, 0, 1), 3);
const easeIO = x => { x = cl(x, 0, 1); return x < .5 ? 4*x*x*x : 1 - Math.pow(-2*x+2, 3)/2; };

/* ---------- the narration index ---------- */
const L = {};
for (const c of window.CAPTIONS) L[c.id] = { start: c.start, dur: c.dur, end: c.start + c.dur };

function A(spec) {
  if (typeof spec === 'number') return spec;
  const m = /^([a-z]\d[a-z])([+\-@$])?(-?[\d.]+)?$/.exec(String(spec).trim());
  if (!m) throw new Error('bad anchor: ' + spec);
  const l = L[m[1]];
  if (!l) throw new Error('unknown line: ' + m[1]);
  const v = m[3] === undefined ? 0 : parseFloat(m[3]);
  switch (m[2]) {
    case '+': return l.start + v;
    case '-': return l.start - v;
    case '@': return l.start + l.dur * v;
    case '$': return l.end + v;
    default:  return l.start;
  }
}
const TOTAL = A('s9b$2.8');

const SCENES = [
  ['sc1', 0,           A('s2a-0.28')],
  ['sc2', A('s2a-0.28'), A('s3a-0.28')],
  ['sc3', A('s3a-0.28'), A('s4a-0.28')],
  ['app', A('s4a-0.28'), A('s7a-0.28')],
  ['sc7', A('s7a-0.28'), A('s8a-0.28')],
  ['sc8', A('s8a-0.28'), A('s9a-0.28')],
  ['sc9', A('s9a-0.28'), TOTAL],
];
const SCENE_START = {}; for (const [id, s] of SCENES) SCENE_START[id] = s;

/* ---------- one-time DOM build ---------- */
for (let i = 0; i < 10; i++) {
  const d = document.createElement('div');
  d.className = 'person anim';
  d.dataset.in = `s3a@${(0.30 + i * 0.045).toFixed(3)}`;
  d.innerHTML = '<span>&#9679;</span><i>!</i>';
  $('people').appendChild(d);
}
for (let i = 0; i < 7; i++) {
  const d = document.createElement('div');
  d.className = 'tile anim';
  d.dataset.in = `s8a+${(1.2 + i * 0.14).toFixed(2)}`;
  d.textContent = String(i + 1).padStart(2, '0');
  $('tiles').appendChild(d);
}
const HIT = [3];   // the one two-signal case allowed at allow_below 0.15
const KEPT = -1;   // none remain allowed after moving to allow_below 0.05

/* resolve every anchored attribute to a scene-local number, once */
for (const [id, start] of SCENES) {
  for (const el of $(id).querySelectorAll('[data-in],[data-t],[data-stamp]')) {
    for (const k of ['in', 't', 'stamp']) {
      const v = el.dataset[k];
      if (v !== undefined && /^[a-z]/.test(v)) el.dataset[k] = (A(v) - start).toFixed(3);
    }
  }
}

/* ---------- trace rows ---------- */
const P_SIM = 'SIMULATOR · mock fixture', P_LIVE = 'RECORDED · Nokia NaC capture';
const GREEDY = 'greedy: highest information-per-cost option still affordable';
const ROWS_A = [   // Act III — approve the invisible
  ['s5a+1.8', 'info', 'Agent selects number_verify', GREEDY, null, 'greedy · budget 12'],
  ['s5a+3.2', 'pass', 'Number Verification', 'network number matches the provided number', P_SIM,
   'policy score 0.191 · 45 ms'],
  ['s5b+0.7', 'info', 'Agent selects sim_swap', GREEDY, null, 'greedy · budget 11'],
  ['s5b+2.1', 'pass', 'SIM Swap', 'no SIM swap in the last 240 h', P_SIM, 'policy score 0.096 · 90 ms'],
  ['s5c+0.3', 'info', 'Agent stops', 'enough evidence gathered — the allow rests on a network fact',
   null, 'policy · budget 9 unspent'],
];
const ROWS_B = [   // Act VI — legitimate SIM replacement, all rows explicitly simulated
  ['s6a+1.5', 'pass', 'Number Verification', 'network number matches the provided number', P_SIM,
   'policy score 0.191 · 45 ms'],
  ['s6a+2.7', 'flag', 'SIM Swap', 'SIM swap inside the last 240 h', P_SIM,
   'policy score 0.681 · 90 ms'],
  ['s6b+0.7', 'info', 'Policy keeps investigating',
   'a SIM change cannot carry a decline without exculpatory checks', null, 'policy · budget 9'],
  ['s6b+2.2', 'pass', 'Device Swap', 'no device swap in the last 240 h', P_SIM,
   'policy score 0.564 · 135 ms'],
  ['s6b+4.0', 'pass', 'Location Verification', 'device is at the claimed location', P_SIM,
   'policy score 0.280 · 45 ms'],
  ['s6b+6.0', 'info', 'Device Roaming Status', 'device is roaming', P_SIM,
   'policy score 0.322 · 135 ms'],
  ['s6b+8.0', 'pass', 'Device Reachability Status', 'device reachable via SMS', P_SIM,
   'policy score 0.242 · 90 ms'],
  ['s6c-1.0', 'info', 'Agent stops with CHALLENGE',
   'adverse evidence remains, so the merchant should step up', null, 'greedy · budget exhausted'],
];
function buildRow(r) {
  const [, kind, title, detail, prov, meta] = r;
  const el = document.createElement('div');
  el.className = 'trow ' + kind;
  const badge = prov
    ? `<span class="prov ${prov === P_LIVE ? 'live' : 'sim'}">${prov}</span>` : '';
  el.innerHTML =
    `<div class="mk">${kind === 'pass' ? '✓' : kind === 'flag' ? '!' : '·'}</div>` +
    `<div><div class="ttl">${title}</div><div class="tdt">${detail}</div>${badge}</div>` +
    `<div class="tmeta">${meta}</div>`;
  el.dataset.at = A(r[0]);
  if (prov === P_LIVE) el.dataset.live = '1';
  return el;
}
const listA = ROWS_A.map(buildRow), listB = ROWS_B.map(buildRow);

/* ---------- app-scene beats ---------- */
const B = {
  curIn:   A('s4b+0.8'),  curMove: A('s4b+1.1'),  click: A('s4b+3.6'),
  curOut:  A('s4b+4.8'),  start:   A('s4b+3.7'),
  hypoA:   A('s5a+0.2'),  evidA:   A('s5a+3.2'),
  verdictA:A('s5c+1.7'),  rcptA:   A('s5c+3.1'),
  reset:   A('s6a+0.15'), hypoB:   A('s6a+1.7'),
  selB:    A('s6b+0.9'),  evidB:   A('s6b+2.1'),
  verdictB:A('s6c+0.5'),  rcptB:   A('s6c+1.7'), arith: A('s6c+2.3'),
};
B.arithOut = SCENES[3][2] - 0.9;

const capEl = $('cap');

/* ---------- generic reveal ---------- */
function reveal(el, lt, t0, dy) {
  const k = ease((lt - t0) / 0.55);
  el.style.opacity = k;
  el.style.transform = `translateY(${(1 - k) * (dy === undefined ? 16 : dy)}px)`;
}
function sceneGeneric(root, lt) {
  root.querySelectorAll('.anim').forEach(el => reveal(el, lt, parseFloat(el.dataset.in || 0)));
  root.querySelectorAll('[data-count]').forEach(el => {
    const t0 = parseFloat(el.dataset.t), to = parseInt(el.dataset.count, 10);
    const k = easeIO((lt - t0) / 1.5);
    el.textContent = (el.dataset.lit ? 1 : Math.round(to * k)) + (el.dataset.suffix || '');
  });
  root.querySelectorAll('[data-w]').forEach(el => {
    const t0 = parseFloat(el.dataset.t), w = parseFloat(el.dataset.w);
    el.style.width = (easeIO((lt - t0) / 1.5) * w) + '%';
  });
  root.querySelectorAll('[data-stamp]').forEach(el => {
    const t0 = parseFloat(el.dataset.stamp), k = ease((lt - t0) / 0.28);
    el.style.opacity = k;
    el.style.transform = `scale(${1.35 - 0.35 * k}) rotate(${-3 + 3 * k}deg)`;
  });
}

/* ---------- the app scene ---------- */
function app(lt, t) {
  const list = $('tracelist');
  const phaseB = t >= B.reset;

  if (phaseB) {
    $('modepill').className = 'pill sim';
    $('modepill').textContent = 'SIMULATOR · mock provider · stage mode';
    $('chkmeta').textContent = 'Legitimate replacement-SIM checkout';
    $('chkbasket').textContent = 'Home essentials';
    $('chktotal').textContent = '1,500 USD';
    $('chklede').textContent = 'The customer replaced her SIM. Isnad investigates the adverse signal ' +
      'instead of turning it directly into a decline.';
  } else {
    $('modepill').className = 'pill sim';
    $('modepill').textContent = 'SIMULATOR · mock provider · stage mode';
    $('chkmeta').textContent = 'Cross-border COD checkout';
    $('chkbasket').textContent = 'Home essentials';
    $('chktotal').textContent = '1,500 USD';
    $('chklede').textContent = 'A new customer has no merchant history. Instead of interrupting ' +
      'them with an OTP, Noura asks Isnad for only the evidence needed to make this decision.';
  }

  const want = phaseB ? listB : listA;
  if (list.firstChild !== want[0]) list.replaceChildren(...want);

  let shown = 0;
  want.forEach(el => {
    const at = parseFloat(el.dataset.at), k = ease((t - at) / 0.45);
    el.style.opacity = k; el.style.transform = `translateY(${(1 - k) * 12}px)`;
    if (k > 0.02) shown++;
    if (el.dataset.live) {
      const g = Math.max(0, 1 - Math.abs(((t - at - 1.2) % 2.4) - 1.2) / 1.2);
      const on = t > at && t < at + 7.5 ? g : 0;
      el.style.boxShadow = `0 0 ${18 * on}px rgba(86,211,160,${0.30 * on})`;
      el.style.borderColor = on > .3 ? '#2c6b56' : '#4a2b3c';
    }
  });
  // auto-scroll, exactly as the real console does — but only past rows that
  // have actually been revealed, or the list starts scrolled to a future row.
  const vh = $('trace').clientHeight;
  let bottom = 0;
  want.forEach(el => { if (parseFloat(el.style.opacity) > 0.02) bottom = el.offsetTop + el.offsetHeight; });
  list.style.transform = `translateY(${-Math.max(0, bottom - vh)}px)`;

  const S = phaseB
    ? [[B.reset, 'Ready for checkout.'],
       [B.hypoB, 'Agent formed an account_takeover hypothesis. Prior policy risk score: 0.440.'],
       [B.selB,  'Agent selected the next check from the remaining evidence budget.'],
       [B.evidB, 'Evidence received with its source and result.'],
       [B.verdictB, 'Decision complete. The receipt below contains the signed evidence chain.']]
    : [[SCENE_START.app, 'Ready for checkout.'],
       [B.start, 'Starting a deterministic, simulated checkout fixture…'],
       [B.hypoA, 'Agent formed an account_takeover hypothesis. Prior policy risk score: 0.440.'],
       [B.evidA, 'Evidence received with its source and result.'],
       [B.verdictA, 'Decision complete. The receipt below contains the signed evidence chain.']];
  let msg = S[0][1];
  for (const [at, m] of S) if (t >= at) msg = m;
  $('statusline').textContent = msg;

  const done = phaseB ? t >= B.verdictB : t >= B.verdictA;
  for (let i = 0; i < 4; i++) {
    const pip = $('st' + i);
    if (done) pip.style.background = (i === 3 && phaseB) ? 'var(--red)' : 'var(--green)';
    else pip.style.background = i < Math.min(4, Math.ceil(shown / 2)) ? 'var(--gold)' : '#26325b';
  }
  $('plannerpill').textContent = (t >= B.hypoA) ? 'planner: greedy' : 'planner: —';

  const dec = $('dec'), rsn = $('rsn'), grade = $('grade');
  if (phaseB) {
    if (t >= B.verdictB) {
      dec.textContent = 'CHALLENGE'; dec.className = 'dec VERIFYING';
      rsn.textContent = 'Recent SIM change remains adverse, while the stable handset and location ' +
        'argue against an automatic decline.';
      grade.textContent = 'chain grade: DEGRADED · 6 evidence steps · evidence cost 12.0 of 12';
    } else {
      dec.textContent = 'VERIFYING'; dec.className = 'dec VERIFYING';
      rsn.textContent = 'The agent is deciding what evidence it needs.'; grade.textContent = '';
    }
  } else if (t >= B.verdictA) {
    dec.textContent = 'ALLOW'; dec.className = 'dec ALLOW';
    rsn.textContent = 'Cleared by: network number matches the provided number, no SIM swap in the last 240 h.';
    grade.textContent = 'chain grade: ATTESTED_FULL · 2 evidence steps · evidence cost 3.0 of 12 · 1302 ms';
  } else if (t >= B.start) {
    dec.textContent = 'VERIFYING'; dec.className = 'dec VERIFYING';
    rsn.textContent = 'The agent is deciding what evidence it needs.'; grade.textContent = '';
  } else {
    dec.textContent = '—'; dec.className = 'dec';
    rsn.textContent = 'No evidence chain yet.'; grade.textContent = '';
  }
  $('rcpt').style.opacity = (!phaseB && t >= B.rcptA) ? ease((t - B.rcptA) / 0.5)
    : (phaseB && t >= B.rcptB) ? ease((t - B.rcptB) / 0.5) : 0;

  // cursor + click
  const cur = $('cursor'), cta = $('cta');
  const r = cta.getBoundingClientRect();
  const cx = r.left + r.width * 0.5, cy = r.top + r.height * 0.55;
  const k = easeIO((t - B.curMove) / 2.3);
  cur.style.opacity = t > B.curIn && t < B.curOut + 0.9
    ? ease((t - B.curIn) / 0.3) * (1 - ease((t - B.curOut) / 0.7)) : 0;
  cur.style.left = (1180 + (cx - 1180) * k) + 'px';
  cur.style.top = (620 + (cy - 620) * k) + 'px';
  cta.style.transform = (t >= B.click && t < B.click + 0.35) ? 'scale(.975)' : 'scale(1)';
  cta.style.filter = (t >= B.click && t < B.click + 0.9) ? 'brightness(1.18)' : 'none';
  const running = (t >= B.start && t < B.verdictA) || (t >= B.reset && t < B.verdictB);
  cta.style.opacity = running ? 0.55 : 1;
  cta.textContent = running ? 'Verifying…' : phaseB ? 'Investigate the SIM change' : 'Try a clean checkout';

  // the arithmetic panel — takes over the (now irrelevant) checkout column
  const a = $('arith');
  const av = t >= B.arith ? ease((t - B.arith) / 0.6) * (1 - ease((t - B.arithOut) / 0.7)) : 0;
  a.style.opacity = av;
  a.style.transform = `translateY(${(1 - ease((t - B.arith) / 0.6)) * 20}px)`;
  document.querySelector('.chk').style.opacity = 1 - 0.88 * av;
}

/* ---------- scene 7 : receipt + tamper ---------- */
const T7 = { panel: A('s7b+0.15'), flip: A('s7b+1.15'), fail: A('s7b+1.70') };
function sc7(t) {
  const tampered = t >= T7.flip;
  $('tamperval').textContent = tampered
    ? 'SIM swap inside the last 241 h' : 'SIM swap inside the last 240 h';
  $('tamperval').style.color = tampered ? 'var(--red)' : '';
  const st = $('rstat');
  if (t >= T7.fail) {
    st.className = 'rstat bad anim';
    st.textContent = 'Illustration: changed bytes fail verification';
  } else {
    st.className = 'rstat anim';
    st.textContent = 'Illustration: original receipt verifies';
  }
  $('sighex').style.color = t >= T7.fail ? 'var(--red)' : 'var(--gold)';
  const tp = $('tamper');
  tp.style.opacity = t >= T7.panel ? ease((t - T7.panel) / 0.5) : 0;
  tp.style.transform = `translateY(${(1 - ease((t - T7.panel) / 0.5)) * 18}px)`;
}

/* ---------- scene 8 : the dial ---------- */
const T8 = { hit: A('s8a$-2.4'), move: A('s8b+1.5') };
function sc8(t) {
  const tiles = $('tiles').children;
  const moved = easeIO((t - T8.move) / 2.0);
  for (let i = 0; i < 7; i++) {
    const isHit = HIT.includes(i);
    const at = T8.hit + HIT.indexOf(i) * 0.19;
    const on = isHit && t >= at ? (i === KEPT ? 1 : 1 - moved) : 0;
    tiles[i].className = 'tile anim' + (on > 0.5 ? ' hit' : '');
  }
  $('knob').style.left = `calc(${moved * 100}% - ${moved * 34}px)`;
}

/* ---------- master ---------- */
const END = A('s9b$1.1');
function setT(t) {
  let capText = '', capOp = 0;
  for (const c of window.CAPTIONS) {
    if (t >= c.start - 0.18 && t <= c.start + c.dur + 0.42) {
      capText = c.text;
      capOp = ease((t - c.start + 0.18) / 0.28) * (1 - ease((t - c.start - c.dur - 0.08) / 0.32));
    }
  }
  capEl.textContent = capText;
  capEl.style.opacity = capOp;

  for (const [id, s, e] of SCENES) {
    const el = $(id), on = t >= s - 0.5 && t < e + 0.5;
    el.classList.toggle('on', on);
    if (!on) continue;
    const lt = t - s;
    const fi = ease((t - s) / 0.5), fo = 1 - ease((t - (e - 0.42)) / 0.42);
    el.style.opacity = Math.min(fi, fo);
    if (id === 'app') app(lt, t);
    else {
      sceneGeneric(el, lt);
      if (id === 'sc7') sc7(t);
      if (id === 'sc8') sc8(t);
    }
  }
  $('endcard').style.opacity = t >= END ? ease((t - END) / 1.0) : 0;
}
window.setT = setT;
window.TOTAL = TOTAL;
setT(0);
