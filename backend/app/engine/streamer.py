"""
Real-Time Event Streamer for Server-Sent Events (SSE).
Publishes asynchronous events to connected frontend clients without polling.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, Set

class EventStreamer:
    """
    In-memory Pub/Sub broadcaster for live UI updates, metrics counters, and alerts.
    """
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Subscribes an SSE client and yields formatted 'data: {...}\n\n' events."""
        queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._subscribers.add(queue)

        try:
            # Yield initial connection heartbeat
            connect_msg = json.dumps({
                "type": "CONNECTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Real-time SSE alert stream active"
            })
            yield f"data: {connect_msg}\n\n"

            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]):
        """Dispatches an event payload to all connected subscribers."""
        msg = json.dumps({
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload
        })
        async with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    # Drop slow consumer event to avoid backpressure leak
                    pass

# Singleton instance
streamer = EventStreamer()
