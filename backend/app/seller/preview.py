"""Preview photos for delivered findings: read each page's og:image / twitter:image.

The page URLs come from a model that read the open web, so they are untrusted. This fetch is therefore narrow:
https only, port 443 only, public IP addresses only (checked for the first URL and for every redirect), a few
seconds and a few hundred kilobytes per page, no cookies, no credentials. Anything that fails just means no photo.
The image itself is never downloaded here; the dashboard loads it in the browser.
"""

import asyncio
import html
import ipaddress
import logging
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx

log = logging.getLogger("astra.seller.preview")

MAX_PAGE_BYTES = 300_000
MAX_REDIRECTS = 3
PAGE_TIMEOUT = 6.0
TOTAL_TIMEOUT = 15.0
MAX_CONCURRENT = 4
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AstraPreview/1.0)", "Accept": "text/html,application/xhtml+xml"}

_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""([a-zA-Z:_-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_IMAGE_KEYS = ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src")


async def _public_host(host: str) -> bool:
    """True only when every address the name resolves to is a public one."""
    if not host:
        return False
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
                return False
        except ValueError:
            return False
    return True


async def _allowed(url: str) -> bool:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme != "https" or parts.username or parts.password or port not in (None, 443):
        return False
    return await _public_host(parts.hostname or "")


def image_from_html(markup: str, base_url: str) -> str | None:
    """The first usable preview image URL in a page, made absolute. Only https images are accepted."""
    found: dict[str, str] = {}
    for tag in _META.findall(markup):
        attrs = {m.group(1).lower(): html.unescape(m.group(2) if m.group(2) is not None else m.group(3)) for m in _ATTR.finditer(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        if key in _IMAGE_KEYS and attrs.get("content", "").strip() and key not in found:
            found[key] = attrs["content"].strip()
    for key in _IMAGE_KEYS:
        if key in found:
            absolute = urljoin(base_url, found[key])
            if absolute.lower().startswith("https://") and len(absolute) <= 500 and urlsplit(absolute).hostname:
                return absolute
    return None


async def _read_page(client: httpx.AsyncClient, url: str) -> tuple[str, str] | None:
    for _ in range(MAX_REDIRECTS + 1):
        if not await _allowed(url):
            return None
        async with client.stream("GET", url, headers=HEADERS) as response:
            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    return None
                url = urljoin(url, location)
                continue
            if response.status_code != 200 or "html" not in response.headers.get("content-type", "").lower():
                return None
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) >= MAX_PAGE_BYTES:
                    break
            return body[:MAX_PAGE_BYTES].decode("utf-8", errors="replace"), url
    return None


async def find_image(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        page = await asyncio.wait_for(_read_page(client, url), PAGE_TIMEOUT)
    except Exception as exc:  # a preview is a nicety: never let it fail a delivery
        log.info("no preview for a finding (%s)", type(exc).__name__)
        return None
    return image_from_html(*page) if page else None


async def attach_images(urls: list[str], client: httpx.AsyncClient | None = None) -> dict[str, str]:
    """Map page URL -> preview image URL for the pages that have one."""
    unique = list(dict.fromkeys(urls))
    if not unique:
        return {}
    gate = asyncio.Semaphore(MAX_CONCURRENT)
    own = client is None
    http = client or httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(PAGE_TIMEOUT), trust_env=False)

    async def one(url: str) -> tuple[str, str | None]:
        async with gate:
            return url, await find_image(http, url)

    tasks = [asyncio.create_task(one(u)) for u in unique]
    try:
        await asyncio.wait(tasks, timeout=TOTAL_TIMEOUT)  # keep what finished; slow pages just get no photo
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if own:
            await http.aclose()
    found = {}
    for task in tasks:
        if task.done() and not task.cancelled() and task.exception() is None:
            url, image = task.result()
            if image:
                found[url] = image
    return found
