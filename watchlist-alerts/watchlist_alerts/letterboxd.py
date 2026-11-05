"""Read a public Letterboxd watchlist."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .http import get

BASE = "https://letterboxd.com"
_NAME_RE = re.compile(r"^(?P<title>.*?)(?:\s+\((?P<year>\d{4})\))?$")


@dataclass(frozen=True)
class Film:
    title: str
    year: int | None
    slug: str

    @property
    def url(self) -> str:
        return f"{BASE}/film/{self.slug}/"


def parse_watchlist_page(html: str) -> tuple[list[Film], bool]:
    """Return the films on one watchlist page and whether a next page exists."""
    soup = BeautifulSoup(html, "html.parser")
    films = []
    for el in soup.select("[data-item-slug]"):
        name = el.get("data-item-full-display-name") or el.get("data-item-name") or ""
        m = _NAME_RE.match(name.strip())
        if not m or not m.group("title"):
            continue
        year = int(m.group("year")) if m.group("year") else None
        films.append(Film(title=m.group("title"), year=year, slug=el["data-item-slug"]))
    has_next = soup.select_one("a.next") is not None
    return films, has_next


def fetch_watchlist(username: str, max_pages: int = 100, delay: float = 1.0) -> list[Film]:
    films: list[Film] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{BASE}/{username}/watchlist/" + (f"page/{page}/" if page > 1 else "")
        page_films, has_next = parse_watchlist_page(get(url))
        for f in page_films:
            if f.slug not in seen:
                seen.add(f.slug)
                films.append(f)
        if not has_next or not page_films:
            break
        time.sleep(delay)
    return films
