# Goose Nest — 5-minute pitch

About 570 spoken words (≈4–4½ min of talking) plus clicks and pauses. The agent takes
**~60 seconds** to fill the form (measured in rehearsal), so the script starts
it early and talks through the safety design while it works — no dead air.

**Roles:** one presenter talking, one driver on the laptop. If you're solo,
drive and talk; the cues are written for that too.

---

## Before you walk up (the checklist that saves the demo)

- [ ] Backend restarted on the current code: `curl -s localhost:8000/inquiries/nope`
      says `inquiry not found` (not `Not Found`)
- [ ] Old showing requests cleared on Rent Panda (there are two from testing)
- [ ] `scripts/steel_login.py --verify` → logged in (role: tenant)
- [ ] Gemini billing on; `scripts/check_steel.py` passes
- [ ] Browser zoomed so the live viewer and approval panel are both readable
- [ ] Search already set: **Whole unit · Either · $1,500 · 10 min · geese ≤ 2**
- [ ] Your name and email already saved in the contact form (it remembers them)
- [ ] Backup video open in another tab

---

## 0:00 – 0:30 · The problem

> Waterloo students all have the same apartment hunt.
>
> You're comparing rooms against a bus route you can't picture. You're guessing
> which street is a goose highway. And then you fill out the same landlord form
> twenty times and wait.
>
> We built Goose Nest to do the comparing for you — and then hand the form to an
> agent that fills it in while you watch.

**Screen:** home page, hero visible.

---

## 0:30 – 1:30 · Search that knows Waterloo

> These are 245 real listings in the City of Waterloo — student rooms and
> sublets from Bamboo Housing, plus Rent Panda.
>
> You tell us what you're renting, your term, your budget, how far you'll walk
> to the ION, and your tolerance for geese.

**Driver:** hit **Find my nest**. Open **Why this score?** on a result.

> Every result is scored on six things, and we show our work. Walking time is
> measured to all nineteen ION stops — for a student here, that matters far more
> than the GO train. And the geese score isn't a joke we made up: it's built from
> almost eighteen hundred real Canada Goose sightings on iNaturalist within
> 500 metres of the door.
>
> Don't like the ranking? Re-weight it.

**Driver:** open **Tune ranking** for a second, close it. Click **Contact** on
**550 King St N**, then **Contact 1 landlord**.

---

## 1:30 – 1:50 · Hand it to the agent

> This one's on Rent Panda. To ask for a showing you have to log in, pick times,
> and write a note. So we let the agent do it.

**Driver:** show the preferred times and questions, then **Have the agent fill
the form**.

> Full disclosure: this is a listing we posted ourselves. The agent never
> contacts real landlords — and that's enforced in code, not just a promise.

---

## 1:50 – 2:50 · While it works (talk over the live view)

**Screen:** the embedded Steel window — a real browser, live.

> That's a real Chrome browser running in the cloud on Steel, logged into a
> tenant account. The AI is Gemini, driving it through browser-use. It's
> opening the listing, finding the showing form, and typing.
>
> Here's the part we care about. An agent that can press "send" for you needs
> more than a prompt telling it not to.
>
> So while it fills, sending is **physically blocked** — the browser itself
> refuses every outgoing write to Rent Panda. Even if the model clicks "Send",
> nothing leaves.
>
> We learned why that matters the fun way. In testing, the agent clicked Send…
> and then ran JavaScript to click it again. So now the browser allows exactly
> one send, after approval, and blocks anything after that.
>
> One more design choice: we collect listings with plain HTTP requests, not
> the agent. Reading a page doesn't need a browser. Acting on a form with no
> API does — so that's the only place we spend one.

**If it's still typing:** "It's reading the page like a person would — which is
also why it doesn't need an integration for every site."

---

## 2:50 – 3:40 · Review and approve

**Screen:** the approval panel appears beside the live form.

> It's done — and it's stopped. Nothing has been sent.
>
> What you're looking at isn't what we *told* it to type. It's what's actually
> in the form, read back off the live page. If those didn't match, the run
> would fail before it ever asked me.
>
> And approval is a press-and-hold, with my name on the audit trail. The
> database itself won't record a send without an approval on it.

**Driver:** read one value out loud, then **hold to approve & send**.

---

## 3:40 – 4:15 · Sent, and proven

**Screen:** step timeline ticks through submit; outcome shows **Sent**.

> It clicks Send once — and then we don't trust it. We go check the tenant's
> showings page and confirm the request actually landed.
>
> That's the whole loop: search, compare, draft, fill, approve, confirmed —
> and a human decided the only thing that mattered.

---

## 4:15 – 5:00 · What's next, and close

> Two honest limits. Most platforms hide landlord contact behind accounts, and
> some block automated traffic entirely — we don't work around that. So today
> the agent contacts one listing we own, and the others link out.
>
> Next: lease analysis — upload the lease, get the deadlines and the weird
> clauses — and more sources, done with permission.
>
> Goose Nest. Find the nest, skip the geese, and let the agent handle the
> paperwork — with you holding the button.

---

## If something breaks live

| What happens | Say | Do |
|---|---|---|
| Agent is slow (Gemini busy) | "Google's model is under load — it retries and falls back to a second model on its own." | Keep talking the 1:50 section; it has slack. |
| Run shows **failed** | "And that's the safety working — it couldn't verify the form, so it refused to ask me to send." | Switch to the backup video at the review step. |
| Viewer footer says **SIMULATED** | — | The backend is stale or down. Restart it, or go to the video. |
| Rent Panda rejects a duplicate request | "Rent Panda blocks repeat requests — here's the run from this morning." | Video. Clear old requests before the next rehearsal. |

---

## Likely judge questions

**Isn't this just a scraper with a chatbot?**
Reading listings is plain HTTP on purpose — that part should be boring. The
agent does the thing HTTP can't: operate a form that has no API, on a site it
wasn't integrated with, safely.

**How do you stop it sending something wrong?**
Four layers, all tested: writes blocked in the browser during fill; the form
read back and verified before review; a human hold-to-approve, also enforced by
a database constraint; and a one-send limit after approval.

**Why not scrape Rentals.ca? It has way more listings.**
It serves a bot challenge. We could have tried to defeat it with stealth tools;
we chose not to. Access should be by permission.

**Does it message real landlords?**
No. An allowlist in the repo names the only listing it can contact — ours.
Everything else is refused before a browser opens.

**What does Steel give you over running Chrome yourself?**
Hosted sessions we can open and tear down per request, saved login profiles,
and a live player we embed so the user watches the agent instead of a spinner.

**Why Gemini?**
Our choice for the demo; the flow isn't tied to it. We wrap it with retries and
a fallback model because free-tier limits and 503s were our biggest source of
flakiness.

**What would you build next?**
Lease analysis with deadline export, and more sources through proper access.
