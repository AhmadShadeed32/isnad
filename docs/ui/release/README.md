# Release UI captures

Every file here is written by the Playwright suite in `tests/browser/` on each
`make test` run. They are not hand-curated marketing shots and they cannot
drift from the build: if the UI changes and these do not, the diff says so.

Naming is `page-language-state-width.png`.

- **Languages** — `en` and `ar`. The Arabic captures show the full RTL layout
  with translated chrome, headings, panels and merchant copy. **The composed
  verdict paragraph and the per-link evidence sentences are still English**:
  the dictionary covers authored strings, and those sentences are assembled
  server-side from policy state. The page carries its own banner saying the
  Arabic is a draft pending human review. Layout is verified; coverage is not
  complete, and the capture is the evidence of exactly that.
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
