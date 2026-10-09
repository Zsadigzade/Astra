# Public judge materials

Production: **https://astra-haggle-judges.vercel.app**.

This static page hosts the accepted recording, the existing root `the-haggle.html`
deck, its PDF, and the repository link. It explicitly states that interactive live
access is unavailable. It has no application backend or paid-provider endpoints.

From `backend/`, prepare the five-file allowlist without uploading:

```powershell
uv run --locked python scripts/publish_judge_page.py
```

The media and exported PDF must already exist under `backend/data/`. The script
checks the accepted MP4 hash and scans every file for configured secret values.
Output is `backend/data/vercel-public`; the manifest is retained separately.

For an authorized update to the existing Vercel project, set `VERCEL_TOKEN` in the
private process environment and use:

```powershell
uv run --locked python scripts/publish_judge_page.py --publish --team-id YOUR_TEAM_ID
```

Only the allowlisted files are uploaded via Vercel's API. Do not deploy the repository
root, `.env`, `backend/data`, account credentials or recordings from unreviewed takes.
After publication, wait for READY and verify signed-out page/media/deck access.

The HQ requires a separate Unlisted YouTube video; this page does not satisfy that
required field. The website is referenced in HQ's limitations as recorded-only
materials, while the optional Live Demo field remains blank.
