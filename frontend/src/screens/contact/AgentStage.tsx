import { useEffect, useState } from "react";
import type { Inquiry, Listing } from "@shared/types";
import { sourceLabel } from "../../lib/format";
import type { AgentMode } from "../../lib/inquiries";
import { HoldButton } from "../../components/HoldButton";

const SESSION_CAP_S = 15 * 60; // agent/session.py SESSION_CAP_MS

interface Props {
  inquiry: Inquiry;
  listing: Listing;
  mode: AgentMode;
  /** What we asked the agent to type, used to animate the simulated viewer. */
  intended: Record<string, string>;
  busy: boolean;
  onApprove: (approvedBy: string) => void;
  onCancel: () => void;
}

export function AgentStage({ inquiry, listing, mode, intended, busy, onApprove, onCancel }: Props) {
  const browser = inquiry.method === "form";
  const review = inquiry.status === "pending_approval";
  const [approver, setApprover] = useState(inquiry.sender_name);

  return (
    <div className="cols-viewer">
      <div>
        {browser ? (
          <BrowserFrame inquiry={inquiry} listing={listing} mode={mode} intended={intended} />
        ) : (
          <div className="card-night">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div className="eyebrow" style={{ color: "var(--ink-4)" }}>Email draft · to {listing.contact_email ?? "landlord"}</div>
              <div className="tag-dark">not sent</div>
            </div>
            <div className="draft">{inquiry.message}</div>
          </div>
        )}
        <div className="note-warn row" style={{ marginTop: 14, gap: 11 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--bark)", flex: "none" }} />
          {browser ? "Sending is blocked while the agent fills the form." : "Nothing is emailed until you approve."}
        </div>
      </div>

      <div>
        {!review ? (
          <div className="card">
            <h3 className="h3" style={{ fontSize: 21 }}>{browser ? "Agent is working" : "Preparing your message"}</h3>
            <Timeline steps={inquiry.steps} live />
            <button className="btn-ghost-wide" style={{ marginTop: 6 }} onClick={onCancel} disabled={busy}>
              Cancel — don't send
            </button>
          </div>
        ) : (
          <div className="gate" role="region" aria-label="Review and approve">
            <div className="kicker" style={{ color: "#8A5A22" }}>Waiting for you</div>
            <div style={{ fontFamily: "var(--display)", fontWeight: 800, fontSize: 24, letterSpacing: "-.03em", marginTop: 8, lineHeight: 1.1 }}>
              Here's exactly what's in the {browser ? "form" : "email"}. Nothing has been sent.
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 8 }}>
              {browser
                ? mode === "live"
                  ? "Read back from the live page — not what we intended to type."
                  : "Simulated agent: these are the values it would read back from the page."
                : "This is the email that will go out."}
            </div>

            <div className="fields-table">
              {Object.entries(inquiry.filled_fields).map(([k, v]) => (
                <div key={k}>
                  <span>{k}</span>
                  <span>{v}</span>
                </div>
              ))}
            </div>

            <label className="field" style={{ marginTop: 16 }}>
              <span className="eyebrow">Approved by</span>
              <input className="input" value={approver} onChange={(e) => setApprover(e.target.value)} />
            </label>

            <div style={{ marginTop: 14 }}>
              <HoldButton
                disabled={busy || !approver.trim()}
                onConfirm={() => onApprove(approver.trim())}
                label="Hold to approve & send"
                holdingLabel="Keep holding to send…"
              />
              <button className="btn-ghost-wide" style={{ marginTop: 9 }} onClick={onCancel} disabled={busy}>
                Cancel — don't send
              </button>
              <div style={{ marginTop: 10, fontSize: 12, color: "var(--ink-3)", textAlign: "center" }}>
                Approving records {approver.trim() || "your name"} on the audit trail.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function Timeline({ steps, live }: { steps: string[]; live?: boolean }) {
  return (
    <div className="timeline">
      {steps.map((s, i) => {
        const current = live && i === steps.length - 1;
        return (
          <div className="tl-item" key={i}>
            <div className="tl-rail">
              <span className={`tl-mark${current ? " current" : ""}`}>{current ? "" : "✓"}</span>
              <span className="tl-line" />
            </div>
            <div style={{ paddingBottom: 14 }}>
              <div style={{ fontSize: 14, color: current ? "#8A5A22" : "var(--ink)" }}>{s}</div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)", marginTop: 3 }}>{current ? "in progress" : "done"}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function BrowserFrame({ inquiry, listing, mode, intended }: { inquiry: Inquiry; listing: Listing; mode: AgentMode; intended: Record<string, string> }) {
  const left = useCountdown(inquiry.created_at);
  const url = (listing.contact_url ?? listing.url).replace(/^https?:\/\//, "");
  const expired = left <= 0;

  return (
    <div className="browser">
      <div className="browser-bar">
        <span className="dot" />
        <span className="dot" />
        <span className="dot" />
        <div className="url">{url}</div>
        <span className="live"><i />LIVE</span>
        <span className="mono" style={{ fontSize: 10, letterSpacing: ".1em", color: "var(--ink-3)" }}>VIEW ONLY</span>
      </div>
      <div className="viewport">
        {expired ? (
          <div className="connecting">
            <span className="mono" style={{ fontSize: 12, color: "#A39A8C", textAlign: "center", padding: 20 }}>
              Browser session hit its 15-minute cap and closed. Nothing was sent.
            </span>
          </div>
        ) : inquiry.viewer_url ? (
          <iframe src={inquiry.viewer_url} title="Live agent browser (view only)" sandbox="allow-scripts allow-same-origin" />
        ) : mode === "simulated" ? (
          <SimulatedForm listing={listing} intended={intended} inquiry={inquiry} />
        ) : (
          <div className="connecting">
            <div style={{ display: "grid", justifyItems: "center", gap: 14 }}>
              <span className="spinner" />
              <span className="mono" style={{ fontSize: 12, color: "#A39A8C" }}>connecting to Steel session…</span>
            </div>
          </div>
        )}
      </div>
      <div className="browser-foot">
        <span>
          STEEL · SESSION {inquiry.steel_session_id ?? "…"}
          {mode === "simulated" && " · SIMULATED"}
        </span>
        <span>session cap 15:00 · {fmt(left)} left</span>
      </div>
    </div>
  );
}

/** Stand-in for the Steel viewer while the contact endpoints don't exist:
 *  types the intended values in, one field at a time. */
function SimulatedForm({ listing, intended, inquiry }: { listing: Listing; intended: Record<string, string>; inquiry: Inquiry }) {
  const entries = Object.entries(intended);
  const filling = inquiry.steps.some((s) => s.startsWith("agent filling"));
  const doneAll = inquiry.status !== "drafted";
  const [typed, setTyped] = useState(0);
  const connected = inquiry.steps.length > 1;

  useEffect(() => {
    if (!filling || doneAll) return;
    const t = setInterval(() => setTyped((n) => Math.min(entries.length, n + 1)), 520);
    return () => clearInterval(t);
  }, [filling, doneAll, entries.length]);

  const shown = doneAll ? entries.length : typed;
  if (!connected) {
    return (
      <div className="connecting">
        <div style={{ display: "grid", justifyItems: "center", gap: 14 }}>
          <span className="spinner" />
          <span className="mono" style={{ fontSize: 12, color: "#A39A8C" }}>connecting to Steel session…</span>
        </div>
      </div>
    );
  }
  return (
    <div className="sim-form">
      <div style={{ fontSize: 11, letterSpacing: ".12em", textTransform: "uppercase", color: "#8A8275" }}>{sourceLabel(listing.source)}</div>
      <div style={{ fontFamily: "var(--display)", fontWeight: 600, fontSize: 20, marginTop: 6 }}>
        {listing.source === "rent_panda" ? "Request a showing" : "Contact the landlord"}
      </div>
      <div style={{ marginTop: 16, display: "grid", gap: 11 }}>
        {entries.map(([k, v], i) => (
          <div key={k}>
            <div style={{ fontSize: 10.5, letterSpacing: ".08em", textTransform: "uppercase", color: "#8A8275", marginBottom: 4 }}>{k.replace(/_/g, " ")}</div>
            <div className={`sim-field${i < shown ? " filled" : ""}`}>
              {i < shown ? v : ""}
              {filling && !doneAll && i === shown && <span className="caret" />}
            </div>
          </div>
        ))}
      </div>
      <div className="row" style={{ marginTop: 18, gap: 12 }}>
        <div style={{ background: "#C9C6BD", color: "#7A776E", borderRadius: 8, padding: "11px 20px", fontSize: 14, fontWeight: 500 }}>Send request</div>
        <div style={{ fontSize: 12, color: "#8A8275" }}>blocked by Goose Nest</div>
      </div>
    </div>
  );
}

function useCountdown(createdAt: string) {
  const calc = () => Math.max(0, SESSION_CAP_S - Math.floor((Date.now() - new Date(createdAt).getTime()) / 1000));
  const [left, setLeft] = useState(calc);
  useEffect(() => {
    const t = setInterval(() => setLeft(calc()), 1000);
    return () => clearInterval(t);
  }, [createdAt]);
  return left;
}

const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
