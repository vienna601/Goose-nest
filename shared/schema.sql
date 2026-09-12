-- Supabase DDL — mirror of shared/schema.py. Proposal for C.
-- Enum values below MUST match the Python enums character for character.

create type source_enum        as enum ('rentals_ca', 'rent_panda');
create type contact_method_enum as enum ('form', 'email', 'phone', 'unknown');
create type inquiry_status_enum as enum (
  'drafted', 'pending_approval', 'approved', 'submitted', 'failed', 'cancelled'
);

create table listings (
  id                uuid primary key default gen_random_uuid(),
  source            source_enum not null,
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
  unique (source, source_id)
);

create index listings_cluster_idx  on listings (cluster_id);
create index listings_price_idx    on listings (price_max);
create index listings_beds_idx     on listings (beds);
create index listings_ion_idx      on listings (ion_walk_min);

create table inquiries (
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

create table lease_analyses (
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
