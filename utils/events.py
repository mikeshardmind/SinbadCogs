import asyncio
import functools
from typing import Callable, List, Optional, Tuple


class MultiWaiter:  # works with stock d.py

    def __init__(self, bot):
        self.bot = bot
        self._waiters = []
        self._queue: asyncio.Queue = asyncio.Queue()
        self._tasks: List[asyncio.Task] = []
        self._prepared = False
        self._num_tasks = 0

    def _internal_callback(self, event_name, fut):
        self._queue.put_nowait((event_name, fut))

    def _prepare_for_async(self, timeout):
        if self._prepared:
            raise RuntimeError("Can't reuse this class.")

        for (event_name, check) in self._waiters:
            task = asyncio.create_task(
                self.bot.wait_for(event_name, check=check, timeout=timeout)
            )
            task.add_done_callback(
                functools.partial(self._internal_callback, event_name)
            )
            task.add_done_callback(functools.partial(self._tasks.remove))
            self._tasks.append(task)

        self._num_tasks = len(self._tasks)
        self._prepared = True

    def add_waiter(self, event_name: str, check: Optional[Callable[..., bool]] = None):
        if self._prepared:
            raise RuntimeError("You can't add waiters once you've started waiting!")
        self._waiters.append((event_name, check))

    async def wait_first(self, timeout=None) -> Tuple[str, ...]:

        self._prepare_for_async(timeout)

        (event_name, future) = await self._queue.get()
        try:
            return (event_name, future.result())
        finally:
            self._queue.task_done()
            for task in self._tasks:
                task.cancel()

    def __aiter__(self):
        self._prepare_for_async(None)
        return self

    async def __anext__(self):
        if self._num_tasks == 0:
            raise StopAsyncIteration
        (event_name, future) = await self._queue.get()
        try:
            return (event_name, future.result())
        finally:
            self._queue.task_done()
            self._num_tasks -= 1
