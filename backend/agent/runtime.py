"""Bound inference concurrency and total wall time without unbounded worker queues."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import BoundedSemaphore

from backend.config import MAX_CONCURRENT_TRIAGE, TRIAGE_TIMEOUT_SECONDS


class TriageBusy(RuntimeError):
    pass


class TriageTimeout(RuntimeError):
    pass


class InferenceRunner:
    def __init__(self, workers=MAX_CONCURRENT_TRIAGE, timeout=TRIAGE_TIMEOUT_SECONDS):
        self.slots = BoundedSemaphore(workers)
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="triage")
        self.timeout = timeout

    def run(self, function, *args):
        if not self.slots.acquire(blocking=False):
            raise TriageBusy("Inference capacity is full.")
        try:
            future = self.executor.submit(function, *args)
        except BaseException:
            self.slots.release()
            raise
        # Timed-out Python threads retain their slot until they really finish.
        future.add_done_callback(lambda _: self.slots.release())
        try:
            return future.result(timeout=self.timeout)
        except TimeoutError as error:
            future.cancel()
            raise TriageTimeout("Inference deadline exceeded.") from error


runner = InferenceRunner()
