"""Contracts between buyer, seller and dashboard. Change here = tell the team (see INTERFACES.md)."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class DemoMode(StrEnum):
    """Seller behaviour for the demo acts. Anything but `honest` is STAGED and labelled so."""

    honest = "honest"  # Act 1: fair haggle, real delivery
    con = "con"  # Act 2: Viktor fakes a manager approval at 25 tADA
    junk = "junk"  # Act 4: Viktor delivers garbage, verifier refunds


# ---------- dashboard -> buyer ----------


class JobSpec(BaseModel):
    count: int = Field(default=20, ge=1, le=200)
    district: str = Field(default="Praha 7", min_length=1, max_length=100)
    max_price_czk: int = Field(default=25_000, gt=0)

    @field_validator("district")
    @classmethod
    def district_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("district must not be blank")
        return value


def describe_job(job: JobSpec) -> str:
    """The request in one line, used in agent prompts and dialogue so they follow the real job."""
    return f"{job.count} flat{'s' if job.count != 1 else ''} in {job.district} under {job.max_price_czk:,} CZK per month"


class BoundedJobSpec(JobSpec):
    """JobSpec as accepted from the network. The seller builds `count` listings in-process, so an
    unbounded count can stall it for every deal. Adapters keep taking plain JobSpec (they re-check themselves)."""

    count: int = Field(default=20, ge=1, le=100)
    district: str = Field(default="Praha 7", min_length=1, max_length=64)
    max_price_czk: int = Field(default=25_000, ge=1, le=1_000_000)


class TaskCreate(BaseModel):
    text: str = Field(default="Find me 20 flats in Prague 7 under 25,000 CZK", max_length=500)
    budget: float = Field(default=20, gt=0, le=1000, allow_inf_nan=False)
    job: BoundedJobSpec = Field(default_factory=BoundedJobSpec)
    demo_mode: DemoMode = DemoMode.honest


class TaskCreated(BaseModel):
    task_id: str
    deal_id: str


class RequestText(BaseModel):
    text: str = Field(default="", max_length=600)


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
    job: BoundedJobSpec = Field(default_factory=BoundedJobSpec)
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
    message: str = ""
    # Masumi mode only (MIP-003 names): the buyer copies these into POST /purchase.
    blockchainIdentifier: str | None = None
    payByTime: str | None = None
    submitResultTime: str | None = None
    unlockTime: str | None = None
    externalDisputeUnlockTime: str | None = None
    agentIdentifier: str | None = None
    sellerVKey: str | None = None
    inputHash: str | None = None


JobStatus = Literal["awaiting_payment", "running", "completed", "failed"]


class Flat(BaseModel):
    title: str
    price_czk: int = Field(strict=True)
    district: str
    url: str


class JobResult(BaseModel):
    flats: list[Flat]
    source: Literal["sample", "apify", "apify_cached"]  # provenance must be labelled in UI
    fetched_at: str | None = None
    actor_id: str | None = None
    dataset_id: str | None = None
    run_id: str | None = None


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
    "controls_updated",  # data: the operator controls that changed
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
