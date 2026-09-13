# services/geocode.py — Google geocoding, Waterloo-biased, resumable SQLite cache.
from __future__ import annotations
import os, json, sqlite3, time
from dataclasses import dataclass, asdict
import httpx

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_PATH  = os.environ.get("GEOCODE_CACHE", "geocode_cache.sqlite")
WATERLOO_BOUNDS = "43.36,-80.62|43.53,-80.44"   # bias results into the tri-city box


@dataclass
class GeoResult:
    lat: float | None
    lng: float | None
    postal_code: str | None       # full, e.g. "N2J 3A5"
    postal_prefix: str | None     # FSA, e.g. "N2J"  (geofence uses this)
    location_type: str | None     # ROOFTOP > RANGE_INTERPOLATED > GEOMETRIC_CENTER > APPROXIMATE
    partial_match: bool
    formatted_address: str | None
    status: str                   # OK / ZERO_RESULTS / REQUEST_DENIED / ...


def _key() -> str:
    k = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not k:
        raise RuntimeError("GOOGLE_MAPS_API_KEY not set (add to .env or `export` it)")
    return k

def _cache():
    con = sqlite3.connect(CACHE_PATH)
    con.execute("create table if not exists geo (addr text primary key, json text)")
    return con

def _norm(address: str) -> str:
    return " ".join(address.strip().lower().split())


def geocode_one(address: str, client: httpx.Client | None = None) -> GeoResult:
    con = _cache()
    key = _norm(address)
    row = con.execute("select json from geo where addr=?", (key,)).fetchone()
    if row:
        con.close()
        return GeoResult(**json.loads(row[0]))

    owns = client is None
    client = client or httpx.Client(timeout=15)
    params = {
        "address": address,
        "key": _key(),
        "region": "ca",
        "components": "country:CA|administrative_area:ON",
        "bounds": WATERLOO_BOUNDS,
    }
    result = _request_with_retry(client, params)

    con.execute("insert or replace into geo (addr, json) values (?,?)",
                (key, json.dumps(asdict(result))))
    con.commit(); con.close()
    if owns:
        client.close()
    return result


def _request_with_retry(client, params, max_tries=4) -> GeoResult:
    for attempt in range(max_tries):
        r = client.get(GEOCODE_URL, params=params)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "OK":
            return _parse(data["results"][0], status)
        if status == "ZERO_RESULTS":
            return GeoResult(None, None, None, None, None, False, None, status)
        if status in ("OVER_QUERY_LIMIT", "UNKNOWN_ERROR"):
            time.sleep(2 ** attempt)                 # backoff, then retry
            continue
        return GeoResult(None, None, None, None, None, False, None, status)  # config error
    return GeoResult(None, None, None, None, None, False, None, "RETRY_EXHAUSTED")


def _parse(res: dict, status: str) -> GeoResult:
    loc = res["geometry"]["location"]
    postal = None
    for comp in res.get("address_components", []):
        if "postal_code" in comp.get("types", []):
            postal = comp["long_name"].upper()       # "N2J 3A5"
            break
    prefix = postal.replace(" ", "")[:3] if postal else None
    return GeoResult(
        lat=loc["lat"], lng=loc["lng"],
        postal_code=postal, postal_prefix=prefix,
        location_type=res["geometry"].get("location_type"),
        partial_match=res.get("partial_match", False),
        formatted_address=res.get("formatted_address"),
        status=status,
    )