"""Event bus feeding the dashboard SSE stream. History is persisted, so a reload or restart replays it."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from buyer.ledger import Ledger
from shared.models import Event, EventType

log = logging.getLogger("astra.events")


class EventBus:
    def __init__(self, ledger: Ledger, simulated: bool):
        self.ledger = ledger
        self.simulated = simulated
        self.history = [Event(**e) for e in ledger.load_events()]
        self._next_id = (self.history[-1].id + 1) if self.history else 1
        self._subscribers: set[asyncio.Queue[Event]] = set()

    def emit(
        self,
        type: EventType,
        task_id: str | None = None,
        deal_id: str | None = None,
        staged: bool = False,
        **data: Any,
    ) -> Event:
        ev = Event(
            id=self._next_id,
            ts=time.time(),
            type=type,
            task_id=task_id,
            deal_id=deal_id,
            simulated=self.simulated,
            staged=staged,
            data=data,
        )
        self._next_id += 1
        self.history.append(ev)
        self.ledger.append_event(ev.id, ev.model_dump())
        tags = ("[SIMULATED]" if self.simulated else "") + ("[STAGED]" if staged else "")
        log.info("%s %s deal=%s %s", tags, type, deal_id, data)
        for q in self._subscribers:
            q.put_nowait(ev)
        return ev

    async def stream(self, ping_seconds: float = 15) -> AsyncIterator[Event | None]:
        """Replay history, then live events. Yields None as a keep-alive tick."""
        q: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.add(q)
        try:
            for ev in list(self.history):
                yield ev
            while True:
                try:
                    yield await asyncio.wait_for(q.get(), ping_seconds)
                except TimeoutError:
                    yield None
        finally:
            self._subscribers.discard(q)
