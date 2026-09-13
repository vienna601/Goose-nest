// FastAPI client. Everything goes through /api: the Vite proxy in dev, the
// rewrite in vercel.json in production.
import type { Inquiry, Listing, ScoredListing, SearchRequirements, StreamEvent } from "@shared/types";

const BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "Can't reach the Goose Nest API. Is the backend running on :8000?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean }>("/health"),
  listings: (limit = 1000, offset = 0) => request<Listing[]>(`/listings?limit=${limit}&offset=${offset}`),
  search: (req: SearchRequirements, signal?: AbortSignal) =>
    request<ScoredListing[]>("/search", { method: "POST", body: JSON.stringify(req), signal }),

  // ---- inquiries --------------------------------------------------------
  // Proposed contract; backend/routes/contact.py is not built yet. See
  // frontend/README.md for the shapes.
  createInquiry: (body: CreateInquiryBody) =>
    request<Inquiry>("/inquiries", { method: "POST", body: JSON.stringify(body) }),
  getInquiry: (id: string) => request<Inquiry>(`/inquiries/${id}`),
  approveInquiry: (id: string, approved_by: string) =>
    request<Inquiry>(`/inquiries/${id}/approve`, { method: "POST", body: JSON.stringify({ approved_by }) }),
  cancelInquiry: (id: string) => request<Inquiry>(`/inquiries/${id}/cancel`, { method: "POST" }),

  /** SSE stream of StreamEvent for one inquiry; falls back to polling if the
   *  stream can't open. Returns an unsubscribe function. */
  watchInquiry(id: string, onInquiry: (i: Inquiry) => void, onError: (msg: string) => void): () => void {
    let closed = false;
    let poll: ReturnType<typeof setInterval> | undefined;
    const es = new EventSource(`${BASE}/inquiries/${id}/events`);
    es.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data) as StreamEvent;
        if (ev.type === "inquiry_update") onInquiry(ev.inquiry);
        else if (ev.type === "error") onError(ev.message);
      } catch {
        /* ignore malformed frames */
      }
    };
    es.onerror = () => {
      es.close();
      if (closed || poll) return;
      poll = setInterval(() => {
        api.getInquiry(id).then(onInquiry).catch(() => {});
      }, 1000);
    };
    return () => {
      closed = true;
      es.close();
      if (poll) clearInterval(poll);
    };
  },
};

export interface CreateInquiryBody {
  listing_id: string;
  message: string;
  sender_name: string;
  sender_email: string;
  sender_phone: string | null;
  questions: string[];
  /** Rent Panda showing request slots, "MM/DD/YYYY HH:MM". */
  preferred_times: string[];
}
