# Astra — Topic Shortlist (Agentic Economy track)

**Track brief:** "Build an end-to-end scenario with agentic financial transactions."
**Partner credits:** OpenAI · ElevenLabs · Apify · Masumi (agent payments + escrow on Cardano Preprod).
**Judging:** End-to-end works 35% · Value / track fit 25% · Tech 20% · Originality 10% · Honest limitations 10%.
**Deadline:** code + 2-min video by **07:14** (sunrise). Team MMZ: Ziya, Murad, Mais.

> How to pick: vote 1st/2nd choice for each topic below. Highest total wins.
> Tie-break: whichever we can demo end-to-end by **01:00**, leaving 6 hours for polish and the video.

---

## Ranked shortlist

| # | Topic | E2E risk | Value | Originality | Partners used |
|---|-------|----------|-------|-------------|---------------|
| 1 | Agents Hire Agents | Medium | High | Medium | All 4 |
| 2 | Agent Spend Firewall | Low | High | Medium | OpenAI, Masumi |
| 3 | Haggle: agent-to-agent negotiation | Low | Medium | High | OpenAI, Masumi |
| 4 | Bounty Board for agents | Medium | Medium | Medium | OpenAI, Apify, Masumi |
| 5 | Voice Shopkeeper | High | Medium | High | ElevenLabs, OpenAI, Masumi |
| 6 | Pay-per-call Data Agent | Low | Medium | Low | Apify, Masumi |
| 7 | Agent Credit Score | Medium | High | High | OpenAI, Masumi |
| 8 | Royalty Splitter | Medium | Medium | High | OpenAI, Masumi |

---

## 1. Agents Hire Agents (recommended)
A user posts a task and a budget. Astra's **buyer agent** breaks the task into jobs, asks
**seller agents** for quotes, locks payment in escrow, checks each deliverable, then releases
the money or refunds it.

- **Demo:** "Brief me on competitor X with a voice summary, budget 20 ADA." The dashboard shows
  quotes coming in, escrow locking, the Apify research agent delivering, the ElevenLabs voice
  agent delivering, the verifier passing or failing each one, and funds moving.
- **Why it wins:** a full economic loop (discover, quote, pay, verify, settle) that uses every
  partner. Easy to explain in a 2-minute video.
- **Honest limits:** the verifier is an LLM judge and can be fooled; only 2-3 seller agents;
  testnet money only.

## 2. Agent Spend Firewall
A policy layer that sits between any agent and its wallet. It enforces budgets, a merchant
allowlist and per-transaction caps, asks a human to approve anything above a threshold, and keeps
an audit trail.

- **Demo:** a shopping agent tries 5 purchases: 3 pass, 1 is blocked (unknown merchant), 1 waits
  for human approval in the UI and then settles on Masumi.
- **Why it wins:** solves the real fear of "my agent spent my money". Low build risk.
- **Honest limits:** rules are static; a prompt-injected agent can still pick a bad allowed merchant.

## 3. Haggle: agent-to-agent negotiation
A buyer agent and a seller agent each hold a private reservation price and negotiate in rounds.
When they agree, the deal settles on Masumi.

- **Demo:** live transcript of the haggling, the agreed price, then the payment transaction.
  Swap the strategies (aggressive vs. fair) and show different outcomes.
- **Why it wins:** fun to watch, very original, simple architecture.
- **Honest limits:** LLM negotiation is unstable; there is a risk of collusion or leaking the
  reservation price.

## 4. Bounty Board for agents
Someone posts a bounty with locked funds. Several solver agents compete, and the first answer
that passes verification is paid automatically.

- **Demo:** a "find 10 AI startups in Prague with funding data" bounty. Three agents race using
  Apify, one wins, the payout lands.
- **Honest limits:** wasted compute for the losing agents; verification quality caps the whole
  system.

## 5. Voice Shopkeeper
An ElevenLabs voice agent sells a product or service by voice. It quotes, takes the order and
triggers payment, and the buyer can be another agent.

- **Demo:** a live voice call where the agent sells and the payment confirms on screen.
- **Why it wins:** a striking video. **Risk:** voice + payment latency overnight; venue Wi-Fi.

## 6. Pay-per-call Data Agent
One seller agent wraps Apify scrapers and sells data per request; buyer agents pay per call.

- **Simplest to finish.** Weak on originality; a good fallback if we are behind at 01:00.

## 7. Agent Credit Score
Reputation from on-chain transaction history: agents with a good track record get better escrow
terms (lower deposit, faster release).

- **Original, strong "infrastructure" story.** Needs fake history to be convincing, so we have to
  label it clearly as seeded data.

## 8. Royalty Splitter
A composite agent automatically pays the sub-agents and data sources it used, split by their
contribution to the final output.

- **Original.** Measuring "contribution" fairly is hard; it would be a heuristic.

---

## Fallback rule (applies to any topic)
If Masumi Preprod is down or too slow, payments go through a **SIMULATED ledger** that is clearly
labelled in the UI and the video. Saying so openly earns the "honest limitations" 10%; hiding it
loses it.
