const out = document.getElementById('out');

function el(tag, cls, text){
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;   // never innerHTML: S10
  return n;
}

function section(title){ out.appendChild(el('h2', null, title)); }

function card(){ const c = el('div','card'); out.appendChild(c); return c; }

function kv(parent, k, v, cls){
  const grid = el('div','kv');
  grid.appendChild(el('span','k',k));
  grid.appendChild(el('span', cls || null, v));
  parent.appendChild(grid);
}

fetch('/v1/privacy/posture').then(r => r.json()).then(d => {
  out.textContent = '';

  section('The subject');
  const s = card();
  kv(s, 'binding', d.subject_binding.method);
  kv(s, 'stored', d.subject_binding.stored, 'yes');
  kv(s, 'not stored', d.subject_binding.not_stored, 'no');

  section('The evidence');
  const e = card();
  kv(e, 'normalized', d.evidence.normalized);
  kv(e, 'consent', d.evidence.consent_recorded_per_link
      ? 'recorded on every link, inside the signed bytes' : 'not recorded', 'yes');
  kv(e, 'bases in use', d.evidence.consent_bases_in_use.join(' · '));

  section('Retention');
  d.retention.forEach(w => {
    const c = card();
    kv(c, w.name, '');
    c.appendChild(el('div','win', w.human));
    c.appendChild(el('p','why', w.why));
  });
  const sw = card();
  kv(sw, 'sweeper', d.sweeper.enabled
      ? 'running every ' + d.sweeper.interval_seconds + 's' : 'DISABLED',
      d.sweeper.enabled ? 'yes' : 'err');
  sw.appendChild(el('p','why', d.sweeper.note));

  section('What this page is not');
  const l = card(); const ul = el('ul');
  d.limits.forEach(t => ul.appendChild(el('li', null, t)));
  l.appendChild(ul);
}).catch(() => {
  out.textContent = '';
  out.appendChild(el('p','err','Could not read the posture endpoint.'));
});
