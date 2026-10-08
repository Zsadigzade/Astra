# Handoff — state of `main`

updated: 2026-10-08 19:32 · ziya

## What works
- No code yet. Topic, roles and seller protocol decided (see DECISIONS.md).

## What's next
1. 21:30 checkpoint: each owner fills their INTERFACES.md section, skeletons answer HTTP.
2. Ziya: verify hosted Masumi `/api/v1/health`, register agents, test one escrow.
3. Murad: seller-research MIP-003 skeleton on :8001.
4. Mais: dashboard skeleton reading buyer event feed (contract TBD with Ziya).

## Known broken / risky
- No OpenAI access yet (2026-10-08 20:10). Verifier and research seller need it; keep LLM calls behind `MODEL` env + mockable interface.
- Hosted Masumi URL not yet in anyone's `.env`; `/health` unchecked.
- No one on the team has Cardano/Masumi experience. Default PAYMENTS_MODE=simulated until escrow test passes.
