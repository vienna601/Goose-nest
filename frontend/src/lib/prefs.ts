// UI form state and its mapping onto the backend's SearchRequirements.
import type { LeaseType, ListingKind, ScoreWeights, SearchRequirements } from "@shared/types";

export interface Prefs {
  kind: ListingKind | null;
  lease: LeaseType | "either";
  term: number | "any";
  priceMax: number;
  walkMax: number;
  gooseMax: number;
  triCity: boolean;
  availableBy: string;
}

/** Demo defaults from the brief: Room · Sublet · 4 months · ≤ $1,000 · ≤ 10 min · geese ≤ 2. */
export const DEFAULT_PREFS: Prefs = {
  kind: "room",
  lease: "sublet",
  term: 4,
  priceMax: 1000,
  walkMax: 10,
  gooseMax: 2,
  triCity: false,
  availableBy: "",
};

export const PRICE_CEIL = 3000;
export const WALK_CEIL = 30;

export const DEFAULT_WEIGHTS: ScoreWeights = {
  price: 1,
  ion_proximity: 1,
  beds_match: 1,
  term_match: 1,
  geese: 0.5,
  highway: 0.25,
  go_proximity: 0.25,
};

export const WEIGHT_ROWS: { key: keyof ScoreWeights; label: string }[] = [
  { key: "price", label: "Price" },
  { key: "ion_proximity", label: "Close to ION" },
  { key: "beds_match", label: "Bedrooms match" },
  { key: "term_match", label: "Term match" },
  { key: "geese", label: "Few geese" },
  { key: "highway", label: "Near a highway" },
  { key: "go_proximity", label: "Near a GO station" },
];

export function toRequirements(p: Prefs, weights: ScoreWeights): SearchRequirements {
  return {
    listing_kind: p.kind,
    lease_type: p.lease === "either" ? null : p.lease,
    term_months: p.term === "any" ? null : p.term,
    price_min: null,
    price_max: p.priceMax >= PRICE_CEIL ? null : p.priceMax,
    beds_min: null,
    beds_max: null,
    baths_min: null,
    max_ion_walk_min: p.walkMax >= WALK_CEIL ? null : p.walkMax,
    max_geese_score: p.gooseMax >= 5 ? null : p.gooseMax,
    available_by: p.availableBy || null,
    include_kitchener_cambridge: p.triCity,
    weights,
  };
}
