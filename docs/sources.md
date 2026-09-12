# Source survey — what we probed and what we found

Run at H1. Every number here came from an actual request, not a guess.
Redo this before adding any source; two of the plan's assumptions were wrong.

## Verdicts

| Source | Status | Waterloo inventory |
|---|---|---|
| rentals.ca | Cloudflare challenge (403, `cf-mitigated: challenge`) on every path incl. the sitemap its own robots.txt advertises | 1,162 claimed, unverifiable |
| realtors.ca | not probed — sales portal, CREA-licensed MLS data | thin rentals at best |
| Rent Panda | **open**, permissive robots, clean JSON payload | **1 listing** |
| Homestead | open, sitemap published | **1 building** (Metropolitan Towers), ~5 suite types |
| Killam REIT | Cloudflare challenge | — |
| places4students | persistent 429 from Vercel | — |
| WCRI | open, but availability is behind a members-only rentmanager portal | no public listings |
| UW off-campus housing | open, but it's an **advice site**, not a listings database | 0 — its value is the referral list below |
| **Bamboo Housing** | **open**, permissive robots, Next.js `__NEXT_DATA__` JSON, 9 pages × 30 | **248 listings, all Waterloo** |
| rez-one | open (robots allows) | 1 building (Elora House) |
| 4stay | open (robots allows; `/v2/listings` disallowed — stay off it) | not parsed |
| myidealhome / och101 | open but JS-rendered, no data in HTML | unknown |
| icon | open, 18KB marketing page | ~1 building |
| accommod8u | TLS handshake failure (ancient TLS) | — |
| kwpmc.com | wrong company — KW Property Management is **Florida** | — |

## Where the inventory actually is

UW's own "looking for a place" page is the map to this: it's a curated referral
list of where Waterloo students really search. **Bamboo Housing** was on it and
carries 248 Waterloo listings behind a clean Next.js JSON payload — more than
the original plan's Gate 1 target, from one open source.

Two caveats that shape the schema:

- They are **rooms in shared houses**, not whole units. A $695 room in a
  5-bedroom house is not comparable to a $2400 apartment. Hence `listing_kind`.
- **136 of 248 are 4- or 8-month sublets.** For a student search that's a
  primary filter, so `lease_type` and `term_months` are first-class columns.

## Two things that surprised us

**Rent Panda is not an Ontario rental portal.** 88 listings site-wide across
5 pages. 50 of them are Thunder Bay. There is one Waterloo listing. It is
still our contact-form target — the site is open, the form is real, and we
post our own listing there — but it is not an inventory source.

**A robots.txt check can lie to you.** `urllib.robotparser` fetches robots.txt
with Python's default user-agent, plenty of WAFs answer that with a 403, and
robotparser reads a 403 as "disallow the entire site". That silently marked
rez-one, 4stay and accommod8u as off-limits when all three allow crawling.
`collection/fetch.py` now fetches robots.txt with our own UA and follows
RFC 9309 status handling. If a source looks blocked, verify before believing it.

**Waterloo property managers mostly don't publish listings.** They hand off to
Rentsync, SecureCafe/Yardi, or RentManager, and those portals are login-gated.
The "just parse a few local landlords" plan yields single-digit buildings each,
not the hundreds we assumed.

## On bot challenges

We do not work around them. No stealth fingerprinting, no residential proxy
rotation, no CAPTCHA solving — not for rentals.ca, not for Killam. A site
serving a challenge is telling us it doesn't want automated collection, and
"we defeated their bot protection" is a bad sentence to say in front of judges.

`collection/fetch.py` raises `Blocked` on a challenge and stops. That is
deliberate; don't add a bypass path to it.

Steel still runs the contact-form agent. That is the browser work that
genuinely needs a browser — see docs/steel_pitch.md.

## If you want rentals.ca in the deck

Pull the pages by hand in a normal browser and commit the HTML to
`collection/fixtures/`. The parser work proceeds exactly as it would have, the
data is real, and nobody's bot protection gets circumvented. Say on stage that
the rentals.ca sample is a manual export.
