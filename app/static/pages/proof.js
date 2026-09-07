const $ = (id) => document.getElementById(id);

function hexToBytes(hex){
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
  return out;
}

function setStatus(state, text, note){
  const el = $('status');
  el.className = 'status ' + state;
  el.textContent = text;
  $('statusNote').textContent = note || '';
}

// The server signs a canonical JSON serialization of the attestation with its
// `signature` field absent. Rebuilding those exact bytes here is what makes
// this verifiable rather than merely displayed.
function canonicalBytes(attestation){
  const copy = {};
  for (const key of Object.keys(attestation).sort()) {
    if (key === 'signature') continue;
    copy[key] = attestation[key];
  }
  return new TextEncoder().encode(JSON.stringify(copy));
}

async function verify(attestation){
  if (!window.isSecureContext || !crypto.subtle){
    setStatus('pending', '⋯ cannot verify here',
      'WebCrypto needs HTTPS (or localhost). Open this page over HTTPS to verify.');
    return null;
  }
  try{
    const key = await crypto.subtle.importKey(
      'raw', hexToBytes(attestation.issuer_public_key), {name:'Ed25519'}, false, ['verify']);
    return await crypto.subtle.verify(
      {name:'Ed25519'}, key, hexToBytes(attestation.signature), canonicalBytes(attestation));
  }catch(err){
    setStatus('pending', '⋯ cannot verify here',
      'This browser does not support Ed25519 in WebCrypto.');
    return null;
  }
}

function render(attestation){
  $('shareId').textContent = attestation.chain_id;

  const decision = $('decision');
  decision.textContent = attestation.decision;
  decision.className = 'decision ' + attestation.decision;
  $('grade').textContent = attestation.chain_grade || 'UNGRADED';
  $('issuedAt').textContent = attestation.issued_at;
  $('expiresAt').textContent = attestation.expires_at;
  // Integrity and access are separate facts, and the difference is the whole
  // point of an expiring link: the summary keeps verifying after the link
  // stops working, and revoking the link does not reach anything already
  // downloaded — or the original public receipt, which was never gated by it.
  $('accessNote').textContent =
    'Access through this link ends at the time above. That is separate from the ' +
    'signature: a copy saved now still verifies afterwards, and revoking this ' +
    'link does not withdraw the original receipt or anything already downloaded.';
  $('summaryCard').hidden = false;

  $('digest').textContent = attestation.source_payload_digest;
  $('issuerKey').textContent = attestation.issuer_public_key;
  $('signature').textContent = attestation.signature;
  $('proofCard').hidden = false;
}

(async function main(){
  const token = location.pathname.split('/').pop() || '';
  try{
    if (!token){
      setStatus('bad', '✗ invalid link', 'This URL does not contain a share token.');
      return;
    }
    const response = await fetch(location.pathname, {headers: {'Accept': 'application/json'}});
    if (!response.ok){
      // Missing, expired and revoked deliberately answer identically — a
      // reader learns nothing about which one it was.
      setStatus('bad', '✗ link unavailable',
        'This link is not available. It may never have existed, may have expired, or may have been revoked.');
      $('shareId').textContent = '—';
      return;
    }
    const attestation = await response.json();
    const ok = await verify(attestation);
    if (ok === null) { render(attestation); return; }
    if (ok){
      setStatus('ok', '✓ signature valid',
        'This summary was issued by the key below and has not been altered since.');
    } else {
      setStatus('bad', '✗ signature INVALID',
        'These bytes do not match the signature. Do not rely on this summary.');
    }
    render(attestation);
  }catch(err){
    setStatus('bad', '✗ could not load', 'The summary could not be fetched.');
  }
})();
