#!/usr/bin/env python
"""write_guard regression suite. Runs on example.com with a plain session — no
profile, no Rent Panda, nothing real is ever sent.

    .venv/bin/python scripts/check_guard.py
"""
import asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent.cdp import CDP
from agent.steel_common import client
FETCH = """(async (m, path) => { try { const r = await fetch('https://example.com' + path, {method: m}); return 'sent'; } catch (e) { return 'BLOCKED'; } })"""
XHR = """((path) => new Promise(res => { const x = new XMLHttpRequest(); x.open('POST', 'https://example.com' + path);
  x.onload = () => res('sent'); x.onerror = () => res('BLOCKED'); x.send('a=1'); }))"""
results = []
def check(name, got, want):
    ok = got == want; results.append(ok)
    print(f"  {'ok ' if ok else 'BAD'} {name:<40} got={got!r} want={want!r}")
async def main():
    steel = client()
    sess = steel.sessions.create(inactivity_timeout=120_000, api_timeout=300_000)
    try:
        async with CDP(sess.id) as cdp:
            page = await cdp.page()
            await cdp.goto(page, "https://example.com")
            print("plain guard:")
            async with cdp.write_guard("example.com") as b:
                check("GET passes", await cdp.js(page, f"({FETCH})('GET','/x')"), "sent")
                check("fetch POST blocked (existing tab)", await cdp.js(page, f"({FETCH})('POST','/x')"), "BLOCKED")
                check("XHR POST blocked", await cdp.js(page, f"({XHR})('/x')"), "BLOCKED")
                t = await cdp.send("Target.createTarget", {"url": "https://example.com"}); await asyncio.sleep(3)
                tab2 = (await cdp.send("Target.attachToTarget", {"targetId": t["targetId"], "flatten": True}))["sessionId"]
                check("POST blocked (new tab)", await cdp.js(tab2, f"({FETCH})('POST','/x')"), "BLOCKED")
            print("allow_once=('POST', '/send'):")
            async with cdp.write_guard("example.com", allow_once=("POST", "/send")) as b:
                check("1st POST /send allowed", await cdp.js(page, f"({FETCH})('POST','/send')"), "sent")
                check("2nd POST /send blocked", await cdp.js(page, f"({FETCH})('POST','/send')"), "BLOCKED")
                check("XHR POST /send (3rd) blocked", await cdp.js(page, f"({XHR})('/send')"), "BLOCKED")
                check("POST /other blocked", await cdp.js(page, f"({FETCH})('POST','/other')"), "BLOCKED")
                print("  blocked log:", b)
            print("guard removed:")
            check("POST passes again", await cdp.js(page, f"({FETCH})('POST','/x')"), "sent")
    finally:
        steel.sessions.release(sess.id)
    print("\nALL PASS" if all(results) else f"\n{results.count(False)} FAILED")
    return 0 if all(results) else 1
raise SystemExit(asyncio.run(main()))
