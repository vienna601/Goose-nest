"""
The one way this project talks to the outside world.

Everything goes through fetch(): robots check, per-domain rate limit, retries,
and a write-through disk cache. If you find yourself reaching for httpx
directly in a parser, don't — you'll lose the cache and start hammering
someone's site while you iterate on selectors.

    from collection.fetch import fetch
    html = fetch("https://example.com/listings?page=2")

Second call for the same URL is served from collection/cache/ and never
touches the network. Pass force=True to refresh deliberately.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.robotparser
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()   # without this, SCRAPER_CONTACT_EMAIL below is never seen

CACHE_DIR = Path(__file__).parent / "cache"
MIN_INTERVAL_S = 2.5           # per domain. Be a good guest.
TIMEOUT_S = 25

# Put a real address here (or in .env) before any bulk run. If a site owner
# wants to tell us to stop, they should have a way to do it.
CONTACT = (
    os.getenv("SCRAPER_CONTACT_EMAIL")      # the name .env.example documents
    or os.getenv("SCRAPER_CONTACT")         # older name, still accepted
    or "CONTACT@EXAMPLE.COM"
)
USER_AGENT = f"Mozilla/5.0 (compatible; WaterlooRentalResearch/0.1; +mailto:{CONTACT})"

_last_hit: dict[str, float] = {}
_robots: dict[str, urllib.robotparser.RobotFileParser] = {}


class Blocked(Exception):
    """Site said no — robots.txt, or a bot challenge. Not retryable."""


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:20]}.html"


def _throttle(domain: str) -> None:
    elapsed = time.monotonic() - _last_hit.get(domain, 0.0)
    if elapsed < MIN_INTERVAL_S:
        time.sleep(MIN_INTERVAL_S - elapsed)
    _last_hit[domain] = time.monotonic()


def _robots_allows(url: str) -> bool:
    """Cheap, cached robots.txt check.

    We fetch robots.txt with OUR user-agent via httpx rather than letting
    urllib.robotparser do it. robotparser uses Python's default UA, which a lot
    of WAFs answer with 403 — and robotparser reads a 403 as "disallow the
    entire site". That silently marked rez-one, 4stay and accommod8u as
    off-limits when all three actually allow crawling.

    Status handling follows RFC 9309: 2xx parse, 4xx allow all, 5xx/429 assume
    disallow (the site is unwell; don't pile on).
    """
    domain = _domain(url)
    if domain not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
        try:
            resp = httpx.get(
                robots_url,
                headers={"User-Agent": USER_AGENT},
                timeout=10,
                follow_redirects=True,
            )
            if resp.status_code >= 500 or resp.status_code == 429:
                rp.disallow_all = True
            elif resp.status_code >= 400:
                rp.allow_all = True          # no robots.txt == allowed
            else:
                rp.parse(resp.text.splitlines())
        except Exception:
            rp.allow_all = True              # unreachable robots.txt is not a no
        _robots[domain] = rp
    return _robots[domain].can_fetch(USER_AGENT, url)


def _is_challenge(resp: httpx.Response) -> bool:
    return (
        "cf-mitigated" in resp.headers
        or "Just a moment" in resp.text[:2000]
        or "Enable JavaScript and cookies" in resp.text[:4000]
    )


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _get(url: str) -> httpx.Response:
    _throttle(_domain(url))
    resp = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-CA,en;q=0.9"},
        follow_redirects=True,
        timeout=TIMEOUT_S,
    )
    if resp.status_code in (429, 500, 502, 503, 504):
        resp.raise_for_status()      # retryable
    return resp


def fetch(url: str, force: bool = False) -> str:
    """Return page HTML, from cache when we already have it."""
    path = _cache_path(url)
    if path.exists() and not force:
        return path.read_text(encoding="utf-8")

    if not _robots_allows(url):
        raise Blocked(f"robots.txt disallows {url}")

    resp = _get(url)

    # A bot challenge is a no. We do not work around these — see docs/sources.md.
    if _is_challenge(resp) or resp.status_code == 403:
        raise Blocked(f"{resp.status_code} bot challenge at {_domain(url)}")
    if resp.status_code >= 400:
        raise Blocked(f"{resp.status_code} for {url}")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    path.with_suffix(".meta.json").write_text(
        json.dumps({"url": url, "status": resp.status_code, "fetched_at": time.time()}, indent=1)
    )
    return resp.text


def cache_key(url: str) -> str:
    """The value that goes in Listing.cache_key."""
    return hashlib.sha256(url.encode()).hexdigest()[:20]
