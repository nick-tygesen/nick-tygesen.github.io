"""Small parsing helpers shared by venue modules."""

from __future__ import annotations

import re
from datetime import date

_TIME = re.compile(r"(\d{1,2})[:.](\d{2})\s*([ap])\.?m?\.?", re.IGNORECASE)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_MONTH_DAY = re.compile(r"\b(" + "|".join(_MONTHS) + r")[a-z]*\.?\s+(\d{1,2})\b", re.IGNORECASE)
_YEAR = re.compile(r"\b(18[89]\d|19\d\d|20\d\d)\b")


def parse_time(text: str) -> tuple[int, int] | None:
    """'7:30 PM', '1.15pm', '9:00 p.m.' -> (19, 30)."""
    m = _TIME.search(text)
    if not m:
        return None
    h, mi = int(m.group(1)) % 12, int(m.group(2))
    if m.group(3).lower() == "p":
        h += 12
    return h, mi


def month_day(text: str, today: date) -> date | None:
    """'Wed Nov 4' / 'Fri, Nov 6 at 4:30PM' -> date, picking the year nearest today."""
    m = _MONTH_DAY.search(text)
    if not m:
        return None
    month, day = _MONTHS[m.group(1)[:3].lower()], int(m.group(2))
    year = today.year
    # A December page read in January (or vice versa) shouldn't land a year off.
    if month < today.month - 6:
        year += 1
    elif month > today.month + 6:
        year -= 1
    try:
        return date(year, month, day)
    except ValueError:
        return None


def find_year(text: str) -> int | None:
    m = _YEAR.search(text or "")
    return int(m.group(1)) if m else None
