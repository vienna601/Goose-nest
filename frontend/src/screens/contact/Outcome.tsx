import type { Inquiry, Listing } from "@shared/types";
import { sourceLabel, time } from "../../lib/format";
import { Goose } from "../../components/Goose";
import { StatusPill } from "../../components/Badges";
import { Timeline } from "./AgentStage";

const rand = (i: number, m: number) => ((i * 9301 + 49297) % m) / m;

interface Props {
  inquiry: Inquiry;
  listing: Listing;
  nextLabel: string;
  onNext: () => void;
  onInquiries: () => void;
  onCopy: (text: string) => void;
}

export function Outcome({ inquiry: q, listing, nextLabel, onNext, onInquiries, onCopy }: Props) {
  const src = sourceLabel(listing.source);
  const copy = {
    approved: { h: "Approved — agent is clicking Send…", b: "Hang tight. We confirm the request actually went through before calling it sent." },
    submitted: { h: "Sent. The landlord has your message.", b: `Replies usually land in your email within a day or two. The record lives in My inquiries.` },
    failed: { h: "The agent couldn't finish this one.", b: q.failure_reason ?? "Something went wrong on the landlord's site." },
    cancelled: { h: "Cancelled. Nothing was sent.", b: "The browser session was closed and the form was left untouched. You can draft this one again any time." },
  }[q.status as "approved" | "submitted" | "failed" | "cancelled"] ?? { h: q.status, b: "" };

  const mailto = listing.contact_email
    ? `mailto:${listing.contact_email}?subject=${encodeURIComponent("Inquiry: " + listing.address_raw)}&body=${encodeURIComponent(q.message)}`
    : null;

  return (
    <div style={{ marginTop: 18, maxWidth: 760 }}>
      <div className="card outcome">
        {q.status === "submitted" && (
          <div style={{ position: "absolute", top: 0, right: 0, width: 210, height: 56, overflow: "hidden", pointerEvents: "none" }} aria-hidden="true">
            {Array.from({ length: 9 }, (_, i) => (
              <span key={i} style={{ position: "absolute", top: `${(2 + rand(i + 1, 13) * 58).toFixed(0)}%`, left: `${(2 + rand(i + 6, 17) * 82).toFixed(0)}%`, opacity: 0.3, animation: `gnPop .6s both ${(i * 0.07).toFixed(2)}s` }}>
                <Goose size={13 + rand(i, 5) * 13} />
              </span>
            ))}
          </div>
        )}
        <div style={{ position: "relative" }}>
          <StatusPill status={q.status} />
          <div className="h2" style={{ marginTop: 14 }}>
            {q.status === "approved" && <span className="spinner" style={{ display: "inline-block", width: 22, height: 22, marginRight: 12, verticalAlign: 0 }} />}
            {copy.h}
          </div>
          <div style={{ fontSize: 15, color: "var(--ink-2)", marginTop: 8, lineHeight: 1.55 }}>{copy.b}</div>

          {q.status === "failed" && (
            <div className="card-sm" style={{ marginTop: 18, background: "var(--sunken)" }}>
              <div style={{ fontSize: 14, fontWeight: 500 }}>Send it yourself — the draft is ready.</div>
              <div className="row wrap" style={{ marginTop: 12, gap: 8 }}>
                <button className="btn btn-white" onClick={() => onCopy(q.message)}>Copy message</button>
                {mailto && <a className="btn btn-white" href={mailto} style={{ textDecoration: "none" }}>Open in email</a>}
                <a className="btn btn-white" href={listing.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>Open on {src} ↗</a>
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>Check {src} before retrying, in case the request did go through.</div>
            </div>
          )}

          <div className="eyebrow" style={{ marginTop: 22, letterSpacing: ".08em" }}>Audit trail</div>
          <div className="audit">
            <div><span>{time(q.created_at)}</span><span>Message drafted for {q.sender_name} ({q.method === "form" ? `agent on ${src}'s form` : q.method})</span></div>
            {q.approved_at && <div><span>{time(q.approved_at)}</span><span>Approved by <b>{q.approved_by}</b></span></div>}
            {q.submitted_at && <div><span>{time(q.submitted_at)}</span><span>Submitted to {src}</span></div>}
            {q.status === "cancelled" && <div><span>—</span><span>Cancelled. Nothing was sent.</span></div>}
            {q.status === "failed" && <div><span>—</span><span>Failed: {q.failure_reason ?? "unknown error"}</span></div>}
          </div>

          <details style={{ marginTop: 14 }}>
            <summary className="link-btn" style={{ display: "inline" }}>Full agent step history ({q.steps.length})</summary>
            <Timeline steps={q.steps} />
          </details>

          <div className="row wrap" style={{ marginTop: 22, gap: 10 }}>
            <button className="btn-cta" onClick={onNext} disabled={q.status === "approved"}>{nextLabel}</button>
            <button className="btn" style={{ fontSize: 14, padding: "13px 18px", borderRadius: 11 }} onClick={onInquiries}>See my inquiries</button>
          </div>
        </div>
      </div>
    </div>
  );
}
