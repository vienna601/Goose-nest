"""
The approval gate. Nothing this project sends bypasses this file.

State machine:

    DRAFTED ──fill──> PENDING_APPROVAL ──approve──> APPROVED ──submit──> SUBMITTED
                              │                          │
                              └──reject──> CANCELLED     └──error──> FAILED

Two rules, both enforced here and again in Postgres:

  * submit() refuses anything that is not APPROVED.
  * approve() requires a human identifier. There is no auto-approve, no
    approve_all, and no flag to skip this. Don't add one at hour 20.

The database carries the same rule as a check constraint
(`submitted_requires_approval`), so a bug here still can't record a send that
nobody signed off on.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from shared.schema import Inquiry, InquiryStatus


class NotApproved(Exception):
    """Someone tried to send without a human in the loop."""


class BadTransition(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ready_for_review(
    inquiry: Inquiry,
    filled_fields: dict[str, str],
    viewer_url: Optional[str] = None,
    steel_session_id: Optional[str] = None,
) -> Inquiry:
    """Agent has filled the form and stopped. Hand it to the human.

    `filled_fields` is what the UI shows in the approval dialog — the actual
    values sitting in the form, not our intent. If the agent typed something
    into a field we didn't expect, the human sees it here.
    """
    if inquiry.status != InquiryStatus.DRAFTED:
        raise BadTransition(f"expected DRAFTED, got {inquiry.status.value}")
    return inquiry.model_copy(update={
        "status": InquiryStatus.PENDING_APPROVAL,
        "filled_fields": filled_fields,
        "viewer_url": viewer_url,
        "steel_session_id": steel_session_id,
        "steps": inquiry.steps + ["form filled, waiting for human approval"],
    })


def approve(inquiry: Inquiry, approved_by: str) -> Inquiry:
    if inquiry.status != InquiryStatus.PENDING_APPROVAL:
        raise BadTransition(f"expected PENDING_APPROVAL, got {inquiry.status.value}")
    if not approved_by or not approved_by.strip():
        raise NotApproved("approve() needs a human identifier, not a blank string")
    return inquiry.model_copy(update={
        "status": InquiryStatus.APPROVED,
        "approved_at": _now(),
        "approved_by": approved_by.strip(),
        "steps": inquiry.steps + [f"approved by {approved_by.strip()}"],
    })


def reject(inquiry: Inquiry, reason: str = "", by_human: bool = True) -> Inquiry:
    if inquiry.status not in (InquiryStatus.PENDING_APPROVAL, InquiryStatus.DRAFTED):
        raise BadTransition(f"cannot reject from {inquiry.status.value}")
    return inquiry.model_copy(update={
        "status": InquiryStatus.CANCELLED,
        "steps": inquiry.steps + [f"cancelled{' by human' if by_human else ''}{': ' + reason if reason else ''}"],
    })


def submit(inquiry: Inquiry) -> Inquiry:
    """Call this immediately before the actual send. It is the last gate."""
    if inquiry.status != InquiryStatus.APPROVED:
        raise NotApproved(
            f"refusing to send an inquiry in state {inquiry.status.value}. "
            "Only APPROVED may be submitted."
        )
    if inquiry.approved_at is None or not inquiry.approved_by:
        raise NotApproved("APPROVED but no approver recorded — refusing to send")
    return inquiry.model_copy(update={
        "status": InquiryStatus.SUBMITTED,
        "submitted_at": _now(),
        "steps": inquiry.steps + ["submitted"],
    })


def fail(inquiry: Inquiry, reason: str) -> Inquiry:
    return inquiry.model_copy(update={
        "status": InquiryStatus.FAILED,
        "failure_reason": reason[:500],
        "steps": inquiry.steps + [f"failed: {reason[:120]}"],
    })
