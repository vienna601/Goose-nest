"""
Agent service — runs the contact flow for the API. Owner: A.

The contract is the one B's frontend already calls (frontend/src/lib/api.ts,
frontend/README.md):

    POST /inquiries                start; returns the Inquiry (status drafted)
    GET  /inquiries/{id}           current state
    GET  /inquiries/{id}/events    SSE of {"type": "inquiry_update", "inquiry": ...}
    POST /inquiries/{id}/approve   {approved_by}; only from pending_approval
    POST /inquiries/{id}/cancel    only from drafted or pending_approval

Each inquiry is a background asyncio task running
agent.flows.contact_rent_panda.request_showing. The approval the flow waits on
is a Future that /approve and /cancel resolve — the terminal prompt in
scripts/contact.py, swapped for HTTP. Everything else (allowlist, write guard,
one-send limit, read-back verification, DB constraint) is the same code path.

State lives in this process. A server restart orphans in-flight runs: their
rows stay in the DB, but approve/cancel answer 409 because the browser session
that held the filled form is gone.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import AsyncIterator, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# `shared.schema`, not the bare `schema` pathsetup exposes: the agent code uses
# these classes, and two import paths would give two different Inquiry types.
from shared import db  # noqa: E402
from shared.schema import Inquiry, InquiryStatus, Listing, Source  # noqa: E402

log = logging.getLogger("goose.agent")

TERMINAL = {InquiryStatus.SUBMITTED, InquiryStatus.CANCELLED, InquiryStatus.FAILED}
MAX_SLOTS = 3


class ServiceError(Exception):
    status = 400


class NotFound(ServiceError):
    status = 404


class Forbidden(ServiceError):
    status = 403


class Conflict(ServiceError):
    status = 409


class Invalid(ServiceError):
    status = 422


@dataclass
class _Run:
    inquiry: Inquiry
    decision: asyncio.Future
    task: Optional[asyncio.Task] = None
    listeners: set[asyncio.Queue] = field(default_factory=set)


_runs: dict[str, _Run] = {}


# --------------------------------------------------------------------------- helpers

def _publish(inquiry: Inquiry) -> None:
    run = _runs.get(inquiry.id)
    if run is None:
        return
    run.inquiry = inquiry
    for queue in list(run.listeners):
        queue.put_nowait(inquiry)


def _persist(inquiry: Inquiry) -> None:
    fields = inquiry.model_dump(mode="json")
    fields.pop("id")
    db.update_inquiry(inquiry.id, **fields)
    _publish(inquiry)


def _parse_times(raw: list[str]):
    from agent.flows.contact_rent_panda import Slot

    if len(raw) > MAX_SLOTS:
        raise Invalid(f"Rent Panda accepts at most {MAX_SLOTS} proposed times")
    slots = []
    for text in raw:
        try:
            dt = datetime.strptime(text.strip(), "%m/%d/%Y %H:%M")
        except ValueError:
            raise Invalid(f'preferred time {text!r} must look like "MM/DD/YYYY HH:MM"') from None
        if dt <= datetime.now():
            raise Invalid(f"preferred time {text} is in the past")
        slots.append(Slot(dt.date().isoformat(), dt.strftime("%H:%M")))
    if not slots:   # same default as scripts/contact.py
        today = date.today()
        slots = [Slot((today + timedelta(days=d)).isoformat(), "18:00") for d in (2, 3)]
    return slots


async def _wait_until_not(run: _Run, status: InquiryStatus, timeout_s: float) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_s
    while run.inquiry.status == status and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.1)


def _run_or_404(inquiry_id: str) -> _Run:
    run = _runs.get(inquiry_id)
    if run is not None:
        return run
    stored = db.get_inquiry(inquiry_id)
    if stored is None:
        raise NotFound("inquiry not found")
    if stored.status in TERMINAL:
        raise Conflict(f"inquiry is already {stored.status.value}")
    raise Conflict("this inquiry's browser session is no longer running (server restarted) — start a new one")


# --------------------------------------------------------------------------- API

async def start(
    listing_id: str,
    sender_name: str,
    sender_email: str,
    sender_phone: Optional[str],
    questions: list[str],
    preferred_times: list[str],
) -> Inquiry:
    from agent import approve as gate
    from agent.allowlist import NotAllowed, check_allowed
    from agent.draft import CannotContact, draft_inquiry, showing_note

    busy = [r for r in _runs.values() if r.inquiry.status not in TERMINAL]
    if busy:
        raise Conflict("the agent is already working on another request — approve or cancel it first")

    listing = db.get_listing(listing_id)
    if listing is None:
        raise NotFound("listing not found")
    try:
        check_allowed(listing)
    except NotAllowed as exc:
        raise Forbidden(str(exc)) from None
    if listing.source != Source.RENT_PANDA:
        raise Invalid("only Rent Panda showing requests are automated")

    questions = [q.strip() for q in questions if q and q.strip()]
    slots = _parse_times(preferred_times)
    # The backend composes the note (frontend/src/lib/draft.ts says as much):
    # the flow verifies the textarea against exactly this string.
    note = showing_note(listing, questions)
    try:
        inquiry = draft_inquiry(
            listing,
            sender_name=sender_name.strip() or "Rent Panda tenant account",
            sender_email=sender_email.strip() or "via-platform@rentpanda.invalid",
            sender_phone=(sender_phone or "").strip() or None,
        )
    except CannotContact as exc:
        raise Invalid(str(exc)) from None
    inquiry = Inquiry.model_validate(db.insert_inquiry(inquiry.model_copy(update={"message": note})))

    run = _Run(inquiry=inquiry, decision=asyncio.get_running_loop().create_future())
    _runs[inquiry.id] = run
    run.task = asyncio.create_task(_drive(run, listing, slots, note, gate))
    return inquiry


async def _drive(run: _Run, listing: Listing, slots, note: str, gate) -> None:
    from agent.flows.contact_rent_panda import request_showing
    from agent.steel_common import redact

    async def ask_approval(_inquiry: Inquiry) -> tuple[bool, str]:
        return await run.decision

    try:
        final = await request_showing(
            listing, run.inquiry, slots, note,
            persist=_persist, ask_approval=ask_approval,
            log=lambda msg: log.info(msg.strip()),
        )
        _publish(final)
    except asyncio.CancelledError:
        # /cancel while the agent was still filling. steel_browser's finally has
        # already released the session; nothing was sent (writes were blocked).
        if run.inquiry.status in (InquiryStatus.DRAFTED, InquiryStatus.PENDING_APPROVAL):
            _persist(gate.reject(run.inquiry, "browser session closed, nothing sent"))
    except Exception as exc:  # the flow's own failures return; this is the unexpected
        log.exception("contact flow crashed")
        if run.inquiry.status not in TERMINAL:
            _persist(gate.fail(run.inquiry, redact(f"{type(exc).__name__}: {exc}")[:500]))


def get(inquiry_id: str) -> Inquiry:
    run = _runs.get(inquiry_id)
    if run is not None:
        return run.inquiry
    stored = db.get_inquiry(inquiry_id)
    if stored is None:
        raise NotFound("inquiry not found")
    return stored


async def approve(inquiry_id: str, approved_by: str) -> Inquiry:
    run = _run_or_404(inquiry_id)
    if not approved_by or not approved_by.strip():
        raise Invalid("approval needs a human name")
    if run.inquiry.status != InquiryStatus.PENDING_APPROVAL:
        raise Conflict(f"expected pending_approval, got {run.inquiry.status.value}")
    if not run.decision.done():
        run.decision.set_result((True, approved_by.strip()))
    await _wait_until_not(run, InquiryStatus.PENDING_APPROVAL, 5)
    return run.inquiry


async def cancel(inquiry_id: str) -> Inquiry:
    run = _run_or_404(inquiry_id)
    status = run.inquiry.status
    if status == InquiryStatus.PENDING_APPROVAL:
        if not run.decision.done():
            run.decision.set_result((False, ""))
        await _wait_until_not(run, InquiryStatus.PENDING_APPROVAL, 10)
    elif status == InquiryStatus.DRAFTED:
        if run.task and not run.task.done():
            run.task.cancel()
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError, Exception):
                await asyncio.wait_for(asyncio.shield(run.task), 20)
    else:
        raise Conflict(f"cannot cancel from {status.value}")
    return run.inquiry


def _frame(inquiry: Inquiry) -> str:
    return "data: " + json.dumps({"type": "inquiry_update", "inquiry": inquiry.model_dump(mode="json")}) + "\n\n"


async def events(inquiry_id: str) -> AsyncIterator[str]:
    """SSE frames. Stays open after a terminal status (keepalives only) — closing
    would trip EventSource.onerror, and the frontend then polls every second."""
    run = _runs.get(inquiry_id)
    if run is None:
        yield _frame(get(inquiry_id))
        while True:
            await asyncio.sleep(15)
            yield ": keepalive\n\n"
    queue: asyncio.Queue = asyncio.Queue()
    run.listeners.add(queue)
    try:
        yield _frame(run.inquiry)
        while True:
            try:
                inquiry = await asyncio.wait_for(queue.get(), 15)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            yield _frame(inquiry)
    finally:
        run.listeners.discard(queue)
