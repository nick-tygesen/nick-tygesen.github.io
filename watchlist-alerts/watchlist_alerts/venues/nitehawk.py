"""Nitehawk (Williamsburg + Prospect Park): schema.org data on the homepage and
coming-soon page lists films; each film page lists all of its screenings."""

from __future__ import annotations

import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ..http import get
from . import NYC, Screening, Want, in_window
from ._parse import find_year

NAME = "Nitehawk"
LOCATIONS = {
    "williamsburg": "Nitehawk Williamsburg",
    "prospectpark": "Nitehawk Prospect Park",
}
BASE = "https://nitehawkcinema.com"


def graph(html: str) -> list[dict]:
    out = []
    for tag in BeautifulSoup(html, "html.parser").select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        items = data.get("@graph", [data]) if isinstance(data, dict) else data
        out += [x for x in items if isinstance(x, dict)]
    return out


def movies(items: list[dict]) -> dict[str, dict]:
    return {m["url"]: m for m in items if m.get("@type") == "Movie" and m.get("url")}


def screenings(venue: str, movie: dict, items: list[dict], days: int) -> list[Screening]:
    directors = [d.get("name") for d in movie.get("director", []) if isinstance(d, dict)]
    out = []
    for ev in items:
        if ev.get("@type") != "ScreeningEvent" or not ev.get("startDate"):
            continue
        start = datetime.fromisoformat(ev["startDate"]).astimezone(NYC)
        if in_window(start.date(), days):
            out.append(Screening(venue, movie["name"], start, ev.get("url") or movie["url"],
                                 year=find_year(movie.get("dateCreated", "")),
                                 director=", ".join(filter(None, directors)) or None))
    return out


def fetch(days: int, want: Want) -> list[Screening]:
    out = []
    for slug, venue in LOCATIONS.items():
        listed: dict[str, dict] = {}
        for page in (f"{BASE}/{slug}/", f"{BASE}/{slug}/coming-soon/"):
            try:
                listed.update(movies(graph(get(page))))
            except requests.HTTPError:
                continue  # a location page can be missing; the other still works
        for url, movie in listed.items():
            if want(movie.get("name", "")):
                out += screenings(venue, movie, graph(get(url)), days)
    return out
