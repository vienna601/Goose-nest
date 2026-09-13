import type { InquiryRecord } from "../lib/records";
import { shortAddress, sourceLabel, time } from "../lib/format";
import { StatusPill } from "../components/Badges";
import { Goose, GooseRow } from "../components/Goose";

interface Props {
  records: InquiryRecord[];
  open: (r: InquiryRecord) => void;
  goHome: () => void;
}

const ORDER = { pending_approval: 0, drafted: 1, approved: 2, failed: 3, submitted: 4, cancelled: 5 };

export function Inquiries({ records, open, goHome }: Props) {
  const sorted = [...records].sort(
    (a, b) => ORDER[a.inquiry.status] - ORDER[b.inquiry.status] || b.inquiry.created_at.localeCompare(a.inquiry.created_at),
  );
  const sent = records.filter((r) => r.inquiry.status === "submitted").length;
  const waiting = records.filter((r) => r.inquiry.status === "pending_approval").length;

  return (
    <div className="page" style={{ maxWidth: 1000, paddingTop: 30 }}>
      <h2 className="h2">My inquiries</h2>
      <div style={{ fontSize: 14.5, color: "var(--ink-2)", marginTop: 8 }}>
        {records.length === 0
          ? "Nothing sent yet."
          : `${sent} sent${waiting ? ` · ${waiting} waiting for your approval` : ""}. Every message here was approved by you — or not sent at all.`}
      </div>

      <div style={{ marginTop: 22, display: "grid", gap: 11 }}>
        {sorted.map((r) => {
          const q = r.inquiry;
          const attention = q.status === "pending_approval";
          const meta = [
            sourceLabel(r.listing.source),
            `started ${time(q.created_at)}`,
            q.approved_by && `approved by ${q.approved_by}`,
            q.submitted_at && `sent ${time(q.submitted_at)}`,
            q.status === "failed" && q.failure_reason,
          ].filter(Boolean).join(" · ");
          return (
            <div key={q.id} className={`inq${attention ? " attention" : ""}`}>
              <div className="thumb" style={{ width: 44, height: 44, borderRadius: 10 }}>
                {r.listing.image_url ? <img src={r.listing.image_url} alt="" /> : <Goose size={24} />}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 15, fontWeight: 500 }}>{shortAddress(r.listing.address_raw)}</div>
                <div style={{ fontSize: 13, color: "var(--ink-3)" }}>{meta}</div>
              </div>
              <StatusPill status={q.status} />
              <button className={attention ? "btn-short" : "btn"} onClick={() => open(r)}>
                {attention ? "Review now" : q.status === "drafted" || q.status === "approved" ? "Open" : "View"}
              </button>
            </div>
          );
        })}

        {records.length === 0 && (
          <div className="empty">
            <GooseRow count={1} size={28} opacity={0.7} />
            <div className="empty-title" style={{ fontSize: 22 }}>No inquiries yet.</div>
            <div style={{ fontSize: 14, color: "var(--ink-2)", marginTop: 7 }}>Shortlist a few nests and let the agent do the typing.</div>
            <button className="btn-dark" style={{ marginTop: 18, cursor: "pointer" }} onClick={goHome}>Start a search</button>
          </div>
        )}
      </div>
    </div>
  );
}
