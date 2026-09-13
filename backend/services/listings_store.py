# services/listings_store.py — where routes get listings from.
#
# Reads the scraped rows out of Supabase (via shared/db.py, secret key, server
# side) and fills any missing enrichment on the fly. Falls back to
# sample_data.SAMPLE_LISTINGS when Supabase isn't configured or is unreachable,
# so the demo still runs on a laptop with no .env.
from __future__ import annotations

import os
import sys
import time

from schema import Listing
from services.enrich import enrich
from sample_data import SAMPLE_LISTINGS

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

TTL_S = 60
_cache: dict = {"at": 0.0, "rows": None, "source": None}


def _enriched(l: Listing) -> Listing:
    if l.lat is None or l.lng is None or l.ion_walk_min is not None:
        return l
    return l.model_copy(update=enrich(l.lat, l.lng))


def _from_supabase() -> list[Listing]:
    from shared.db import get_client   # imported lazily: needs SUPABASE_* env
    rows = get_client().table("listings").select("*").eq("is_available", True).limit(1000).execute().data or []
    # Validate with the backend's `schema.Listing`, not shared.schema.Listing —
    # they're the same file imported under two module names, and pydantic
    # treats them as different classes.
    return [Listing.model_validate(r) for r in rows]


def load_listings() -> list[Listing]:
    now = time.monotonic()
    if _cache["rows"] is not None and now - _cache["at"] < TTL_S:
        return _cache["rows"]
    try:
        rows, source = _from_supabase(), "supabase"
    except Exception as exc:
        print(f"WARN: Supabase listings unavailable ({type(exc).__name__}: {exc}); using sample data")
        rows, source = list(SAMPLE_LISTINGS), "sample"
    _cache.update(at=now, rows=[_enriched(l) for l in rows], source=source)
    return _cache["rows"]


def listings_source() -> str | None:
    return _cache["source"]
