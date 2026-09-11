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
- **Pages** — `judge`, `api-keys`, `console`, `lab`, `receipt`, `consent-complete`,
  `privacy`, `network-conditions`. The `network-conditions-*` captures are of
  the panel on **`/console`**: it moved there from `/judge` on 8 September 2026,
  because it describes the network rather than a person, never touches a
  verdict, and on the checkout page it pushed the primary action below the
  first screen.
- **The Evidence source panel** is in every `judge-*` capture, at the top of the
  checkout card, because it is now the first choice a judge makes. In these
  captures it reads *"Real NaC is not enabled on this deployment. Mock evidence
  is unaffected"* and the real radio is disabled: they are taken with the test
  configuration, and a capture must never imply the public deployment offers a
  Nokia path it does not. The three authored stories moved below the basket
  under **Custom mock scenarios**, with the label saying they are teaching
  fixtures rather than Nokia contracts.
- **States** — `initial`, plus the interesting ones: `replacement` (the lead
  CHALLENGE), `clean` (ALLOW after two checks), `gap` (unresolved evidence),
  `after-checkout` (the continuity session), `connected` (console with a live
  stream), `case` (a selected lab recording), `valid` / `unavailable` for
  receipts, `forecast` for network conditions, and `issued` for the API-keys
  page after a key has been minted with the test configuration's code: the
  key in the capture is a throwaway from that run and authorizes nothing.

The README's hero image is
[`judge-en-replacement-1440.png`](judge-en-replacement-1440.png); its Arabic
counterpart is [`judge-ar-replacement-1440.png`](judge-ar-replacement-1440.png).

To regenerate:

```bash
.venv311/bin/python -m playwright install chromium
.venv311/bin/python -m pytest -q tests/browser
```
