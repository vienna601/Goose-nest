"""
Minimal raw Chrome DevTools Protocol client for Steel sessions.

For deterministic steps where an LLM adds nothing but risk: opening a page,
checking login state, reading back what's actually in a form, and — most
importantly — write_guard(), which makes "fill but don't submit" a property of
the browser instead of a hope about the model.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
from typing import Any, Awaitable, Callable, Optional
from urllib.parse import urlparse

import websockets

from agent.steel_common import connect_url, redact

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CDPError(RuntimeError):
    pass


class CDP:
    def __init__(self, session_id: str):
        self._url = connect_url(session_id)
        self._ids = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
        self._tasks: list[asyncio.Task] = []

    async def __aenter__(self) -> "CDP":
        try:
            self.ws = await websockets.connect(self._url, open_timeout=30, max_size=None)
        except Exception as exc:                      # message may contain the URL
            raise CDPError(redact(f"{type(exc).__name__}: {exc}")) from None
        self._tasks.append(asyncio.create_task(self._reader()))
        return self

    async def __aexit__(self, *exc: Any) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        await self.ws.close()

    async def _reader(self) -> None:
        async for raw in self.ws:
            msg = json.loads(raw)
            if "id" in msg and msg["id"] in self._pending:
                self._pending.pop(msg["id"]).set_result(msg)
            elif "method" in msg:
                for handler in self._handlers.get(msg["method"], []):
                    asyncio.create_task(handler(msg))

    def on(self, event: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._handlers.setdefault(event, []).append(handler)

    async def send(self, method: str, params: Optional[dict] = None, session: Optional[str] = None) -> dict:
        mid = next(self._ids)
        msg: dict[str, Any] = {"id": mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        fut = asyncio.get_running_loop().create_future()
        self._pending[mid] = fut
        await self.ws.send(json.dumps(msg))
        reply = await asyncio.wait_for(fut, 30)
        if "error" in reply:
            raise CDPError(f"{method}: {reply['error']}")
        return reply.get("result", {})

    async def page(self) -> str:
        """Attach to the first page target; returns the CDP session id to pass around."""
        targets = (await self.send("Target.getTargets"))["targetInfos"]
        target = next(t for t in targets if t["type"] == "page")
        attached = await self.send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
        return attached["sessionId"]

    async def goto(self, page: str, url: str, settle_s: float = 3.0) -> None:
        await self.send("Page.enable", session=page)
        await self.send("Page.navigate", {"url": url}, session=page)
        await asyncio.sleep(settle_s)

    async def js(self, page: str, expression: str) -> Any:
        result = await self.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
            session=page,
        )
        return result.get("result", {}).get("value")

    def keep_alive(self, page: str, every_s: float = 30.0) -> None:
        """Ping so inactivity_timeout doesn't release the session while a human
        reads instructions or decides whether to approve."""
        async def _loop() -> None:
            while True:
                await asyncio.sleep(every_s)
                with contextlib.suppress(Exception):
                    await self.js(page, "1")
        self._tasks.append(asyncio.create_task(_loop()))

    @contextlib.asynccontextmanager
    async def write_guard(
        self,
        host: str,
        blocked: Optional[list[str]] = None,
        allow_once: Optional[tuple[str, str]] = None,
    ):
        """Fail every non-GET request to `host`, in every tab, for the duration.

        Two layers, because one isn't enough (verified on example.com):
          * Fetch.enable on the BROWSER target catches tabs opened after the
            guard starts — but NOT tabs that already exist. A POST from the
            already-open tab sailed straight through with only this layer.
          * So we also attach to every existing page and enable Fetch there.
        Blocked requests fail with BlockedByClient; the page sees a network
        error and nothing leaves the browser. `blocked` collects "METHOD path"
        for everything it stopped.

        allow_once=("POST", "/tenant/showing/request") lets exactly one matching
        request through and blocks every write after it, including a second
        identical one. That's how "click Send exactly once" is enforced: the
        agent did, in fact, click Send, then run JavaScript to click it again.
        """
        log = blocked if blocked is not None else []
        # The same request pauses once per interception layer (browser + each tab),
        # so the allowance is keyed on networkId, which both layers share. Keying on
        # a counter let layer 1 spend it and layer 2 block the very same request.
        allowed_ids: set[str] = set()

        async def on_paused(evt: dict) -> None:
            p = evt["params"]
            req = p["request"]
            session = evt.get("sessionId")
            method, url = req["method"].upper(), urlparse(req["url"])
            net_id = p.get("networkId") or p["requestId"]
            if url.netloc == host and method not in SAFE_METHODS:
                matches = bool(allow_once) and (method, url.path) == (allow_once[0].upper(), allow_once[1])
                if matches and (net_id in allowed_ids or not allowed_ids):
                    allowed_ids.add(net_id)
                    await self.send("Fetch.continueRequest", {"requestId": p["requestId"]}, session=session)
                    return
                log.append(f"{method} {url.path}")
                await self.send("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"}, session=session)
            else:
                await self.send("Fetch.continueRequest", {"requestId": p["requestId"]}, session=session)

        patterns = {"patterns": [{"urlPattern": f"*://{host}/*", "requestStage": "Request"}]}
        self.on("Fetch.requestPaused", on_paused)
        sessions: list[Optional[str]] = [None]                  # None = browser target
        await self.send("Fetch.enable", patterns)
        for target in (await self.send("Target.getTargets"))["targetInfos"]:
            if target["type"] == "page":
                attached = await self.send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
                await self.send("Fetch.enable", patterns, session=attached["sessionId"])
                sessions.append(attached["sessionId"])
        try:
            yield log
        finally:
            for session in sessions:
                with contextlib.suppress(Exception):
                    await self.send("Fetch.disable", session=session)
            self._handlers["Fetch.requestPaused"].remove(on_paused)
