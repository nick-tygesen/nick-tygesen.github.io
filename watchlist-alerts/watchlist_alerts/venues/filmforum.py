"""Film Forum: a 7-day tabbed schedule; year and director come from each film's page."""

from __future__ import annotations

import re
from datetime import timedelta

from bs4 import BeautifulSoup

from ..http import get
from . import Screening, Want, at, in_window, today
from ._parse import find_year

NAME = "Film Forum"
URL = "https://filmforum.org/now_playing"
_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _to_24h(times: list[str]) -> list[tuple[int, int]]:
    """Film Forum omits am/pm. 12 and 1–9 are afternoon/evening; 10–11 are
    morning unless an afternoon show came earlier in the same row."""
    out, seen_pm = [], False
    for t in times:
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", t.strip())
        if not m:
            continue
        h, mi = int(m.group(1)), int(m.group(2))
        if h == 12 or 1 <= h <= 9 or (h in (10, 11) and seen_pm):
            h = 12 if h == 12 else h + 12
        seen_pm = seen_pm or h >= 12
        out.append((h, mi))
    return out


def parse_schedule(html: str, days: int) -> list[Screening]:
    soup = BeautifulSoup(html, "html.parser")
    labels = [li.get_text(strip=True).upper()[:3] for li in soup.select("#tabs ul li")]
    first = today()
    if labels and labels[0] in _DAYS:
        while first.weekday() != _DAYS.index(labels[0]):
            first += timedelta(days=1)
    out = []
    for tab in soup.select("div[id^=tabs-]"):
        m = re.fullmatch(r"tabs-(\d+)", tab.get("id", ""))
        if not m:
            continue
        d = first + timedelta(days=int(m.group(1)))
        if not in_window(d, days):
            continue
        for p in tab.find_all("p"):
            a = p.select_one("strong a") or p.find("a")
            if not a:
                continue
            for hm in _to_24h([s.get_text() for s in p.find_all("span")]):
                out.append(Screening(NAME, a.get_text(" ", strip=True), at(d, *hm), a["href"]))
    return out


def parse_film_page(html: str) -> tuple[int | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    text = (soup.select_one(".copy") or soup).get_text(" ", strip=True)
    m = re.search(r"(\d{4})\s+Directed by\s+(.+?)(?:\s+(?:Starring|Approx\.|Produced)|$)", text)
    if m:
        return int(m.group(1)), m.group(2).strip()
    return find_year(text), None


def fetch(days: int, want: Want) -> list[Screening]:
    screenings = parse_schedule(get(URL), days)
    details: dict[str, tuple[int | None, str | None]] = {}
    out = []
    for s in screenings:
        if not want(s.title):
            continue
        if s.url not in details:
            details[s.url] = parse_film_page(get(s.url))
        year, director = details[s.url]
        out.append(Screening(s.venue, s.title, s.start, s.url, year=year, director=director))
    return out
