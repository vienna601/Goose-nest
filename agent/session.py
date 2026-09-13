"""
Steel session lifecycle + browser-use wiring. Every agent run goes through here.

Three things in this file were learned the hard way, verified live on
2026-09-12 against steel-sdk 0.19.0 and browser-use 0.13.10:

  1. Steel's `inactivity_timeout` is MILLISECONDS. Passing 300 gives the
     session a 0.3s idle window; it is released before you can connect, and
     every connect after that is a bare HTTP 404 that never mentions timeouts.

  2. Connect with `wss://connect.steel.dev?apiKey=...&sessionId=...`.
     The `websocket_url` Steel returns 404s through browser-use's connector,
     and header auth (`steel-api-key`) gets a 401.

  3. Two viewer URLs, verified in a browser: `session_viewer_url`
     (app.steel.dev/sessions/<id>) redirects to Steel's sign-in page — it is
     YOUR dashboard, useless to an audience. `debug_url`
     (api.steel.dev/v1/sessions/<id>/player) renders the live browser in a
     plain iframe with no login. B embeds that one.

     The bare player URL is INTERACTIVE by default (verified: the page
     renders `interactive = true` with no query string). Anyone watching can
     click and type into the remote browser — which, once we use a logged-in
     profile, is your Rent Panda account. So:
       embed_url        = debug_url + ?interactive=false   (B, audience, always)
       interactive_url  = debug_url + ?interactive=true    (you, one-time login only)
     Interaction is gated behind a "Click to interact" card that appears on
     mouse movement; typed input then reaches the page (verified end to end).

  4. The connect URL carries the API key, and browser-use prints the full URL in its
     connection errors. `redact()` exists for this; route any log you show a
     human (or stream to B's UI) through it.

We never pass solve_captcha, stealth_config, or use_proxy. See docs/sources.md.
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass
from typing import AsyncIterator

os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")   # before browser_use imports

from browser_use import BrowserSession, ChatGoogle  # noqa: E402

from agent.steel_common import client, connect_url, redact, viewer_urls  # noqa: E402

# gemini-flash-latest is an alias Google re-points; it returned 503 "model is
# currently overloaded" three times running while this pinned model answered.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
INACTIVITY_MS = 180_000          # milliseconds. See note 1.
SESSION_CAP_MS = 15 * 60_000     # api_timeout: default 5 min is too short with a human approving; 15 is the launch-plan max
PROFILE_ID = os.getenv("STEEL_PROFILE_ID") or None   # written by scripts/steel_login.py

class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


for _name in ("browser_use", "cdp_use", "bubus"):
    logging.getLogger(_name).addFilter(_RedactingFilter())


def make_llm() -> ChatGoogle:
    return ChatGoogle(model=GEMINI_MODEL, api_key=os.environ["GEMINI_API_KEY"])


@dataclass
class LiveSession:
    id: str
    embed_url: str            # view-only player -> Inquiry.viewer_url. B iframes this.
    interactive_url: str      # clickable player. Only for you, only for logging in.
    dashboard_url: str        # session_viewer_url. Needs your Steel login; for you only.
    browser: BrowserSession


@contextlib.asynccontextmanager
async def steel_browser(
    use_profile: bool = True,
    allowed_domains: list[str] | None = None,
) -> AsyncIterator[LiveSession]:
    """One Steel session, connected, always released — even on exceptions.

        async with steel_browser() as live:
            agent = Agent(task=..., llm=make_llm(), browser_session=live.browser)

    keep_alive=True means the browser outlives a single Agent.run(), which is
    what lets fill and submit be two runs with the approval gate in between.
    """
    steel = client()
    extra = {"profile_id": PROFILE_ID} if (use_profile and PROFILE_ID) else {}
    session = steel.sessions.create(
        inactivity_timeout=INACTIVITY_MS, api_timeout=SESSION_CAP_MS, **extra
    )
    embed_url, interactive_url = viewer_urls(session.debug_url)
    browser = BrowserSession(
        cdp_url=connect_url(session.id),
        is_local=False,
        keep_alive=True,
        allowed_domains=allowed_domains,   # browser-use refuses to navigate anywhere else
    )
    try:
        await browser.start()
        yield LiveSession(
            id=session.id,
            embed_url=embed_url,
            interactive_url=interactive_url,
            dashboard_url=session.session_viewer_url,
            browser=browser,
        )
    finally:
        with contextlib.suppress(Exception):
            await browser.kill()
        steel.sessions.release(session.id)   # unreleased sessions keep billing
