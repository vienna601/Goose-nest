// One interface over the real contact endpoints and a simulated agent.
//
// The simulator exists because backend/routes/contact.py is still empty. It
// walks the same state machine as agent/approve.py (drafted → pending_approval
// → approved → submitted, or cancelled) and never contacts anyone. As soon as
// POST /inquiries answers, the real client is used and the simulator is idle.
import type { Inquiry, Listing } from "@shared/types";
import { api, ApiError, type CreateInquiryBody } from "./api";

export type AgentMode = "live" | "simulated";

export interface InquiryClient {
  mode: AgentMode;
  start(listing: Listing, body: CreateInquiryBody, intendedFields: Record<string, string>): Promise<Inquiry>;
  approve(id: string, approvedBy: string): Promise<Inquiry>;
  cancel(id: string): Promise<Inquiry>;
  watch(id: string, onInquiry: (i: Inquiry) => void, onError: (m: string) => void): () => void;
}

const forceMock = import.meta.env.VITE_MOCK_AGENT === "true";

const liveClient: InquiryClient = {
  mode: "live",
  start: (_l, body) => api.createInquiry(body),
  approve: api.approveInquiry,
  cancel: api.cancelInquiry,
  watch: api.watchInquiry,
};

// ---------------------------------------------------------------------------
// simulator
// ---------------------------------------------------------------------------

type Listener = (i: Inquiry) => void;
const sims = new Map<string, { inq: Inquiry; listeners: Set<Listener>; timers: ReturnType<typeof setTimeout>[] }>();

function emit(id: string, patch: Partial<Inquiry> & { step?: string }) {
  const s = sims.get(id);
  if (!s) return;
  const { step, ...rest } = patch;
  s.inq = { ...s.inq, ...rest, steps: step ? [...s.inq.steps, step] : s.inq.steps };
  s.listeners.forEach((fn) => fn(s.inq));
}

function later(id: string, ms: number, fn: () => void) {
  const s = sims.get(id);
  if (s) s.timers.push(setTimeout(fn, ms));
}

const simClient: InquiryClient = {
  mode: "simulated",
  async start(listing, body, intended) {
    const id = "sim-" + Math.random().toString(36).slice(2, 10);
    const browser = listing.contact_method === "form";
    const inq: Inquiry = {
      id,
      listing_id: listing.id,
      status: "drafted",
      method: listing.contact_method,
      message: body.message,
      sender_name: body.sender_name,
      sender_email: body.sender_email,
      sender_phone: body.sender_phone,
      steel_session_id: browser ? "st_sim_" + id.slice(4) : null,
      viewer_url: null,
      filled_fields: {},
      steps: [browser ? "browser session opened on Steel" : "message drafted"],
      approved_at: null,
      approved_by: null,
      submitted_at: null,
      failure_reason: null,
      created_at: new Date().toISOString(),
    };
    sims.set(id, { inq, listeners: new Set(), timers: [] });

    if (browser) {
      later(id, 1200, () => emit(id, { step: "navigated to the landlord's inquiry form" }));
      later(id, 2300, () => emit(id, { step: "agent filling the showing request (sending is blocked)" }));
      later(id, 2300 + 520 * (Object.keys(intended).length + 1), () =>
        emit(id, { step: "read the filled values back off the page" }),
      );
      later(id, 3100 + 520 * (Object.keys(intended).length + 1), () =>
        emit(id, { status: "pending_approval", filled_fields: intended, step: "form filled, waiting for human approval" }),
      );
    } else {
      later(id, 900, () =>
        emit(id, { status: "pending_approval", filled_fields: intended, step: "waiting for human approval" }),
      );
    }
    return inq;
  },
  async approve(id, approvedBy) {
    const s = sims.get(id);
    if (!s) throw new ApiError(404, "inquiry not found");
    if (s.inq.status !== "pending_approval") throw new ApiError(409, `expected pending_approval, got ${s.inq.status}`);
    if (!approvedBy.trim()) throw new ApiError(422, "approval needs a human name");
    emit(id, { status: "approved", approved_at: new Date().toISOString(), approved_by: approvedBy.trim(), step: `approved by ${approvedBy.trim()}` });
    later(id, 1400, () =>
      emit(id, {
        status: "submitted",
        submitted_at: new Date().toISOString(),
        step: s.inq.method === "form" ? "clicked Send and confirmed the request went through" : "email sent",
      }),
    );
    return s.inq;
  },
  async cancel(id) {
    const s = sims.get(id);
    if (!s) throw new ApiError(404, "inquiry not found");
    if (!["drafted", "pending_approval"].includes(s.inq.status)) {
      throw new ApiError(409, `cannot cancel from ${s.inq.status}`);
    }
    s.timers.forEach(clearTimeout);
    emit(id, { status: "cancelled", step: "cancelled by you — browser session closed, nothing sent" });
    return s.inq;
  },
  watch(id, onInquiry) {
    const s = sims.get(id);
    if (!s) return () => {};
    s.listeners.add(onInquiry);
    onInquiry(s.inq);
    return () => s.listeners.delete(onInquiry);
  },
};

// ---------------------------------------------------------------------------

let resolved: InquiryClient | null = forceMock ? simClient : null;

/** Start an inquiry on the live backend if it has the endpoint, otherwise on
 *  the simulator. The choice sticks for the session. */
export async function startInquiry(
  listing: Listing,
  body: CreateInquiryBody,
  intended: Record<string, string>,
): Promise<{ client: InquiryClient; inquiry: Inquiry }> {
  if (resolved) return { client: resolved, inquiry: await resolved.start(listing, body, intended) };
  try {
    const inquiry = await liveClient.start(listing, body, intended);
    resolved = liveClient;
    return { client: liveClient, inquiry };
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 405 || e.status === 0)) {
      console.info("[goose-nest] /inquiries not available — using the simulated agent");
      resolved = simClient;
      return { client: simClient, inquiry: await simClient.start(listing, body, intended) };
    }
    throw e;
  }
}

export const clientFor = (id: string): InquiryClient => (id.startsWith("sim-") ? simClient : liveClient);
