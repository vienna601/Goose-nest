"""
The only listings the agent is ever allowed to contact.

This is a file in the repo on purpose: anyone reviewing the code — or a judge
asking "does this message real landlords?" — can read the whole answer here.
Adding a listing is a code change, not a flag.

Rent Panda has at least one real Waterloo landlord listing with the same
contact_method as ours. Without this list the agent would happily message them.
"""

from __future__ import annotations

from shared.schema import Listing

OWN_TEST_LISTINGS: frozenset[tuple[str, str]] = frozenset({
    ("rent_panda", "20684"),   # 550 King St N, Waterloo — our own test listing
})


class NotAllowed(Exception):
    pass


def check_allowed(listing: Listing) -> None:
    key = (listing.source.value, listing.source_id)
    if key not in OWN_TEST_LISTINGS:
        raise NotAllowed(
            f"{key} is not one of our own test listings. The agent only contacts "
            f"listings in agent/allowlist.py — it never messages real landlords."
        )
