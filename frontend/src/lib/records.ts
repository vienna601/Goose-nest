import type { Inquiry, Listing } from "@shared/types";
import { load, save } from "./storage";

/** An inquiry plus the listing it was about, so My inquiries can render
 *  without re-fetching. Persisted locally. */
export interface InquiryRecord {
  inquiry: Inquiry;
  listing: Listing;
}

const KEY = "inquiries";
const TERMINAL = new Set(["submitted", "failed", "cancelled"]);

export function loadRecords(): InquiryRecord[] {
  const recs = load<InquiryRecord[]>(KEY, []);
  // A simulated agent lives in page memory; after a reload it's gone. Say so
  // instead of leaving it "in progress" forever.
  return recs.map((r) =>
    r.inquiry.id.startsWith("sim-") && !TERMINAL.has(r.inquiry.status)
      ? {
          ...r,
          inquiry: {
            ...r.inquiry,
            status: r.inquiry.status === "approved" ? "failed" : "cancelled",
            failure_reason: "The simulated session ended when the page reloaded. Nothing was sent.",
          },
        }
      : r,
  );
}

export const saveRecords = (recs: InquiryRecord[]) => save(KEY, recs);

export const isTerminal = (i: Inquiry) => TERMINAL.has(i.status);
