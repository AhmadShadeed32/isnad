---
title: Isnad — Agentic Network Trust Engine
emoji: 🔗
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Judge-selectable mock and real Nokia simulator evidence
---

# Isnad · إسناد

Start at **[/judge](https://ahmadshadeed32-isnad-trust-engine.hf.space/judge)**.
Choose an evidence source and a Nokia simulator scenario, then run the
investigation and verify its signed receipt. Custom teaching stories remain
available in their own mock-only group.

| Evidence source | What happens |
| --- | --- |
| Mock — Nokia-compatible demo | The actual Nokia SDK serializes requests; a local transport supplies verified responses for the two supported swap checks. No requests reach Nokia. |
| Real NaC — Nokia hosted simulator | After entering an organizer access code, the same application path sends authenticated HTTP requests to Nokia using documented synthetic subscribers. |

The local mock supports repeatable demonstrations, development, and failure
tests without Nokia access or allowance consumption. Compatibility covers SIM
Swap and Device Swap checks for the two documented paired subscribers, at the
pinned contract version. It does not reproduce Nokia's entire service or prove
a physical handset's state.

Evidence source and planner are separate choices. Gemini uses the site's server
key when available; Greedy is deterministic. Only **Mock + Greedy** is fully
independent of external services. Model selections, policy overrides, and any
fallback remain labelled in the trace. The score is an uncalibrated policy score.

Real calls are limited to two Nokia attempts per run, six per judge session,
24 per rolling hour across the deployment, and two concurrent real runs. The
judge path permits at most three model calls per run, also subject to the
deployment's model allowance. A live failure never becomes mock success; choose
Mock to start a separate run. Opening a page or replaying a completed run makes
no new provider request.

The source and contract identity are inside the signed receipt. Signing proves
integrity of the recorded result; it does not turn mock data into network evidence.
Number Verification and physical-operator validation remain outside this paired
demo. Merchant review after CHALLENGE records a separate follow-up without
rewriting the original decision.

Deployment uses one worker and one replica. The signing key and subject pepper
are restored from private Space Secrets across restarts. The demonstration
database and sessions remain ephemeral, so receipt URLs may disappear when the
container is replaced; download receipts you want to retain. Server setup is in
[SERVER_KEYS.md](SERVER_KEYS.md). The release manifest records the source revision.

Other pages: `/api-keys`, `/console`, `/lab`, `/privacy`, and `/docs`.

`/api-keys` issues a merchant API key to a judge who enters the organizer's
access code, and prints the `curl` commands to call `/v1/verify` with it. The
key drives this Space's mock provider only; it is held in memory for two
hours and is forgotten when the container restarts. Keys are never issued on
a deployment whose default provider makes billable calls.

The `/console` network-conditions panel uses the deployment's mock provider.
Its subscription, forecast, history and delete flow is enabled by the
server-owned HTTPS callback base configured as a Space Variable. It is a local
lifecycle demonstration with `mock` provenance; it does not call Nokia or
claim that Nokia delivered a notification.

Team Isnad — Ahmad Shadeed and Yousef Al Masri.
