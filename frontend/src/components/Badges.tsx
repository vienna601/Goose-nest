import type { InquiryStatus, Listing, Source } from "@shared/types";
import { sourceLabel } from "../lib/format";

export function KindBadge({ kind }: { kind: Listing["listing_kind"] }) {
  return <span className={`badge badge-kind ${kind}`}>{kind === "room" ? "ROOM" : "UNIT"}</span>;
}

export function SourceBadges({ source, also }: { source: Source; also: Source[] }) {
  return (
    <>
      <span className="badge badge-src">{sourceLabel(source)}</span>
      {also.map((s) => (
        <span key={s} className="badge badge-also">
          Also on {sourceLabel(s)}
        </span>
      ))}
    </>
  );
}

const STATUS_TEXT: Record<InquiryStatus, string> = {
  drafted: "drafted",
  pending_approval: "needs your approval",
  approved: "approved",
  submitted: "submitted",
  failed: "failed",
  cancelled: "cancelled",
};

export function StatusPill({ status }: { status: InquiryStatus }) {
  return <span className={`status-pill status-${status}`}>{STATUS_TEXT[status]}</span>;
}
