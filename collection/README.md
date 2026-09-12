# Collection (owner: A)

Plain HTTP scraping. No browser. `httpx` + `selectolax` + `tenacity`.

    parsers/rentals_ca.py    list pages: rentals.ca/waterloo?p=N
    parsers/rent_panda.py    list pages: app.rentpanda.ca/search-result
    fetch.py                 shared httpx client: rate limit, retries, cache
    normalize.py             raw dict -> shared.schema.Listing
    dedupe.py                same building across both sources
    run.py                   CLI: full Waterloo pull -> Supabase

Rules:
- 1 request per 2-3s per domain. Honest User-Agent with contact email.
- Cache every response to collection/cache/ keyed by URL hash. Re-parse from
  cache, never re-fetch, while iterating on selectors.
- Full Waterloo pull happens ONCE (~H4). After that, work off cache.

Geofence: Waterloo city only — N2J N2K N2L N2M N2T N2V.
Kitchener/Cambridge stay behind a flag.

fixtures/ holds a few saved pages committed to the repo so parser tests run
offline and B/C aren't blocked on the network.
