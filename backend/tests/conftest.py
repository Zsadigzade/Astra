import os

# Tests never touch real services or the dev ledger.
os.environ.update({"PAYMENTS_MODE": "simulated", "LLM_MODE": "mock", "TTS_MODE": "off",
                   "APIFY_MODE": "sample", "JOB_SECONDS": "0", "POLL_SECONDS": "0.01",
                   "LEDGER_PATH": ":memory:"})
