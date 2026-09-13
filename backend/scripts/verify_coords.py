# scripts/verify_coords.py — check hardcoded ION/GO coords vs Google, with map links.
from services.enrich import ION_STOPS, GO_STOPS, haversine
from services.geocode import geocode_one


def check(kind, entries, suffix):
    print(f"\n=== {kind} ===")
    for name, lat, lng in entries:
        print(f"\n[{name}]")
        print(f"  hardcoded: {lat},{lng}")
        print(f"  map:       https://www.google.com/maps?q={lat},{lng}")
        g = geocode_one(f"{name}{suffix}")
        if g.lat is None:
            print(f"  google:    FAILED ({g.status}) — verify manually via the map link above")
            continue
        delta = round(haversine(lat, lng, g.lat, g.lng))
        flag = "   <-- CHECK (off by >200m)" if delta > 200 else ""
        print(f"  google:    {g.lat:.5f},{g.lng:.5f}   Δ={delta}m{flag}")


check("ION stops", ION_STOPS, " ION station, Waterloo Region, ON")
check("GO stops",  GO_STOPS,  ", Ontario")