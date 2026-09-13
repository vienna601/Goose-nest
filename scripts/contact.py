#!/usr/bin/env python
"""Request a showing on our own Rent Panda test listing.

    .venv/bin/python scripts/contact.py                   # FILL ONLY: nothing is sent
    .venv/bin/python scripts/contact.py --submit          # fill, then ask you to approve
    .venv/bin/python scripts/contact.py --slot 2026-09-18T18:00 --slot 2026-09-19T12:30 \\
        --question "Is parking included"

Fill-only is the default so a test run can never send by accident. Even with
--submit, nothing is sent until you type APPROVE in this terminal.
Watch it live at the printed view-only link.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.allowlist import OWN_TEST_LISTINGS, NotAllowed  # noqa: E402
from agent.draft import draft_inquiry, showing_note  # noqa: E402
from agent.flows.contact_rent_panda import Slot, request_showing  # noqa: E402
from shared.db import fetch_listings, insert_inquiry, update_inquiry  # noqa: E402
from shared.schema import Inquiry, Source  # noqa: E402


def default_slots() -> list[Slot]:
    """Two evenings, 2 and 3 days out — always in the future."""
    today = date.today()
    return [Slot((today + timedelta(days=d)).isoformat(), "18:00") for d in (2, 3)]


def parse_slot(text: str) -> Slot:
    dt = datetime.fromisoformat(text)
    if dt <= datetime.now():
        raise argparse.ArgumentTypeError(f"{text} is in the past")
    return Slot(dt.date().isoformat(), dt.strftime("%H:%M"))


def persist(inq: Inquiry) -> None:
    fields = inq.model_dump(mode="json")
    fields.pop("id")
    update_inquiry(inq.id, **fields)


async def terminal_approval(inq: Inquiry) -> tuple[bool, str]:
    print("\n" + "=" * 72)
    print("  REVIEW — this is what is in the Rent Panda form right now:\n")
    for key, value in inq.filled_fields.items():
        print(f"    {key:<18} {value}")
    print(f"\n  Watch (view-only): {inq.viewer_url}")
    print("\n  Type APPROVE to send this showing request. Anything else cancels.")
    print("=" * 72)
    answer = await asyncio.to_thread(input, "> ")
    return answer.strip() == "APPROVE", getpass.getuser()


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-id", default="20684", help="Rent Panda property_detail_id (must be allowlisted)")
    ap.add_argument("--slot", action="append", type=parse_slot, help="ISO datetime, up to 3")
    ap.add_argument("--question", action="append", help="added to the note")
    ap.add_argument("--submit", action="store_true", help="after filling, ask for approval and send")
    args = ap.parse_args()

    if ("rent_panda", args.source_id) not in OWN_TEST_LISTINGS:
        print(f"REFUSED  rent_panda:{args.source_id} is not in agent/allowlist.py")
        return 1
    listing = next((l for l in fetch_listings(Source.RENT_PANDA) if l.source_id == args.source_id), None)
    if listing is None:
        print(f"FAIL  rent_panda:{args.source_id} isn't in the database — run scripts/load_listings.py")
        return 1

    slots = (args.slot or default_slots())[:3]
    note = showing_note(listing, args.question)
    inquiry = draft_inquiry(listing, sender_name="Rent Panda tenant account",
                            sender_email="via-platform@rentpanda.invalid")
    inquiry = inquiry.model_copy(update={"message": note})
    inquiry = Inquiry.model_validate(insert_inquiry(inquiry))

    print(f"listing : {listing.address_raw} (${listing.price_min})")
    print(f"times   : {', '.join(f'{s.date} {s.time}' for s in slots)}")
    print(f"note    : {note}")
    print(f"mode    : {'fill, then approval' if args.submit else 'FILL ONLY — nothing will be sent'}")
    print(f"inquiry : {inquiry.id}\n")

    try:
        result = await request_showing(listing, inquiry, slots, note, persist=persist,
                                       ask_approval=terminal_approval if args.submit else None)
    except NotAllowed as exc:
        print(f"REFUSED  {exc}")
        return 1

    print(f"\nfinal status: {result.status.value}" + (f" — {result.failure_reason}" if result.failure_reason else ""))
    return 0 if result.status.value in ("submitted", "cancelled") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
