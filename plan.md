# Astra build plan · 2026-10-08 → 10-09

> **Now:** 21:40–22:15 · Skeleton runs  **Next gate:** 22:15  **Submit by:** 07:00 (hard deadline 07:14)
>
> **Rule:** at each gate, stop and check it. Gate fails → apply its fallback and move on. Never let a gate slip.

## Gates at a glance

| Time | Gate | Pass when | If it fails |
|---|---|---|---|
| **22:15** | Skeleton runs | Act 1 (honest) runs end to end, SIMULATED, text only, on **every** laptop | Ziya fixes the blocker; others keep working on their own parts |
| **23:30** | Acts from dashboard | Acts 1, 2, 4 run from dashboard buttons (SIMULATED) | — |
| **01:00** | Full E2E *(decided)* | All 4 acts + approval path run E2E. SIMULATED is OK | See the 01:00 decisions below |
| **04:00** | Feature freeze | — | Bug fixes only from here on |
| **06:30** | Video + repo *(decided)* | Video done, repo public | — |
| **07:00** | Submitted | Form sent, links checked in incognito | 14 min buffer to 07:14 |

## Who owns what

| Person | Area | Files |
|---|---|---|
| Ziya | Buyer "Max", wallet guard, Masumi payments | `buyer/`, `shared/` |
| Murad | Seller "Viktor", Apify scrape, ElevenLabs voice | `seller/`, `voice/` |
| Mais | Dashboard, video | `dashboard/` |

---

## 1 · 21:40–22:15 · Skeleton runs

**Ziya**
- [x] Finish skeleton, `uv sync`, `uv run pytest` (11 pass)
- [x] Buyer :8000 + seller :8001 answer `/health`
- [ ] Share branch `feat/ziya-skeleton` + this plan

**Murad**
- [ ] Pull branch, read `seller/`
- [ ] Pick Apify actor for Prague 7 rentals
- [ ] Create ElevenLabs voices for Max + Viktor, put IDs in `.env` (`VOICE_MAX`, `VOICE_VIKTOR`)

**Mais**
- [ ] Pull branch, `npm install` in `dashboard/`
- [ ] Connect to `GET /events`, show raw event list

🚦 **Gate 22:15:** Act 1 SIMULATED, text only, on every laptop.

## 2 · 22:15–23:30 · Real parts, one each

**Ziya**
- [ ] Hosted Masumi `/health`
- [ ] Register buyer + seller agents
- [ ] Fund buyer from Preprod faucet
- [ ] One manual test escrow

**Murad**
- [ ] Real Apify scrape behind `APIFY_MODE=apify`, map to `Flat`
- [ ] Save one real result JSON as offline fallback
- [ ] `TTS_MODE=elevenlabs` working

**Mais**
- [ ] Real layout: 2 avatars, chat bubbles, balances
- [ ] SIMULATED + STAGED badges, red BLOCKED banner, Approve button

🚦 **Gate 23:30:** Acts 1, 2, 4 run from dashboard buttons (SIMULATED).

## 3 · 23:30–01:00 · Integrate

**Ziya**
- [x] `MasumiPayments.lock` / `refund` + seller side of Masumi payment (code done, tested on fake)
- [ ] Act 3 crash + restart (`CRASH_AFTER_LOCK=1`) on real setup
- [ ] OpenAI Max, only if credits arrived

**Murad**
- [ ] Viktor LLM persona (only if OpenAI)

**Mais**
- [ ] Audio playback queue (lines play in order)
- [ ] Preprod tx link on screen
- [ ] Act selector

🚦 **Gate 01:00 (decided):** all 4 acts + approval path E2E. SIMULATED is OK. Decide here:
1. **Masumi:** no Preprod escrow by now → SIMULATED for the video, stated as a limitation
2. **Voice:** broken → cut it, text only (first in cut order)
3. **Apify:** flaky → use the saved real JSON, labelled

## 4 · 01:00–02:30 · Harden

- [ ] **Everyone:** run each act **3 times** in a row; fix anything that fails even once
- [ ] **Ziya:** real Masumi in Act 1 if go. Idempotency: restart twice, still one payment
- [ ] **Murad:** timeouts + fallbacks for Apify and TTS
- [ ] **Mais:** polish; readable at 1080p video size

## 5 · 02:30–04:00 · Prepare the video

- [ ] **Mais:** video script + storyboard (4 acts, ≤ 2:00)
- [ ] **Ziya:** README (run steps, architecture, honest limitations)
- [ ] **Murad:** screen-record each working act as **backup footage**
- [ ] **03:30 · Everyone:** full rehearsal of the demo script, timed

🚦 **Gate 04:00: FEATURE FREEZE.** Bug fixes only from here on.

## 6 · 04:00–05:30 · Record

- [ ] **Mais:** records
- [ ] **Ziya + Murad:** run the backend live, fix issues between takes
- [ ] Captions on screen: SIMULATED / STAGED wherever they apply

## 7 · 05:30–06:30 · Edit + clean up

- [ ] **Mais:** edit, voiceover, captions, export
- [ ] **Ziya:** `memory/HANDOFF.md` final; secret scan of repo + git history (`.env` never committed)
- [ ] **Murad:** `.env.example` complete; fresh-clone run test

🚦 **Gate 06:30 (decided):** video done, repo public.

## 8 · 06:30–07:14 · Submit

- [ ] **06:30** submit form, video link, repo link
- [ ] **06:50** open every link in incognito: repo visible, video plays
- [ ] **07:00 submitted.** 14 min buffer
