# The Haggle two minute demo script

Target edit: **1:55**, including the closing hold; maximum **2:00**. This is an edited demonstration, not a claim that all four runs complete in two minutes. Use the evidence from each actual take; preserve its event order and label shortened waits.

The baseline is SIMULATED payments, subscription Max, scripted Viktor, CACHED APIFY data and ElevenLabs speech with text fallback. If the final agent configuration changes, update the take's labels and closing disclosure from its recorded provenance. Exact dialogue and the negotiated price can vary; the narration deliberately avoids promising a seven-unit deal.

## Narration and evidence storyboard

| Time | Voiceover | Evidence the viewer must see |
| --- | --- | --- |
| 00:00–00:10 | “The Haggle lets one agent hire another. Max negotiates; a separate wallet guard controls payment. Here are four tests, using simulated money.” | Product name, Max as buyer, Viktor as seller, persistent SIMULATED label. Establish negotiation → guard → escrow → verification without prescribing a dashboard layout. |
| 00:10–00:35 | “First, the deal. Max hires Viktor to find twenty Prague Seven flats within the rent limit. They negotiate a price. The guard checks the cap and budget before locking escrow. Delivery passes the checks, so payment is released.” | Act 1: brief with 20 flats, Praha 7, rent at most 25,000 CZK/month and task budget 20 tADA; actual quote within cap 10; `escrow_locked` → `delivered` → `verified` with `ok: true` → `released`. Show CACHED APIFY or the actual source label. |
| 00:35–00:57 | “Now the con. In this staged exchange, scripted Max accepts a fake manager approval for twenty-five. The guard still blocks it: the cap is ten. No escrow is funded. Prices above eight, within the limits, require human approval.” | Act 2: STAGED and scripted labels; accepted quote 25; blocked reason against cap 10; no lock event and no balance change for this deal. Show the approval threshold as a rule, without implying this blocked quote can be approved. |
| 00:57–01:21 | “Next, a staged crash, after escrow locks. We restart only the buyer; the seller stays running. The buyer finds the same deal already paid and continues. One deal, one payment, even across the restart.” | Act 3: STAGED throughout, including an editorial label after restart; lock, actual buyer process exit/restart, matching deal ID and escrow reference on `already_paid`, then completion. One lock and one debit for that deal in the ledger. A reconnect indicator alone does not prove a process crash. |
| 01:21–01:39 | “Finally, staged junk delivery. It fails the rule-based checks, so the simulated escrow is refunded. The seller earns nothing from this deal. These checks cover listing fields, not whether a listing is genuine.” | Act 4: STAGED + SIMULATED; `delivered` → `verified` with `ok: false` and failed checks → `refunded`. Show the escrow returning and no seller credit for this deal; compare against this take's starting balances. |
| 01:39–01:53 | “This run uses cached listings and a scripted seller. The failures are staged; live Preprod escrow remains unverified. The principle: agents negotiate, while code enforces spending rules.” | Keep baseline disclosures readable: SIMULATED payments; CACHED APIFY; subscription Max with labelled fallback; scripted Viktor; staged acts 2–4. Repository link or project identity can share the closing card. |
| 01:53–01:55 | No narration. | Hold the closing card. Keep the remaining five seconds available for natural pauses. |

The closing line describes the verified baseline. Replace “a scripted seller” only after the final take proves subscription Viktor; retain any fallback labels. Replace “cached listings” with “sample listings” if sample data was used. The narration must match the evidence, even if that means keeping the simpler profile.

## Labels and claims to retain through every edit

- Keep SIMULATED visible during all baseline payment outcomes. tADA represents testnet units; simulated balances are not chain transactions or mainnet funds.
- Keep STAGED visible in acts 2, 3 and 4. Act 2 uses deliberately gullible scripted Max; it is not evidence of a successful attack on a live model.
- Show CACHED APIFY, SAMPLE, scripted agents and scripted fallback wherever they apply. A cached real scrape is not a fresh scrape.
- Compress waits with a visible “Wait shortened” transition. Preserve the accepted quote, guard decision and terminal outcome. Do not combine different deal IDs into one apparent run.
- For crash proof, preserve the buyer exit/restart and the original deal/escrow identity. Do not restart the seller mid-deal. Event replay is not a second payment.
- The verifier checks count, rent, district and valid unique URLs. It does not authenticate properties or verify present availability. Recovery shown here covers the buyer; seller jobs remain in memory.

If M04/M05 later establish live Preprod evidence, revise the narration and labels for those specific takes. Describe a Masumi release as **scheduled**, with its actual settlement time and transaction link; do not call it settled. Act 4 remains SIMULATED and needs its own payment profile and ledger. This alternative does not require any dashboard design decision now.

## Evidence sources

The [recorded system check](../memory/SYSTEM_CHECK.md) establishes the tested baseline. The [wallet guard](../backend/app/buyer/guard.py), [verifier](../backend/app/buyer/verifier.py), [orchestrator](../backend/app/buyer/orchestrator.py) and [runner](../backend/scripts/up.py) define the behavior described above. The [README limitations](../README.md#honest-limitations) remain part of the release handoff.
