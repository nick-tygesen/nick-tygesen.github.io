"""IFC Center: homepage has the week's schedule; year/director come from film pages."""

from __future__ import annotations

from bs4 import BeautifulSoup

from ..http import get
from . import Screening, Want, at, in_window, today
from ._parse import find_year, month_day, parse_time

NAME = "IFC Center"
URL = "https://www.ifccenter.com/"


def parse_schedule(html: str, days: int) -> list[Screening]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for day in soup.select(".daily-schedule"):
        if "show-coming-soon" in day.get("class", []):
            continue
        h = day.find("h3")
        d = month_day(h.get_text(" ", strip=True), today()) if h else None
        if not d or not in_window(d, days):
            continue
        for det in day.select(".details"):
            a = det.select_one("h3 a")
            if not a:
                continue
            for t in det.select("ul.times a"):
                hm = parse_time(t.get_text())
                if hm:
                    out.append(Screening(NAME, a.get_text(" ", strip=True), at(d, *hm), a["href"],
                                         note=t.get("href", "").strip() or None))  # ticket link
    return out


def parse_film_page(html: str) -> tuple[int | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    year = director = None
    for li in soup.select("ul.film-details li"):
        label = li.find("strong")  # <li><strong>Year</strong> 1971</li>
        if not label:
            continue
        key = label.get_text(strip=True)
        value = li.get_text(" ", strip=True)[len(key):].strip()
        if key == "Year":
            year = find_year(value)
        elif key == "Director":
            director = value
    return year, director


def fetch(days: int, want: Want) -> list[Screening]:
    details: dict[str, tuple[int | None, str | None]] = {}
    out = []
    for s in parse_schedule(get(URL), days):
        if not want(s.title):
            continue
        if s.url not in details:
            details[s.url] = parse_film_page(get(s.url))
        year, director = details[s.url]
        out.append(Screening(s.venue, s.title, s.start, s.note or s.url, year=year, director=director))
    return out
