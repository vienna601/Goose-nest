-- Supabase DDL — mirror of shared/schema.py. Proposal for C.
-- Enum values below MUST match the Python enums character for character.
--
-- Re-runnable: paste the whole file into the Supabase SQL editor as many times
-- as you like. Enums are guarded, tables are `if not exists`, policies are
-- dropped before create. It will NOT drop or alter an existing column — if you
-- add a field to schema.py mid-hack, add an `alter table ... add column if not
-- exists` to the MIGRATIONS section at the bottom.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------

-- `source` is deliberately NOT an enum — see the MIGRATIONS note at the bottom.
-- shared/schema.py holds the canonical list and does the validating.

do $$ begin
  create type contact_method_enum as enum ('form', 'email', 'phone', 'unknown');
exception when duplicate_object then null; end $$;

do $$ begin
  create type inquiry_status_enum as enum (
    'drafted', 'pending_approval', 'approved', 'submitted', 'failed', 'cancelled'
  );
exception when duplicate_object then null; end $$;

-- ---------------------------------------------------------------------------
-- listings
-- ---------------------------------------------------------------------------

create table if not exists listings (
  id                uuid primary key default gen_random_uuid(),
  source            text        not null,
  source_id         text        not null,
  url               text        not null,
  cluster_id        uuid,

  address_raw        text not null,
  address_normalized text not null,
  unit               text,
  city               text not null default 'Waterloo',
  postal_prefix      text,
  postal_code        text,
  lat                double precision,
  lng                double precision,

  price_min int,
  price_max int,

  beds           real,
  den            boolean not null default false,
  baths          real,
  sqft           int,
  available_date date,

  contact_method       contact_method_enum not null default 'unknown',
  contact_url          text,
  contact_email        text,
  contact_phone        text,
  contact_name         text,
  contact_behind_click boolean not null default false,

  image_url text,
  images    jsonb not null default '[]'::jsonb,

  nearest_ion_stop   text,
  ion_distance_m     int,
  ion_walk_min       int,
  go_distance_m      int,
  highway_distance_m int,
  geese_zone         text,
  geese_score        int check (geese_score between 1 and 5),

  scraped_at timestamptz not null default now(),
  cache_key  text not null,
  raw        jsonb not null default '{}'::jsonb,

  -- Re-running the collector updates rows instead of duplicating them.
  -- Named explicitly because shared/db.py passes it as the upsert target.
  constraint listings_source_source_id_key unique (source, source_id)
);

create index if not exists listings_cluster_idx on listings (cluster_id);
create index if not exists listings_price_idx   on listings (price_max);
create index if not exists listings_beds_idx    on listings (beds);
create index if not exists listings_ion_idx     on listings (ion_walk_min);
create index if not exists listings_postal_idx  on listings (postal_prefix);

-- ---------------------------------------------------------------------------
-- inquiries
-- ---------------------------------------------------------------------------

create table if not exists inquiries (
  id         uuid primary key default gen_random_uuid(),
  listing_id uuid not null references listings(id) on delete cascade,
  status     inquiry_status_enum not null default 'drafted',
  method     contact_method_enum not null,

  message      text not null,
  sender_name  text not null,
  sender_email text not null,
  sender_phone text,

  steel_session_id text,
  viewer_url       text,
  filled_fields    jsonb not null default '{}'::jsonb,
  steps            jsonb not null default '[]'::jsonb,

  approved_at    timestamptz,
  approved_by    text,
  submitted_at   timestamptz,
  failure_reason text,

  created_at timestamptz not null default now(),

  -- Belt and braces: the DB refuses to record a send that nobody approved.
  constraint submitted_requires_approval
    check (submitted_at is null or approved_at is not null)
);

create index if not exists inquiries_listing_idx on inquiries (listing_id);
create index if not exists inquiries_status_idx  on inquiries (status);

-- ---------------------------------------------------------------------------
-- lease_analyses
-- ---------------------------------------------------------------------------

create table if not exists lease_analyses (
  id           uuid primary key default gen_random_uuid(),
  listing_id   uuid references listings(id) on delete set null,
  filename     text not null,
  monthly_rent int,
  term_start   date,
  term_end     date,
  deposit      int,
  deadlines    jsonb not null default '[]'::jsonb,
  flags        jsonb not null default '[]'::jsonb,
  summary      text,
  created_at   timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Row Level Security
--
-- Supabase exposes every table over PostgREST to anyone holding the publishable
-- key, and that key ships in B's frontend bundle. Without RLS that is a public
-- read/write endpoint on our inquiries table. So: RLS on everywhere, the
-- publishable key gets SELECT only, and all writes go through the secret key
-- from the backend (it bypasses RLS — that is why it never leaves the server).
--
-- `anon` and `authenticated` below are POSTGRES ROLE names, not key names, and
-- they did not change when the keys were renamed. A request carrying the
-- publishable key still arrives as the `anon` role; the secret key arrives as
-- `service_role`. Do not "modernize" these to publishable/secret — there are no
-- such roles and the policies will fail to create.
-- ---------------------------------------------------------------------------

alter table listings       enable row level security;
alter table inquiries      enable row level security;
alter table lease_analyses enable row level security;

drop policy if exists listings_anon_read on listings;
create policy listings_anon_read on listings
  for select to anon, authenticated using (true);

drop policy if exists inquiries_anon_read on inquiries;
create policy inquiries_anon_read on inquiries
  for select to anon, authenticated using (true);

drop policy if exists lease_analyses_anon_read on lease_analyses;
create policy lease_analyses_anon_read on lease_analyses
  for select to anon, authenticated using (true);

-- ---------------------------------------------------------------------------
-- MIGRATIONS — append here when schema.py changes mid-hack, so the file stays
-- safe to re-run against a database that already has data in it.
-- e.g.  alter table listings add column if not exists pet_friendly boolean;
-- ---------------------------------------------------------------------------

-- 2026-09-12 (A) — the source survey forced three changes. See docs/sources.md.

-- 1. `source` stops being an enum. We churned sources twice in one morning
--    (rentals.ca out on a bot challenge, bamboo in) and each change would have
--    been a type migration. The canonical list now lives in shared/schema.py,
--    which still validates it; Postgres just stores the text.
alter table listings alter column source type text using source::text;
drop type if exists source_enum;

-- 2. Room vs unit. Bamboo listings are ROOMS in shared student houses — a
--    5-bedroom house with one $695 room free. rentals.ca-style listings are
--    whole units. Ranking "under $2400" across both without this column
--    compares a single bedroom against an entire apartment and calls it a win.
alter table listings add column if not exists listing_kind text not null default 'unit'
  check (listing_kind in ('unit', 'room'));
alter table listings add column if not exists total_bedrooms int;   -- in the whole house
alter table listings add column if not exists rooms_available int;

-- 3. Sublet vs lease. 136 of 248 real Waterloo listings are 4- or 8-month
--    sublets. For a student search that is a primary filter, not a footnote.
alter table listings add column if not exists lease_type text
  check (lease_type is null or lease_type in ('lease', 'sublet'));
alter table listings add column if not exists term_months int;

alter table listings add column if not exists is_available boolean not null default true;

create index if not exists listings_kind_idx       on listings (listing_kind);
create index if not exists listings_lease_type_idx on listings (lease_type);
