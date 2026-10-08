"""Contracts between buyer, seller and dashboard. Change here = tell the team (see INTERFACES.md)."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class DemoMode(StrEnum):
    """Seller behaviour for the demo acts. Anything but `honest` is STAGED and labelled so."""

    honest = "honest"  # Act 1: fair haggle, real delivery
    con = "con"  # Act 2: Viktor fakes a manager approval at 25 tADA
    junk = "junk"  # Act 4: Viktor delivers garbage, verifier refunds


# ---------- dashboard -> buyer ----------


class JobSpec(BaseModel):
    count: int = 20
    district: str = "Praha 7"
    max_price_czk: int = 25_000


class TaskCreate(BaseModel):
    text: str = "Find me 20 flats in Prague 7 under 25,000 CZK"
    budget: float = 20
    job: JobSpec = Field(default_factory=JobSpec)
    demo_mode: DemoMode = DemoMode.honest


class TaskCreated(BaseModel):
    task_id: str
    deal_id: str


class ApprovalDecision(BaseModel):
    approve: bool


# ---------- buyer <-> seller: haggle (custom, not MIP-003) ----------

Action = Literal["open", "counter", "accept", "walk"]


class NegotiateRequest(BaseModel):
    deal_id: str
    round: int
    action: Action  # buyer's move; "open" asks the seller for an opening price
    offer: float | None = None  # tADA
    message: str = ""
    job: JobSpec = Field(default_factory=JobSpec)
    demo_mode: DemoMode = DemoMode.honest


class NegotiateResponse(BaseModel):
    deal_id: str
    round: int
    action: Literal["counter", "accept", "walk"]
    price: float  # seller's current price in tADA
    message: str


# ---------- buyer <-> seller: MIP-003 (field names: verify against Masumi docs) ----------


class StartJobRequest(BaseModel):
    identifier_from_purchaser: str  # = deal_id, our idempotency key
    input_data: dict[str, Any]  # {"deal_id", "agreed_price", "job": JobSpec, "demo_mode"}


class StartJobResponse(BaseModel):
    status: Literal["success", "error"]
    job_id: str
    price: float
    blockchainIdentifier: str | None = None  # set in masumi mode; buyer pays against it
    message: str = ""


JobStatus = Literal["awaiting_payment", "running", "completed", "failed"]


class Flat(BaseModel):
    title: str
    price_czk: int
    district: str
    url: str


class JobResult(BaseModel):
    flats: list[Flat]
    source: Literal["sample", "apify"]  # "sample" = canned data, must be labelled in UI


class StatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: JobResult | None = None


# ---------- buyer -> dashboard: SSE event ----------

EventType = Literal[
    "task_created",
    "negotiation",  # data: speaker, text, price, action, audio_url
    "quote",  # data: agreed price
    "needs_approval",
    "approved",
    "blocked",  # data: reason
    "escrow_locked",
    "already_paid",  # Act 3: restart found deal paid, did not pay twice
    "delivered",
    "verified",  # data: ok, checks
    "released",
    "refunded",
    "walked_away",
    "balances",  # data: buyer, seller, escrow
    "error",
]


class Event(BaseModel):
    id: int
    ts: float
    type: EventType
    task_id: str | None = None
    deal_id: str | None = None
    simulated: bool  # True = money is SIMULATED; UI must show it
    staged: bool = False  # True = demo act forced this behaviour; UI must show it
    data: dict[str, Any] = Field(default_factory=dict)
