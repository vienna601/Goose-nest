#!/usr/bin/env python
"""Prove the Supabase plumbing before you rely on it.

    .venv/bin/python scripts/check_db.py

Writes one fake listing, reads it back through the Pydantic model, upserts it a
second time to confirm re-runs update instead of duplicating, then deletes it.
Leaves the database exactly as it found it.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from postgrest.exceptions import APIError  # noqa: E402

from shared.db import (  # noqa: E402
    MissingCredentials,
    count_listings,
    get_client,
    make_listing_id,
    upsert_listings,
)
from shared.schema import ContactMethod, Listing, Source  # noqa: E402

PROBE_SOURCE_ID = "__connectivity_probe__"


def probe() -> Listing:
    return Listing(
        id=make_listing_id(Source.RENT_PANDA, PROBE_SOURCE_ID),
        source=Source.RENT_PANDA,
        source_id=PROBE_SOURCE_ID,
        url="https://example.invalid/probe",
        address_raw="1 Probe St, Waterloo, ON",
        address_normalized="1 probe street",
        postal_prefix="N2L",
        price_min=1800,
        price_max=1800,
        beds=2.0,
        baths=1.0,
        contact_method=ContactMethod.FORM,
        scraped_at=datetime.now(timezone.utc),
        cache_key="probe",
    )


def main() -> int:
    try:
        client = get_client()
    except MissingCredentials as exc:
        print(f"FAIL  {exc}")
        return 1

    try:
        before = count_listings()
    except APIError as exc:
        if exc.code == "PGRST205":
            print("FAIL  connected, but the tables aren't there yet.\n"
                  "      Supabase Dashboard -> SQL Editor -> paste all of\n"
                  "      shared/schema.sql -> Run. Then re-run this script.")
        elif exc.code == "PGRST125":
            print("FAIL  SUPABASE_URL should be just https://<ref>.supabase.co\n"
                  "      — no /rest/v1 on the end. The client appends it.")
        else:
            print(f"FAIL  {exc.code}: {exc.message}")
        return 1
    print(f"connected. listings table currently holds {before} rows")

    n = upsert_listings([probe()])
    print(f"upsert wrote {n} row")

    rows = (
        client.table("listings")
        .select("*")
        .eq("source_id", PROBE_SOURCE_ID)
        .execute()
        .data
    )
    if len(rows) != 1:
        print(f"FAIL  expected 1 probe row, found {len(rows)}")
        return 1
    round_tripped = Listing.model_validate(rows[0])
    print(f"read back and validated: {round_tripped.address_raw} @ ${round_tripped.price_max}")

    upsert_listings([probe()])
    again = (
        client.table("listings")
        .select("id")
        .eq("source_id", PROBE_SOURCE_ID)
        .execute()
        .data
    )
    if len(again) != 1:
        print(f"FAIL  second upsert duplicated the row ({len(again)} rows). "
              "Check the unique (source, source_id) constraint.")
        return 1
    print("second upsert updated in place — re-running the pull is safe")

    client.table("listings").delete().eq("source_id", PROBE_SOURCE_ID).execute()
    after = count_listings()
    print(f"cleaned up. listings back to {after} rows")

    if after != before:
        print(f"FAIL  row count changed ({before} -> {after})")
        return 1

    print("\nOK — schema, credentials, upsert and the Pydantic contract all line up.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
