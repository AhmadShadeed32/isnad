/* One tab-scoped key, shared by the site's navigation pages. */
window.IsnadKey = (() => {
  const store = 'isnad.byok.gemini';
  const plannerStore = 'isnad.planner';
  let enabled = false;
  let serverGemini = false;
  let feedback = '';
  const read = () => { try { return sessionStorage.getItem(store) || ''; } catch { return ''; } };
  const choice = () => {
    try {
      const saved = sessionStorage.getItem(plannerStore);
      if (saved === 'greedy') return 'greedy';
      // A configured site key makes Gemini the default for a new tab. An
      // explicit Greedy choice remains sticky for that tab.
      //
      // `saved === 'llm'` was a third disjunct here and had to go. Saving a key
      // writes `isnad.planner = 'llm'`, and forgetting the key does not clear
      // it — so after "Forget key" on a deployment with no site key, every
      // model request still went out claiming `X-Isnad-Planner: llm` with no
      // credential anywhere to honour it. The server then builds an LLMPlanner
      // that finds no client and falls through to greedy, so the request
      // advertised a planner that could not run.
      //
      // LLM is available exactly when a key exists — the site's or the
      // reader's. Nothing is lost: the only way to have chosen it was to have
      // one, and if it is gone the choice is gone with it.
      return (serverGemini || read()) ? 'llm' : 'greedy';
    } catch { return serverGemini ? 'llm' : 'greedy'; }
  };
  const mount = document.getElementById('sharedGemini');
  const text = (key, fallback) => window.Isnad ? window.Isnad.t('ui.' + key, fallback) : fallback;
  // Built from DOM nodes, never by assigning markup (S10). This template is
  // static and interpolates nothing, but the rule is a blanket one precisely so
  // nobody has to audit each new template to decide whether it is the dangerous
  // kind — and the guard test matches on the property name, so even naming it
  // in a comment trips it. That strictness is the point.
  //
  // The one external reference is an anchor to Google AI Studio, so a reviewer
  // can get a key. That is a navigation, not a load: the page still fetches
  // nothing from outside, still works in a locked-down venue, and the CSP is
  // untouched. Loads (`src`) remain forbidden.
  const el = (tag, props = {}, kids = []) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
      if (k === 'dataset') Object.assign(node.dataset, v);
      else if (k in node) node[k] = v;
      else node.setAttribute(k, v);
    }
    for (const kid of kids) node.append(kid);
    return node;
  };
  const i18n = (key, fallback, tag = 'span', props = {}) =>
    el(tag, {...props, textContent: fallback, dataset: {i18n: 'ui.' + key}});

  if (mount) {
    const plannerBar = el('div', {className: 'planner-bar'}, [
      i18n('planner_label', 'Planner', 'label', {htmlFor: 'plannerChoice'}),
      el('select', {id: 'plannerChoice', disabled: true}, [
        i18n('planner_greedy', 'Greedy · deterministic', 'option', {value: 'greedy'}),
        i18n('planner_llm', 'Gemini · LLM', 'option', {value: 'llm'}),
      ]),
      i18n('planner_scope',
           'Applies to your next investigation. Lab recordings stay unchanged.'),
    ]);

    const body = el('div', {className: 'site-key-body'}, [
      i18n('key_scope',
           'One key for Checkout, Console, and Lab model runs in this browser '
           + 'tab. Viewing recordings does not call Gemini.', 'p'),
      el('form', {id: 'byokForm', className: 'site-key-actions'}, [
        i18n('key_label', 'Your Gemini key', 'label', {htmlFor: 'byokKey'}),
        el('input', {id: 'byokKey', type: 'password', autocomplete: 'off',
                     spellcheck: false, placeholder: 'AIza…', disabled: true,
                     'aria-describedby': 'byokPromise'}),
        i18n('key_save', 'Save key', 'button', {id: 'byokUse', type: 'submit',
                                                disabled: true}),
        i18n('key_forget', 'Forget key', 'button', {id: 'byokForget',
                                                    type: 'button'}),
      ]),
      i18n('key_privacy',
           'Stored in this tab’s session storage. Sent to this app’s server for '
           + 'model requests, then to Google. The app does not write it to its '
           + 'database, receipts, or logs. Calls use your saved key’s quota, or '
           + 'the site key when none is saved.', 'p', {id: 'byokPromise'}),
      el('p', {}, [i18n('key_get', 'Get a key from Google AI Studio', 'a', {
        id: 'googleStudioLink',
        href: 'https://aistudio.google.com/apikey',
        target: '_blank',
        rel: 'noopener noreferrer',
      })]),
      el('p', {id: 'byokFeedback', role: 'status'}),
    ]);

    const details = el('details', {className: 'site-key', id: 'byok'}, [
      el('summary', {}, [i18n('key_title', 'Gemini API key'),
                         el('span', {id: 'byokState', role: 'status'})]),
      body,
    ]);

    mount.replaceChildren(plannerBar, details);
  }
  function render() {
    if (!mount) return;
    const saved = !!read();
    document.getElementById('plannerChoice').value = choice();
    document.getElementById('plannerChoice').disabled = !enabled;
    document.getElementById('byokState').textContent = saved
      ? text('key_saved', 'Saved · connection unverified')
      : serverGemini ? text('key_server', 'Site Gemini key available · no personal key needed') : text('key_unset', 'No key saved');
    document.getElementById('byokForget').disabled = !saved;
    document.getElementById('byokUse').disabled = !enabled;
    document.getElementById('byokKey').disabled = !enabled;
    document.getElementById('byokFeedback').textContent = feedback ? text(...feedback) : '';
  }
  if (mount) {
    document.getElementById('plannerChoice').addEventListener('change', event => {
      if (event.target.value === 'llm' && !read() && !serverGemini) {
        feedback = ['planner_key_needed', 'Save a Gemini key to enable LLM mode.'];
        document.getElementById('byok').open = true;
        document.getElementById('byokKey').focus();
        render(); return;
      }
      try { sessionStorage.setItem(plannerStore, event.target.value); feedback = ''; }
      catch { feedback = ['key_storage_error', 'Could not save the key. Allow session storage and try again.']; }
      render();
    });
    document.getElementById('byokForm').addEventListener('submit', event => {
      event.preventDefault();
      if (!enabled) return;
      const input = document.getElementById('byokKey');
      const value = input.value.trim();
      if (!/^[\x21-\x7e]{1,200}$/.test(value)) {
        feedback = ['key_invalid', 'Enter a key without spaces, up to 200 characters.']; render(); return;
      }
      try { sessionStorage.setItem(store, value); sessionStorage.setItem(plannerStore, 'llm'); }
      catch { feedback = ['key_storage_error', 'Could not save the key. Allow session storage and try again.']; render(); return; }
      input.value = '';
      feedback = ['key_next', 'Ready for your next investigation. The trace will show model selections or errors.'];
      render();
    });
    document.getElementById('byokForget').addEventListener('click', () => {
      try { sessionStorage.removeItem(store); }
      catch { feedback = ['key_forget_error', 'Could not remove the saved key. Clear this site’s session storage.']; render(); return; }
      document.getElementById('byokKey').value = '';
      feedback = ['key_forgotten', 'Key removed. Requests already in progress may finish.']; render();
    });
    render();
    document.addEventListener('DOMContentLoaded', () => {
      if (window.Isnad) window.Isnad.onChange(render);
      render();
    });
  }
  const ready = fetch('/ui/settings.json')
    .then(response => { if (!response.ok) throw new Error('Settings unavailable'); return response.json(); })
    .then(data => {
      enabled = data.accepts_request_key === true;
      serverGemini = data.server_gemini_available === true;
      if (!enabled) feedback = ['key_disabled', 'Personal keys are disabled on this deployment.'];
      render();
    })
    .catch(() => { feedback = ['key_unavailable', 'Could not check key support. Reload to try again.']; render(); });
  function headers(path) {
    const url = new URL(path, location.href);
    // Never attach a credential to external links, recordings, assets, or polling.
    const modelRequest = /^\/v1\/(console\/run\/|lab\/run\/|verify$|reverse-verify$|chains\/[^/]+\/explain$|consents\/[^/]+\/verify$)/.test(url.pathname);
    if (!enabled || !modelRequest || url.origin !== location.origin) return {};
    const planner = choice();
    return {'X-Isnad-Planner': planner, ...(planner === 'llm' && read() ? {'X-Isnad-Gemini-Key': read()} : {})};
  }
  return {headers, ready};
})();
