#!/usr/bin/env python
"""Exercise the /inquiries API end to end with a FAKE agent flow.

    .venv/bin/python scripts/check_contact_api.py

No Steel, no Gemini, no Rent Panda: request_showing is swapped for a stub that
walks the real approval gate. Inquiry writes go to memory; listing lookups read
the real database (read-only). Tests status codes, the approval handoff,
cancel from both states, the one-run-at-a-time rule, and the SSE stream.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import main  # noqa: E402  (backend app; loads .env, sets up import paths)
from fastapi.testclient import TestClient  # noqa: E402

import agent.flows.contact_rent_panda as flow  # noqa: E402
from agent import approve as gate  # noqa: E402
from services import agent_service as svc  # noqa: E402
from shared import db  # noqa: E402
from shared.db import make_listing_id  # noqa: E402

# ---- in-memory inquiry storage --------------------------------------------------
store: dict[str, dict] = {}
svc.db.insert_inquiry = lambda inq: store.setdefault(inq.id, inq.model_dump(mode="json"))
svc.db.update_inquiry = lambda iid, **f: store[iid].update(f) or store[iid]
svc.db.get_inquiry = lambda iid: None

# ---- fake flow: same gate calls, no browser -------------------------------------
FILL_DELAY = {"s": 0.3}

async def fake_request_showing(listing, inquiry, slots, note, *, persist, ask_approval, log=print):
    inquiry = inquiry.model_copy(update={"steps": ["browser session opened"], "viewer_url": "https://example.invalid/player?interactive=false"})
    persist(inquiry)
    await asyncio.sleep(FILL_DELAY["s"])
    fields = {"notes": note, **{f"preferred_time_{i + 1}": f"{s.date} {s.time}" for i, s in enumerate(slots)}}
    inquiry = gate.ready_for_review(inquiry, fields, viewer_url=inquiry.viewer_url)
    persist(inquiry)
    ok, who = await ask_approval(inquiry)
    if not ok:
        done = gate.reject(inquiry, "nothing sent"); persist(done); return done
    inquiry = gate.approve(inquiry, who); persist(inquiry)
    await asyncio.sleep(0.2)
    sent = gate.submit(inquiry); persist(sent); return sent

flow.request_showing = fake_request_showing

MINE = make_listing_id("rent_panda", "20684")
BAMBOO = db.get_client().table("listings").select("id").eq("source", "bamboo").limit(1).execute().data[0]["id"]
results: list[bool] = []


def check(name, got, want):
    ok = got == want
    results.append(ok)
    print(f"  {'ok ' if ok else 'BAD'} {name:<52} got={got!r}" + ("" if ok else f" want={want!r}"))


def body(listing_id=MINE, **kw):
    return {"listing_id": listing_id, "message": "(ui preview)", "sender_name": "Test", "sender_email": "t@example.invalid",
            "sender_phone": None, "questions": ["Is parking included"], "preferred_times": ["12/01/2030 18:00"], **kw}


def wait_status(c, iid, want, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        s = c.get(f"/inquiries/{iid}").json()["status"]
        if s == want:
            return s
        time.sleep(0.05)
    return c.get(f"/inquiries/{iid}").json()["status"]


with TestClient(main.app) as c:
    print("validation:")
    check("C's /listings still works", c.get("/listings?limit=1").status_code, 200)
    check("unknown listing -> 404", c.post("/inquiries", json=body("00000000-0000-0000-0000-000000000000")).status_code, 404)
    check("real landlord / bamboo listing -> 403", c.post("/inquiries", json=body(BAMBOO)).status_code, 403)
    check("bad time format -> 422", c.post("/inquiries", json=body(preferred_times=["2030-12-01 18:00"])).status_code, 422)
    check("time in the past -> 422", c.post("/inquiries", json=body(preferred_times=["01/01/2020 18:00"])).status_code, 422)
    check("4 times -> 422", c.post("/inquiries", json=body(preferred_times=["12/0%d/2030 18:00" % d for d in range(1, 5)])).status_code, 422)
    check("unknown inquiry GET -> 404", c.get("/inquiries/nope").status_code, 404)

    print("happy path:")
    r = c.post("/inquiries", json=body())
    inq = r.json()
    check("POST /inquiries -> 200 drafted", (r.status_code, inq["status"]), (200, "drafted"))
    check("server composed the note, not the UI preview", inq["message"].startswith("Hi! I'm interested in"), True)
    check("second start while busy -> 409", c.post("/inquiries", json=body()).status_code, 409)
    check("approve before review -> 409", c.post(f"/inquiries/{inq['id']}/approve", json={"approved_by": "x"}).status_code, 409)
    check("reaches pending_approval", wait_status(c, inq["id"], "pending_approval"), "pending_approval")
    got = c.get(f"/inquiries/{inq['id']}").json()
    check("filled_fields has the slot", got["filled_fields"].get("preferred_time_1"), "2030-12-01 18:00")
    check("viewer_url published", got["viewer_url"].endswith("interactive=false"), True)
    check("blank approver -> 422", c.post(f"/inquiries/{inq['id']}/approve", json={"approved_by": "  "}).status_code, 422)
    r = c.post(f"/inquiries/{inq['id']}/approve", json={"approved_by": "vienna"})
    check("approve -> 200, left pending", (r.status_code, r.json()["status"] in ("approved", "submitted")), (200, True))
    check("ends submitted", wait_status(c, inq["id"], "submitted"), "submitted")
    check("approve again -> 409", c.post(f"/inquiries/{inq['id']}/approve", json={"approved_by": "vienna"}).status_code, 409)
    check("cancel after submit -> 409", c.post(f"/inquiries/{inq['id']}/cancel").status_code, 409)

    print("cancel from pending_approval:")
    inq = c.post("/inquiries", json=body()).json()
    wait_status(c, inq["id"], "pending_approval")
    r = c.post(f"/inquiries/{inq['id']}/cancel")
    check("cancel -> cancelled", (r.status_code, r.json()["status"]), (200, "cancelled"))
    check("approved_at never set", store[inq["id"]]["approved_at"], None)

    print("cancel while the agent is still filling (drafted):")
    FILL_DELAY["s"] = 30
    inq = c.post("/inquiries", json=body()).json()
    time.sleep(0.2)
    t = time.time()
    r = c.post(f"/inquiries/{inq['id']}/cancel")
    check("cancel -> cancelled", (r.status_code, r.json()["status"]), (200, "cancelled"))
    check("didn't wait for the fill to finish", time.time() - t < 5, True)
    check("free to start another", c.post("/inquiries", json=body()).status_code, 200)

    print("SSE (real server — TestClient buffers streams and would wait forever):")
    import threading
    import httpx
    import uvicorn
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8765, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    iid = [k for k, v in store.items() if v["status"] == "drafted"][-1]
    # uvicorn runs its own event loop, so it has no _Run for this inquiry and
    # takes the stored-inquiry branch. Point the store lookup at our memory.
    svc.db.get_inquiry = lambda i: __import__("shared.schema", fromlist=["Inquiry"]).Inquiry.model_validate(store[i]) if i in store else None
    with httpx.stream("GET", f"http://127.0.0.1:8765/inquiries/{iid}/events", timeout=10) as s:
        check("content-type", s.headers["content-type"].split(";")[0], "text/event-stream")
        line = next(l for l in s.iter_lines() if l.startswith("data: "))
        ev = json.loads(line[6:])
        check("first frame is inquiry_update for this id", (ev["type"], ev["inquiry"]["id"]), ("inquiry_update", iid))
    check("events for unknown -> 404", httpx.get("http://127.0.0.1:8765/inquiries/nope/events").status_code, 404)
    c.post(f"/inquiries/{iid}/cancel")

    print("live updates over SSE while the (fake) agent runs — the frontend's path:")
    FILL_DELAY["s"] = 0.5
    base = "http://127.0.0.1:8765"
    created = httpx.post(f"{base}/inquiries", json=body(), timeout=10).json()
    seen, approved = [], False
    with httpx.stream("GET", f"{base}/inquiries/{created['id']}/events", timeout=15) as stream:
        for line in stream.iter_lines():
            if not line.startswith("data: "):
                continue
            status = json.loads(line[6:])["inquiry"]["status"]
            if not seen or seen[-1] != status:
                seen.append(status)
            if status == "pending_approval" and not approved:
                approved = True
                threading.Thread(target=lambda: httpx.post(f"{base}/inquiries/{created['id']}/approve",
                                                           json={"approved_by": "vienna"}, timeout=10)).start()
            if status == "submitted":
                break
    check("stream showed every state in order", seen, ["drafted", "pending_approval", "approved", "submitted"])
    server.should_exit = True

print("\nALL PASS" if all(results) else f"\n{results.count(False)} FAILED")
raise SystemExit(0 if all(results) else 1)
