"""
Raw scraped dicts -> shared.schema.Listing.

Every quirk handled here was found in real data, not imagined. See the
docstrings — if you remove a guard, check the fixture first.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from shared.schema import ContactMethod, LeaseType, Listing, ListingKind, Source

# City of Waterloo only. Kitchener/Cambridge ride the tri-city toggle.
# NOTE: the original plan listed N2M as Waterloo. It is Kitchener — it was
# classifying 652 Victoria St S, Kitchener as a Waterloo listing. Removed.
WATERLOO_PREFIXES = {"N2J", "N2K", "N2L", "N2T", "N2V"}
TRI_CITY = {"waterloo", "kitchener", "cambridge"}

# Kitchener-Waterloo-Cambridge bounding box — the same one C's geocoder biases
# to (backend/services/geocode.py WATERLOO_BOUNDS). Anything outside it is a bad
# pin, not a Waterloo listing.
KW_BOX = (43.36, -80.62, 43.53, -80.44)   # south, west, north, east


def plausible_coords(lat: Optional[float], lng: Optional[float]) -> bool:
    if lat is None or lng is None:
        return False
    south, west, north, east = KW_BOX
    return south <= lat <= north and west <= lng <= east


def _coords(lat: Any, lng: Any) -> tuple[Optional[float], Optional[float]]:
    """Drop coordinates that can't be right. A missing walk time is better than
    "1110 min walk to Fairway". The original values stay in `raw`."""
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return None, None
    return (lat, lng) if plausible_coords(lat, lng) else (None, None)


_POSTAL = re.compile(r"\b([A-Z]\d[A-Z])\s*\d[A-Z]\d\b", re.I)


def norm_city(city: Optional[str]) -> str:
    """Rent Panda ships both 'Kitchener' and 'kitchener'. Compare lowered, always."""
    return (city or "").strip().lower()


def parse_price(value: Any) -> Optional[int]:
    """Prices arrive as '2950', '$1,795', '1650.00', or None. Integer dollars out."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) or None
    digits = re.sub(r"[^\d.]", "", str(value))
    if not digits:
        return None
    try:
        return int(float(digits)) or None
    except ValueError:
        return None


def parse_beds(value: Any) -> tuple[Optional[float], bool]:
    """Returns (beds, den). 'Studio'/'Bachelor' -> 0.0. '1+den' -> (1.0, True)."""
    if value is None:
        return None, False
    text = str(value).strip().lower()
    den = "den" in text
    if "studio" in text or "bachelor" in text:
        return 0.0, den
    m = re.search(r"\d+(?:\.\d+)?", text)
    return (float(m.group()) if m else None), den


def parse_date(value: Any) -> Optional[str]:
    """Bamboo ships a few RentFrom values with an extended-year format
    ('+020260-09-01T...') that no date parser accepts. One bad row should not
    kill a 248-row batch, so anything that isn't a plain YYYY-MM-DD is dropped.
    """
    if not value:
        return None
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", str(value))
    return m.group(1) if m else None


def postal_prefix(address: Optional[str]) -> Optional[str]:
    m = _POSTAL.search(address or "")
    return m.group(1).upper() if m else None


def in_waterloo(city: Optional[str], address: Optional[str], tri_city: bool = False) -> bool:
    """Postal prefix is authoritative; city name is the fallback when it's absent."""
    prefix = postal_prefix(address)
    if prefix:
        return prefix in WATERLOO_PREFIXES if not tri_city else prefix.startswith("N2")
    c = norm_city(city)
    return c in TRI_CITY if tri_city else c == "waterloo"


def _slug_address(url: Optional[str]) -> Optional[str]:
    """30 of 88 Rent Panda listings have address=None. The URL slug still carries it:
    /for-rent/135-pine-st-windsor-on-n9a-6c8-canada-hogd7f/20208/20678/details"""
    if not url:
        return None
    m = re.search(r"/for-rent/([^/]+)/", url)
    if not m:
        return None
    slug = re.sub(r"-[a-z0-9]{6}$", "", m.group(1))       # trailing hash
    return slug.replace("-", " ").title() or None


def normalize_address(address: Optional[str]) -> str:
    """Lowercased, punctuation-stripped, for dedupe comparison."""
    a = (address or "").lower()
    a = re.sub(r"\b(canada|on|ontario)\b", " ", a)
    a = re.sub(r"[^\w\s]", " ", a)
    return re.sub(r"\s+", " ", a).strip()


def from_rent_panda(raw: dict, cache_key: str) -> Listing:
    """Inertia payload item -> Listing. Field names are theirs, verbatim."""
    address = raw.get("address") or raw.get("title") or _slug_address(raw.get("url"))
    price = parse_price(raw.get("price"))
    beds, den = parse_beds(raw.get("bedroom_name") or raw.get("bedrooms"))
    url = raw.get("url") or ""
    if url.startswith("/"):
        url = "https://app.rentpanda.ca" + url

    return Listing(
        id=str(uuid.uuid4()),
        source=Source.RENT_PANDA,
        source_id=str(raw.get("property_detail_id") or raw.get("id")),
        url=url,
        address_raw=address,
        address_normalized=normalize_address(address),
        city=(raw.get("city") or "").strip().title() or "Unknown",
        postal_prefix=postal_prefix(address),
        lat=_coords(raw.get("latitude"), raw.get("longitude"))[0],
        lng=_coords(raw.get("latitude"), raw.get("longitude"))[1],
        price_min=price,
        price_max=price,          # single price: both set, so filters never branch
        beds=beds,
        den=den,
        baths=float(raw["bathrooms"]) if raw.get("bathrooms") is not None else None,
        available_date=parse_date(raw.get("available_date")),
        contact_method=ContactMethod.FORM,   # confirm on the detail page
        contact_url=url,
        image_url=raw.get("image"),
        images=[raw["image"]] if raw.get("image") else [],
        scraped_at=datetime.now(timezone.utc),
        cache_key=cache_key,
        raw=raw,
    )


def from_bamboo(raw: dict, cache_key: str) -> Listing:
    """Bamboo Housing __NEXT_DATA__ item -> Listing.

    These are ROOMS in shared student houses, not whole units: a 5-bedroom house
    with one room free at $695. listing_kind='room' keeps ranking honest.
    """
    address = raw.get("Address")
    lease_raw = raw.get("LeaseType") or ""
    is_sublet = "sublet" in lease_raw.lower()
    term = raw.get("RentDuration")

    return Listing(
        id=str(uuid.uuid4()),
        source=Source.BAMBOO,
        source_id=str(raw["_id"]),
        # Bamboo has no per-listing permalink — I checked /listing/<id>,
        # /listings/<id>, /property/<id> and friends; all 404. The cards render
        # client-side off /homepage's payload. The id lives in `raw`.
        url="https://bamboohousing.ca/homepage",
        address_raw=address,
        address_normalized=normalize_address(address),
        city="Waterloo",
        postal_prefix=postal_prefix(address),
        lat=_coords(raw.get("Latitude"), raw.get("Longitude"))[0],
        lng=_coords(raw.get("Latitude"), raw.get("Longitude"))[1],
        price_min=parse_price(raw.get("Price")),
        price_max=parse_price(raw.get("Price")),
        listing_kind=ListingKind.ROOM,
        beds=1.0,                                     # one room on offer
        total_bedrooms=raw.get("TotalBedrooms"),
        rooms_available=raw.get("RoomsAvailable"),
        is_available=bool(raw.get("IsAvailable", True)),
        lease_type=LeaseType.SUBLET if is_sublet else LeaseType.LEASE,
        term_months=int(term) if term else None,
        available_date=parse_date(raw.get("RentFrom")),
        # No anonymous contact path: the bundle only exposes /api/mylistings,
        # /api/profiles etc. behind an Authorization token. The agent cannot
        # reach these, and we do not create accounts. Inventory only.
        contact_method=ContactMethod.ACCOUNT_REQUIRED,
        contact_url="https://bamboohousing.ca/homepage",
        image_url=raw.get("MainUrl"),
        images=raw.get("ImageUrls") or [],
        scraped_at=datetime.now(timezone.utc),
        cache_key=cache_key,
        raw=raw,
    )
