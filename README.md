# goose-nest

Waterloo rental search: scrape both local listing sites, rank against what you
actually care about, and let an agent fill in the landlord contact form for you
(with a human approval gate in front of it).

    shared/       the data contract. schema.py is the source of truth.
    collection/   plain-HTTP scraping -> Listing rows   (A)
    agent/        browser-use on Steel, contact forms   (A)
    backend/      API + ranking + lease analysis        (C)
    frontend/     the UI                                (B)

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env      # then fill in the Supabase keys
```

## Database

One hosted Supabase project, shared by the whole team. No local Postgres, no
Docker — the collector, the backend and the frontend all point at the same URL.

1. Create the project at supabase.com (region: East US, closest to Waterloo).
2. SQL Editor -> paste all of `shared/schema.sql` -> Run. It is re-runnable;
   paste it again whenever the schema changes.
3. Project Settings -> API Keys. Put `URL` and the `secret` key
   (`sb_secret_...`) into your `.env`. The `publishable` key
   (`sb_publishable_...`) is the one B puts in the frontend. If you are looking
   at `anon` / `service_role`, that is the "Legacy API keys" tab.
4. `.venv/bin/python scripts/check_db.py` — writes a probe row, reads it back
   through the Pydantic model, deletes it. If that passes, the contract holds.

Writes go through `shared/db.py` with the secret key, server-side only. RLS
pins the publishable key to SELECT, so the frontend can read listings and
nobody on the internet can write to `inquiries`.

`.env` is gitignored. Keys go in the team chat, not in a commit.
