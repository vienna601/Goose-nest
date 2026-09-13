import { useEffect, useMemo, useState } from "react";
import type { Inquiry, Listing } from "@shared/types";
import { contactMethodLabel, ionLine, priceLabel, shortAddress, sourceLabel, termLine, unitLine } from "../../lib/format";
import { composeMessage, showingNote, usDateTime, usesShowingRequest, type Sender, type ViewingTime } from "../../lib/draft";
import { clientFor, startInquiry, type InquiryClient } from "../../lib/inquiries";
import { isTerminal } from "../../lib/records";
import { load, save } from "../../lib/storage";
import { ApiError } from "../../lib/api";
import { Goose } from "../../components/Goose";
import { DetailsStep, senderReady } from "./DetailsStep";
import { AgentStage } from "./AgentStage";
import { Outcome } from "./Outcome";

interface Props {
  queue: Listing[];
  resume: Inquiry | null;
  sender: Sender;
  setSender: (s: Sender) => void;
  onInquiry: (i: Inquiry, l: Listing) => void;
  onBack: () => void;
  onInquiries: () => void;
  onQueueDone: () => void;
  toast: (m: string) => void;
}

function defaultTimes(): ViewingTime[] {
  const d = new Date();
  const day = (n: number) => {
    const x = new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);
    return `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
  };
  return [{ date: day(1), time: "18:00" }, { date: day(2), time: "18:00" }];
}

export function ContactFlow({ queue, resume, sender, setSender, onInquiry, onBack, onInquiries, onQueueDone, toast }: Props) {
  const [idx, setIdx] = useState(0);
  const [questions, setQuestionsRaw] = useState<string[]>(() => load("questions", ["Is parking included?", "Are utilities included?"]));
  const [times, setTimes] = useState<ViewingTime[]>(defaultTimes);
  const [inquiry, setInquiry] = useState<Inquiry | null>(resume);
  const [client, setClient] = useState<InquiryClient | null>(resume ? clientFor(resume.id) : null);
  const [busy, setBusy] = useState(false);

  const listing = queue[idx];
  const setQuestions = (q: string[]) => { setQuestionsRaw(q); save("questions", q); };

  // Drafts and what the agent should type.
  const draft = useMemo(() => composeMessage(listing, sender, questions), [listing, sender, questions]);
  const showing = usesShowingRequest(listing);
  const intended = useMemo<Record<string, string>>(() => {
    if (listing.contact_method === "email") {
      return { to: listing.contact_email ?? "", subject: `Inquiry: ${shortAddress(listing.address_raw)}`, body: draft };
    }
    if (showing) {
      const f: Record<string, string> = { notes: showingNote(listing, questions) };
      times.forEach((t, i) => (f[`preferred_time_${i + 1}`] = usDateTime(t)));
      return f;
    }
    const f: Record<string, string> = { full_name: sender.name, email: sender.email };
    if (sender.phone) f.phone = sender.phone;
    f.message = draft;
    return f;
  }, [listing, showing, questions, times, sender, draft]);

  // Live updates for the active inquiry.
  useEffect(() => {
    if (!inquiry || !client || isTerminal(inquiry)) return;
    return client.watch(
      inquiry.id,
      (i) => { setInquiry(i); onInquiry(i, listing); },
      (m) => toast(m),
    );
    // Re-subscribe only when the inquiry itself changes, not on every update.
  }, [inquiry?.id, client]);

  const run = async (fn: () => Promise<Inquiry | void>) => {
    setBusy(true);
    try {
      const out = await fn();
      if (out) { setInquiry(out); onInquiry(out, listing); }
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Something went wrong. Nothing was sent.");
    } finally {
      setBusy(false);
    }
  };

  const start = () =>
    run(async () => {
      const res = await startInquiry(
        listing,
        {
          listing_id: listing.id,
          message: draft,
          sender_name: sender.name.trim(),
          sender_email: sender.email.trim(),
          sender_phone: sender.phone.trim() || null,
          questions,
          preferred_times: showing ? times.map(usDateTime) : [],
        },
        intended,
      );
      setClient(res.client);
      return res.inquiry;
    });

  const approve = (by: string) => run(() => client!.approve(inquiry!.id, by));
  const cancel = () => run(() => client!.cancel(inquiry!.id));

  const next = () => {
    if (idx + 1 < queue.length) {
      setIdx(idx + 1);
      setInquiry(null);
      setClient(null);
    } else {
      onQueueDone();
    }
  };

  const copy = (text: string) =>
    navigator.clipboard?.writeText(text).then(() => toast("Copied to clipboard."), () => toast("Couldn't copy — select the text instead."));

  const method = listing.contact_method;
  const phase = !inquiry ? 0 : inquiry.status === "drafted" ? 1 : inquiry.status === "pending_approval" ? 2 : 3;
  const stepLabels = method === "form" ? ["Your details", "Agent fills", "Review", "Sent"] : ["Your details", "Draft", "Review", "Sent"];
  const left = queue.length - idx - 1;
  const nextLabel = left > 0 ? `Next listing (${left} left) →` : "Back to results";

  return (
    <div className="page">
      <div className="row wrap" style={{ gap: 16 }}>
        <button className="btn" onClick={onBack}>← Results</button>
        <div className="mono" style={{ fontSize: 12, color: "var(--ink-3)" }}>
          Listing {idx + 1} of {queue.length} · {left} after this
        </div>
        <div className="grow" />
        {(method === "form" || method === "email") && (
          <div className="stepper" aria-label="Progress">
            {stepLabels.map((label, i) => (
              <span key={label} className={`stepper-item${i < phase ? " done" : i === phase ? " current" : ""}`}>
                <i>{i + 1}</i>
                {label}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="listing-strip">
        <div className="thumb">{listing.image_url ? <img src={listing.image_url} alt="" /> : <Goose size={26} fill="#E9E1D3" />}</div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontFamily: "var(--display)", fontWeight: 600, fontSize: 18, letterSpacing: "-.02em" }}>
            {priceLabel(listing)} · {shortAddress(listing.address_raw)}
          </div>
          <div style={{ fontSize: 13.5, color: "var(--ink-2)" }}>
            {[unitLine(listing), termLine(listing), ionLine(listing)].filter(Boolean).join(" · ")}
          </div>
        </div>
        <div className="grow" />
        <div className="mono" style={{ fontSize: 11, letterSpacing: ".08em", textTransform: "uppercase", color: "var(--ink-3)", textAlign: "right" }}>
          contact method
          <br />
          <span style={{ color: "var(--ink)" }}>{contactMethodLabel(method)}</span>
        </div>
      </div>

      {(method === "account_required" || method === "unknown") && (
        <NoAutoContact listing={listing} draft={draft} onCopy={copy} onNext={next} nextLabel={left > 0 ? "Skip to next listing →" : "Back to results"} />
      )}

      {(method === "form" || method === "email" || method === "phone") && !inquiry && (
        <DetailsStep
          listing={listing}
          sender={sender}
          setSender={setSender}
          questions={questions}
          setQuestions={setQuestions}
          times={method === "form" && showing ? times : null}
          setTimes={setTimes}
          preview={
            showing && method === "form"
              ? { title: "Showing request note", text: intended.notes + "\n\nPreferred times:\n" + times.map(usDateTime).join("\n") }
              : { title: "Draft message", text: draft }
          }
        >
          {method === "phone" ? (
            <>
              <div style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
                This landlord takes calls or texts only, so there's no form for the agent. Your message is ready to paste.
              </div>
              <div className="price" style={{ marginTop: 12 }}>
                <a href={`tel:${listing.contact_phone}`} style={{ color: "inherit" }}>{listing.contact_phone ?? "Number on listing"}</a>
              </div>
              <div className="row wrap" style={{ marginTop: 14, gap: 8 }}>
                <button className="btn-cta" onClick={() => copy(draft)}>Copy message</button>
                <button className="btn" onClick={next}>{nextLabel}</button>
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
                {method === "form" ? (
                  <>The agent opens a real browser on <strong>Steel</strong>, finds {sourceLabel(listing.source)}'s inquiry form, fills these values, and stops. You'll watch it live and read back exactly what's in the form before anything sends.</>
                ) : (
                  <>We'll prepare this email to {listing.contact_name ?? "the landlord"} and show it to you one more time before it goes out.</>
                )}
              </div>
              <button className="btn-cta btn-block" style={{ marginTop: 16, fontSize: 17, padding: 15 }} disabled={busy || !senderReady(sender)} onClick={start}>
                {busy ? "Starting…" : method === "form" ? "Have the agent fill the form" : "Prepare the email"}
              </button>
              <div style={{ marginTop: 9, textAlign: "center", fontSize: 12, color: "var(--ink-3)" }}>
                {senderReady(sender) ? "Nothing is sent until you approve." : "Add your name and a valid email first."}
              </div>
            </>
          )}
        </DetailsStep>
      )}

      {inquiry && (inquiry.status === "drafted" || inquiry.status === "pending_approval") && client && (
        <AgentStage inquiry={inquiry} listing={listing} mode={client.mode} intended={intended} busy={busy} onApprove={approve} onCancel={cancel} />
      )}

      {inquiry && phase === 3 && (
        <Outcome inquiry={inquiry} listing={listing} nextLabel={nextLabel} onNext={next} onInquiries={onInquiries} onCopy={copy} />
      )}
    </div>
  );
}

function NoAutoContact({ listing, draft, onCopy, onNext, nextLabel }: { listing: Listing; draft: string; onCopy: (t: string) => void; onNext: () => void; nextLabel: string }) {
  const src = sourceLabel(listing.source);
  const login = listing.contact_method === "account_required";
  return (
    <div className="cols-2">
      <div className="card">
        <h3 className="h3">{login ? `${src} needs a login to contact this landlord.` : "We couldn't find a way to contact this landlord."}</h3>
        <p style={{ fontSize: 14.5, color: "var(--ink-2)", lineHeight: 1.55 }}>
          {login
            ? `We don't create accounts on other sites on your behalf, so the agent stops here. Sign in on ${src} and paste the message — it's ready.`
            : "The listing didn't include a form, email or phone number we could read. The original post may have more."}
        </p>
        <div className="row wrap" style={{ gap: 8, marginTop: 16 }}>
          <a className="btn-cta" href={listing.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>Open on {src} ↗</a>
          <button className="btn" onClick={() => onCopy(draft)}>Copy message</button>
          <button className="btn" onClick={onNext}>{nextLabel}</button>
        </div>
      </div>
      <div className="card-night">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="eyebrow" style={{ color: "var(--ink-4)" }}>Draft message</div>
          <div className="tag-dark">for you to paste</div>
        </div>
        <div className="draft">{draft}</div>
      </div>
    </div>
  );
}
