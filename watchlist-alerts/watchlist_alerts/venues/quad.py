"""Quad Cinema: homepage has a week of day grids; year/director come from film pages."""

from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

from ..http import get
from . import Screening, Want, at, in_window
from ._parse import find_year, parse_time

NAME = "Quad Cinema"
URL = "https://quadcinema.com/"


def parse_schedule(html: str, days: int) -> list[Screening]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for item in soup.select(".day-wrap .grid-item"):
        a = item.select_one("h4 a")
        if not a:
            continue
        for t in item.select(".showtimes-list a"):
            # Ticket links carry the full date: ...theaterpage?date=2026-11-09
            m = re.search(r"date=(\d{4})-(\d{2})-(\d{2})", t.get("href", ""))
            hm = parse_time(t.get_text())
            if not m or not hm:
                continue
            d = date(*map(int, m.groups()))
            if in_window(d, days):
                out.append(Screening(NAME, a.get_text(" ", strip=True), at(d, *hm), a["href"]))
    return out


def parse_film_page(html: str) -> tuple[int | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    info = soup.select_one(".film-info p")  # "1945, 110m, DCP, U.S."
    director = None
    for item in soup.select(".credits .credit-item"):
        label = item.select_one(".credit-label")
        if label and label.get_text(strip=True).lower() in ("a film by", "directed by", "director"):
            director = ", ".join(n.get_text(strip=True) for n in item.select(".credit-name")) or None
    return (find_year(info.get_text()) if info else None), director


def fetch(days: int, want: Want) -> list[Screening]:
    details: dict[str, tuple[int | None, str | None]] = {}
    out = []
    for s in parse_schedule(get(URL), days):
        if not want(s.title):
            continue
        if s.url not in details:
            details[s.url] = parse_film_page(get(s.url))
        year, director = details[s.url]
        out.append(Screening(s.venue, s.title, s.start, s.url, year=year, director=director))
    return out
