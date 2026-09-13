## Inspiration

Every Waterloo student has done the same apartment hunt. Forty tabs open.
Squinting at a map to guess whether "close to campus" means a five-minute walk
to the ION or a twenty-five-minute one. Wondering which street is a goose
highway. And then filling out the same landlord form, again and again, before
waiting to hear back.

Search sites are good at showing you listings. None of them help with the
parts that actually take the time: comparing places the way students live, and
doing the tedious back-and-forth with landlords. We wanted to build something
that does both, and we wanted the second part to be done by an AI agent you'd
actually trust near a send button.

## What it does

**Goose Nest ranks Waterloo student housing by what actually matters, then
hands the landlord's form to an agent that fills it in while you watch.**

- **Search real listings.** 245 current listings in the City of Waterloo, from
  Bamboo Housing (student rooms and sublets) and Rent Panda. Filter by room or
  whole unit, lease or 4- or 8-month sublet, budget, walk to the ION, and
  tolerance for geese.
- **Ranking that shows its work.** Every listing gets a score out of 100 from
  six factors: price, walking time to the nearest of all 19 ION stops,
  bedrooms, geese nearby (from 1,789 real Canada Goose sightings on
  iNaturalist), highway access, and GO proximity. "Why this score?" shows the
  exact points each factor contributed, and you can re-weight them. Results
  come as a list, a map, or both.
- **An agent that requests the showing.** Pick a listing and an AI agent opens
  a real cloud browser, logged in to Rent Panda, fills out the *Request a
  Showing* form with your times and questions, and stops. You watch it live in
  an embedded window, see exactly what's in the form, and press and hold to
  approve. Only then does it send, exactly once, and it checks that the request
  arrived.

It only ever contacts a test listing we posted ourselves. No real landlords
were messaged.

## How we built it

**Collecting listings.** Before writing a single parser, we surveyed about 15
Waterloo housing sites. The two we used both turned out to embed their listings
as JSON inside the page: Bamboo Housing in Next.js's `__NEXT_DATA__`, and Rent
Panda in Inertia's `data-page` attribute. That meant plain HTTP with `httpx`
was faster and more reliable than any browser. Every request goes through one
polite fetch layer that respects robots.txt, waits between requests, retries
failures, caches to disk, and stops outright if a site serves a bot challenge.

**One shared data contract.** A single Pydantic schema, mirrored in TypeScript
and SQL, defines a listing and an inquiry for the whole team. A normalizer
turns each site's raw data into that shape and fixes the real-world messiness:
prices as strings, missing addresses, inconsistent city names, a malformed date,
map pins in the wrong city (which we re-geocode with OpenStreetMap), and the
difference between renting a room and renting a whole unit.

**Enrichment and ranking.** A FastAPI backend computes walking time to the 19
ION stops, distance to highways and GO, and a goose score from iNaturalist
sightings within 500 m. Ranking filters out listings that don't fit, then scores
the rest on six weighted factors and returns the per-factor breakdown the UI
displays. Data lives in Supabase Postgres, with row-level security so the
frontend can only read.

**The frontend.** React, TypeScript and Vite: a search form, list, map and
split views, score breakdowns, a shortlist, a contact queue, and the contact
flow with the live agent viewer and a press-and-hold approval button.

**The agent.** Gemini decides what to click and type, `browser-use` carries it
out, and Steel provides the cloud browser. You log in to Rent Panda once inside
Steel's live player, and Steel saves that session so every run starts signed in.
The agent never sees the password. Around the agent we built the parts we
wouldn't leave to a prompt:

- **Sending is blocked while it fills.** Using the Chrome DevTools Protocol, the
  browser itself fails every write request to Rent Panda, in every tab.
- **Read-back verification.** The values are read out of the live page and
  compared to the draft before the user is ever asked to approve.
- **Human approval**, enforced in the UI, in the agent's state machine, and by
  a database constraint that won't record a send without an approval.
- **Exactly one send.** After approval, the browser allows one showing request
  through and blocks anything after it.
- **An allowlist** in the repo naming the only listing the agent may contact.

The backend runs each request as a background task and streams progress to the
UI with Server-Sent Events.

**Built with:** Python, FastAPI, httpx, selectolax, Pydantic, Supabase
(Postgres), React, TypeScript, Vite, Steel, browser-use, Gemini, the Chrome
DevTools Protocol, the iNaturalist API, and OpenStreetMap Nominatim.

## Challenges we ran into

- **Our data plan fell apart in the first hour.** The site with the most
  Waterloo listings served a bot challenge, and we decided not to work around
  it. The open site we'd planned to use turned out to have 88 listings across
  all of Ontario, and one in Waterloo. We found our real inventory, 248
  listings, through the University of Waterloo's own list of housing sites.
- **Nobody lets you contact a landlord anonymously.** Every platform put contact
  behind a login. We changed the design so you log in once yourself, and the
  agent works inside that session.
- **Bugs that looked like something else.** A robots.txt checker that wrongly
  reported whole sites as off-limits. A Steel session timeout that's in
  milliseconds, not seconds, which failed only as an unexplained HTTP 404. An
  AI-framework retry loop that silently skipped Google's rate-limit and
  "model overloaded" errors, so one busy minute killed the whole run.
- **Our first safety guard had a hole.** Blocking network writes at the browser
  level covered new tabs, but not the tab that was already open, which is
  exactly where the form was. We only caught it because we tested the guard
  against a harmless page before trusting it.
- **The agent tried to send twice.** On our first real submit, it clicked
  "Send", then ran JavaScript to click it again. That's why the browser now
  allows exactly one send.
- **Small data, big consequences.** One postal code in our original plan
  belonged to Kitchener, not Waterloo. Our own test listing had its map pin in
  downtown Toronto, which showed up as an "1110 min walk" to the ION.
- **Free-tier AI limits.** Gemini's free tier allows a handful of requests a
  minute, and a single form fill uses most of them.

## Accomplishments that we're proud of

- An agent that does a real task on a real website, with safety that doesn't
  depend on the model behaving: blocked writes, verified read-back, human
  approval, a one-send limit and an allowlist, each tested on its own.
- A live window into the agent inside the app, so users watch it work instead
  of staring at a spinner.
- Ranking that explains itself. Every score is the actual maths, broken down by
  factor.
- Turning a joke into data: the goose score comes from nearly 1,800 real
  iNaturalist sightings.
- Getting real, local data without scraping anything that asked us not to.
- Test scripts for the database, approval gate, network guard, API, and agent
  connection, none of which send anything.

## What we learned

- **Not everything needs an agent.** Reading a page is a job for plain HTTP.
  Browsers and AI are worth their cost when the task is acting on a site with no
  API.
- **Put the guard rails in the browser, not the prompt.** A prompt that says
  "don't click send" is a suggestion. A network rule that blocks the request is
  a guarantee.
- **Test the safety code like it's the product.** Both of our worst bugs were in
  code meant to prevent problems, and both only showed up because we tried to
  break it first.
- **Verify before you build.** Several assumptions in our original plan, about
  data sources, postal codes and API units, were wrong, and checking early saved
  hours.
- **Respect the web you're building on.** robots.txt, rate limits, bot
  challenges and API usage policies shaped what we built, and we're better for
  following them.

## What's next for Goose Nest

- **Lease analysis.** Upload your lease and get the key dates, the deadlines,
  and any unusual clauses, in plain English. We planned this and ran out of time.
- **More sources, with permission.** Partnering with listing platforms and
  property managers instead of being limited to what's publicly readable.
- **Real walking times** using walking routes instead of straight-line distance.
- **More ways to contact landlords**, including drafted emails for listings
  that publish one, always behind the same approval step.
- **Beyond Waterloo**, starting with Kitchener and Cambridge, which the search
  already has a toggle for.
