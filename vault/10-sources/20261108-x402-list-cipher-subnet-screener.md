---
title: "x402 List — Cipher Bittensor Subnet Screener listing"
created: 2026-11-08
type: source
source_type: url
url: "https://x402-list.com/services/cipher-bittensor-subnet-screener"
path: ""
author: "x402 List (independent directory; not affiliated with Coinbase or the x402 Foundation)"
status: captured
tags: [x402, fees, settlement, micropayments, stablecoin, bittensor, brobot]
---

# x402 List — Cipher Bittensor Subnet Screener listing

> Our own service (`screener.brobotapp.com`) was approved on x402-list.com on 2026-11-07.
> The listing is a live, third-party-measured record of a pay-per-call API settling in
> USDC on Base via the x402 protocol: no API key, no account, HTTP 402 carries the price.

Read on 2026-11-08 from the listing page and `/about`. Approval email arrived 2026-11-07, 5:39 PM.

## Why it matters
- First-hand, monitored example of a crypto payment rail doing something card rails cannot
  price: $0.01 to $0.25 per HTTP call with on-chain settlement. Useful like-for-like data
  for the `#fees` and `#settlement` threads (compare interchange minimums and T+N clearing).
- The directory publishes its measurements as read-only JSON, so the numbers below are
  independently reproducible rather than operator claims.

## Key claims / data (as measured by x402-list, 2026-11-07 to 2026-11-08 UTC)
- Status: online, payment-ready. Score 95/100 ("strong"), ranked #6 of 95 in Blockchain.
- 7 paid routes, x402 v2, header channel, asset USDC on Base mainnet (`eip155:8453`).
  Prices $0.01 (single screener row) to $0.25 (full subnet dossier); median $0.05.
- Compliance 14/14 checks (valid payTo, CAIP-2 network, EIP-712 domain params, HTTPS, etc).
- Uptime 100% since first capture; response p95 147 ms on the unpaid 402 handshake.
- Caveat stated by the directory: an unpaid 402 check does not prove a paid call delivers.
  On-chain traction not yet assessed. The "payment-ready" tier shows "until 2026-11-15".
- Site signals 3/6 found: homepage, openapi, pricing present; llms.txt, robots.txt, terms
  not detected at capture time.

## Follow-ups for the operator
- Payment-ready tier expires 2026-11-15; check whether it renews automatically or needs action.
- Optional $0.25 "delivery-verified" tier: x402-list pays one real call and confirms delivery.
- Badge embed (Markdown) for the screener README:
  `[![Cipher Bittensor Subnet Screener on x402-list](https://x402-list.com/badge/cipher-bittensor-subnet-screener.svg)](https://x402-list.com/services/cipher-bittensor-subnet-screener?utm_source=badge&utm_medium=referral&utm_campaign=embed)`
- Adding `llms.txt`, `robots.txt` and a terms page would lift site signals from 3/6.
- Listing edits go through `/services/cipher-bittensor-subnet-screener/update` with a
  one-time `/.well-known/` domain proof.

## Related
- MOC:: [[Bitcoin-vs-Banks]]
- See also:: x402 protocol background at https://x402-list.com/learn/what-is-x402 (not yet captured)
