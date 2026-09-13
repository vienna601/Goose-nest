// Display rules from docs/frontend_design_brief.md §5. Null is "unknown",
// never 0 — callers render a skeleton or "—" when these return null.
import { SOURCE_LABEL, type Listing, type Source } from "@shared/types";

export const money = (n: number) => "$" + n.toLocaleString("en-CA");

export function priceLabel(l: Pick<Listing, "price_min" | "price_max">): string {
  const lo = l.price_min ?? l.price_max;
  const hi = l.price_max ?? l.price_min;
  if (lo == null || hi == null) return "Price on request";
  if (lo === hi) return money(lo) + "/mo";
  return money(lo) + "–" + hi.toLocaleString("en-CA") + "/mo";
}

export const dist = (m: number | null) =>
  m == null ? null : m < 1000 ? `${m} m` : `${(m / 1000).toFixed(1)} km`;

/** Bamboo suffixes addresses with " CA". */
export const cleanAddress = (a: string) => a.replace(/,?\s+CA$/, "").trim();
export const shortAddress = (a: string) => cleanAddress(a).split(",")[0];

export const sourceLabel = (s: Source) => SOURCE_LABEL[s] ?? s;

const GOOSE_WORDS = ["no geese", "almost no geese", "light goose activity", "busy with geese", "goose hellscape"];
export const gooseWord = (g: number) => GOOSE_WORDS[Math.min(5, Math.max(1, g)) - 1];

export function bedsLabel(beds: number | null, den = false): string | null {
  if (beds == null) return null;
  if (beds === 0) return "studio";
  return `${beds % 1 ? beds : beds.toFixed(0)} bed${den ? "+den" : ""}`;
}

export function unitLine(l: Listing): string {
  if (l.listing_kind === "room") {
    return l.total_bedrooms ? `Room in a ${l.total_bedrooms}-bedroom house` : "Room in a shared house";
  }
  const parts = [bedsLabel(l.beds, l.den), l.baths != null ? `${l.baths} bath` : null].filter(Boolean);
  return parts.length ? parts.join(" · ") + " unit" : "Whole unit";
}

export function termLine(l: Listing): string | null {
  if (!l.lease_type && !l.term_months) return null;
  const kind = l.lease_type ?? "term";
  return l.term_months ? `${l.term_months}-month ${kind}` : kind === "lease" ? "Lease" : "Sublet";
}

export function availableLine(date: string | null): string | null {
  if (!date) return null;
  const d = new Date(date + "T12:00:00");
  return "Available " + d.toLocaleDateString("en-CA", { month: "short", day: "numeric" });
}

export const ionLine = (l: Listing) =>
  l.ion_walk_min == null ? null : `${l.ion_walk_min} min walk to ${l.nearest_ion_stop ?? "ION"}`;

export const time = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString("en-CA", { hour: "2-digit", minute: "2-digit" }) : "—";

export const contactMethodLabel = (m: string) => m.replace("_", " ");
