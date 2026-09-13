# Why Steel, and where it actually earns its place

## The honest split

Reading a listings page is a solved problem. `httpx` and a parser do it faster
and cheaper than any browser, and a technical judge knows that. So we don't use
a browser to read.

We use it to **act**.

    inbound  (collect listings)     plain HTTP        no browser
    outbound (contact a landlord)   Steel + browser-use

That second row is the part that cannot be an API call, because the people on
the other end of it are landlords, and landlords do not have APIs. Every
listing site has its own inquiry form: different fields, different validation,
some hidden behind a "show contact" click, some multi-step. There is no
endpoint to POST to. There is only a page, and something has to drive it.

## How that maps to Steel

Steel is a browser API built for AI agents — hosted browser sessions, lifecycle
management, and a live session viewer, so you write agent logic instead of
running browser infrastructure. The premise is that the web was built for
humans to click through, and agents increasingly need to do the same thing.

Our contact-form step is that premise in miniature:

- **It's an action, not a read.** State, validation, submission. The failure
  modes are interaction failures — exactly what a real browser session is for.
- **It generalizes badly on purpose.** N sites, N forms. Hand-writing an
  integration per landlord is precisely the work the agent exists to avoid.
- **It's observable.** The live session viewer turns "the agent did something"
  into ninety seconds of watching it happen. Most agent demos are a spinner and
  a claim. This one you can see.
- **It has a human in the loop.** The agent fills the form and stops. A person
  approves. Then it submits. That gate is enforced in the database, not just
  the UI: `submitted_at` cannot be set without `approved_at`.

## Pitch (~30 seconds, spoken)

> Finding an apartment isn't hard because listings are hard to find. It's hard
> because of everything after: messaging twelve landlords through twelve
> different forms, then reading a lease you don't understand, then missing a
> deadline nobody told you about.
>
> So we collect listings the boring way, with an HTTP client, because that part
> should be boring. Where we use a real browser — on Steel — is the part that
> actually needs one. The agent opens the listing, fills out that landlord's
> inquiry form, and stops. You see the filled form, you approve it, and only
> then does it send. You'll watch it happen live in about a minute.
>
> And it never sends a thing until you've held the button.

## One-liner

> An agent that does the annoying half of apartment hunting — filling out the
> landlord's form — with a human approving every request before it sends.

## Notes for the demo

- Contact **our own test listing**. Say that out loud on stage.
- Lease analysis was planned and not built — don't promise it. The full
  5-minute script is in docs/pitch_5min.md.
- Keep the approval gate visible. It is a feature, not a disclaimer.
- If the live form flow breaks, the fallback is a drafted message plus a
  one-click mailto. Rehearse saying that without apologizing for it.
