"""
Shared data contract. Source of truth for the whole project.

MIRRORED BY:
  shared/types.ts    frontend  (B)
  shared/schema.sql  Supabase  (C)

If you change a field or an enum value here, change it in both mirrors in the
same commit. Field names are snake_case everywhere, including TypeScript —
we are not building a case-translation layer at a hackathon.

CONVENTIONS (decided once, never revisited):
  money      integer CAD dollars. No cents, no floats, no strings.
  distance   integer metres.
  duration   integer minutes. Walk time = metres / 80, rounded up.
  dates      datetime.date for calendar days, datetime (UTC, tz-aware) for instants.
  missing    None. Never 0, never "", never -1 as a sentinel.
  ids        uuid4 str for ours; source_id preserves theirs verbatim.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums. Lock these first — every branch in the codebase keys off them.
# Values are the literal strings stored in Postgres. Never renumber, never
# rename; only append.
# ---------------------------------------------------------------------------

class Source(str, Enum):
    RENTALS_CA = "rentals_ca"
    RENT_PANDA = "rent_panda"


class ContactMethod(str, Enum):
    FORM = "form"      # browser agent on Steel
    EMAIL = "email"    # Resend fallback, no browser
    PHONE = "phone"    # draft only, surface to the user
    UNKNOWN = "unknown"  # parsed the listing, couldn't determine. Not a crash.


class InquiryStatus(str, Enum):
    DRAFTED = "drafted"                    # message composed, nothing opened
    PENDING_APPROVAL = "pending_approval"  # form filled, waiting on the human
    APPROVED = "approved"                  # human said go, not yet submitted
    SUBMITTED = "submitted"                # confirmed sent
    FAILED = "failed"                      # see failure_reason
    CANCELLED = "cancelled"                # human said no


# ---------------------------------------------------------------------------
# Listing. One row per listing PER SOURCE. Duplicates across sources are
# grouped by cluster_id, not merged — we keep both rows so provenance badges
# and per-source links stay honest.
# ---------------------------------------------------------------------------

class Listing(BaseModel):
    id: str                                  # uuid4, ours
    source: Source
    source_id: str                           # their id, verbatim, e.g. "id905220"
    url: str                                 # canonical detail page
    cluster_id: Optional[str] = None         # shared by dupes across sources

    # --- location -----------------------------------------------------------
    address_raw: str                         # exactly as scraped
    address_normalized: str                  # lowercased, expanded, no unit
    unit: Optional[str] = None
    city: str = "Waterloo"
    postal_prefix: Optional[str] = None       # N2J, N2K, N2L, N2M, N2T, N2V
    postal_code: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    # --- money --------------------------------------------------------------
    # rentals.ca cards show a RANGE. Single-price listings set both to the same
    # value so downstream filters never branch on "is this a range".
    price_min: Optional[int] = None
    price_max: Optional[int] = None

    # --- specs --------------------------------------------------------------
    beds: Optional[float] = None             # 0.0 = studio/bachelor. 1.0, 2.0...
    den: bool = False                        # "1+den" -> beds=1.0, den=True
    baths: Optional[float] = None            # 1.5 is real
    sqft: Optional[int] = None               # rentals.ca cards don't carry this
    available_date: Optional[date] = None    # Rent Panda exposes this

    # --- contact (drives the agent's branch) --------------------------------
    contact_method: ContactMethod = ContactMethod.UNKNOWN
    contact_url: Optional[str] = None        # form page, if not the detail page
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    contact_behind_click: bool = False       # "show contact" gate before the form

    # --- media --------------------------------------------------------------
    image_url: Optional[str] = None          # card thumbnail, for the grid
    images: list[str] = Field(default_factory=list)

    # --- enrichment (C fills; collection leaves None) -----------------------
    nearest_ion_stop: Optional[str] = None
    ion_distance_m: Optional[int] = None
    ion_walk_min: Optional[int] = None
    go_distance_m: Optional[int] = None       # Kitchener GO, weekend-trip signal
    highway_distance_m: Optional[int] = None  # nearest of 7/8, 85, 401
    geese_zone: Optional[str] = None
    geese_score: Optional[int] = None         # 1 = no geese, 5 = geese hellscape

    # --- provenance ---------------------------------------------------------
    scraped_at: datetime
    cache_key: str                           # sha256 of the fetched URL
    raw: dict[str, Any] = Field(default_factory=dict)  # anything unparsed


# ---------------------------------------------------------------------------
# Search. B's form produces this; C ranks against it.
# ---------------------------------------------------------------------------

class ScoreWeights(BaseModel):
    """Sum need not be 1.0 — scores are normalized at the end."""
    price: float = 1.0
    ion_proximity: float = 1.0
    beds_match: float = 1.0
    geese: float = 0.5
    highway: float = 0.25
    go_proximity: float = 0.25


class SearchRequirements(BaseModel):
    """The demo query encodes as:
    beds_min=2, baths_min=1, price_max=2400, max_ion_walk_min=10, max_geese_score=2
    """
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    beds_min: Optional[float] = None
    beds_max: Optional[float] = None
    baths_min: Optional[float] = None
    max_ion_walk_min: Optional[int] = None
    max_geese_score: Optional[int] = None
    available_by: Optional[date] = None
    include_kitchener_cambridge: bool = False   # the tri-city toggle
    weights: ScoreWeights = Field(default_factory=ScoreWeights)


class ScoreFactor(BaseModel):
    """One row of the visible score breakdown. If it can't be explained in a
    sentence it doesn't belong in the ranking."""
    factor: str                  # "ion_proximity"
    label: str                   # "7 min walk to Laurier"
    raw_value: Optional[float] = None
    weight: float
    points: float                # contribution to the 0-100 total
    explanation: str


class ScoredListing(BaseModel):
    listing: Listing
    score: float                 # 0-100
    breakdown: list[ScoreFactor]
    also_listed_on: list[Source] = Field(default_factory=list)  # from cluster_id


# ---------------------------------------------------------------------------
# Inquiry. The agent's unit of work. B renders the approval UI off this, so it
# is locked at H0 alongside Listing — not at H4.
# ---------------------------------------------------------------------------

class Inquiry(BaseModel):
    id: str
    listing_id: str
    status: InquiryStatus = InquiryStatus.DRAFTED
    method: ContactMethod

    message: str                             # what we intend to send
    sender_name: str
    sender_email: str
    sender_phone: Optional[str] = None

    # Populated by the browser agent as it works.
    steel_session_id: Optional[str] = None
    viewer_url: Optional[str] = None         # B embeds this live
    filled_fields: dict[str, str] = Field(default_factory=dict)  # approval preview
    steps: list[str] = Field(default_factory=list)               # streamed to UI

    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    created_at: datetime


# ---------------------------------------------------------------------------
# Lease. C's territory; stubbed here so B can build the timeline against it.
# ---------------------------------------------------------------------------

class Deadline(BaseModel):
    id: str
    label: str                   # "First month's rent due"
    due_date: date
    source_quote: Optional[str] = None   # the clause it came from
    page: Optional[int] = None


class LeaseAnalysis(BaseModel):
    id: str
    listing_id: Optional[str] = None
    filename: str
    monthly_rent: Optional[int] = None
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    deposit: Optional[int] = None
    deadlines: list[Deadline] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)   # unusual clauses, plain English
    summary: Optional[str] = None
    created_at: datetime
