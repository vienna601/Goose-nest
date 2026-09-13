"""
Request a showing on a Rent Panda listing: fill, stop, human approves, submit.

One Steel session, logged in via the saved tenant profile, two agent runs:

  fill    Gemini + browser-use open the listing, open "Request a Showing",
          enter the proposed times and the note. Runs INSIDE cdp.write_guard:
          every POST/PUT/PATCH/DELETE to app.rentpanda.ca fails in the browser,
          so even if the model clicks "Send request", nothing is sent.
  review  We read back what is ACTUALLY in the form (not what the model says it
          typed) and hand that to the human. Session kept alive meanwhile.
  submit  Only after approve.approve() + approve.submit() pass. Guard lifted,
          agent clicks "Send request" once, and we confirm on the tenant's
          own showings page that the request exists.

Refuses, before opening a browser: listings not in agent/allowlist.py, and
anything draft.route() won't contact.

Every state change is written to the inquiries table, so C's backend can
stream it and B's UI can render it.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from browser_use import Agent

from agent import approve as gate
from agent.allowlist import check_allowed
from agent.cdp import CDP
from agent.draft import route
from agent.session import SESSION_CAP_MS, make_llm, redact, steel_browser
from shared.schema import ContactMethod, Inquiry, InquiryStatus, Listing

HOST = "app.rentpanda.ca"
SHOWINGS_URL = f"https://{HOST}/tenant/showings"
APPROVAL_BUDGET_S = 8 * 60        # inside the 15-min session cap, with room to submit


@dataclass
class Slot:
    date: str   # YYYY-MM-DD
    time: str   # HH:MM, 24h

    def us_date(self) -> str:
        y, m, d = self.date.split("-")
        return f"{m}/{d}/{y}"


# (approved?, approver). Terminal today; C's backend polls the DB later.
ApprovalFn = Callable[[Inquiry], Awaitable[tuple[bool, str]]]
PersistFn = Callable[[Inquiry], None]


READ_FORM_JS = r"""
(() => {
  const notes = document.querySelector('#showing-notes');
  if (!notes) return null;
  const out = {notes: notes.value};
  document.querySelectorAll('[id^="showing-date-"]').forEach(e => out['date_' + e.id.split('-').pop()] = e.value);
  document.querySelectorAll('[id^="showing-time-"]').forEach(e => out['time_' + e.id.split('-').pop()] = e.value);
  return out;
})()
"""

# Total showing requests on the tenant's own showings page (Inertia props,
# verified: component Tenant/Showings/Index, props.showings is a paginated list
# with `total`). A number and the page's filter name only — nothing about the account.
COUNT_JS = r"""
(() => {
  const el = document.querySelector('[data-page]');
  if (!el) return null;
  const props = JSON.parse(el.dataset.page).props;
  if (!props.showings) return null;
  return {total: props.showings.total, filter: props.filter};
})()
"""


def fill_task(listing: Listing, slots: list[Slot], note: str) -> str:
    lines = [
        f"Go to {listing.url}",
        'Click the "Request a Showing" button. A dialog opens.',
    ]
    for i, slot in enumerate(slots):
        if i > 0:
            lines.append('Click "+ Add another time" to add another row.')
        lines.append(
            f"In time row {i + 1}: set PREFERRED DATE to {slot.date} "
            f"(the field may expect {slot.us_date()}) and TIME to {slot.time}."
        )
    lines += [
        f"In NOTES, enter exactly this text:\n{note}",
        'STOP. Do NOT click "Send request". Do not click Cancel or close the dialog.',
        "Do not click anything else on the page: not Apply Now, not Log out, not favourites.",
        "When the fields are filled, finish and report the values now shown in each field.",
    ]
    return "\n".join(f"{n}. {line}" for n, line in enumerate(lines, 1))


SUBMIT_TASK = (
    'A "Request a Showing" dialog is already open and filled in. Do not change any field. '
    'Click the "Send request" button exactly once. Then report what the page shows.'
)


async def _form_values(cdp: CDP) -> tuple[Optional[str], Optional[dict]]:
    """Find whichever tab has the dialog and read it. The agent may have opened a new tab."""
    for target in (await cdp.send("Target.getTargets"))["targetInfos"]:
        if target["type"] != "page":
            continue
        s = (await cdp.send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True}))["sessionId"]
        values = await cdp.js(s, READ_FORM_JS)
        if values is not None:
            return s, values
    return None, None


async def _showing_count(cdp: CDP, page: str) -> Optional[dict]:
    await cdp.goto(page, SHOWINGS_URL, settle_s=4)
    return await cdp.js(page, COUNT_JS)


def _mismatches(values: dict, slots: list[Slot], note: str) -> list[str]:
    problems = []
    for i, slot in enumerate(slots):
        if values.get(f"date_{i}") != slot.date:
            problems.append(f"row {i + 1} date is {values.get(f'date_{i}')!r}, expected {slot.date!r}")
        if values.get(f"time_{i}") != slot.time:
            problems.append(f"row {i + 1} time is {values.get(f'time_{i}')!r}, expected {slot.time!r}")
    if (values.get("notes") or "").strip() != note.strip():
        problems.append("notes don't match the approved draft")
    return problems


async def request_showing(
    listing: Listing,
    inquiry: Inquiry,
    slots: list[Slot],
    note: str,
    *,
    persist: PersistFn,
    ask_approval: Optional[ApprovalFn],
    log: Callable[[str], None] = print,
) -> Inquiry:
    """Runs the whole flow. ask_approval=None means fill-only: stop at review and cancel."""
    if not 1 <= len(slots) <= 3:
        raise ValueError("Rent Panda accepts 1 to 3 proposed times")
    check_allowed(listing)
    if route(listing) != ContactMethod.FORM:
        raise ValueError(f"{listing.url} is not a form contact")

    def step(inq: Inquiry, text: str, **fields) -> Inquiry:
        inq = inq.model_copy(update={"steps": inq.steps + [text], **fields})
        persist(inq)
        log(f"  · {text}")
        return inq

    started = time.monotonic()
    async with steel_browser(allowed_domains=[f"https://{HOST}"]) as live:
        # Publish the view-only player before the agent moves, so B's viewer shows the fill.
        inquiry = step(inquiry, "browser session opened", viewer_url=live.embed_url, steel_session_id=live.id)

        async with CDP(live.id) as cdp:
            probe = await cdp.page()
            cdp.keep_alive(probe)
            before = await _showing_count(cdp, probe)
            log(f"  · tenant showings before: {before}")
            if before is None:
                return step(gate.fail(inquiry, "not logged in to Rent Panda — run scripts/steel_login.py"), "failed: not logged in")

            # ---- fill, with writes physically blocked ------------------------
            async with cdp.write_guard(HOST) as blocked:
                inquiry = step(inquiry, "agent filling the showing request (sending is blocked)")
                agent = Agent(task=fill_task(listing, slots, note), llm=make_llm(),
                              browser_session=live.browser, use_vision=True, max_failures=4)
                history = await agent.run(max_steps=20)
                form_page, values = await _form_values(cdp)

            if blocked:
                # The model tried to write something. The guard stopped it; we stop too.
                return step(gate.fail(inquiry, f"agent attempted blocked writes: {blocked}"),
                            f"failed: agent tried to send during fill ({len(blocked)} blocked)")
            if values is None:
                return step(gate.fail(inquiry, "showing dialog not open after fill: "
                                      + redact(history.final_result() or history.errors()[-1:])[:300]),
                            "failed: dialog not found")
            problems = _mismatches(values, slots, note)
            if problems:
                return step(gate.fail(inquiry, "; ".join(problems)), f"failed: form doesn't match draft ({len(problems)})")

            filled = {"notes": values["notes"]}
            for i, slot in enumerate(slots):
                filled[f"preferred_time_{i + 1}"] = f"{values[f'date_{i}']} {values[f'time_{i}']}"
            inquiry = gate.ready_for_review(inquiry, filled, viewer_url=live.embed_url, steel_session_id=live.id)
            persist(inquiry)
            log("  · form filled and verified — waiting for human approval")

            # ---- human decides --------------------------------------------------
            if ask_approval is None:
                done = gate.reject(inquiry, "fill-only run, nothing sent", by_human=False)
                persist(done)
                return done
            try:
                ok, approver = await asyncio.wait_for(ask_approval(inquiry), APPROVAL_BUDGET_S)
            except asyncio.TimeoutError:
                done = gate.reject(inquiry, "no approval decision in time, nothing sent", by_human=False)
                persist(done)
                return done
            if not ok:
                done = gate.reject(inquiry, "nothing sent")
                persist(done)
                return done

            inquiry = gate.approve(inquiry, approver)
            persist(inquiry)
            gate.submit(inquiry)          # last gate: raises unless APPROVED with an approver. Not persisted yet.

            if time.monotonic() - started > SESSION_CAP_MS / 1000 - 90:
                return step(gate.fail(inquiry, "too close to the session time cap to submit safely"), "failed: session nearly expired")

            # ---- submit, guard lifted -------------------------------------------
            if form_page is None or await cdp.js(form_page, READ_FORM_JS) != values:
                return step(gate.fail(inquiry, "form changed between approval and submit"), "failed: form changed")
            inquiry = step(inquiry, "approved — agent clicking Send request")
            submit_agent = Agent(task=SUBMIT_TASK, llm=make_llm(), browser_session=live.browser,
                                 use_vision=True, max_failures=2)
            await submit_agent.run(max_steps=4)
            await asyncio.sleep(3)

            after = await _showing_count(cdp, probe)
            log(f"  · tenant showings after: {after}")
            if after and before and after["total"] > before["total"]:
                sent = gate.submit(inquiry)
                persist(sent)
                log("  · confirmed: request appears on your Rent Panda showings page")
                return sent
            return step(gate.fail(inquiry, f"could not confirm the request was sent (showings {before} -> {after})"),
                        "failed: send not confirmed — check Rent Panda before retrying")
