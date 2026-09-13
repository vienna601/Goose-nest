# YouTube — title and description

## Title options

- Goose Nest: an AI agent that requests apartment showings (while you watch)
- Goose Nest — Waterloo student housing, ranked, with a human-approved browser agent
- We built an AI agent that fills landlord forms… and physically can't hit Send without you

## Description (paste below the line)

---

Goose Nest ranks real Waterloo student housing by what students actually care
about — then hands the landlord's form to an AI agent that fills it in live,
stops, and waits for you to approve before anything is sent.

🔍 SEARCH
245 current listings in the City of Waterloo from Bamboo Housing and Rent Panda,
filtered by room vs. whole unit, lease vs. 4- or 8-month sublet, budget, walk to
the ION, and tolerance for geese.

📊 RANKING YOU CAN READ
Every listing is scored on six factors, with the breakdown shown:
• Walking time to all 19 ION LRT stops
• Geese nearby — from 1,789 real Canada Goose sightings on iNaturalist
• Price, bedrooms, highway access, and GO train proximity
Re-weight any of them.

🤖 THE AGENT
A real cloud browser on Steel, driven by Gemini through browser-use, opens the
listing, fills out Rent Panda's "Request a Showing" form, and stops. You watch it
live inside the app, review what's actually in the form, and hold to approve.

🛡️ SAFETY, ENFORCED IN CODE
• Sending is blocked inside the browser while the agent fills the form
• The form is read back from the page and verified before you're asked
• Human press-and-hold approval, also enforced by a database constraint
• Exactly one send after approval — any second attempt is blocked
• An allowlist means it only ever contacts a listing we posted ourselves
• No CAPTCHA solving, stealth, or proxy tricks — sites that block bots are left out

Disclosure: every inquiry in this video goes to a test listing we created on
Rent Panda. No real landlords were contacted.

⏱️ CHAPTERS
(Update the times after you cut the video — YouTube needs the first one at 0:00.)
0:00 The problem
0:30 Searching 245 Waterloo listings
1:00 Why this score? — ION, geese, and ranking
1:30 Handing it to the agent
1:50 Watching the agent work on Steel
2:50 Review: what's actually in the form
3:20 Hold to approve
3:40 Sent — and confirmed
4:15 Limits and what's next

🧰 BUILT WITH
Steel · browser-use · Gemini · FastAPI · Supabase · React · Vite · Python ·
iNaturalist · OpenStreetMap

💻 CODE
https://github.com/vienna601/Goose-nest

Built for Battle of the Schools by Geese gang.

#hackathon #AIagents #browserautomation #Waterloo #studenthousing #Steel
