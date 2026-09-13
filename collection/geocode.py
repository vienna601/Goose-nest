"""
Fallback geocoding for listings whose coordinates are missing or implausible.

Why this exists: our own Rent Panda test listing says "550 King St N, Waterloo"
but its map pin is still downtown Toronto (43.6527, -79.3872) from the address
it was first created with. Every distance downstream came out as "1110 min walk
to Fairway". Four Bamboo rows have no coordinates at all.

OpenStreetMap Nominatim: free, no key. Its usage policy allows light API use —
at most one request a second, with an identifying User-Agent — which is what
this does, and only for the handful of rows that fail the plausibility check.
Results are cached in collection/fixtures/geocoded.json, which is committed, so
re-running the loader (or the demo) never needs the network again.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import httpx

from collection.fetch import USER_AGENT
from collection.normalize import plausible_coords

CACHE = Path(__file__).parent / "fixtures" / "geocoded.json"
_last = [0.0]


def _load() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def geocode(address: str) -> Optional[tuple[float, float]]:
    """(lat, lng) inside the K-W area, or None. Cache first, network second."""
    key = " ".join(address.split())
    cache = _load()
    if key in cache:
        hit = cache[key]
        return (hit["lat"], hit["lng"]) if hit else None

    wait = 1.1 - (time.monotonic() - _last[0])
    if wait > 0:
        time.sleep(wait)
    _last[0] = time.monotonic()
    resp = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": key.removesuffix(" CA") + ", Canada", "format": "jsonv2", "limit": 1, "countrycodes": "ca"},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    resp.raise_for_status()
    results = resp.json()
    hit = None
    # A city- or region-level match ("Waterloo, ON N2L 4H9" with no street) is the
    # middle of town, not the listing. Precise-looking walk times from it would lie.
    if results and results[0].get("addresstype") not in {"city", "town", "municipality", "county", "state", "region", "country"}:
        lat, lng = float(results[0]["lat"]), float(results[0]["lon"])
        if plausible_coords(lat, lng):
            hit = {"lat": lat, "lng": lng, "display_name": results[0].get("display_name", "")}
    cache[key] = hit   # cache misses too, so we don't re-ask
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n")
    return (hit["lat"], hit["lng"]) if hit else None
