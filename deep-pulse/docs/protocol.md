# Deep Ledger Intelligence Standard v1.0

The Deep Ledger Intelligence Standard provides the canonical architecture for the P2P propagation of "Verified Facts" discovered by independent Swarm nodes. 

To prevent "Signal Drift" between autonomous agents (e.g., a node in Indiana vs a node in Tokyo), every node must adhere strictly to this schema when broadcasting over the Gossip Synapse.

## 1. The Content Identifier (CID) Formatter
To allow multiple nodes to debate, verify, and agree upon a piece of intelligence without necessarily transmitting the raw target payload locally, the intelligence must be hashed into a Universal CID.

**The Specification**: Multihash SHA-256
```python
import hashlib
import json

payload = {"data": discovered_data, "metadata": intelligence_metadata}
cid_string = f"0x{hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}"
```
*Note: The JSON payload must be structurally deterministic. `sort_keys=True` ensures nodes calculate identical hashes for identical JSON trees.*

## 2. P2P Gossip Envelope (JSON-LD)
When a node broadcasts an Extraction using the UDP/TCP Synapse, the data must be wrapped in a W3C-style Verifiable Credential envelope matching the `@context`.

```json
{
  "@context": "Deep Ledger Intelligence Standard v1.0",
  "id": "0x123abc456...",
  "data": {
    "target": "gold_price_usd",
    "value": "2430.50"
  },
  "metadata": {
    "engine": "crawl4ai",
    "timestamp": 1712213400
  },
  "proof": {
    "type": "Ed25519Signature2020",
    "verificationMethod": "did:key:z6Mk...",
    "signature": "abcdef123456..."
  }
}
```

## 3. The Ed25519 "Sybil Shield" Handshake
Every intelligence node operates with an ED25519 cryptographic keypair generated via `src/core/identity.py`. 

- **Signing Rule**: The raw `id` (the CID hash) is locally signed by the extracting node's private key.
- **Verification Hook**: A listening node will decode the `signature` using the `verificationMethod` (the public key mapping of the broadcaster) against the `id` itself. If the signature is spoofed or fails, the node's REP-G score is blacklisted at the gateway level.
