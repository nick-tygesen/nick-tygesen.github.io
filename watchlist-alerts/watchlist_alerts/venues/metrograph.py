"""Metrograph: one calendar page with date, director/year and ticket link per showtime."""

from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from ..http import get
from . import Screening, Want, at, in_window
from ._parse import find_year, parse_time

NAME = "Metrograph"
URL = "https://metrograph.com/nyc/"


def parse(html: str, days: int) -> list[Screening]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for day in soup.select("[id^=calendar-list-day-]"):
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})$", day["id"])
        if not m:
            continue
        d = date(*map(int, m.groups()))
        if not in_window(d, days):
            continue
        for item in day.select(".homepage-in-theater-movie"):
            a = item.select_one("h4 a")
            if not a:
                continue
            meta = [p.strip() for p in (item.select_one(".film-metadata") or a).get_text().split("/")]
            year = next((find_year(p) for p in meta if re.fullmatch(r"\d{4}", p)), None)
            director = re.sub(r"\s+", " ", meta[0]) if meta and not re.fullmatch(r"\d{4}", meta[0]) else None
            for t in item.select(".showtimes a"):
                hm = parse_time(t.get_text())
                if hm:
                    out.append(Screening(NAME, a.get_text(strip=True), at(d, *hm), t.get("href") or a["href"],
                                         year=year, director=director))
    return out


def fetch(days: int, want: Want) -> list[Screening]:
    return parse(get(URL), days)
