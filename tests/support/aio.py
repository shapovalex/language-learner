"""Running the async adapter from sync tests, with failures returned as values."""

import asyncio
from collections.abc import Awaitable
from concurrent.futures import ThreadPoolExecutor


async def settled[T](awaitable: Awaitable[T]) -> T | Exception:
    """The awaitable's result, or the exception it raised, so the test body asserts on it."""
    try:
        return await awaitable
    except Exception as exc:  # noqa: BLE001 -- returned to the test, never swallowed
        return exc


def settle[T](awaitable: Awaitable[T]) -> T | Exception:
    """`settled()` on a fresh event loop, in its own thread.

    Once the E2E session starts, Playwright's sync API keeps an event loop running in the main
    thread, where `asyncio.run()` refuses to start another.
    """
    with ThreadPoolExecutor(max_workers=1) as worker:
        return worker.submit(asyncio.run, settled(awaitable)).result()
