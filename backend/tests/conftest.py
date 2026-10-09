import os

# Tests never touch real services or the dev ledger.
os.environ.update({"PAYMENTS_MODE": "simulated", "LLM_MODE": "mock", "SELLER_LLM_MODE": "mock", "TTS_MODE": "off",
                   "APIFY_MODE": "sample", "JOB_SECONDS": "0", "POLL_SECONDS": "0.01",
                   "LEDGER_PATH": ":memory:", "SELLER_STORE_PATH": ":memory:",
                   # Never inherit real access tokens or production strictness from the root .env.
                   "STRICT_LIVE": "0", "PRICING_MODE": "fixed", "APIFY_TOKEN": "", "API_TOKEN": "", "SELLER_API_TOKEN": "", "RATE_LIMIT_PER_MINUTE": "0"})
