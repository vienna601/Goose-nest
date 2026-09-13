"""
Compose the inquiry message. No network, no browser, no API key.

This runs first in every flow — browser, email, or mailto fallback — so the
human sees exactly what will be sent before anything opens a session.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from shared.schema import (
    ContactMethod,
    Inquiry,
    InquiryStatus,
    LeaseType,
    Listing,
    ListingKind,
)


class CannotContact(Exception):
    """No contact path we're willing to use. Surface the listing URL instead."""


def listing_label(listing: Listing) -> str:
    """How a human would refer to this listing in a sentence."""
    where = listing.address_raw or listing.city
    where = re.sub(r",?\s+CA$", "", where.strip())      # Bamboo suffixes ", ... CA"

    if listing.listing_kind == ListingKind.ROOM:
        if listing.total_bedrooms:
            return f"the room in the {listing.total_bedrooms}-bedroom place at {where}"
        return f"the room at {where}"

    beds = f"{listing.beds:g}-bedroom " if listing.beds else ""
    return f"the {beds}unit at {where}"


def availability_line(listing: Listing) -> str:
    """One sentence about terms. Built by hand rather than with .capitalize(),
    which lowercases everything after the first character and turned
    "August 1" into "august 1"."""
    parts = []
    if listing.lease_type == LeaseType.SUBLET and listing.term_months:
        parts.append(f"I'm looking for a {listing.term_months}-month sublet")
    elif listing.lease_type == LeaseType.LEASE:
        parts.append("I'm looking for a standard lease")

    if listing.available_date:
        d = listing.available_date
        when = f"{d:%B} {d.day}"          # %-d isn't portable; do it by hand
        parts.append(
            f"and the {when} start date works for me" if parts
            else f"the {when} start date works for me"
        )

    if not parts:
        return "I'd like to know more about the terms and start date."
    text = ", ".join(parts)
    return text[0].upper() + text[1:] + "."


def compose(
    listing: Listing,
    sender_name: str,
    sender_email: str,
    sender_phone: Optional[str] = None,
    questions: Optional[list[str]] = None,
) -> str:
    lines = [f"Hi{' ' + listing.contact_name if listing.contact_name else ''},", ""]
    price = f" listed at ${listing.price_min}/month" if listing.price_min else ""
    lines += [f"I'm interested in {listing_label(listing)}{price}.", ""]
    lines += [availability_line(listing), ""]
    if questions:
        lines.append("A couple of questions:")
        lines += [f"- {q}" for q in questions]
        lines.append("")
    lines += ["Is it still available? I'm happy to arrange a viewing.", ""]
    lines += ["Thanks,", sender_name, sender_email]
    if sender_phone:
        lines.append(sender_phone)
    return "\n".join(lines)


def showing_note(listing: Listing, questions: Optional[list[str]] = None) -> str:
    """The NOTES field on a platform showing request. The platform already
    knows who we are, so no signature or contact details — just intent."""
    parts = [f"Hi! I'm interested in {listing_label(listing)} and would love to see it."]
    terms = availability_line(listing)
    if not terms.startswith("I'd like to know"):
        parts.append(terms)
    if questions:
        parts.append(" ".join(q if q.endswith("?") else q + "?" for q in questions))
    parts.append("Thanks!")
    return " ".join(parts)


def route(listing: Listing) -> ContactMethod:
    """Which flow handles this listing. The agent branches here and nowhere else."""
    if listing.contact_method == ContactMethod.ACCOUNT_REQUIRED:
        raise CannotContact(
            f"{listing.source.value} requires a platform account to contact a "
            f"listing. We don't create accounts — surface {listing.url} to the user."
        )
    if listing.contact_method == ContactMethod.UNKNOWN:
        raise CannotContact(f"no contact path parsed for {listing.url}")
    return listing.contact_method


def draft_inquiry(
    listing: Listing,
    sender_name: str,
    sender_email: str,
    sender_phone: Optional[str] = None,
    questions: Optional[list[str]] = None,
) -> Inquiry:
    """Build a DRAFTED inquiry. Nothing is sent, nothing is opened."""
    method = route(listing)
    return Inquiry(
        id=str(uuid.uuid4()),
        listing_id=listing.id,
        status=InquiryStatus.DRAFTED,
        method=method,
        message=compose(listing, sender_name, sender_email, sender_phone, questions),
        sender_name=sender_name,
        sender_email=sender_email,
        sender_phone=sender_phone,
        created_at=datetime.now(timezone.utc),
    )
