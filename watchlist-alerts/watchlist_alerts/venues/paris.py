"""Paris Theater: film records (title, year, director, run dates) are embedded in the
page's Next.js data. Showtimes load from the ticketing system in the browser, so
alerts give the run dates rather than times."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

from ..http import get
from . import Screening, Want, today
from ._parse import find_year

NAME = "Paris Theater"
BASE = "https://www.paristheaternyc.com"
_PUSH = re.compile(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', re.S)
_FILM_START = re.compile(r'\{"id":\d+,"attributes":\{"FilmName":')


def films(html: str) -> list[dict]:
    payload = "".join(json.loads(s) for s in _PUSH.findall(html))
    dec, out, seen = json.JSONDecoder(), [], set()
    for m in _FILM_START.finditer(payload):
        try:
            obj, _ = dec.raw_decode(payload, m.start())
        except json.JSONDecodeError:
            continue
        attrs = obj.get("attributes", {})
        if attrs.get("Slug") and attrs["Slug"] not in seen:
            seen.add(attrs["Slug"])
            out.append(attrs)
    return out


def _d(s: str | None) -> date | None:
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _fmt(d: date) -> str:
    return d.strftime("%b %-d")


def to_screenings(records: list[dict], days: int) -> list[Screening]:
    t, out = today(), []
    for f in records:
        if "Paris" not in (f.get("Association") or ["Paris"]):
            continue
        opens, closes = _d(f.get("OpeningDate")), _d(f.get("ClosingDate"))
        if not opens or opens > t + timedelta(days=days) or (closes and closes < t):
            continue
        if closes == opens:
            note = f"{_fmt(opens)} only"
        elif closes:
            note = f"Playing {_fmt(opens)} – {_fmt(closes)}"
        else:
            note = f"Opens {_fmt(opens)}" if opens > t else "Now playing"
        out.append(Screening(NAME, f.get("FilmName", "").strip(), None, f"{BASE}/film/{f['Slug']}",
                             year=find_year(str(f.get("Year") or "")), director=f.get("Director"),
                             note=note + " (see site for showtimes)"))
    return out


def fetch(days: int, want: Want) -> list[Screening]:
    return [s for s in to_screenings(films(get(BASE + "/")), days) if s.title]
