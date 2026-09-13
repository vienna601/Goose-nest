#!/usr/bin/env python
"""Prove Gemini + browser-use + Steel work end to end, read-only.

    .venv/bin/python scripts/check_steel.py

Opens a Steel session, has the agent read the first Rent Panda listing, and
releases the session. Clicks nothing, fills nothing, contacts nobody.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser_use import Agent  # noqa: E402

from agent.session import GEMINI_MODEL, make_llm, redact, steel_browser  # noqa: E402

TASK = (
    "Go to https://app.rentpanda.ca/search-result . Read the page. Report the price "
    "and city of the FIRST listing shown. Do not click contact, message, apply, or "
    "login buttons. Do not fill any forms."
)


async def main() -> int:
    t = time.time()
    try:
        async with steel_browser() as live:
            print(f"steel session up\n  embed (what B iframes): {live.embed_url}\n  dashboard (your login): {live.dashboard_url}")
            agent = Agent(task=TASK, llm=make_llm(), browser_session=live.browser,
                          use_vision=False, max_failures=4)
            hist = await agent.run(max_steps=6)
    except Exception as exc:
        print(f"FAIL  {type(exc).__name__}: {redact(exc)[:200]}")
        return 1
    print(f"model: {GEMINI_MODEL} | steps: {hist.number_of_steps()} | {time.time() - t:.0f}s")
    print(f"result: {redact(hist.final_result())}")
    if not hist.is_successful():
        print("FAIL  agent did not finish:", [redact(e)[:90] for e in hist.errors() if e])
        return 1
    print("\nOK — Gemini, browser-use and Steel are wired end to end.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
