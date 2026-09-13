# services/ranking.py — weighted, explainable scoring. Pure functions, no network.
from __future__ import annotations
from schema import Listing, SearchRequirements, ScoreWeights, ScoreFactor, ScoredListing

WATERLOO_PREFIXES = {"N2J", "N2K", "N2L", "N2M", "N2T", "N2V"}
KIT_CAM_PREFIXES  = {"N2A", "N2B", "N2C", "N2E", "N2G", "N2H", "N2N", "N2P", "N2R",
                     "N1P", "N1R", "N1S", "N1T", "N3C", "N3E", "N3H"}


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def _allowed_prefixes(req):
    a = set(WATERLOO_PREFIXES)
    if req.include_kitchener_cambridge:
        a |= KIT_CAM_PREFIXES
    return a


# ---- hard filters: decide in/out ----
def passes_hard_filters(l: Listing, req: SearchRequirements) -> bool:
    if l.postal_prefix and l.postal_prefix not in _allowed_prefixes(req):
        return False
    if req.listing_kind is not None and l.listing_kind != req.listing_kind:
        return False
    if req.lease_type is not None and l.lease_type is not None and l.lease_type != req.lease_type:
        return False
    if req.term_months is not None and l.term_months is not None and l.term_months != req.term_months:
        return False
    price = l.price_min or l.price_max
    if req.price_max and price and price > req.price_max:
        return False
    if req.price_min and (l.price_max or price) and (l.price_max or price) < req.price_min:
        return False
    if req.beds_min is not None and l.beds is not None and l.beds < req.beds_min:
        return False
    if req.beds_max is not None and l.beds is not None and l.beds > req.beds_max:
        return False
    if req.baths_min is not None and l.baths is not None and l.baths < req.baths_min:
        return False
    if req.max_ion_walk_min is not None and l.ion_walk_min is not None and l.ion_walk_min > req.max_ion_walk_min:
        return False
    if req.max_geese_score is not None and l.geese_score is not None and l.geese_score > req.max_geese_score:
        return False
    if req.available_by is not None and l.available_date is not None and l.available_date > req.available_by:
        return False
    return True


# ---- soft scorers: (normalized 0..1, raw, short label, explanation) ----
def _s_price(l, req):
    price = l.price_min or l.price_max
    budget = req.price_max or 3000
    if not price:
        return 0.0, None, "price unknown", "no price listed"
    return _clamp((budget - price) / budget), float(price), f"${price:,}/mo", \
        f"${price:,}/mo vs ${budget:,} budget"

def _s_ion(l, req):
    if l.ion_walk_min is None:
        return 0.0, None, "ION unknown", "no ION data"
    return _clamp(1 - l.ion_walk_min / 20), float(l.ion_walk_min), \
        f"{l.ion_walk_min} min to ION", f"{l.ion_walk_min} min walk to {l.nearest_ion_stop}"

def _s_beds(l, req):
    if l.beds is None:
        return 0.0, None, "beds unknown", "no bed count"
    lo = req.beds_min if req.beds_min is not None else l.beds
    hi = req.beds_max if req.beds_max is not None else l.beds
    label = "studio" if l.beds == 0 else f"{l.beds:g} bed" + ("+den" if l.den else "")
    if lo <= l.beds <= hi:
        return 1.0, l.beds, label, f"{label} — matches"
    target = lo if l.beds < lo else hi
    return _clamp(1 - abs(l.beds - target) / 2), l.beds, label, f"{label} — wanted {lo:g}-{hi:g}"

def _s_geese(l, req):
    if l.geese_score is None:
        return 0.0, None, "geese unknown", "no goose data"
    norm = (5 - l.geese_score) / 4     # inverted: 1(good)->1.0, 5(bad)->0.0
    phrase = l.geese_zone or {1: "no geese", 2: "light geese", 3: "moderate geese",
                              4: "heavy geese", 5: "goose hotspot"}[l.geese_score]
    return norm, float(l.geese_score), phrase, f"goose score {l.geese_score}/5 ({phrase})"

def _s_highway(l, req):
    if l.highway_distance_m is None:
        return 0.0, None, "highway unknown", "no highway data"
    km = l.highway_distance_m / 1000
    return _clamp(1 - l.highway_distance_m / 5000), float(l.highway_distance_m), \
        f"{km:.1f} km to highway", f"{km:.1f} km to nearest highway"

def _s_go(l, req):
    if l.go_distance_m is None:
        return 0.0, None, "GO unknown", "no GO data"
    km = l.go_distance_m / 1000
    return _clamp(1 - l.go_distance_m / 8000), float(l.go_distance_m), \
        f"{km:.1f} km to GO", f"{km:.1f} km to nearest GO stop"


SCORERS = {
    "price":         ("Price", _s_price),
    "ion_proximity": ("ION proximity", _s_ion),
    "beds_match":    ("Bedrooms", _s_beds),
    "geese":         ("Geese", _s_geese),
    "highway":       ("Highway access", _s_highway),
    "go_proximity":  ("GO proximity", _s_go),
}


def _norm_weights(w: ScoreWeights):
    raw = {"price": w.price, "ion_proximity": w.ion_proximity, "beds_match": w.beds_match,
           "geese": w.geese, "highway": w.highway, "go_proximity": w.go_proximity}
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in raw.items()}


def score_listing(l: Listing, req: SearchRequirements) -> ScoredListing:
    w = _norm_weights(req.weights)
    breakdown, total = [], 0.0
    for key, (_, fn) in SCORERS.items():
        norm, raw, short, expl = fn(l, req)
        pts = round(w[key] * norm * 100, 1)
        total += pts
        breakdown.append(ScoreFactor(factor=key, label=short, raw_value=raw,
                                     weight=round(w[key], 3), points=pts, explanation=expl))
    breakdown.sort(key=lambda f: f.points, reverse=True)
    return ScoredListing(listing=l, score=round(total, 1), breakdown=breakdown, also_listed_on=[])


def search(listings: list[Listing], req: SearchRequirements) -> list[ScoredListing]:
    survivors = [l for l in listings if passes_hard_filters(l, req)]

    # collapse cross-source dupes (same building) into one card per cluster
    reps, seen = [], {}
    for l in survivors:
        if l.cluster_id:
            if l.cluster_id not in seen:
                seen[l.cluster_id] = l
                reps.append(l)
            elif (l.price_min or 1e9) < (seen[l.cluster_id].price_min or 1e9):
                reps[reps.index(seen[l.cluster_id])] = l   # keep the cheaper listing
                seen[l.cluster_id] = l
        else:
            reps.append(l)

    # which sources each cluster appears on (across ALL listings)
    cluster_sources = {}
    for l in listings:
        if l.cluster_id:
            cluster_sources.setdefault(l.cluster_id, set()).add(l.source)

    scored = []
    for l in reps:
        s = score_listing(l, req)
        if l.cluster_id:
            s.also_listed_on = [src for src in cluster_sources.get(l.cluster_id, set())
                                if src != l.source]
        scored.append(s)

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored