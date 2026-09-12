# Agent (owner: A)

`browser-use` on Steel. Scoped to ONE job: submitting landlord contact forms.
It does not collect listings. No stealth config, no residential proxy —
neither site needs it.

    flows/contact_rentals_ca.py   inquiry form on a rentals.ca detail page
    flows/contact_rent_panda.py   inquiry form on a rentpanda listing
    prompts/inquiry.md            message template the agent fills and sends
    session.py                    Steel session lifecycle + live viewer URL
    approve.py                    human approval gate — nothing sends without it

Branching is on Listing.contact_method:
    form  -> browser agent
    email -> Resend (fallback, no browser)
    phone -> draft only, surface to user

Safety: only ever contact our own test listing during the demo.
Human approval in the UI, and say so on stage.

Fallback if forms aren't working by H9: draft the message, one-click mailto,
user sends it. Still a good demo, much smaller lift.
