/**
 * Shared data contract — TypeScript mirror of shared/schema.py.
 *
 * Field names are snake_case to match the Python and the JSON on the wire.
 * Do not camelCase them; we are not writing a translation layer at a hackathon.
 *
 * Python Optional[X] maps to `X | null` (the key is present and null), NOT
 * `X?` (key absent). Pydantic serializes None as null, so `| null` is correct
 * and `?` will lie to you.
 *
 * If you change anything here, change shared/schema.py and shared/schema.sql
 * in the same commit.
 */

// ---------------------------------------------------------------------------
// Enums — string unions, so they compare directly against the API payload.
// ---------------------------------------------------------------------------

export type Source = "rentals_ca" | "rent_panda" | "bamboo" | "homestead";

/** Bamboo rents ROOMS in shared houses; other sources rent whole UNITS.
 *  Never sort a $695 room against a $2400 apartment without showing the badge. */
export type ListingKind = "unit" | "room";

export type LeaseType = "lease" | "sublet";

export type ContactMethod =
  | "form"              // browser agent on Steel
  | "email"             // Resend fallback
  | "phone"             // draft only
  | "account_required"  // platform login needed — show the link, no auto-contact
  | "unknown";

export type InquiryStatus =
  | "drafted"
  | "pending_approval"
  | "approved"
  | "submitted"
  | "failed"
  | "cancelled";

/** Display labels. Keep the mapping here so badges never hardcode a string. */
export const SOURCE_LABEL: Record<Source, string> = {
  rentals_ca: "Rentals.ca",
  rent_panda: "Rent Panda",
  bamboo: "Bamboo Housing",
  homestead: "Homestead",
};

// ---------------------------------------------------------------------------
// Listing — one row per listing PER SOURCE. Cross-source duplicates share a
// cluster_id; the grid groups on it and shows `also_listed_on` badges.
// ---------------------------------------------------------------------------

export interface Listing {
  id: string;
  source: Source;
  source_id: string;
  url: string;
  cluster_id: string | null;

  // location
  address_raw: string;
  address_normalized: string;
  unit: string | null;
  city: string;
  postal_prefix: string | null;
  postal_code: string | null;
  lat: number | null;
  lng: number | null;

  // money — integer CAD dollars. Single-price listings set both to the same
  // value, so the UI can always render min–max without branching.
  price_min: number | null;
  price_max: number | null;

  // specs
  listing_kind: ListingKind;
  beds: number | null; // 0 = studio; for a room listing, the room itself
  total_bedrooms: number | null; // bedrooms in the whole house
  rooms_available: number | null;
  den: boolean;
  baths: number | null; // 1.5 is real
  sqft: number | null; // usually null on rentals.ca
  available_date: string | null; // ISO date, "2026-09-01"
  is_available: boolean;
  lease_type: LeaseType | null;
  term_months: number | null; // 4 and 8 are the student sublet terms

  // contact
  contact_method: ContactMethod;
  contact_url: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  contact_name: string | null;
  contact_behind_click: boolean;

  // media
  image_url: string | null;
  images: string[];

  // enrichment — null until the backend fills it. Render a skeleton, not a 0.
  nearest_ion_stop: string | null;
  ion_distance_m: number | null;
  ion_walk_min: number | null;
  go_distance_m: number | null;
  highway_distance_m: number | null;
  geese_zone: string | null;
  geese_score: number | null; // 1 = no geese, 5 = geese hellscape

  // provenance
  scraped_at: string; // ISO datetime, UTC, with Z
  cache_key: string;
  raw: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Search
// ---------------------------------------------------------------------------

export interface ScoreWeights {
  price: number;
  ion_proximity: number;
  beds_match: number;
  term_match: number;
  geese: number;
  highway: number;
  go_proximity: number;
}

export interface SearchRequirements {
  listing_kind: ListingKind | null; // defaults to "room" — that's the inventory
  lease_type: LeaseType | null;
  term_months: number | null;
  price_min: number | null;
  price_max: number | null;
  beds_min: number | null;
  beds_max: number | null;
  baths_min: number | null;
  max_ion_walk_min: number | null;
  max_geese_score: number | null;
  available_by: string | null; // ISO date
  include_kitchener_cambridge: boolean;
  weights: ScoreWeights;
}

export interface ScoreFactor {
  factor: string;
  label: string;
  raw_value: number | null;
  weight: number;
  points: number;
  explanation: string;
}

export interface ScoredListing {
  listing: Listing;
  score: number; // 0–100
  breakdown: ScoreFactor[];
  also_listed_on: Source[];
}

// ---------------------------------------------------------------------------
// Inquiry — drives the approval UI and the Steel viewer embed.
// ---------------------------------------------------------------------------

export interface Inquiry {
  id: string;
  listing_id: string;
  status: InquiryStatus;
  method: ContactMethod;

  message: string;
  sender_name: string;
  sender_email: string;
  sender_phone: string | null;

  steel_session_id: string | null;
  viewer_url: string | null; // iframe this while status is pending_approval
  filled_fields: Record<string, string>; // show this in the approval dialog
  steps: string[]; // append-only agent narration, streamed over SSE

  approved_at: string | null;
  approved_by: string | null;
  submitted_at: string | null;
  failure_reason: string | null;

  created_at: string;
}

// ---------------------------------------------------------------------------
// Lease
// ---------------------------------------------------------------------------

export interface Deadline {
  id: string;
  label: string;
  due_date: string; // ISO date
  source_quote: string | null;
  page: number | null;
}

export interface LeaseAnalysis {
  id: string;
  listing_id: string | null;
  filename: string;
  monthly_rent: number | null;
  term_start: string | null;
  term_end: string | null;
  deposit: number | null;
  deadlines: Deadline[];
  flags: string[];
  summary: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// SSE event envelope — the progress stream B subscribes to.
// ---------------------------------------------------------------------------

export type StreamEvent =
  | { type: "collection_progress"; source: Source; fetched: number; total: number | null }
  | { type: "listing_batch"; listings: Listing[] }
  | { type: "ranking_done"; results: ScoredListing[] }
  | { type: "inquiry_update"; inquiry: Inquiry }
  | { type: "error"; message: string };
