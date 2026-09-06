/* I6 — the locale switch, shared by every page that has one.

   One implementation, not one per page. The rule that matters here is the
   fallback rule: an unknown key must produce the English string, visibly, and
   two copies of that rule are two chances for one page to quietly start
   showing a blank or a raw key instead.

   Locale is presentation only. Nothing in this file touches a verification
   request, a policy decision or a signed value, and the only request it makes
   is for a dictionary from this same origin. A translated phrase is always
   shown *beside* a signed token, never in place of it — see `codedInto`.

   Served from /ui/i18n.js: same origin, no CDN, no font host, consistent with
   the zero-external-origin rule these pages keep. */

const Isnad = (() => {
  const LOCALE_KEY = 'isnad.locale';
  const SUPPORTED = ['en', 'ar'];
  const dicts = {};
  const ORIGINAL_TEXT = new WeakMap();
  let activeLocale = 'en';
  let localeRequest = 0;
  let observer;
  const originalNodes = new WeakMap();
  const originalAttributes = new WeakMap();
  const listeners = [];

  const lookup = (dict, path) =>
    path.split('.').reduce((o, k) => (o && typeof o === 'object' ? o[k] : undefined), dict);

  async function loadDictionary(locale) {
    if (dicts[locale]) return;
    try {
      const response = await fetch(`/ui/i18n/${locale}.json`);
      if (response.ok) dicts[locale] = await response.json();
    } catch (_) { /* stay in English: the visible fallback is the point */ }
  }

  /* Unknown keys fall back to English *visibly*: the reader gets the English
     sentence — never a raw key and never a blank — and the element is marked
     lang="en" so assistive technology switches voice and a stylesheet can show
     that the string is untranslated rather than an editorial choice. */
  function applyText(el, path, literal, prefix) {
    const local = path ? lookup(dicts[activeLocale], path) : undefined;
    let value = local;
    let fellBack = false;
    if (typeof value !== 'string') {
      value = path ? lookup(dicts.en, path) : undefined;
      fellBack = true;
    }
    if (typeof value !== 'string') { value = literal; fellBack = true; }
    el.textContent = (prefix || '') + value;
    // Always stated, never merely cleared: a translated string sitting inside
    // an English-marked region would otherwise inherit the wrong language, and
    // a screen reader would read Arabic with English phonetics.
    el.setAttribute('lang', fellBack ? 'en' : activeLocale);
  }

  function applyDictionary(root) {
    (root || document).querySelectorAll('[data-i18n]').forEach(el => {
      if (!ORIGINAL_TEXT.has(el)) ORIGINAL_TEXT.set(el, el.textContent.trim());
      applyText(el, el.dataset.i18n, ORIGINAL_TEXT.get(el));
    });
  }

  /* LTR isolation for anything a signature covers. Under dir="rtl" the bidi
     algorithm reorders a bare chain id, hex digest, ISO timestamp or signed
     number at its neutral edges, and a reordered string is no longer the one
     the reader is being asked to compare. */
  function isolate(value) {
    const bdi = document.createElement('bdi');
    bdi.dir = 'ltr';
    bdi.textContent = value;          // textContent throughout: never markup
    return bdi;
  }

  /* One string, for text a page builds at runtime rather than authors in HTML.
     Falls back to English and then to the caller's own sentence, so a missing
     Arabic key degrades to readable English instead of a raw key. */
  function t(path, fallback) {
    const value = lookup(dicts[activeLocale] || {}, path);
    if (typeof value === 'string') return value;
    const english = lookup(dicts.en || {}, path);
    return typeof english === 'string' ? english : (fallback || '');
  }

  function setIsolated(el, value) {
    el.replaceChildren(isolate(value));
  }

  /* A signed enum shown as signed, LTR-isolated, with the translation beside
     it. Replacing "CHALLENGE" with a translated phrase would mean the page no
     longer displays the value the signature actually covers. */
  function codedInto(el, code, group) {
    el.replaceChildren(isolate(code));
    const path = group + '.' + code;
    const local = lookup(dicts[activeLocale], path);
    const phrase = typeof local === 'string' ? local : lookup(dicts.en, path);
    if (typeof phrase !== 'string') return;   // e.g. UNGRADED: the code stands alone
    const gloss = document.createElement('span');
    gloss.className = 'gloss';
    gloss.textContent = ' · ' + phrase;
    if (typeof local !== 'string' && activeLocale !== 'en') gloss.setAttribute('lang', 'en');
    el.appendChild(gloss);
  }

  /* Whatever a page must redraw after the language changes. Registered rather
     than hard-coded here, because this module has no business knowing what a
     receipt or a checkout looks like. */
  function onChange(fn) { listeners.push(fn); }

  async function setLocale(requested) {
    const request = ++localeRequest;
    const locale = SUPPORTED.includes(requested) ? requested : 'en';
    // English is the fallback dictionary, so it is loaded whatever the reader
    // chose. Without it, a key the Arabic dictionary is missing would fall
    // back to whatever the markup happened to say rather than to English.
    await Promise.all(locale === 'en'
      ? [loadDictionary('en')]
      : [loadDictionary('en'), loadDictionary(locale)]);
    if (request !== localeRequest) return activeLocale;
    activeLocale = dicts[locale] ? locale : 'en';
    document.documentElement.lang = activeLocale;
    document.documentElement.dir = activeLocale === 'ar' ? 'rtl' : 'ltr';
    applyDictionary();
    listeners.forEach(fn => fn(activeLocale));
    translatePage();
    const control = document.getElementById('isnadLanguage');
    if (control) control.value = activeLocale;
    try { localStorage.setItem(LOCALE_KEY, activeLocale); } catch (_) { /* private mode */ }
    return activeLocale;
  }

  function preferred() {
    try { return localStorage.getItem(LOCALE_KEY) || 'en'; } catch (_) { return 'en'; }
  }

  /* The review status of the *active* dictionary, or null. A machine-assisted
     translation has to say so on the page, not only in its JSON file. */
  function reviewStatus() {
    const dict = dicts[activeLocale];
    return (dict && dict.review_status) || null;
  }

  // Translate authored display text only. Never rewrite code, signed tokens,
  // identifiers, input values or the request payload. Exact matches keep
  // arbitrary provider/model prose out of the translation contract.
  const excluded = 'script,style,code,pre,bdi,textarea,[data-i18n],.gloss,[data-no-translate]';
  function translatePage() {
    if (!document.body) return;
    if (observer) observer.disconnect();
    const catalog = (dicts[activeLocale] || {}).text || {};
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent || parent.closest(excluded)) continue;
      const previous = originalNodes.get(node);
      const original = previous && node.nodeValue === previous.rendered
        ? previous.original : node.nodeValue;
      const key = original.trim().replace(/\s+/g, ' ');
      // Machine-readable state tokens may also be used by page logic.
      if (!key || /^[A-Z0-9_ .:/-]+$/.test(key)) continue;
      const translated = catalog[key];
      const rendered = typeof translated === 'string'
        ? original.replace(original.trim(), translated) : original;
      originalNodes.set(node, {original, rendered});
      if (node.nodeValue !== rendered) node.nodeValue = rendered;
      if (parent.childNodes.length === 1) {
        parent.lang = typeof translated === 'string' ? activeLocale : 'en';
        parent.dir = 'auto';
      }
    }
    document.body.querySelectorAll('[placeholder],[title],[aria-label]').forEach(el => {
      if (el.closest(excluded)) return;
      const records = originalAttributes.get(el) || {};
      ['placeholder','title','aria-label'].forEach(name => {
        const value = el.getAttribute(name);
        if (value === null) return;
        const previous = records[name];
        const original = previous && value === previous.rendered ? previous.original : value;
        const rendered = catalog[original] || original;
        records[name] = {original, rendered};
        if (value !== rendered) el.setAttribute(name, rendered);
      });
      originalAttributes.set(el, records);
    });
    if (observer) observer.observe(document.body, {subtree:true,childList:true,characterData:true});
  }

  function initializePage() {
    const style = document.createElement('style');
    style.textContent = `html[lang="ar"] body{font-family:Tahoma,Arial,sans-serif;line-height:1.7}
      html[dir="rtl"] th{text-align:start} html[dir="rtl"] input:not([type="checkbox"]),
      html[dir="rtl"] code,html[dir="rtl"] pre{direction:ltr;unicode-bidi:isolate}
      .isnad-language{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;
      padding:.5rem 1rem;margin-block-end:.5rem;font:14px/1.5 system-ui,sans-serif}
      .isnad-language select{width:auto;max-width:100%;padding:.25rem}
      .isnad-language small{max-width:38rem}`;
    document.head.appendChild(style);
    if (!document.getElementById('locale')) {
      const bar = document.createElement('div');
      bar.className = 'isnad-language';
      const label = document.createElement('label');
      label.htmlFor = 'isnadLanguage'; label.textContent = 'Language / اللغة';
      label.setAttribute('data-no-translate','');
      const select = document.createElement('select');
      select.id = 'isnadLanguage'; select.setAttribute('data-no-translate','');
      [['en','English'],['ar','العربية']].forEach(([value,text]) => {
        const option = document.createElement('option'); option.value=value;
        option.textContent=text; select.appendChild(option);
      });
      select.addEventListener('change', () => setLocale(select.value));
      const note = document.createElement('small'); note.setAttribute('data-no-translate','');
      onChange(() => { note.textContent = reviewStatus() || ''; });
      bar.append(label,select,note); document.body.prepend(bar);
      setLocale(preferred());
    }
    observer = new MutationObserver(() => translatePage());
    translatePage();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializePage);
  else initializePage();

  return {
    LOCALE_KEY, SUPPORTED, dicts, applyText, applyDictionary, t,
    isolate, setIsolated, codedInto, onChange, setLocale, preferred, reviewStatus,
    locale: () => activeLocale
  };
})();
