"""Go-live preflight: is THIS machine ready to run Haggle against real services?

Reads the root .env exactly like the app does and reports, per integration, what is configured, what is
missing and the single next action. It never prints a secret, moves no money and spends no credits.

Run:  uv run python scripts/doctor.py            offline: configuration only
      uv run python scripts/doctor.py --live     also runs the read-only live checks
                                                 (Masumi node, voice list or a tiny speech probe, one Codex Max round; the probe costs a few credits)
Exit 0 = every integration you have switched on is ready. SIMULATED/sample modes are reported, not failed.
"""

import argparse
import json
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.core.config import PROJECT_ROOT, Settings  # noqa: E402

OK, WARN, FAIL, INFO = "READY", "SIMULATED", "MISSING", "INFO"
rows: list[tuple[str, str, str, str]] = []  # area, status, what, next action


def add(area: str, status: str, what: str, nxt: str = "") -> None:
    rows.append((area, status, what, nxt))


def port_busy(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_check(script: str, *args: str, timeout: int = 150) -> tuple[bool, str]:
    try:
        p = subprocess.run([sys.executable, f"scripts/{script}", *args], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    tail = [ln for ln in (p.stdout + p.stderr).strip().splitlines() if ln.strip()][-1:] or [""]
    return p.returncode == 0, tail[0][:160]


def tts_probe(s: Settings) -> tuple[bool, str]:
    """One tiny real synthesis per configured voice (a few credits). Never prints the key or response body."""
    import httpx

    try:
        for name, voice in (("Max", s.voice_max), ("Viktor", s.voice_viktor)):
            r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_22050_32",
                           headers={"xi-api-key": s.elevenlabs_api_key}, timeout=30,
                           json={"text": "Deal.", "model_id": s.tts_model})
            if r.status_code != 200 or not r.content:
                return False, f"{name}'s voice returned HTTP {r.status_code}"
        return True, "both voices synthesized audio"
    except httpx.HTTPError as e:
        return False, f"request failed ({type(e).__name__})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="also run the read-only live checks")
    live = ap.parse_args().live

    env_file = PROJECT_ROOT / ".env"
    add("Environment", OK if env_file.exists() else INFO, ".env file" + (" found" if env_file.exists() else " not found (running on defaults: everything simulated)"),
        "" if env_file.exists() else "npm run setup   (creates .env from .env.example; then fill in the keys)")
    try:
        s = Settings()
    except ValueError as e:
        add("Environment", FAIL, f"invalid setting: {e}", "fix the value in .env")
        return report()

    # --- runtime
    for tool, hint in (("uv", "install uv: https://docs.astral.sh/uv/"), ("node", "install Node 20+")):
        add("Runtime", OK if shutil.which(tool) else FAIL, tool, "" if shutil.which(tool) else hint)
    busy = [p for p in (8000, 8001, 5173) if port_busy(p)]
    add("Runtime", WARN if busy else OK, "ports 8000/8001/5173 " + (f"in use: {busy}" if busy else "free"),
        "stop the old processes before npm start" if busy else "")

    # --- agent brain
    if s.llm_mode == "codex":
        has = shutil.which(s.codex_command) is not None
        add("Max (LLM)", OK if has else FAIL, f"LLM_MODE=codex, CLI '{s.codex_command}' " + ("found" if has else "not found"),
            "" if has else "npm install -g @openai/codex, then `codex login` (ChatGPT subscription, no API key)")
        if live and has:
            ok, tail = run_check("llm_check.py", timeout=180)
            add("Max (LLM)", OK if ok else FAIL, f"live Codex round: {tail}", "" if ok else "run `codex login`, then retry")
    else:
        add("Max (LLM)", WARN, "LLM_MODE=mock: Max is scripted", "set LLM_MODE=codex after `uv run python scripts/llm_check.py` passes")
    if s.seller_llm_mode == "codex":
        has = shutil.which(s.codex_command) is not None
        add("Viktor (LLM)", OK if has else FAIL, f"SELLER_LLM_MODE=codex, CLI '{s.codex_command}' " + ("found" if has else "not found"),
            "" if has else "install and sign in to the Codex CLI (same login as Max)")
    else:
        add("Viktor (LLM)", WARN, "SELLER_LLM_MODE=mock: Viktor is scripted", "set SELLER_LLM_MODE=codex to let Viktor negotiate with the same Codex login")

    # --- data
    cache = Path(s.apify_cache_path)
    cache_ok = False
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding="utf-8"))
            cache_ok = bool(data)
        except (OSError, ValueError):
            cache_ok = False
    if s.apify_mode == "apify":
        have = bool(s.apify_token)
        add("Flats (Apify)", OK if have else FAIL, "APIFY_MODE=apify, token " + ("set" if have else "missing") +
            f"; saved fallback {'present' if cache_ok else 'absent'}",
            "" if have and cache_ok else ("set APIFY_TOKEN" if not have else "uv run python scripts/scrape_flats.py  (saves the labelled fallback; costs Apify credits)"))
    elif s.apify_mode == "cached":
        add("Flats (Apify)", OK if cache_ok else FAIL, "APIFY_MODE=cached, saved real scrape " + ("present" if cache_ok else "missing"),
            "" if cache_ok else "set APIFY_TOKEN, then uv run python scripts/scrape_flats.py")
    else:
        add("Flats (Apify)", WARN, "APIFY_MODE=sample: canned listings (labelled SAMPLE DATA)",
            "set APIFY_TOKEN, run scripts/scrape_flats.py, then APIFY_MODE=apify (or cached)")

    # --- voice
    if s.tts_mode == "elevenlabs":
        miss = [n for n, v in (("ELEVENLABS_API_KEY", s.elevenlabs_api_key), ("VOICE_MAX", s.voice_max), ("VOICE_VIKTOR", s.voice_viktor)) if not v]
        add("Voice", FAIL if miss else OK, "TTS_MODE=elevenlabs" + (f", missing {', '.join(miss)}" if miss else ", key and both voices set"),
            "uv run python scripts/voice_check.py  (lists voices; then set the IDs)" if miss else "")
        if live and not miss:
            ok, tail = run_check("voice_check.py", timeout=60)
            if ok:
                add("Voice", OK, f"live voice list: {tail}")
            else:
                # A key restricted to text-to-speech cannot list voices; the real question is whether it can speak.
                spoke, why = tts_probe(s)
                add("Voice", OK if spoke else FAIL, "live speech probe (voice list not permitted for this key): " + why,
                    "" if spoke else "check the key's Text to Speech permission and the voice IDs")
    else:
        add("Voice", WARN, "TTS_MODE=off: text only", "set TTS_MODE=elevenlabs with key + VOICE_MAX + VOICE_VIKTOR for spoken haggling")

    # --- money
    if s.payments_mode == "masumi":
        miss = [n for n, v in (("MASUMI_PAYMENT_URL", s.masumi_payment_url), ("MASUMI_API_KEY", s.masumi_api_key),
                               ("MASUMI_AGENT_ID", s.masumi_agent_id), ("SELLER_VKEY", s.seller_vkey)) if not v]
        bad = []
        if s.masumi_agent_id and len(s.masumi_agent_id) < 57:
            bad.append("MASUMI_AGENT_ID looks too short (57+ chars)")
        if s.seller_vkey and not re.fullmatch(r"[0-9a-fA-F]{56}", s.seller_vkey):
            bad.append("SELLER_VKEY must be 56 hex chars")
        add("Money (Masumi)", FAIL if miss or bad else OK, "PAYMENTS_MODE=masumi" + (f", missing {', '.join(miss)}" if miss else "") + (f"; {'; '.join(bad)}" if bad else ""),
            "see README 'Masumi' steps: bring up the node, fund wallets, register Viktor (Dynamic pricing)" if miss or bad else "")
        default_ledger = Path(s.ledger_path).resolve() == (ROOT / "data" / "buyer.db").resolve()
        add("Money (Masumi)", WARN if default_ledger else OK, "ledger " + ("is the default simulated one" if default_ledger else "is a separate file"),
            "set LEDGER_PATH=backend/data/buyer-live.db so real and simulated deals never mix" if default_ledger else "")
        if live and not miss:
            ok, tail = run_check("masumi_check.py", timeout=90)
            add("Money (Masumi)", OK if ok else FAIL, f"live node check: {tail}", "" if ok else "see scripts/masumi_check.py output")
    else:
        add("Money (Masumi)", WARN, "PAYMENTS_MODE=simulated: local ledger, labelled SIMULATED",
            "after `masumi_check.py --node-only` passes and Viktor is registered: PAYMENTS_MODE=masumi + a separate LEDGER_PATH")

    return report()


def report() -> int:
    width = max(len(a) for a, *_ in rows)
    mark = {OK: "[ OK ]", WARN: "[SIM ]", FAIL: "[FAIL]", INFO: "[info]"}
    print()
    for area, status, what, nxt in rows:
        print(f"{mark[status]} {area:<{width}}  {what}")
        if nxt:
            print(f"       {'':<{width}}  -> {nxt}")
    failed = [r for r in rows if r[1] == FAIL]
    simulated = [r for r in rows if r[1] == WARN and r[0] != "Runtime"]
    print()
    if failed:
        print(f"NOT READY: {len(failed)} integration(s) switched on but incomplete (see [FAIL] lines).")
    elif simulated:
        print(f"READY, PARTLY SIMULATED: {len(simulated)} area(s) still use scripted/sample/simulated behaviour. "
              "That is honest and demo-safe; the UI labels it.")
    else:
        print("READY: every integration is live.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
