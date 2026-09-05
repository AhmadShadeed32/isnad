# Number Verification handset validation

Status on 5 September 2026: **the local consent contract is automated; the
operator-hosted consent page has not been exercised on a physical handset.** A
mock pass is integration evidence about Isnad's routes. It is not live consent
evidence and must never be labelled as such.

## What “handset consent” and “callback” mean

Number Verification needs the mobile subscriber to approve an operator OAuth
request. Isnad creates that request and shows its authorization URL as a QR code.
The subscriber scans it on the phone whose number is being checked and approves
on the operator's page. The operator then redirects the phone browser to Isnad's
registered HTTPS callback with a short-lived authorization code. Isnad exchanges
that code server-to-server, runs Number Verification with the resulting token,
and stores a signed receipt. The callback is therefore a public HTTPS endpoint
on the Isnad deployment, not something Ahmad must implement on the handset.

The current flow keeps the state and token in process, so the deployment must run
exactly one application worker for this test. A load-balanced or multi-worker
deployment needs shared consent storage before it can be used reliably.

## Safe local proof (no operator, handset, or network call)

Run:

```bash
.venv311/bin/python scripts/handset_validation.py contract
```

This exercises the real HTTP route sequence with a deterministic fake provider:

1. initiate consent and receive `PENDING`;
2. deliver the callback and reach `AUTHORIZED`;
3. reject reuse of the OAuth state and exchange the code once;
4. resume the investigator with Number Verification as the required first action;
5. persist the completed verdict and return the same result on a duplicate
   completion request;
6. retrieve the authenticated verification record and public receipt; and
7. verify the Ed25519 signature over the exact stored payload.

It writes `/tmp/isnad-consent-contract.json` with mode `mock_contract`,
`network_calls: false`, and `physical_handset_reported: false`. The report stores
no phone, authorization URL, OAuth state, code, token, or API key.

## Inputs still needed for a live handset proof

All of these must exist before a live run can succeed:

- a Nokia Network as Code application with Number Verification enabled for the
  test operator and subscriber;
- the application's server-side API credential and OAuth client details, or SDK
  access that can discover the client and authorization metadata;
- the exact callback URL
  `https://<public-host>/v1/consents/number-verification/callback` registered on
  that application;
- an Isnad deployment at that public HTTPS host, running one worker with a
  persistent vault key, persistent subject pepper, private merchant API key,
  `ISNAD_PROVIDER=nac`, and demo mode disabled;
- a supported E.164 mobile subscription in the physical handset, with the person
  entitled to approve its consent; and
- explicit approval for the provider spend. The required Number Verification
  call always runs first. If it returns a mismatch or no usable answer, policy
  may purchase additional configured evidence calls before issuing a verdict.

Do not paste provider credentials, OAuth secrets, merchant API keys, or a real
phone number into this document, a ticket, a chat, or a screen recording.

## Live procedure

Before a live run, complete the current OAuth contract checks in
[P4a of the handoff](PHASE2_HANDOFF.md#p4a--build-the-live-consent-journey-locally).
Start the controlled deployment using the [live deployment checklist](PHASE2_HANDOFF.md#4-path-to-a-live-product).
Confirm `/readyz` returns 200 and confirm the
registered callback matches `ISNAD_NAC_REDIRECT_URI` byte for byte.

On the laptop that will display the QR code, enter the test inputs through hidden prompts so their values do not appear in
shell history (the commands below use zsh):

```bash
read -rs 'ISNAD_HANDSET_API_KEY?Merchant API key: '
read -rs 'ISNAD_HANDSET_PHONE?Test mobile number: '
export ISNAD_HANDSET_API_KEY ISNAD_HANDSET_PHONE
export ISNAD_HANDSET_ARM='i-understand-this-may-call-a-billable-provider'
```

Turn off Wi-Fi on the test handset and confirm mobile data works. Then run:

```bash
.venv311/bin/python scripts/handset_validation.py live \
  --base-url https://<public-host> \
  --connection mobile-data \
  --output /tmp/isnad-handset-mobile-data.json
```

Scan the terminal QR code with the handset, approve on the operator page, and
leave the script running. It polls the tenant-scoped status, completes the
verification, repeats completion to prove the stored response is reused, fetches
the public receipt, and verifies its Ed25519 signature. It deliberately does not
replay the live OAuth callback because that would require copying a sensitive
authorization URL from the handset; state replay is exercised in contract mode.

The saved report is redacted and mode-labelled `live_handset`.
`physical_handset_reported` records the human tester’s connection declaration;
the laptop does not independently observe the handset. The connection
field is an operator declaration supplied by `--connection`; software running on
the laptop cannot detect whether the handset used Wi-Fi. Keep the terminal QR and
the handset callback address bar out of retained screenshots because they may
contain short-lived OAuth state or code. A useful video shows the handset with
Wi-Fi disabled, the operator consent page and approval, then the final redacted
report. It does not show the terminal environment or browser address bar.

Repeat with `--connection wifi` only if operator behavior over Wi-Fi is also a
required observation. Store that as a separate report; do not overwrite the
mobile-data artifact.

## Pass criteria

A live handset claim is supported only when the report says all of the following:

- `scope.mode` is `live_handset`;
- `scope.network_calls` and `scope.physical_handset_reported` are true;
- lifecycle is `PENDING` → `AUTHORIZED` → `COMPLETED`;
- the signed chain contains exactly one `number_verify` link with source `nac`
  and signal `NUMBER_MATCH` or `NUMBER_MISMATCH`;
- duplicate completion returned the stored response; and
- the receipt signature is valid under a trusted key.

Anything less remains an unverified or failed live attempt and should be reported
with its actual status rather than promoted to “handset consent works.”
