# Goose Nest 🪿

**Student housing in Waterloo, ranked by what you actually care about — and an AI goose
agent that asks the landlord for a showing while you watch.**

Finding a place isn't hard because listings are hard to find. It's hard because
of everything after: comparing rooms against a bus route you can't picture,
guessing which street is a goose highway, and filling out the same landlord
form over and over. Goose Nest does the comparing for you, then hands the form
to an AI agent running a real browser — which fills it in, stops, and waits for
you to approve before anything is sent.

> 📺 Demo video: [Goose Nest - Waterloo Housing Ranked With Geese Spawns](https://www.youtube.com/watch?v=WCDtgOVVVzs)

---

## What it does

**1. Search real Waterloo listings.** 245 current listings, pulled from Bamboo
Housing (student rooms and sublets) and Rent Panda, geofenced to the City of
Waterloo by postal code.

**2. Rank them against how students live.** Every listing is scored on six
factors you can re-weight, with the breakdown shown on every card:

| Factor         | How it's measured                                                   |
| -------------- | ------------------------------------------------------------------- |
| Price          | against your budget                                                 |
| ION proximity  | walking minutes to the nearest of all **19 ION LRT stops**          |
| Bedrooms       | against what you're renting — a room, or a whole unit               |
| Geese          | **1,789 real Canada Goose sightings** from iNaturalist within 500 m |
| Highway access | distance to Conestoga Pkwy (7/8), Highway 85, Highway 401           |
| GO proximity   | Kitchener GO / University of Waterloo GO, the weekend-trip score    |

Filter by room vs. whole unit, lease vs. 4- or 8-month sublet, budget, walk to
ION, and goose tolerance. View as a list, a map, or both.

**3. Let an agent request the showing.** Pick a listing and the agent opens a
real browser on [Steel](https://steel.dev), logged into a Rent Panda tenant
account, fills out _Request a Showing_ with your preferred times and questions,
and **stops**. You watch it happen in an embedded live view. Then you see the
values it actually typed — read back off the page — and hold to approve.
Only then does it send, exactly once, and it confirms the request arrived.

---

## How the agent stays safe

An agent that can press "send" on your behalf needs more than a prompt telling
it not to. Every one of these is enforced in code and tested:

- **Sending is physically blocked while it fills.** The browser itself fails
  every POST/PUT/PATCH/DELETE to the site during the fill, in every tab — so
  even if the model clicks _Send request_, nothing leaves.
- **What you approve is what's on the page.** The form is read back from the
  DOM and compared to the draft; any mismatch fails the run before you're asked.
- **A human approves every send.** Press-and-hold in the UI. The database
  refuses to record a submission without an approval
  (`check (submitted_at is null or approved_at is not null)`).
- **Exactly one send.** On approval the guard allows a single showing request
  through and blocks anything after it. (We added this after watching the
  agent click Send, then try again with JavaScript.)
- **It never contacts real landlords.** `agent/allowlist.py` lists the only
  listing it may contact — our own test listing. Anything else is refused
  before a browser opens.
- **The live view is view-only.** Steel's player is interactive by default;
  we embed it with `?interactive=false`.
- **No bot-protection bypass.** No CAPTCHA solving, stealth fingerprinting or
  proxy rotation. Sites that challenge automated traffic are left out — see
  [docs/sources.md](docs/sources.md).

---

## Architecture

```
 collection/  httpx + selectolax ──► normalize ──► Supabase Postgres (listings)
   Bamboo Housing (Next.js JSON)                          │
   Rent Panda (Inertia JSON)                              ▼
                                   backend/  FastAPI ── enrich (ION, GO, highways,
                                      │                  iNaturalist geese) ── rank
                                      │
 frontend/  React + Vite ◄── /listings, /search, /inquiries (+ SSE live updates)
      │
      └─ embedded Steel player (view-only)
                                      │
 agent/  Gemini ─► browser-use ─► CDP ─► Steel cloud browser ─► Rent Panda
          │                                 ▲
          └─ write guard, read-back, approval gate, allowlist
```

Listings are collected the boring way — plain HTTP — because reading a page
doesn't need a browser. The browser is reserved for the part that does:
acting on a form that has no API.

| Layer      | Stack                                                                                                       |
| ---------- | ----------------------------------------------------------------------------------------------------------- |
| Collection | Python 3.14, `httpx`, `selectolax`, `tenacity`, OpenStreetMap geocoding fallback                            |
| Agent      | `browser-use` 0.13, Steel (`steel-sdk`), Gemini 3.8 Flash with a Flash-Lite fallback, raw CDP for the guard |
| Backend    | FastAPI, Server-Sent Events                                                                                 |
| Database   | Supabase Postgres with row-level security                                                                   |
| Frontend   | React, TypeScript, Vite                                                                                     |

---

## Repo layout

    shared/       the data contract — schema.py (Pydantic), types.ts, schema.sql
    collection/   scrapers, normalizer, geocoding fallback, cached fixtures
    agent/        Steel session, Gemini, contact flow, write guard, approval gate, allowlist
    backend/      FastAPI app: listings, search + ranking, enrichment, inquiry endpoints
    frontend/     React app: search, results, map, shortlist, contact flow with live viewer
    scripts/      loaders, login, and every check listed below
    docs/         source survey, pitch, video description

---

## Setup

```bash
python3 -m venv .venv                     # Python 3.11+ (browser-use requires it)
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env                      # fill in the keys below
npm --prefix frontend install
```

`.env` needs: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_PUBLISHABLE_KEY`,
`SCRAPER_CONTACT_EMAIL`, `STEEL_API_KEY`, `GEMINI_API_KEY`. `.env` is
gitignored — keys go in the team chat, never in a commit.

### Database

One hosted Supabase project, shared by the team. No local Postgres.

1. Create the project at supabase.com.
2. SQL Editor → paste all of `shared/schema.sql` → Run. It's re-runnable.
3. Project Settings → API Keys → put the URL, the `sb_secret_...` key and the
   `sb_publishable_...` key into `.env`.
4. `.venv/bin/python scripts/check_db.py` — round-trips a probe row.

Writes go through `shared/db.py` with the secret key, server-side only. RLS pins
the publishable key to SELECT.

### Load listings

```bash
.venv/bin/python scripts/load_listings.py       # from cached fixtures — no scraping
```

### Log the agent in (once)

```bash
.venv/bin/python scripts/steel_login.py         # you log in yourself in Steel's live player
.venv/bin/python scripts/steel_login.py --verify
```

The script never sees your password. It saves a Steel profile id to `.env`.

---

## Run it

```bash
cd backend && ../.venv/bin/python -m uvicorn main:app --port 8000
```

```bash
npm --prefix frontend run dev                   # http://localhost:5173
```

The frontend proxies `/api` to the backend. If the contact endpoints aren't
reachable it falls back to a simulated agent (the viewer footer says
`SIMULATED`); force that with `VITE_MOCK_AGENT=true`.

## Checks

None of these send anything.

| Command                           | Proves                                                                                           |
| --------------------------------- | ------------------------------------------------------------------------------------------------ |
| `scripts/check_db.py`             | Supabase credentials, schema, upsert                                                             |
| `scripts/check_agent.py`          | the approval gate refuses every unapproved path                                                  |
| `scripts/check_guard.py`          | write guard blocks fetch/XHR/form POSTs in old and new tabs; allow-once lets exactly one through |
| `scripts/check_contact_api.py`    | every `/inquiries` endpoint and the SSE stream, with a fake agent                                |
| `scripts/check_steel.py`          | Gemini + browser-use + Steel end to end, read-only                                               |
| `scripts/steel_login.py --verify` | the saved profile is still logged in                                                             |

Run each with `.venv/bin/python`.

## API

| Method | Path                      |                                                |
| ------ | ------------------------- | ---------------------------------------------- |
| GET    | `/listings`               | all listings, enriched                         |
| POST   | `/search`                 | ranked results with score breakdowns           |
| POST   | `/inquiries`              | start a showing request (returns `drafted`)    |
| GET    | `/inquiries/{id}`         | current state                                  |
| GET    | `/inquiries/{id}/events`  | SSE stream of state changes                    |
| POST   | `/inquiries/{id}/approve` | `{approved_by}` — only from `pending_approval` |
| POST   | `/inquiries/{id}/cancel`  | only from `drafted` or `pending_approval`      |

---

## Honest limits

- **One contactable listing.** Both sources gate landlord contact behind an
  account. We automate Rent Panda through our own tenant account against a
  listing we posted; Bamboo listings link out.
- **Two sources.** Rentals.ca and others challenge automated traffic, and we
  don't work around that. Details in [docs/sources.md](docs/sources.md).
- **Lease analysis and deadline export were planned and not built.**
- **Gemini's free tier won't carry a live demo** — enable billing.
- **One agent run at a time**, held in memory; restarting the backend
  mid-run orphans it.

## Team

Built by Vienna, Ansh, Maira — GitHub: [@vienna601](https://github.com/vienna601),
[@anshjindal7](https://github.com/anshjindal7), [@MairaOpel](https://github.com/MairaOpel)
