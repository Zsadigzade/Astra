# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

## Environment variables
| Name | Used by | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | all agents | OpenAI key |
| `MODEL` | all agents | model id, cheap default |
| `MASUMI_PAYMENT_URL` | payments | hosted Masumi payment service base URL, ends in `/api/v1` |
| `MASUMI_API_KEY` | payments | Masumi admin/API key |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated` |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |

## Components
Ports and paths below are decided; payload fields are TBD by each owner.

### buyer (orchestrator + firewall + verifier) — owner: ziya
- runs: TBD, port `8000`
- exposes: TBD (task submit, live event feed for dashboard)
- consumes: sellers via MIP-003; Masumi payment service

### seller-research (Apify) — owner: murad
- runs: FastAPI, port `8001`
- exposes MIP-003: `GET /availability`, `GET /input_schema`, `POST /start_job`, `GET /status?job_id=`

### seller-voice (ElevenLabs) — owner: murad
- runs: FastAPI, port `8002`
- exposes MIP-003: same four endpoints as seller-research

### dashboard — owner: mais
- runs: TBD
- consumes: buyer event feed (TBD)
