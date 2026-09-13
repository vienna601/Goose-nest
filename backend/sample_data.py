from datetime import datetime, timezone, date
from schema import Listing, Source, ContactMethod

NOW = datetime(2026, 9, 12, tzinfo=timezone.utc)


def _mk(**kw) -> Listing:
    kw.setdefault("scraped_at", NOW)
    kw.setdefault("cache_key", f"sha-{kw['source_id']}")
    return Listing(**kw)


SAMPLE_LISTINGS: list[Listing] = [
    # 1) Downtown Waterloo, steps from Waterloo Public Square ION, no geese.
    _mk(
        id="00000000-0000-0000-0000-000000000001",
        source=Source.RENTALS_CA, source_id="id100001",
        url="https://rentals.ca/waterloo/50-regina-st-n-id100001",
        cluster_id="cluster-regina50",
        address_raw="50 Regina St N, Waterloo, ON",
        address_normalized="50 regina street north waterloo on",
        postal_prefix="N2L", postal_code="N2J 3A5",
        lat=43.4665, lng=-80.5230,
        price_min=2100, price_max=2100, beds=2.0, baths=1.0,
        contact_method=ContactMethod.FORM,
        image_url="https://example.com/1.jpg",
    ),
    # 2) Right on Waterloo Park — great ION, geese hellscape.
    _mk(
        id="00000000-0000-0000-0000-000000000002",
        source=Source.RENT_PANDA, source_id="id100002",
        url="https://app.rentpanda.ca/listing/id100002",
        address_raw="120 Westmount Rd N, Waterloo, ON",
        address_normalized="120 westmount road north waterloo on",
        postal_prefix="N2L", postal_code="N2L 3G6",
        lat=43.4668, lng=-80.5300,
        price_min=1800, price_max=1800, beds=1.0, baths=1.0,
        contact_method=ContactMethod.EMAIL, contact_email="landlord@example.com",
        available_date=date(2026, 10, 1),
        image_url="https://example.com/2.jpg",
    ),
    # 3) Near UW / Columbia Lake — close to R&T ION, heavy geese, price RANGE.
    _mk(
        id="00000000-0000-0000-0000-000000000003",
        source=Source.RENTALS_CA, source_id="id100003",
        url="https://rentals.ca/waterloo/330-columbia-st-w-id100003",
        address_raw="330 Columbia St W, Waterloo, ON",
        address_normalized="330 columbia street west waterloo on",
        postal_prefix="N2T", postal_code="N2T 0C2",
        lat=43.4760, lng=-80.5560,
        price_min=2600, price_max=2900, beds=3.0, baths=2.0,
        contact_method=ContactMethod.FORM, contact_behind_click=True,
        image_url="https://example.com/3.jpg",
    ),
    # 4) Suburban east Waterloo — far from ION, no geese.
    _mk(
        id="00000000-0000-0000-0000-000000000004",
        source=Source.RENT_PANDA, source_id="id100004",
        url="https://app.rentpanda.ca/listing/id100004",
        address_raw="55 Eastbridge Blvd, Waterloo, ON",
        address_normalized="55 eastbridge boulevard waterloo on",
        postal_prefix="N2K", postal_code="N2K 4H9",
        lat=43.4900, lng=-80.4900,
        price_min=2400, price_max=2400, beds=2.0, baths=1.5,
        contact_method=ContactMethod.PHONE, contact_phone="519-555-0134",
        image_url="https://example.com/4.jpg",
    ),
    # 5) Kitchener, near Fairway ION — only shows up with tri-city toggle on.
    _mk(
        id="00000000-0000-0000-0000-000000000005",
        source=Source.RENTALS_CA, source_id="id100005",
        url="https://rentals.ca/kitchener/2960-kingsway-dr-id100005",
        address_raw="2960 Kingsway Dr, Kitchener, ON",
        address_normalized="2960 kingsway drive kitchener on",
        postal_prefix="N2C", postal_code="N2C 1X1",
        lat=43.4205, lng=-80.4410,
        price_min=1600, price_max=1600, beds=1.0, den=True, baths=1.0,
        contact_method=ContactMethod.UNKNOWN,
        image_url="https://example.com/5.jpg",
    ),
    # 6) Same building as #1, different source — tests also_listed_on.
    _mk(
        id="00000000-0000-0000-0000-000000000006",
        source=Source.RENT_PANDA, source_id="id100006",
        url="https://app.rentpanda.ca/listing/id100006",
        cluster_id="cluster-regina50",
        address_raw="50 Regina Street N, Waterloo",
        address_normalized="50 regina street north waterloo on",
        postal_prefix="N2L", postal_code="N2J 3A5",
        lat=43.4665, lng=-80.5230,
        price_min=2050, price_max=2050, beds=2.0, baths=1.0,
        contact_method=ContactMethod.FORM,
        image_url="https://example.com/6.jpg",
    ),
]