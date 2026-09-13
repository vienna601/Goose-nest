# frontend (B)

Vite + React + TypeScript, built from `Goose Nest.dc.html` (Claude Design) and
`docs/frontend_design_brief.md`. Types come straight from `shared/types.ts` via
the `@shared` alias — no copy, no camelCase.

## Run

```bash
# terminal 1 — API (reads listings from Supabase, falls back to sample data)
cd backend && ../.venv/bin/uvicorn main:app --port 8000

# terminal 2 — UI on http://localhost:5173
cd frontend && npm install && npm run dev
```

The dev server proxies `/api/*` → `http://127.0.0.1:8000`. Override with
`VITE_API_TARGET` in `frontend/.env`. `npm run build` type-checks and bundles.

## Layout

    src/lib/          api client, inquiry client + simulator, formatting, draft text
    src/components/   listing card, score breakdown, map, detail drawer, hold button
    src/screens/      Home, Searching, Results, Inquiries, contact/ (the agent flow)

## Contact flow and the simulated agent

`backend/routes/contact.py` is still empty, so the first time you start a
contact the UI tries `POST /inquiries`; on 404 it switches to an in-browser
simulator (`src/lib/inquiries.ts`) that walks the same state machine as
`agent/approve.py` and never contacts anyone. The viewer footer says
`SIMULATED` while that's active. Set `VITE_MOCK_AGENT=true` to force it.

Once these endpoints exist, the real flow lights up with no UI changes:

| Endpoint | Body | Returns |
|---|---|---|
| `POST /inquiries` | `{ listing_id, message, sender_name, sender_email, sender_phone, questions[], preferred_times[] }` — times are `"MM/DD/YYYY HH:MM"` | `Inquiry` (status `drafted`) |
| `GET /inquiries/{id}` | — | `Inquiry` (polled once a second if SSE fails) |
| `GET /inquiries/{id}/events` | — | SSE, `data:` frames of `StreamEvent` (`inquiry_update` / `error`) |
| `POST /inquiries/{id}/approve` | `{ approved_by }` | `Inquiry` (status `approved`) |
| `POST /inquiries/{id}/cancel` | — | `Inquiry` (status `cancelled`) |

The UI renders `viewer_url` in an iframe as soon as it's non-null, shows
`filled_fields` on the approval gate, and streams `steps` into the timeline.
Approval is press-and-hold and always sends a non-blank `approved_by`.

Inquiries, sender details and filters are kept in `localStorage`.
