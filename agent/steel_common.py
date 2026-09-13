"""
Steel plumbing shared by the browser-use agent (session.py) and the raw-CDP
scripts (cdp.py, scripts/steel_login.py). No browser-use import here, so the
scripts stay fast.

Units, verified against steel-sdk 0.19.0 docstrings and live sessions:
  inactivity_timeout   milliseconds. Released after this long with no CDP
                       command or remote input.
  api_timeout          milliseconds. Hard cap on session lifetime. Default
                       is 5 minutes — too short for login, and too short for a
                       fill -> human approval -> submit flow. Always set it.
                       The "launch" plan rejects anything over 15 minutes
                       (400 Bad Request), so 15 * 60_000 is the ceiling.
  timeout              SECONDS, and it's the HTTP request timeout, not the
                       session. Don't confuse it with api_timeout.
"""

from __future__ import annotations

import os
import re

from dotenv import load_dotenv
from steel import Steel

load_dotenv()

_SECRET = re.compile(r"(apiKey=|token=)[^&\s'\"]+|ste-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}")


def redact(text: object) -> str:
    return _SECRET.sub(lambda m: (m.group(1) or "") + "<REDACTED>", str(text))


def client() -> Steel:
    return Steel(steel_api_key=os.environ["STEEL_API_KEY"])


def connect_url(session_id: str) -> str:
    """The CDP URL that works. Steel's returned websocket_url 404s through
    browser-use and header auth 401s. Carries the key — never log it raw."""
    return f"wss://connect.steel.dev?apiKey={os.environ['STEEL_API_KEY']}&sessionId={session_id}"


def viewer_urls(debug_url: str) -> tuple[str, str]:
    """(view-only, interactive). The bare player URL is interactive by default."""
    return f"{debug_url}?interactive=false", f"{debug_url}?interactive=true"
