# Windows launcher

Double-click `dist/AstraLauncher.exe`. Keep the repository: this executable launches its
existing code, dependencies and development tests. It can discover the checkout above
the executable, or you can select it with **Browse** after moving the EXE elsewhere.
No Python installation is needed for the launcher's window itself; running the project
still requires Node.js/npm, uv and the backend Python environment.

First-time repository setup, from the root:

```powershell
npm run setup
uv sync --directory backend
npm ci --prefix frontend
```

1. Leave **Sample (no keys)** selected and click **All local checks**. This runs local
   readiness, every backend test, every frontend test, a production frontend build,
   and real HTTP release/block/refund checks with balance conservation. The HTTP check
   uses private ports so it can coexist with another terminal's demo.
2. Click **Start demo**, wait for **Demo ready**, then **Open dashboard**. Run normal,
   con and refund requests; inspect the guard, delivery and timeline. The sample
   profile deliberately has scripted agents, sample listings and no speech.
3. Click **Stop current action** before switching actions. **Start recovery demo**
   starts the staged buyer-crash path; submit a normal request in the dashboard to
   trigger it. The buyer restarts once while the seller stays alive.
4. For your configured providers, select **Configured (.env providers)**. Run **Local
   readiness** first, then enable provider usage and select **Live provider probes**.
   The latter uses enabled subscription agents and fresh ElevenLabs speech.
5. **Live four-act rehearsal** uses subscription Codex, scripted Viktor, saved real
   Apify listings, ElevenLabs speech and SIMULATED payments. It runs each act three
   times, including an actual buyer crash, plus approval and decline. It uses private
   ports and fresh storage. This spends subscription/voice credits; it does not scrape
   new listings. A valid exact-job cache and configured voices are required. This is
   HTTP/provider acceptance; it does not automate browser controls or audible playback.

Configured interactive demos use the provider modes in `.env` (and inherited process
environment). If `APIFY_MODE=apify`, requesting data may spend Apify credits. Launcher
payments always remain **SIMULATED**. Codex requires your external ChatGPT sign-in;
there is no OpenAI API-key requirement.

Interactive demos require ports 8000, 8001 and 5173. If occupied, the launcher reports
the conflict without stopping the other session. Stop that session in its own terminal
before starting an interactive demo. Closing the launcher or pressing Stop terminates
only its owned process tree. It preserves all ledgers, including interrupted runs.

Logs, isolated ledger/audio and `report.json` are under `backend/data/launcher-*/`.
**Open logs/report** opens the current run's folder. The live rehearsal additionally
prints its own `backend/data/r-rehearsal-*/report.json` path. Existing `.env` and demo
ledgers are never overwritten. No keys, cache, ledgers or authentication files are
bundled in the EXE. Local logs may contain application data; review before sharing.

## Command-line automation

The windowed executable writes results to files. PowerShell can wait for completion:

```powershell
$run = Start-Process -FilePath .\dist\AstraLauncher.exe -ArgumentList '--run all --report data/launcher-result.json' -WindowStyle Hidden -Wait -PassThru
$run.ExitCode
Get-Content data/launcher-result.json
```

Actions: `all`, `tests` (backend + frontend + build), `backend`, `frontend`, `build`,
`readiness`, `smoke`, `demo`, `recovery`, `live-probe`, `rehearse`. Use `--repo` with
the checkout path if autodetection cannot find it. Live actions require both
`--profile configured` and `--allow-live`. Exit 0 means successful completion; exit 1
means a failed check, prerequisite or cancellation. Stopping an interactive demo after
successful startup is a normal completion, with `cancelled: true` recorded in its report.

## Rebuild

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build_launcher.ps1
```

This uses PyInstaller 6.22.3 in an isolated uv tool environment and verifies Tcl can
initialize before packaging. Output: `dist/AstraLauncher.exe`, with SHA-256 printed
after the build. The EXE is a local unsigned Windows x64 build; generated artifacts
remain git-ignored. Source and tests are committed. See the official
[PyInstaller documentation](https://pyinstaller.org/en/stable/usage.html) for packaging options.
