import { useState } from "react";
import type { Listing } from "@shared/types";
import type { Sender, ViewingTime } from "../../lib/draft";

interface Props {
  listing: Listing;
  sender: Sender;
  setSender: (s: Sender) => void;
  questions: string[];
  setQuestions: (q: string[]) => void;
  times: ViewingTime[] | null; // null when the site has no showing slots
  setTimes: (t: ViewingTime[]) => void;
  preview: { title: string; text: string };
  children: React.ReactNode; // the CTA card, which differs by contact method
}

const emailOk = (e: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e);

export function DetailsStep({ sender, setSender, questions, setQuestions, times, setTimes, preview, children }: Props) {
  const [draftQ, setDraftQ] = useState("");
  const addQ = () => {
    const q = draftQ.trim();
    if (q) setQuestions([...questions, q]);
    setDraftQ("");
  };

  return (
    <div className="cols-2">
      <div className="card">
        <h3 className="h3">Your details</h3>
        <div style={{ fontSize: 13.5, color: "var(--ink-2)", marginTop: 6 }}>Saved on this device so you only type this once.</div>
        <div style={{ marginTop: 18, display: "grid", gap: 13 }}>
          <label className="field">
            <span className="eyebrow">Full name</span>
            <input className="input" value={sender.name} autoComplete="name" onChange={(e) => setSender({ ...sender, name: e.target.value })} />
          </label>
          <label className="field">
            <span className="eyebrow">Email</span>
            <input
              className="input"
              type="email"
              autoComplete="email"
              value={sender.email}
              aria-invalid={!!sender.email && !emailOk(sender.email)}
              onChange={(e) => setSender({ ...sender, email: e.target.value })}
            />
          </label>
          <label className="field">
            <span className="eyebrow">Phone (optional)</span>
            <input className="input" type="tel" autoComplete="tel" placeholder="519-555-0134" value={sender.phone} onChange={(e) => setSender({ ...sender, phone: e.target.value })} />
          </label>
        </div>

        <div className="eyebrow" style={{ marginTop: 20 }}>Questions to ask</div>
        <div style={{ marginTop: 9, display: "grid", gap: 7 }}>
          {questions.map((q, i) => (
            <div className="q-item" key={q + i}>
              <span className="grow">{q}</span>
              <button className="x-btn" style={{ width: 20, height: 20, background: "var(--line-soft)" }} onClick={() => setQuestions(questions.filter((_, k) => k !== i))} aria-label={`Remove question ${q}`}>
                ×
              </button>
            </div>
          ))}
        </div>
        <form className="row" style={{ gap: 7, marginTop: 9 }} onSubmit={(e) => { e.preventDefault(); addQ(); }}>
          <input className="input input-dashed grow" style={{ padding: "9px 11px", fontSize: 13.5 }} placeholder="Is parking included?" value={draftQ} onChange={(e) => setDraftQ(e.target.value)} />
          <button className="btn btn-white" type="submit">Add</button>
        </form>

        {times && (
          <>
            <div className="eyebrow" style={{ marginTop: 20 }}>Preferred viewing times</div>
            <div style={{ marginTop: 9, display: "grid", gap: 7 }}>
              {times.map((t, i) => (
                <div className="row" style={{ gap: 7 }} key={i}>
                  <input type="date" className="input grow" aria-label={`Viewing ${i + 1} date`} value={t.date} onChange={(e) => setTimes(times.map((x, k) => (k === i ? { ...x, date: e.target.value } : x)))} />
                  <input type="time" className="input" style={{ width: 120 }} aria-label={`Viewing ${i + 1} time`} value={t.time} onChange={(e) => setTimes(times.map((x, k) => (k === i ? { ...x, time: e.target.value } : x)))} />
                  {times.length > 1 && (
                    <button className="x-btn" style={{ width: 20, height: 20, flex: "none" }} onClick={() => setTimes(times.filter((_, k) => k !== i))} aria-label="Remove time">×</button>
                  )}
                </div>
              ))}
              {times.length < 3 && (
                <button className="link-btn" style={{ justifySelf: "start" }} onClick={() => setTimes([...times, { ...times[times.length - 1] }])}>
                  + Add another time
                </button>
              )}
            </div>
          </>
        )}
      </div>

      <div>
        <div className="card-night">
          <div className="row" style={{ justifyContent: "space-between", gap: 12 }}>
            <div className="eyebrow" style={{ color: "var(--ink-4)", letterSpacing: ".08em" }}>{preview.title}</div>
            <div className="tag-dark">not sent</div>
          </div>
          <div className="draft">{preview.text}</div>
        </div>
        <div className="card-sm" style={{ marginTop: 14 }}>{children}</div>
      </div>
    </div>
  );
}

export const senderReady = (s: Sender) => s.name.trim().length > 1 && emailOk(s.email);
