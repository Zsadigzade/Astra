"""Turn a plain-language request into a validated rental job, or say plainly why Viktor cannot do it.

Deterministic on purpose: no model call, so it is instant, free, testable and cannot be talked into
inventing a job. Viktor sells exactly one thing, Prague rental listings, so everything else is refused.
"""

import re
from dataclasses import dataclass, field

from app.core.models import BoundedJobSpec

DEFAULT_COUNT = 20
DEFAULT_DISTRICT = "Praha 7"
DEFAULT_MAX_RENT = 25_000
EXAMPLES = [
    "Find me 20 flats in Praha 7 under 25,000 CZK",
    "10 apartments in Prague 2, max 30k",
    "Explain in two sentences why escrow protects buyers",
]

_RENTAL_WORDS = re.compile(
    r"\b(flats?|apartments?|apts?|rentals?|rent|listings?|byt[yů]?|bytu|housing|place to live|\d\+(?:kk|1))\b", re.I)
# With general answers on, bare "rent" / "listings" are ambiguous ("rent a car", "5 listings of used cars"), so a request
# only counts as a flat search when it names housing.
_HOUSING = re.compile(r"\b(flats?|apartments?|apts?|rentals?|byt[yů]?|bytu|housing|place to live|\d\+(?:kk|1))\b", re.I)
_OTHER_PLACES = re.compile(
    r"\b(brno|ostrava|plze[nň]|pilsen|olomouc|liberec|hradec|pardubice|vienna|wien|berlin|munich|london|paris|"
    r"bratislava|warsaw|budapest|amsterdam|madrid|rome|new york|barcelona)\b", re.I)
_DISTRICT = re.compile(r"\b(?:praha|prague|prag)\s*(\d{1,2})\b", re.I)
_PRAGUE_ONLY = re.compile(r"\b(?:praha|prague|prag)\b", re.I)
_COUNT = re.compile(
    r"\b(\d{1,4})\s+(?:[a-zà-ž0-9+\-]+\s+){0,3}?(?:flats?|apartments?|apts?|rentals?|listings?|places?|byt[yů]?)\b", re.I)
_RENT = re.compile(
    r"(?:under|below|max(?:imum)?|up\s*to|less\s+than|at\s+most|within|no\s+more\s+than|<=?|budget(?:\s+of)?)\s*"
    r"(?:czk|kč|kc)?\s*(\d[\d\s,.]*)\s*(k(?![a-zà-ž])|tis(?:ic)?\.?)?\s*(?:czk|kč|kc)?(?:\s*(?:/|per|a)\s*month)?", re.I)


@dataclass
class ParsedRequest:
    ok: bool
    summary: str
    job: BoundedJobSpec | None = None
    notes: list[str] = field(default_factory=list)  # defaults we filled in, shown to the person

    def public(self) -> dict:
        return {"ok": self.ok, "kind": self.job.kind if self.job else None, "summary": self.summary, "job": self.job.model_dump() if self.job else None,
                "notes": self.notes, "examples": EXAMPLES}


def _money(raw: str, k: str | None) -> int | None:
    digits = re.sub(r"[\s,.]", "", raw)
    if not digits:
        return None
    value = int(digits)
    return value * 1000 if k else value


def _general(t: str) -> ParsedRequest:
    one_line = " ".join(t.split())
    clip = one_line if len(one_line) <= 90 else one_line[:89].rstrip() + "…"
    return ParsedRequest(True, f'Ask Viktor: "{clip}"', BoundedJobSpec(kind="general", prompt=t),
                         ["Not a flat search: an AI seller writes the answer, using web search when needed. Checked by rules, not for facts."])


def parse_request(text: str, general: bool = False) -> ParsedRequest:
    """`general`: whether an AI seller is available for requests that are not Prague rentals."""
    t = (text or "").strip()
    if not t:
        return ParsedRequest(False, "Type what you want Max to buy, for example: " + EXAMPLES[0])
    if len(t) > 500:
        return ParsedRequest(False, "That request is too long. Keep it under 500 characters.")
    if general and not _HOUSING.search(t):
        return _general(t)
    if _OTHER_PLACES.search(t):
        if general:
            return _general(t)
        return ParsedRequest(False, "Viktor only has Prague rental listings, so other cities cannot be bought. "
                                    "Try: " + EXAMPLES[0])
    if not _RENTAL_WORDS.search(t):
        if general:
            return _general(t)
        return ParsedRequest(False, "Viktor sells Prague rental listings. Ask for flats or apartments, for example: "
                                    + EXAMPLES[1] + ". To ask anything else, turn on Codex answers (LLM_MODE=codex).")

    notes: list[str] = []
    m = _COUNT.search(t)
    count = int(m.group(1)) if m else DEFAULT_COUNT
    if not m:
        notes.append(f"No number of flats given, using {DEFAULT_COUNT}.")
    if not 1 <= count <= 100:
        return ParsedRequest(False, "Ask for between 1 and 100 flats.")

    d = _DISTRICT.search(t)
    if d:
        n = int(d.group(1))
        if not 1 <= n <= 22:
            return ParsedRequest(False, "Prague districts run from Praha 1 to Praha 22.")
        district = f"Praha {n}"
    elif _PRAGUE_ONLY.search(t):
        district = DEFAULT_DISTRICT
        notes.append(f"No district number given, using {DEFAULT_DISTRICT}. Say for example 'Praha 2'.")
    else:
        district = DEFAULT_DISTRICT
        notes.append(f"No district given, using {DEFAULT_DISTRICT}.")

    r = _RENT.search(t)
    rent = _money(r.group(1), r.group(2)) if r else None
    if rent is None:
        rent = DEFAULT_MAX_RENT
        notes.append(f"No maximum rent given, using {DEFAULT_MAX_RENT:,} CZK per month.")
    elif rent < 1000 and not (r and r.group(2)):
        rent *= 1000
        notes.append(f"Read the rent cap as {rent:,} CZK per month.")
    if not 1000 <= rent <= 1_000_000:
        return ParsedRequest(False, "Maximum rent should be between 1,000 and 1,000,000 CZK per month.")

    job = BoundedJobSpec(count=count, district=district, max_price_czk=rent)
    return ParsedRequest(True, f"{count} flat{'s' if count != 1 else ''} in {district}, up to {rent:,} CZK per month",
                         job, notes)
