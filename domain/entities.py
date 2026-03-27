from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Record:
    name: str
    value: float
    dttm: datetime
