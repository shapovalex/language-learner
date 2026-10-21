"""Time as the Sync scheduler sees it: a fake clock that only moves when the test moves it.

The scheduler takes a clock whose `sleep(seconds)` it awaits for the five-minute interval and
the 30 s shutdown cap (story 2.10, decided 2026-10-21). `FakeClock.sleep` parks the caller until
`advance()` carries the clock past its deadline, so no test waits in real time.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

# A real-time bound on a whole scenario, so a Sync that never settles fails the test instead of
# hanging the run. Never waited out when the code behaves: the scenarios run on FakeClock time.
SCENARIO_BOUND_S = 5.0
# Enough loop turns for a chain of tasks (request -> Sync -> next pending Sync) to settle
DRAIN_TURNS = 200


async def drain(turns: int = DRAIN_TURNS) -> None:
    """Give every ready task `turns` chances to run. Yields to the loop; never waits on time."""
    for _ in range(turns):
        await asyncio.sleep(0)


async def until(predicate: Callable[[], bool], *, turns: int = DRAIN_TURNS) -> None:
    """Yield to the loop until `predicate()` holds. Raises `TimeoutError` after `turns` turns."""
    for _ in range(turns):
        if predicate():
            return
        await asyncio.sleep(0)
    if not predicate():
        raise TimeoutError(f"condition not met within {turns} loop turns")


async def bounded[T](awaitable: Awaitable[T], seconds: float = SCENARIO_BOUND_S) -> T:
    """`awaitable`'s result. Raises `TimeoutError` if it takes more than `seconds` real time."""
    async with asyncio.timeout(seconds):
        return await awaitable


@dataclass
class _Sleeper:
    deadline: float
    wake: asyncio.Future[None]


@dataclass
class FakeClock:
    """A clock for the Sync scheduler: `sleep()` parks until `advance()` reaches its deadline.

    `requested` records every delay asked for, in order; `sleeping` is the remaining delay of
    each parked sleeper, shortest first.
    """

    now: float = 0.0
    requested: list[float] = field(default_factory=list)
    _sleepers: list[_Sleeper] = field(default_factory=list)

    @property
    def sleeping(self) -> list[float]:
        return sorted(s.deadline - self.now for s in self._sleepers)

    async def sleep(self, seconds: float) -> None:
        self.requested.append(seconds)
        sleeper = _Sleeper(self.now + seconds, asyncio.get_running_loop().create_future())
        self._sleepers.append(sleeper)
        try:
            await sleeper.wake
        finally:
            if sleeper in self._sleepers:
                self._sleepers.remove(sleeper)

    async def advance(self, seconds: float) -> None:
        """Move the clock forward, waking each sleeper at its own deadline, in order.

        A sleeper that wakes and sleeps again inside the window is woken again, so an interval
        shorter than `seconds` fires as often as it would in real time.
        """
        target = self.now + seconds
        while due := [s for s in self._sleepers if s.deadline <= target]:
            self.now = min(s.deadline for s in due)
            for sleeper in [s for s in due if s.deadline <= self.now]:
                self._sleepers.remove(sleeper)
                if not sleeper.wake.done():
                    sleeper.wake.set_result(None)
            await drain()
        self.now = target
        await drain()
