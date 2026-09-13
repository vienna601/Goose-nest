"""
Supabase access for the collector and the agent. Server-side only.

Everything here uses the SECRET key (sb_secret_...), which bypasses RLS. That
is correct for this module and only this module — it runs on our machines and
on the backend, never in B's bundle. The frontend reads with the PUBLISHABLE
key (sb_publishable_...), which RLS pins to SELECT (see shared/schema.sql).

Usage from a parser / run.py:

    from shared.db import upsert_listings
    n = upsert_listings(listings)   # list[Listing]

Re-running the full pull is safe: rows are matched on (source, source_id) and
updated in place, never duplicated.
"""

from __future__ import annotations

import functools
import os
import uuid
from typing import Any, Iterable, Iterator, Optional, Sequence

from dotenv import load_dotenv
from supabase import Client, create_client

from shared.schema import Inquiry, Listing, Source

load_dotenv()

# PostgREST will happily take more, but a hackathon Wi-Fi round trip with 500
# listings is a few hundred KB and completes reliably. Don't raise this.
_CHUNK = 500

# Fixed namespace for deterministic listing ids. Never change it — every id in
# the database derives from it.
_LISTING_NS = uuid.UUID("6f0a9b2c-3d4e-5f60-8a1b-2c3d4e5f6071")


class MissingCredentials(RuntimeError):
    pass


def make_listing_id(source: Source | str, source_id: str) -> str:
    """Deterministic uuid for a listing, derived from (source, source_id).

    schema.py's convention says uuid4 for our ids. This is a deliberate,
    narrow exception for `listings` only, and it buys three things:

      * re-running the collector produces the same id, so upserts never
        renumber a row that an `inquiries.listing_id` FK points at;
      * the id a parser holds in memory is the id in the database, so you can
        write an inquiry without reading the listing back first;
      * dedupe (A8) can reason about ids offline.

    Inquiries and lease analyses keep uuid4 — they have no natural key.
    """
    value = source.value if isinstance(source, Source) else str(source)
    return str(uuid.uuid5(_LISTING_NS, f"{value}:{source_id}"))


def _normalize_url(url: str) -> str:
    """Accept what the dashboard actually puts on your clipboard.

    The Data API panel shows the full endpoint, `https://<ref>.supabase.co/rest/v1`,
    but the client appends `/rest/v1` itself — paste it verbatim and every request
    goes to /rest/v1/rest/v1/... and PostgREST answers PGRST125, which does not
    mention the URL at all. Strip it here so nobody loses twenty minutes to it.
    """
    url = url.strip().rstrip("/")
    for suffix in ("/rest/v1", "/rest"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url.rstrip("/")


@functools.lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    # SUPABASE_SERVICE_ROLE_KEY is the legacy name for the same thing. Accepted
    # so a teammate with an older .env isn't dead in the water, but .env.example
    # only documents the current one.
    key = os.environ.get("SUPABASE_SECRET_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    if not url or not key:
        raise MissingCredentials(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set. "
            "Copy .env.example to .env and fill them in from "
            "Supabase Dashboard -> Project Settings -> API Keys."
        )

    # The two keys look alike at a glance and sit next to each other in the
    # dashboard. Getting them backwards fails in a confusing way here (RLS
    # silently blocks every write) and a dangerous way in the frontend (the
    # secret key ends up in a public bundle). So: check, loudly.
    if key.startswith("sb_publishable_"):
        raise MissingCredentials(
            "SUPABASE_SECRET_KEY holds a PUBLISHABLE key (sb_publishable_...). "
            "The two are swapped in your .env. The secret key starts with "
            "sb_secret_ and never leaves the server."
        )

    return create_client(_normalize_url(url), key)


def _chunked(rows: Sequence[Any], size: int = _CHUNK) -> Iterator[Sequence[Any]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


# ---------------------------------------------------------------------------
# listings
# ---------------------------------------------------------------------------

def upsert_listings(listings: Iterable[Listing]) -> int:
    """Insert or update listings, matched on (source, source_id).

    Returns the number of rows the database wrote back. The `id` on each row is
    forced to make_listing_id(), so a Listing built with a stray uuid4 still
    lands on the same row it landed on last run.
    """
    rows = []
    for listing in listings:
        row = listing.model_dump(mode="json")
        row["id"] = make_listing_id(listing.source, listing.source_id)
        rows.append(row)

    if not rows:
        return 0

    client = get_client()
    written = 0
    for chunk in _chunked(rows):
        resp = (
            client.table("listings")
            .upsert(list(chunk), on_conflict="source,source_id")
            .execute()
        )
        written += len(resp.data or [])
    return written


def fetch_listings(
    source: Optional[Source] = None,
    limit: int = 1000,
) -> list[Listing]:
    """Read listings back out, validated through the Pydantic model.

    This round-trips the contract: if a column drifts from schema.py, this is
    where it blows up, loudly, instead of silently in B's UI.
    """
    query = get_client().table("listings").select("*").limit(limit)
    if source is not None:
        query = query.eq("source", source.value)
    return [Listing.model_validate(row) for row in (query.execute().data or [])]


def get_listing(listing_id: str) -> Optional[Listing]:
    rows = get_client().table("listings").select("*").eq("id", listing_id).limit(1).execute().data
    return Listing.model_validate(rows[0]) if rows else None


def count_listings() -> int:
    resp = get_client().table("listings").select("id", count="exact").limit(1).execute()
    return resp.count or 0


# ---------------------------------------------------------------------------
# inquiries — the agent's unit of work (A13/A14)
# ---------------------------------------------------------------------------

def insert_inquiry(inquiry: Inquiry) -> dict[str, Any]:
    row = inquiry.model_dump(mode="json")
    resp = get_client().table("inquiries").insert(row).execute()
    return (resp.data or [{}])[0]


def get_inquiry(inquiry_id: str) -> Optional[Inquiry]:
    rows = get_client().table("inquiries").select("*").eq("id", inquiry_id).limit(1).execute().data
    return Inquiry.model_validate(rows[0]) if rows else None


def update_inquiry(inquiry_id: str, **fields: Any) -> dict[str, Any]:
    """Patch an inquiry in flight — status, steps, viewer_url, approved_at.

    The `submitted_requires_approval` check constraint means the database will
    reject a submitted_at without an approved_at. Let it. That rejection is the
    safety rail, not a bug to route around.
    """
    resp = (
        get_client().table("inquiries").update(fields).eq("id", inquiry_id).execute()
    )
    return (resp.data or [{}])[0]
