from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")


async def retry_graph_call(call: Callable[[], Awaitable[T]], *, max_retries: int = 3) -> T:
    last_error: Exception | None = None
    for attempt in range(max(1, max_retries + 1)):
        try:
            return await call()
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            await asyncio.sleep(min(2**attempt, 30))
    raise last_error or RuntimeError("Graph call failed")
