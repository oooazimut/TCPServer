from datetime import datetime

from domain.ports import Clock


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now()
