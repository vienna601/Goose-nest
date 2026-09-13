# services/enrich.py — local proximity enrichment. Coords in, schema fields out.
from __future__ import annotations
import json, os, math
from services.geese_source import CACHE_PATH as GEESE_CACHE

R = 6_371_000                 # earth radius, metres
WALK_SPEED_M_PER_MIN = 80     # locked convention: minutes = ceil(metres / 80)
GEESE_RADIUS_M = 500


# ---- geometry ----
def haversine(a_lat, a_lng, b_lat, b_lng) -> float:
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dl   = math.radians(b_lng - a_lng)
    h = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(h))

def _to_xy(lat, lng, lat0):
    return math.radians(lng) * R * math.cos(math.radians(lat0)), math.radians(lat) * R

def _point_to_segment_m(plat, plng, alat, alng, blat, blng) -> float:
    lat0 = plat
    px, py = _to_xy(plat, plng, lat0)
    ax, ay = _to_xy(alat, alng, lat0)
    bx, by = _to_xy(blat, blng, lat0)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax)*dx + (py - ay)*dy) / (dx*dx + dy*dy)))
    cx, cy = ax + t*dx, ay + t*dy
    return math.hypot(px - cx, py - cy)

def _dist_to_polyline_m(plat, plng, line) -> float:
    return min(_point_to_segment_m(plat, plng, line[i][0], line[i][1], line[i+1][0], line[i+1][1])
               for i in range(len(line) - 1))


# ============ STATIC DATA ============

ION_STOPS = [
    ("Conestoga",               43.49821, -80.52953),
    ("Northfield",              43.49736, -80.54330),
    ("Research and Technology", 43.48136, -80.54527),
    ("University of Waterloo",  43.47229, -80.54486),
    ("Laurier–Waterloo Park",   43.46899, -80.53450),
    ("Waterloo Public Square",  43.46414, -80.52289),
    ("Willis Way",              43.46228, -80.52354),
    ("Allen",                   43.46015, -80.51886),
    ("Grand River Hospital",    43.45730, -80.51217),
    ("Central Station",         43.45333, -80.49944),
    ("Kitchener City Hall",     43.45202, -80.49104),
    ("Frederick",               43.44938, -80.48748),
    ("Queen",                   43.44871, -80.48966),
    ("Victoria Park",           43.45016, -80.49354),
    ("Kitchener Market",        43.44639, -80.48361),
    ("Borden",                  43.44228, -80.47501),
    ("Mill",                    43.43395, -80.47839),
    ("Block Line",              43.41902, -80.46660),
    ("Fairway",                 43.42235, -80.44179),
]

HIGHWAYS = {
    "Conestoga Pkwy (7/8)": [(43.4300,-80.5200),(43.4200,-80.4900),(43.4150,-80.4500)],
    "Highway 85":           [(43.5000,-80.5100),(43.4700,-80.5000),(43.4400,-80.4900)],
    "Highway 401":          [(43.3700,-80.4200),(43.3600,-80.3800),(43.3500,-80.3300)],
}

GO_STOPS = [
    ("Kitchener GO",              43.4534,    -80.4899),    # VERIFY or drop — GO train, downtown Kitchener
    ("University of Waterloo GO", 43.4731293, -80.541687),  # verified
    ("Laurier / University Ave",  43.4751141, -80.5274913), # verified
]


# ============ geese: density of iNaturalist observations ============
_GEESE_POINTS = None

def _geese_points():
    global _GEESE_POINTS
    if _GEESE_POINTS is None:
        if os.path.exists(GEESE_CACHE):
            with open(GEESE_CACHE) as f:
                _GEESE_POINTS = [(p["lat"], p["lng"]) for p in json.load(f)]
        else:
            print("WARN: geese cache missing — run `python -m services.geese_source`.")
            _GEESE_POINTS = []
    return _GEESE_POINTS

def _geese(lat, lng):
    """Inverted scale: 1 = no geese (good) ... 5 = hotspot (bad). Count within 500m."""
    count = 0
    for plat, plng in _geese_points():
        if abs(plat - lat) < 0.006 and abs(plng - lng) < 0.008:
            if haversine(lat, lng, plat, plng) <= GEESE_RADIUS_M:
                count += 1
    if   count == 0:  return 1, None,                     count
    elif count <= 3:  return 2, "light goose activity",   count
    elif count <= 10: return 3, "moderate goose activity", count
    elif count <= 30: return 4, "heavy goose activity",   count
    else:             return 5, "goose hotspot",          count


# ============ enrichment ============
def _nearest_ion(lat, lng):
    name, slat, slng = min(ION_STOPS, key=lambda s: haversine(lat, lng, s[1], s[2]))
    d = round(haversine(lat, lng, slat, slng))
    return name, d, math.ceil(d / WALK_SPEED_M_PER_MIN)

def _nearest_highway_m(lat, lng):
    return round(min(_dist_to_polyline_m(lat, lng, line) for line in HIGHWAYS.values()))

def _nearest_go_m(lat, lng):
    return round(min(haversine(lat, lng, s[1], s[2]) for s in GO_STOPS))


def enrich(lat: float, lng: float) -> dict:
    ion_stop, ion_m, ion_min = _nearest_ion(lat, lng)
    g_score, g_zone, _ = _geese(lat, lng)
    return {
        "nearest_ion_stop": ion_stop,
        "ion_distance_m": ion_m,
        "ion_walk_min": ion_min,
        "go_distance_m": _nearest_go_m(lat, lng),
        "highway_distance_m": _nearest_highway_m(lat, lng),
        "geese_zone": g_zone,
        "geese_score": g_score,
    }