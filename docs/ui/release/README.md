# Release UI captures

Every file here is written by the Playwright suite in `tests/browser/` on each
`make test` run. They are not hand-curated marketing shots and they cannot
drift from the build: if the UI changes and these do not, the diff says so.

Naming is `page-language-state-width.png`.

- **Languages** — `en` and `ar`. The Arabic captures are the RTL layout with
  translated verdict prose. Arabic wording remains a draft pending native
  review; the layout is verified.
- **Widths** — `1440` desktop, `375` mobile.
- **Pages** — `judge`, `console`, `lab`, `receipt`, `consent-complete`,
  `privacy`, `network-conditions`.
- **States** — `initial`, plus the interesting ones: `replacement` (the lead
  CHALLENGE), `clean` (ALLOW after two checks), `gap` (unresolved evidence),
  `after-checkout` (the continuity session), `connected` (console with a live
  stream), `case` (a selected lab recording), `valid` / `unavailable` for
  receipts, and `forecast` for network conditions.

The README's hero image is
[`judge-en-replacement-1440.png`](judge-en-replacement-1440.png); its Arabic
counterpart is [`judge-ar-replacement-1440.png`](judge-ar-replacement-1440.png).

To regenerate:

```bash
.venv311/bin/python -m playwright install chromium
.venv311/bin/python -m pytest -q tests/browser
```
