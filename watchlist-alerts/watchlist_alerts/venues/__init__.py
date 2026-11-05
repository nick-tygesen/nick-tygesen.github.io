"""Theater schedule sources.

Each venue module exposes ``NAME`` (display name) and ``fetch(days) -> list[Screening]``
returning screenings in the next ``days`` days. Register new modules in ``VENUES``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Screening:
    venue: str
    title: str
    start: datetime | None  # local NYC time; None if only the date/run is known
    url: str
    year: int | None = None
    director: str | None = None
    note: str | None = None  # e.g. "Opens Friday", "35mm", series name

    @property
    def key(self) -> str:
        when = self.start.isoformat() if self.start else (self.note or "")
        return f"{self.venue}|{self.title}|{when}"


# Venue modules are added here once their sites can be read and tested.
VENUES: list = []
