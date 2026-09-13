// Client-side preview of the inquiry text. Mirrors agent/draft.py (compose and
// showing_note) so what the user reads here is what the agent will type. The
// backend composes the real message; keep the two in step.
import type { Listing } from "@shared/types";
import { cleanAddress } from "./format";

export interface Sender {
  name: string;
  email: string;
  phone: string;
}

export interface ViewingTime {
  date: string; // yyyy-mm-dd
  time: string; // HH:MM
}

function listingLabel(l: Listing): string {
  const where = cleanAddress(l.address_raw || l.city);
  if (l.listing_kind === "room") {
    return l.total_bedrooms ? `the room in the ${l.total_bedrooms}-bedroom place at ${where}` : `the room at ${where}`;
  }
  const beds = l.beds ? `${l.beds}-bedroom ` : "";
  return `the ${beds}unit at ${where}`;
}

function availabilityLine(l: Listing): string {
  const parts: string[] = [];
  if (l.lease_type === "sublet" && l.term_months) parts.push(`I'm looking for a ${l.term_months}-month sublet`);
  else if (l.lease_type === "lease") parts.push("I'm looking for a standard lease");
  if (l.available_date) {
    const d = new Date(l.available_date + "T12:00:00");
    const when = d.toLocaleDateString("en-CA", { month: "long", day: "numeric" });
    parts.push(parts.length ? `and the ${when} start date works for me` : `the ${when} start date works for me`);
  }
  if (!parts.length) return "I'd like to know more about the terms and start date.";
  const text = parts.join(", ");
  return text[0].toUpperCase() + text.slice(1) + ".";
}

export function composeMessage(l: Listing, s: Sender, questions: string[]): string {
  const lines = [`Hi${l.contact_name ? " " + l.contact_name : ""},`, ""];
  const price = l.price_min ? ` listed at $${l.price_min}/month` : "";
  lines.push(`I'm interested in ${listingLabel(l)}${price}.`, "", availabilityLine(l), "");
  if (questions.length) lines.push("A couple of questions:", ...questions.map((q) => `- ${q}`), "");
  lines.push("Is it still available? I'm happy to arrange a viewing.", "", "Thanks,", s.name, s.email);
  if (s.phone) lines.push(s.phone);
  return lines.join("\n");
}

/** Rent Panda's NOTES field — the platform already knows who we are. */
export function showingNote(l: Listing, questions: string[]): string {
  const parts = [`Hi! I'm interested in ${listingLabel(l)} and would love to see it.`];
  const terms = availabilityLine(l);
  if (!terms.startsWith("I'd like to know")) parts.push(terms);
  if (questions.length) parts.push(questions.map((q) => (q.endsWith("?") ? q : q + "?")).join(" "));
  parts.push("Thanks!");
  return parts.join(" ");
}

/** "2026-09-14" + "18:00" → "09/14/2026 18:00", the format Rent Panda reads back. */
export const usDateTime = (t: ViewingTime) => {
  const [y, m, d] = t.date.split("-");
  return `${m}/${d}/${y} ${t.time}`;
};

export const usesShowingRequest = (l: Listing) => l.source === "rent_panda";
