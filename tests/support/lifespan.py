"""Running the app's lifespan from a test's own event loop, without HTTP or a server."""

import asyncio
from contextlib import AsyncExitStack

from fastapi import FastAPI

# A real-time bound on entering or leaving the lifespan, so a startup or shutdown that hangs
# fails the test instead of the run. Never waited out when the app behaves.
LIFESPAN_BOUND_S = 5.0


async def start_lifespan(app: FastAPI) -> AsyncExitStack:
    """Enter `app`'s lifespan (its startup) and return the stack whose `aclose()` shuts it down.

    Raises `TimeoutError` if startup takes longer than `LIFESPAN_BOUND_S`.
    """
    stack = AsyncExitStack()
    async with asyncio.timeout(LIFESPAN_BOUND_S):
        await stack.enter_async_context(app.router.lifespan_context(app))
    return stack
