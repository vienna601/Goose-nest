# services/geese_source.py — Canada Goose occurrence data from iNaturalist. Cached to disk.
from __future__ import annotations
import json, os, time
import httpx

INAT_URL = "https://api.inaturalist.org/v1/observations"
CANADA_GOOSE_TAXON = 7089
CACHE_PATH = os.environ.get("GEESE_CACHE", "geese_inat.json")

# Waterloo tri-city bounding box (matches the geocode bias box).
BBOX = dict(swlat=43.36, swlng=-80.62, nelat=43.53, nelng=-80.44)

UA = "goose-nest-hackathon/1.0 (rental search project)"   # iNat asks apps to identify themselves


def fetch_geese_points(force: bool = False) -> list[dict]:
    """All research-grade Canada Goose sightings in the Waterloo box, as
    [{'lat','lng','year'}]. Cached to disk; force=True refetches."""
    if not force and os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)

    points, id_above = [], 0
    with httpx.Client(timeout=30, headers={"User-Agent": UA}) as c:
        while True:
            params = {
                "taxon_id": CANADA_GOOSE_TAXON,
                "quality_grade": "research",
                "geo": "true",
                "per_page": 200,
                "order_by": "id", "order": "asc",
                "id_above": id_above,          # cursor pagination — works past the 10k window
                **BBOX,
            }
            r = c.get(INAT_URL, params=params)
            r.raise_for_status()
            results = r.json().get("results", [])
            if not results:
                break
            for o in results:
                g = o.get("geojson")
                if not g:
                    continue
                lng, lat = g["coordinates"]     # iNat gives [lng, lat]
                points.append({"lat": lat, "lng": lng, "year": (o.get("observed_on") or "")[:4]})
            id_above = results[-1]["id"]
            print(f"  {len(points)} observations so far...")
            time.sleep(1.0)                     # be polite to iNat (they ask <1 req/sec)

    with open(CACHE_PATH, "w") as f:
        json.dump(points, f)
    print(f"cached {len(points)} Canada Goose observations -> {CACHE_PATH}")
    return points


if __name__ == "__main__":
    fetch_geese_points(force=True)