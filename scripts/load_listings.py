#!/usr/bin/env python
"""Normalize the cached fixtures and push them into Supabase.

    .venv/bin/python scripts/load_listings.py --dry-run   # parse only, no DB
    .venv/bin/python scripts/load_listings.py             # Waterloo only
    .venv/bin/python scripts/load_listings.py --tri-city  # + Kitchener/Cambridge

Reads from collection/fixtures/, never from the network — re-run it as often as
you like. Rows upsert on (source, source_id), so this never duplicates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collection.normalize import from_bamboo, from_rent_panda, in_waterloo  # noqa: E402
from shared.schema import Listing  # noqa: E402

FIXTURES = [
    ("bamboo_all.json", from_bamboo),
    ("rent_panda_all.json", from_rent_panda),
]


def build(tri_city: bool) -> list[Listing]:
    rows: list[Listing] = []
    for filename, normalizer in FIXTURES:
        path = ROOT / "collection" / "fixtures" / filename
        if not path.exists():
            print(f"  skip {filename} (not found)")
            continue
        raw = json.loads(path.read_text())
        parsed, failed = [], 0
        for item in raw:
            try:
                parsed.append(normalizer(item, "fixture"))
            except Exception as exc:
                failed += 1
                if failed == 1:
                    print(f"  ! {filename}: {type(exc).__name__}: {str(exc)[:90]}")
        kept = [r for r in parsed if in_waterloo(r.city, r.address_raw, tri_city)]
        print(f"  {filename:<22} {len(parsed):>4}/{len(raw)} parsed, "
              f"{len(kept):>4} in geofence" + (f", {failed} FAILED" if failed else ""))
        rows.extend(kept)
    return rows


def fill_coords(rows: list[Listing]) -> list[Listing]:
    """Geocode rows whose coordinates were missing or implausible (see
    collection/geocode.py). Cache-first, so this is offline after one run."""
    from collection.geocode import geocode

    missing = [r for r in rows if r.lat is None]
    if not missing:
        return rows
    fixed = {}
    for r in missing:
        hit = geocode(r.address_raw) if r.address_raw else None
        if hit:
            fixed[r.source_id] = r.model_copy(update={"lat": hit[0], "lng": hit[1]})
    print(f"  coords: {len(missing)} missing/implausible, {len(fixed)} geocoded"
          + (f", {len(missing) - len(fixed)} left without coords" if len(missing) > len(fixed) else ""))
    return [fixed.get(r.source_id, r) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tri-city", action="store_true", help="include Kitchener/Cambridge")
    ap.add_argument("--dry-run", action="store_true", help="parse only, don't touch the DB")
    args = ap.parse_args()

    print("normalizing fixtures:")
    rows = build(args.tri_city)
    if not rows:
        print("nothing to load")
        return 1

    rows = fill_coords(rows)
    print(f"\n{len(rows)} listings ready")
    print("  by source:", dict(Counter(r.source.value for r in rows)))
    print("  by kind:  ", dict(Counter(r.listing_kind.value for r in rows)))
    print("  by lease: ", dict(Counter(r.lease_type.value if r.lease_type else "?" for r in rows)))
    prices = sorted(r.price_min for r in rows if r.price_min)
    if prices:
        print(f"  price:     ${prices[0]}–${prices[-1]}, median ${prices[len(prices)//2]}")
    print(f"  with coords: {sum(1 for r in rows if r.lat)}/{len(rows)}")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 0

    from shared.db import MissingCredentials, count_listings, upsert_listings

    try:
        before = count_listings()
        written = upsert_listings(rows)
        after = count_listings()
    except MissingCredentials as exc:
        print(f"\nFAIL  {exc}")
        return 1

    print(f"\nupserted {written} rows. listings: {before} -> {after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
