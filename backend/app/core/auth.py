"""Shared-token access control and per-client rate limiting for the buyer and seller services.

Local production only: one static token per service, compared in constant time. An empty token
keeps a service open (development). Pure ASGI so it also covers mounted static files and does not
buffer streaming responses (SSE).
"""

import hmac
import json
import math
import time
from collections import deque
from collections.abc import Callable, Iterable
from urllib.parse import parse_qs

from fastapi import HTTPException, Request

TOKEN_HEADER = "x-api-token"
AUTH_HEADERS = ("authorization", TOKEN_HEADER)


def token_matches(expected: str, provided: str | None) -> bool:
    if not expected or provided is None:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def _header(scope, name: bytes) -> str | None:
    for key, value in scope.get("headers") or ():
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def presented_tokens(scope, allow_query: bool) -> list[str]:
    tokens = []
    auth = _header(scope, b"authorization")
    if auth:
        scheme, _, value = auth.strip().partition(" ")
        if scheme.lower() == "bearer" and value.strip():
            tokens.append(value.strip())
    explicit = _header(scope, TOKEN_HEADER.encode())
    if explicit:
        tokens.append(explicit.strip())
    if allow_query:
        query = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
        tokens.extend(query.get("token", []))
    return tokens


class TokenAuth:
    """Rejects requests without the service token, except for `is_open` paths.

    `allow_query(path)` marks paths whose clients cannot set headers (EventSource, <audio src>),
    where `?token=` is accepted as well.
    """

    def __init__(self, app, token: str, is_open: Callable[[str, str], bool],
                 allow_query: Callable[[str], bool] = lambda path: False):
        self.app, self.token, self.is_open, self.allow_query = app, token, is_open, allow_query

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not self.token:
            return await self.app(scope, receive, send)
        method, path = scope["method"], scope["path"]
        if self.is_open(method, path) or any(
                token_matches(self.token, t) for t in presented_tokens(scope, self.allow_query(path))):
            return await self.app(scope, receive, send)
        body = json.dumps({"detail": "missing or invalid API token"}).encode()
        await send({"type": "http.response.start", "status": 401,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode()),
                                (b"www-authenticate", b"Bearer")]})
        await send({"type": "http.response.body", "body": body})


class RateLimiter:
    """In-memory sliding window per (bucket, client host). `limit` requests per `window` seconds; 0 disables."""

    def __init__(self, limit: int, window: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window, self.clock = limit, window, clock
        self.hits: dict[tuple[str, str], deque[float]] = {}

    def check(self, bucket: str, client: str) -> float | None:
        """Record a hit and return None, or return seconds to wait when the client is over the limit."""
        if self.limit <= 0:
            return None
        now = self.clock()
        cutoff = now - self.window
        if len(self.hits) > 10_000:  # bound memory: forget clients idle for a full window
            for key in [k for k, q in self.hits.items() if not q or q[-1] <= cutoff]:
                del self.hits[key]
        q = self.hits.setdefault((bucket, client), deque())
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= self.limit:
            return max(q[0] + self.window - now, 0.0)
        q.append(now)
        return None

    def dependency(self, bucket: str):
        async def limit(request: Request) -> None:
            wait = self.check(bucket, request.client.host if request.client else "unknown")
            if wait is not None:
                raise HTTPException(429, "too many requests; slow down",
                                    headers={"Retry-After": str(max(1, math.ceil(wait)))})
        return limit


def open_paths(*paths: str, methods: Iterable[str] | None = None) -> Callable[[str, str], bool]:
    allowed_methods = None if methods is None else {m.upper() for m in methods}
    allowed = set(paths)

    def is_open(method: str, path: str) -> bool:
        return path in allowed and (allowed_methods is None or method.upper() in allowed_methods)
    return is_open
