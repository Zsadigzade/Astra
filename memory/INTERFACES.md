# Interfaces — contracts between components

Each component owner edits only their own section. Changing a contract someone else consumes:
tell the team first.

## Environment variables
| Name | Used by | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | all agents | OpenAI key |
| `MODEL` | all agents | model id, cheap default |
| `MASUMI_PAYMENT_URL` | payments | Masumi payment service base URL |
| `MASUMI_API_KEY` | payments | Masumi admin/API key |
| `PAYMENTS_MODE` | payments | `masumi` or `simulated` |
| `APIFY_TOKEN` | seller agents | Apify API token |
| `ELEVENLABS_API_KEY` | seller agents | ElevenLabs key |

## Components
_TBD after topic decision. Template:_

### <component> — owner: <name>
- runs: `<command>` on port `<port>`
- exposes: `<METHOD /path>` → `<payload shape>`
- consumes: `<other component endpoint>`
