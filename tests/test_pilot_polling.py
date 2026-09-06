"""Execute the shipped poll loop with controlled HTTP replies and a tiny DOM."""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("node") is None, reason="JavaScript runtime unavailable")
def test_poll_recovers_after_http_error_and_missing_receipt():
    html = (Path(__file__).parents[1] / "demo/merchant_pilot/static/flow.html").read_text()
    poll = html[html.index("async function poll() {"):].split("</script>")[0]
    # Drop the eager invocation; each scheduled callback is driven below.
    poll = poll.rsplit("poll();", 1)[0]
    harness = r'''
const assert = require("node:assert/strict");
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {
    textContent: "", innerHTML: "old-qr", href: "old-authorization", hidden: false,
    replaceChildren() { this.innerHTML = ""; },
    removeAttribute(name) { delete this[name]; }
  });
  return elements.get(id);
}};
const flowId = "synthetic";
const TERMINAL = new Set(["COMPLETED", "DENIED", "FAILED", "EXPIRED", "UNAVAILABLE"]);
let delayMs = 1;
const MAX_DELAY_MS = 10;
let scheduled = [];
const setTimeout = (fn) => scheduled.push(fn);
let rendered = [];
const renderOutcome = result => rendered.push(result.chain_id);
const renderChallengePanel = () => {};
const renderOutcomesPanel = () => {};
const renderSessionPanel = () => {};
let replies = [
  {ok:false, status:503},
  {ok:true, json:async () => ({status:"COMPLETED", recovering:true, result:null})},
  {ok:true, json:async () => ({status:"COMPLETED", recovering:false,
    result:{chain_id:"chn_original", decision:"CHALLENGE"}})}
];
const fetch = async () => replies.shift();
'''
    assertions = r'''
(async () => {
  await poll();
  assert.equal(scheduled.length, 1, "503 must retry");
  await scheduled.shift()();
  assert.equal(scheduled.length, 1, "missing receipt must retry");
  await scheduled.shift()();
  assert.equal(scheduled.length, 0, "receipt completion must stop");
  assert.deepEqual(rendered, ["chn_original"]);
  assert.equal(document.getElementById("qr").innerHTML, "");
  assert.equal(document.getElementById("open-link").href, undefined);
  replies = [{ok:false, status:404}];
  await poll();
  assert.equal(scheduled.length, 0, "expired flow must stop");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    subprocess.run([shutil.which("node"), "-e", harness + poll + assertions], check=True)
