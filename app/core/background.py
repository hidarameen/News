import asyncio
import logging
from typing import Awaitable, Callable, Optional


logger = logging.getLogger(__name__)


class BackgroundTaskQueue:
    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue(maxsize=maxsize)
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._worker_task is not None:
            return

        async def worker() -> None:
            logger.info("Background queue worker started")
            try:
                while not self._stop_event.is_set():
                    try:
                        job = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                    except asyncio.TimeoutError:
                        continue
                    try:
                        await job()
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("Background job failed: %s", exc)
                    finally:
                        self._queue.task_done()
            finally:
                logger.info("Background queue worker stopped")

        self._worker_task = asyncio.create_task(worker())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._worker_task is not None:
            await self._worker_task
            self._worker_task = None

    def enqueue(self, coro_factory: Callable[[], Awaitable[None]]) -> None:
        try:
            self._queue.put_nowait(coro_factory)
        except asyncio.QueueFull:
            logger.warning("Background queue is full; dropping job")

