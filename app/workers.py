# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Custom Gunicorn worker that relaxes uvicorn's WebSocket keepalive timeouts.

Why this exists
---------------
Uvicorn's `UvicornWorker` defaults to `ws_ping_interval=20s` and
`ws_ping_timeout=20s`, so any WebSocket connection is force-closed
with code 1011 ("internal error") if a pong frame doesn't traverse
browser → Cloudflare → Cloud Run within ~40 seconds of the server's
ping. Browsers reliably auto-pong per RFC 6455, but Cloudflare on Free
plan can occasionally drop or delay pong frames on long-lived WebSockets
(connection-coalescing edge cases, Bot Fight Mode artifacts, idle-conn
proxy treatment). The Brain-Dump voice flow is by far the most affected:
WebSockets stay open for entire 15-minute conversations, and the
user-visible symptom — agent introduces itself, connection dies before
the user's first reply can be processed — exactly matches the 38-second
connection lifetime visible in Cloud Run logs.

Behavior after this change
--------------------------
With `ws_ping_interval=None` and `ws_ping_timeout=None`, uvicorn no
longer sends protocol-level pings. The connection stays open as long as
TCP itself does. Truly-dead connections are still surfaced quickly: the
audio forwarding loops in `voice_session.py` `await websocket.receive_text()`
and any closed pipe raises `WebSocketDisconnect`, which we already
handle and use to drive `stop_event`. The frontend's app-level
`{type:"ping"}` heartbeat at 20-second cadence keeps the connection
actively in use, and TCP-level keepalive at the OS/Cloud Run/Cloudflare
layer detects machine-level disconnects.

This change ONLY affects WebSocket keepalive. HTTP requests are
unaffected.
"""

from typing import Any, ClassVar

from uvicorn.workers import UvicornWorker as _UvicornWorker


class UvicornWorker(_UvicornWorker):
    CONFIG_KWARGS: ClassVar[dict[str, Any]] = {
        **_UvicornWorker.CONFIG_KWARGS,
        "ws_ping_interval": None,
        "ws_ping_timeout": None,
    }
