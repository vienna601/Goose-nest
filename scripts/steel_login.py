#!/usr/bin/env python
"""Log the agent's Steel browser into your Rent Panda TENANT account, once.

    .venv/bin/python scripts/steel_login.py            # log in, save profile to .env
    .venv/bin/python scripts/steel_login.py --verify   # is STEEL_PROFILE_ID still logged in?
    .venv/bin/python scripts/steel_login.py --dry-run  # plumbing only, saves nothing

YOU type the password, in Steel's interactive player. This script never asks
for, reads, or stores credentials. What it stores is a Steel profile id; the
logged-in cookies live in that profile on Steel's side. Treat STEEL_API_KEY as
access to your Rent Panda account from here on.

How the save works (both steps verified the hard way — see agent/steel_common.py):
  1. After you log in we leave the page and wait, so Chrome flushes cookies and
     localStorage to disk. Release immediately and nothing is saved.
  2. The profile uploads ~1 min AFTER release, and its `status` says READY the
     whole time. We wait for `updated_at` to move instead.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.cdp import CDP, CDPError  # noqa: E402
from agent.steel_common import client, redact, viewer_urls  # noqa: E402

LOGIN_URL = "https://app.rentpanda.ca/login"
# Your own test listing. A fresh server render of it carries Inertia's
# props.auth.user — null when logged out — which is how we check login state.
PROBE_URL = "https://app.rentpanda.ca/for-rent/university-ave-toronto-on-sll4wp/20214/20684/details"
ENV_PATH = ROOT / ".env"

FLUSH_WAIT_S = 45
UPLOAD_WAIT_S = 240

# Reports login state and the account role only. Never the name, email, or id.
AUTH_JS = r"""
(() => {
  const el = document.querySelector('[data-page]');
  if (!el) return {error: 'no Inertia payload on this page'};
  const user = (JSON.parse(el.dataset.page).props.auth || {}).user;
  if (!user) return {logged_in: false};
  let role = user.role ?? user.user_type ?? user.type ?? null;
  if (role === null && Array.isArray(user.roles)) role = user.roles.map(r => r.name ?? r).join(',');
  if (role === null) {
    if (user.is_landlord === true || user.landlord === true) role = 'landlord';
    else if (user.is_tenant === true || user.tenant === true) role = 'tenant';
  }
  return {logged_in: true, role: role};
})()
"""


def set_env(key: str, value: str) -> None:
    """Replace or append one line in .env without touching anything else."""
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    out, done = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            done = True
        else:
            out.append(line)
    if not done:
        out.append(f"{key}={value}")
    mode = ENV_PATH.stat().st_mode if ENV_PATH.exists() else 0o600
    fd, tmp = tempfile.mkstemp(dir=ROOT, prefix=".env.")
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(out) + "\n")
    os.chmod(tmp, mode)
    os.replace(tmp, ENV_PATH)


async def auth_state(cdp: CDP, page: str) -> dict:
    await cdp.goto(page, PROBE_URL, settle_s=4)
    return await cdp.js(page, AUTH_JS) or {"error": "no result"}


def describe(state: dict) -> str:
    if "error" in state:
        return f"could not tell ({state['error']})"
    if not state.get("logged_in"):
        return "NOT logged in"
    return f"logged in (role: {state.get('role') or 'not exposed'})"


async def wait_for_upload(steel, profile_id: str, baseline) -> bool:
    deadline = time.time() + UPLOAD_WAIT_S
    while time.time() < deadline:
        current = steel.profiles.get(profile_id).updated_at
        if current and baseline and current > baseline:
            print(f"  profile saved (updated {current:%H:%M:%S} UTC)")
            return True
        await asyncio.sleep(5)
        print("  .", end="", flush=True)
    print()
    return False


async def login(dry_run: bool) -> int:
    steel = client()
    session = steel.sessions.create(
        persist_profile=True,
        inactivity_timeout=10 * 60_000,   # ms
        api_timeout=15 * 60_000,          # ms — launch plan max; the 5 min default is too short
    )
    profile_id = session.profile_id
    baseline = steel.profiles.get(profile_id).updated_at if profile_id else None
    _, interactive_url = viewer_urls(session.debug_url)
    released = False
    try:
        async with CDP(session.id) as cdp:
            page = await cdp.page()
            cdp.keep_alive(page)
            before = await auth_state(cdp, page)
            print(f"fresh profile is {describe(before)}")
            if before.get("logged_in"):
                print("FAIL  a brand-new profile should not be logged in — refusing to continue")
                return 1
            await cdp.goto(page, LOGIN_URL)

            if dry_run:
                print("--dry-run: session, CDP, login page and auth probe all work. Nothing saved.")
                return 0

            print(
                "\n" + "=" * 72 +
                "\n  1. Open this in your browser (it controls the remote browser):\n\n"
                f"     {interactive_url}\n\n"
                "  2. Move the mouse over it, click the 'Click to interact' card.\n"
                "  3. Click INTO the email field before typing. If text ever lands in the\n"
                "     address bar, press Escape — never Enter.\n"
                "  4. Log in with your Rent Panda TENANT account.\n"
                "  5. Come back here and press Enter.\n"
                "\n  Don't share that link: while this runs it can drive a browser signed\n"
                "  into your account.\n" + "=" * 72
            )
            await asyncio.to_thread(input, "\nPress Enter once you're logged in... ")

            after = await auth_state(cdp, page)
            print(f"\nafter login: {describe(after)}")
            if not after.get("logged_in"):
                print("FAIL  not logged in. Nothing saved — run the script again.")
                return 1
            if after.get("role") and "landlord" in str(after["role"]).lower():
                print("WARN  this looks like the LANDLORD account. The agent needs the tenant\n"
                      "      account to request a showing on your own listing.")

            await cdp.goto(page, "about:blank", settle_s=1)
            print(f"waiting {FLUSH_WAIT_S}s so Chrome writes the login to disk...")
            await asyncio.sleep(FLUSH_WAIT_S)

        steel.sessions.release(session.id)
        released = True
        print("session released; waiting for Steel to upload the profile", end="", flush=True)
        if not await wait_for_upload(steel, profile_id, baseline):
            print(f"FAIL  profile didn't finish uploading in {UPLOAD_WAIT_S}s. Not written to .env.\n"
                  f"      Profile id, if you want to retry --verify by hand: {profile_id}")
            return 1

        set_env("STEEL_PROFILE_ID", profile_id)
        print("wrote STEEL_PROFILE_ID to .env")
        print("\nOK — now confirm it survives a fresh session:\n  .venv/bin/python scripts/steel_login.py --verify")
        return 0
    except CDPError as exc:
        print(f"FAIL  {redact(exc)}")
        return 1
    finally:
        if not released:
            steel.sessions.release(session.id)


async def verify() -> int:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH, override=True)
    profile_id = os.getenv("STEEL_PROFILE_ID")
    if not profile_id:
        print("FAIL  no STEEL_PROFILE_ID in .env — run the login first")
        return 1
    steel = client()
    # No persist_profile: verifying must not rewrite the saved login.
    session = steel.sessions.create(profile_id=profile_id, inactivity_timeout=120_000, api_timeout=300_000)
    try:
        async with CDP(session.id) as cdp:
            page = await cdp.page()
            state = await auth_state(cdp, page)
    except CDPError as exc:
        print(f"FAIL  {redact(exc)}")
        return 1
    finally:
        steel.sessions.release(session.id)
    print(f"fresh session from saved profile: {describe(state)}")
    return 0 if state.get("logged_in") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="check the saved profile is still logged in")
    mode.add_argument("--dry-run", action="store_true", help="exercise the plumbing, save nothing")
    args = ap.parse_args()
    return asyncio.run(verify() if args.verify else login(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
