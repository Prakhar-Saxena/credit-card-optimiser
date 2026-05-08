import time
from datetime import datetime


class Timer:
    def __init__(self):
        self._start = time.monotonic()

    def ts(self):
        """Return '[HH:MM:SS | +Xs]' — wall clock time and elapsed seconds."""
        now = datetime.now().strftime("%H:%M:%S")
        elapsed = time.monotonic() - self._start
        return f"[{now} | +{elapsed:.0f}s]"

    def elapsed(self):
        return time.monotonic() - self._start
