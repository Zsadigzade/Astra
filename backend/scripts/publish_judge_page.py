"""Build or publish the explicitly recorded-only Vercel judge page.

Only the five allowlisted public files are uploaded. Credentials stay in environment
variables; no application source, runtime state or provider credentials are deployed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from dotenv import dotenv_values
import httpx

ROOT = Path(__file__).resolve().parents[2]
VIDEO_SHA256 = "dce23394eceef8db3f01b046d97665c7bad7912276c2898e42ad8246d46810e6"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--team-id")
    parser.add_argument("--project", default="astra-haggle-judges")
    args = parser.parse_args()
    output = ROOT / "backend/data/vercel-public"
    output.mkdir(parents=True, exist_ok=True)
    sources = {
        "index.html": ROOT / "deploy/vercel/index.html",
        "vercel.json": ROOT / "deploy/vercel/vercel.json",
        "the-haggle-final.mp4": ROOT / "backend/data/video/the-haggle-final.mp4",
        "presentation.html": ROOT / "the-haggle.html",
        "presentation.pdf": ROOT / "backend/data/presentation/full-deck/the-haggle-full-deck.pdf",
    }
    assert hashlib.sha256(sources["the-haggle-final.mp4"].read_bytes()).hexdigest() == VIDEO_SHA256, "Video changed; re-audit before publishing"
    private = {**os.environ, **dotenv_values(ROOT / ".env")}
    values = [v.encode() for k,v in private.items() if isinstance(v,str) and len(v)>=12
              and re.search(r"KEY|TOKEN|SECRET|PASSWORD|MNEMONIC", k)]
    manifest=[]
    for name, source in sources.items():
        data=source.read_bytes()
        if any(value in data for value in values):
            raise RuntimeError(f"Private value found in {name}; refusing publication")
        shutil.copyfile(source, output / name)
        manifest.append({"file":name, "size":len(data), "sha":hashlib.sha1(data).hexdigest(),
                         "sha256":hashlib.sha256(data).hexdigest()})
    evidence=ROOT / "backend/data/judge-live"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "vercel-manifest.json").write_text(json.dumps(manifest,indent=2), encoding="utf-8")
    print(json.dumps({"built":str(output),"files":len(manifest),"secret_scan":"passed","video_sha256":VIDEO_SHA256}),flush=True)
    if not args.publish:
        return
    if not args.team_id or not os.environ.get("VERCEL_TOKEN"):
        raise RuntimeError("Publishing requires --team-id and VERCEL_TOKEN in the environment")
    with httpx.Client(base_url="https://api.vercel.com",timeout=120,trust_env=False,
                      headers={"Authorization":"Bearer "+os.environ["VERCEL_TOKEN"]}) as client:
        for entry in manifest:
            result=client.post("/v2/files",params={"teamId":args.team_id},
                headers={"Content-Type":"application/octet-stream","x-vercel-digest":entry["sha"]},
                content=(output / entry["file"]).read_bytes())
            result.raise_for_status()
            print("Uploaded "+entry["file"],flush=True)
        payload={"name":args.project,"project":args.project,"target":"production",
                 "files":[{k:v for k,v in entry.items() if k in {"file","sha","size"}} for entry in manifest],
                 "projectSettings":{"framework":None}}
        result=client.post("/v13/deployments",params={"teamId":args.team_id},json=payload)
        if result.is_error:
            print(json.dumps({"deployment_error":result.json().get("error",{})}))
        result.raise_for_status()
        deployment=result.json()
        safe={k:deployment.get(k) for k in ("id","url","readyState","alias")}
        (evidence / "vercel-deployment.json").write_text(json.dumps(safe,indent=2),encoding="utf-8")
        print(json.dumps(safe),flush=True)


if __name__ == "__main__":
    main()
