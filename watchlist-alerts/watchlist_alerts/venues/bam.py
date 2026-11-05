"""BAM: the /film page links every film; each film page has year/director and its
showtimes come from BAM's own JSON endpoint (the one the page itself calls)."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..http import get, get_json
from . import Screening, Want, at, in_window, today
from ._parse import month_day, parse_time

NAME = "BAM"
BASE = "https://www.bam.org"
LIST_URL = f"{BASE}/film"
PERF_URL = f"{BASE}/api/BAMApi/GetPerformancesByProduction?ProductionPageId={{}}"


def film_links(html: str) -> list[str]:
    links = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.match(r"^(?:https://www\.bam\.org)?(/film/\d{4}/[\w-]+)", a["href"])
        if m and m.group(1) not in links:
            links.append(m.group(1))
    return links


def parse_film_page(html: str) -> tuple[str | None, int | None, str | None, str | None]:
    """-> (title, year, director, production id)"""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else None
    text = soup.get_text(" ", strip=True)
    m = re.search(r"Directed by\s+(.+?)\s+\((\d{4})\)", text)
    director, year = (m.group(1), int(m.group(2))) if m else (None, None)
    if title and director:
        # "Ken Russell’s The Devils" -> "The Devils"
        title = re.sub(rf"^{re.escape(director)}[’']s\s+", "", title)
    pid = re.search(r"ProductionPageId=(\d+)", html)
    return title, year, director, pid.group(1) if pid else None


def parse_performances(items: list[str], days: int) -> list[tuple]:
    out = []
    for item in items:
        frag = BeautifulSoup(item, "html.parser")
        label = frag.get_text(" ", strip=True)  # "Fri, Nov 6 at 4:30PM"
        d, hm = month_day(label, today()), parse_time(label.split(" at ")[-1])
        a = frag.find("a", href=True)
        if d and hm and in_window(d, days):
            out.append((at(d, *hm), a["href"] if a else None))
    return out


def fetch(days: int, want: Want) -> list[Screening]:
    out = []
    for path in film_links(get(LIST_URL)):
        slug = re.sub(r"-\d{4}$", "", path.rsplit("/", 1)[-1])
        if not want(slug):
            continue
        page_url = BASE + path
        title, year, director, pid = parse_film_page(get(page_url))
        if not title or not pid:
            continue
        for start, ticket in parse_performances(get_json(PERF_URL.format(pid)), days):
            out.append(Screening(NAME, title, start, ticket or page_url, year=year, director=director))
    return out
