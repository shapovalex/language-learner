"""Running the async adapter from sync tests, with failures returned as values."""

import asyncio
from collections.abc import Awaitable


async def settled[T](awaitable: Awaitable[T]) -> T | Exception:
    """The awaitable's result, or the exception it raised, so the test body asserts on it."""
    try:
        return await awaitable
    except Exception as exc:  # noqa: BLE001 -- returned to the test, never swallowed
        return exc


def settle[T](awaitable: Awaitable[T]) -> T | Exception:
    """`settled()` on a fresh event loop."""
    return asyncio.run(settled(awaitable))
