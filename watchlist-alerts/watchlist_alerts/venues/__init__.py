"""Theater schedule sources.

Each venue module exposes ``NAME`` and ``fetch(days, want) -> list[Screening]``,
returning screenings from today through ``days`` days ahead (New York time).

``want(text)`` is a loose test of a title or URL slug against the watchlist.
Venues call it before fetching per-film detail pages, so a daily run only
requests pages for films that might be on the watchlist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

NYC = ZoneInfo("America/New_York")
Want = Callable[[str], bool]


@dataclass(frozen=True)
class Screening:
    venue: str
    title: str
    start: datetime | None  # NYC time; None when only the run dates are known
    url: str
    year: int | None = None
    director: str | None = None
    note: str | None = None  # e.g. "Playing Nov 16 – Nov 30"

    @property
    def key(self) -> str:
        when = self.start.isoformat() if self.start else (self.note or "")
        return f"{self.venue}|{self.title}|{when}"


def today() -> date:
    return datetime.now(NYC).date()


def in_window(d: date, days: int) -> bool:
    t = today()
    return t <= d <= t + timedelta(days=days)


def at(d: date, hour: int, minute: int) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=NYC)


def _load():
    from . import bam, filmforum, ifc, metrograph, nitehawk, paris, quad

    return [filmforum, metrograph, ifc, bam, quad, nitehawk, paris]


VENUES = _load()
