# The Haggle: 90-second jury demo and 60-second pitch

The signed-in [HQ submission form](https://hq.agents007.ai/submit) and 04:17 organizer announcement require **at most 90 seconds**, an **unlisted YouTube link**, and a separate **60-second stage pitch**. These supersede the older two-minute public website and plan. Submission closes 9 October 2026 at **07:14 Europe/Prague / Europe/Budapest**; our target is 07:00. HQ lists presentations at 09:30. Checked 04:48 on the recording laptop.

The selected recording uses two Codex subscription agents, LIVE APIFY and ElevenLabs. Max's opening greeting is scripted. Agent-to-agent escrow is **SIMULATED**; acts 2–4 are **STAGED**. Apify reports actual provider usage charges, separately from that escrow. This is an edited recording of real runs: waits and some dialogue are omitted. It is not a claim that four full scenarios execute in 90 seconds.

## Final edit

| Time | Picture and sound | Evidence |
| --- | --- | --- |
| 0:00–0:08.5 | Introduce Max, Viktor and the guard over the real dashboard. | Agents negotiate; code controls payment. SIMULATED ESCROW stays visible. |
| 0:08.5–0:25 | Negotiation, escrow, then completed listings; narrated. | 20 Praha 7 flats below 25,000 CZK/month, price 7, LIVE APIFY, successful checks and release. |
| 0:25–0:48 | Staged con with the original recorded Viktor and Max audio, then Max's guard notice. | Manager-approved 25; gullible Max agrees; cap 10 blocks payment before funding. |
| 0:48–1:03 | Staged buyer crash, recovery and recorded process evidence; narrated. | Buyer 4584 exits with code 1, restarts as 24024; seller 28884 survives. One lock, one already_paid, one release for the same deal. |
| 1:03–1:15 | Staged junk delivery and refund; narrated. | Real scrape reduced to three listings without links. Verification fails, escrow returns, no simulated seller credit. |
| 1:15–1:29 | Provider charge evidence and limitations over the recorded dashboard. | Act 1 Apify usage USD 0.110573; simulated agent escrow; Preprod unverified; greeting scripted; listing authenticity unverified. |

Approval and decline remain in the uncut master and backup takes. They are not part of the four-act final edit. Captions derive from narration alignment; original con dialogue uses phrase timings. Export locations and review evidence are in [production.md](production.md).

## 60-second stage pitch

> Agents are getting better at saying yes. That makes giving them a wallet dangerous.
>
> Astra: The Haggle lets agents negotiate while code controls spending. Max hires Viktor to find Prague rentals. They bargain aloud, deliver live listings and settle through a separate wallet guard.
>
> The useful part is what happens when things go wrong. A seller claims a manager approved an overpriced deal. The model agrees; the guard refuses. Kill the buyer after funding and it recovers without paying twice. Deliver junk and escrow returns.
>
> We recorded all four cases. Models, data and voices are live. Apify reports real paid API usage; agent escrow is clearly simulated, with live Preprod still unverified.
>
> For teams building purchasing agents, our principle is simple: let agents negotiate. Keep spending authority in code.

This is a speaking draft, not a measured human performance. Rehearse once with the
[offline timer and slide](presenter.html). Target 55 seconds. If time is tight, shorten
the feature explanation; keep the simulated-escrow disclosure. Do not attempt four
live runs or play the full 89-second video inside the one-minute pitch.

Short fallback for a speaker who needs more breathing room:

> Giving an agent a wallet should not mean trusting every decision it makes.
>
> Astra lets agents negotiate while code controls spending. Max hires Viktor for Prague
> rental data. In our staged con, the model agrees to an overpriced deal. The guard blocks it.
>
> We also recorded buyer crash recovery without double payment, and a refund for bad
> delivery. Models, data and voices are live. Agent escrow is simulated; live Preprod
> remains unverified.
>
> For teams building purchasing agents: let agents negotiate. Keep spending authority in code.

## Jury questions

- **What actually costs money?** Apify records paid API usage for the scrape. Displayed tADA escrow is simulated. Its refund does not refund Apify or voice usage.
- **Is the con an attack benchmark?** No. A deliberately gullible buyer role demonstrates the independent guard, not general model resistance.
- **What does verification prove?** Count, rent, district and valid unique URLs. It does not prove property authenticity or current availability.
- **What survives a crash?** The demonstrated buyer restarts with the existing escrow reference and pays once. Seller state persists in SQLite, but the captured recovery keeps the seller running. Live Masumi recovery remains unverified.
- **Can judges run it?** `npm start` supports a no-key sample profile. Live mode needs local Codex sign-in and provider credentials. There is no public hosted app.
- **How does discovery work?** One configured seller endpoint, not an open marketplace or general purchasing agent.

The signed-in [Agentic Economy brief](https://hq.agents007.ai/topics) requires an executed transaction and permits paid APIs as counterparties. Present the recorded provider charge as that evidence; never describe it as an executed Masumi transfer or payment to Viktor.
