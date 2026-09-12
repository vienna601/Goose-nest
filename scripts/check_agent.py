#!/usr/bin/env python
"""Exercise the draft + approval gate offline. No Steel key, no network, no DB.

    .venv/bin/python scripts/check_agent.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.approve import NotApproved, approve, fail, ready_for_review, reject, submit  # noqa: E402
from agent.draft import CannotContact, draft_inquiry, route  # noqa: E402
from collection.normalize import from_bamboo, from_rent_panda  # noqa: E402
from shared.schema import InquiryStatus  # noqa: E402

FIX = ROOT / "collection" / "fixtures"
bamboo = from_bamboo(json.loads((FIX / "bamboo_all.json").read_text())[0], "fixture")
panda = next(
    from_rent_panda(r, "fixture")
    for r in json.loads((FIX / "rent_panda_all.json").read_text())
    if (r.get("city") or "").strip().lower() == "waterloo"
)

fails = 0

print("1. a Bamboo listing must refuse to contact (account-gated)")
try:
    route(bamboo)
    print("   FAIL — it let us through"); fails += 1
except CannotContact as e:
    print(f"   ok — {str(e)[:72]}...")

print("\n2. draft a real inquiry for the Rent Panda listing")
inq = draft_inquiry(panda, "Vienna", "vienna@example.com", questions=["Is parking included?"])
print(f"   status={inq.status.value} method={inq.method.value}")
print("   ---"); print("   " + inq.message.replace("\n", "\n   ")); print("   ---")

print("3. sending a DRAFTED inquiry must be refused")
try:
    submit(inq); print("   FAIL — it sent without approval"); fails += 1
except NotApproved as e:
    print(f"   ok — {str(e)[:72]}")

print("\n4. fill the form, then try to send before a human approves")
pending = ready_for_review(inq, {"name": "Vienna", "email": "vienna@example.com"},
                           viewer_url="https://steel.dev/session/fake")
try:
    submit(pending); print("   FAIL — sent from PENDING_APPROVAL"); fails += 1
except NotApproved:
    print("   ok — still refused")

print("\n5. blank approver must be refused")
try:
    approve(pending, "   "); print("   FAIL — accepted a blank approver"); fails += 1
except NotApproved:
    print("   ok — refused")

print("\n6. the happy path")
sent = submit(approve(pending, "vienna"))
ok = sent.status == InquiryStatus.SUBMITTED and sent.approved_at and sent.submitted_at
print(f"   status={sent.status.value} approved_by={sent.approved_by} "
      f"approved_at set={bool(sent.approved_at)} submitted_at set={bool(sent.submitted_at)}")
if not ok:
    print("   FAIL"); fails += 1

print("\n7. rejection path")
print(f"   {reject(ready_for_review(draft_inquiry(panda,'V','v@e.com'), {}), 'changed my mind').status.value}")

print(f"\n{'FAILURES: ' + str(fails) if fails else 'OK — the gate holds on every path'}")
raise SystemExit(1 if fails else 0)
