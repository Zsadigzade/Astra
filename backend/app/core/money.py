"""Money is a plain float in US dollars (SIMULATED payments only); this is its one display format."""


def usd(amount: float) -> str:
    return f"${amount:g}"
