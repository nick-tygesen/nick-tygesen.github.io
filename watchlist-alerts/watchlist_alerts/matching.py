"""Match theater screenings against watchlist films."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .letterboxd import Film
from .venues import Screening

_ARTICLES = ("the ", "a ", "an ")
# Marketing wrappers venues put around titles.
_NOISE = re.compile(
    r"\s*[\(\[][^\)\]]*(?:\d{2,3}mm|4k|dcp|restor|digital|q&a|preview)[^\)\]]*[\)\]]\s*",
    re.IGNORECASE,
)
_PREFIXES = re.compile(r"^(?:\d{2,3}mm\s*:\s*|[a-z' ]+ presents\s*:\s*)", re.IGNORECASE)
_YEAR_SUFFIX = re.compile(r"\s*\((\d{4})\)\s*$")


def normalize(title: str) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = _NOISE.sub(" ", t)
    t = _PREFIXES.sub("", t.strip())
    t = _YEAR_SUFFIX.sub("", t)
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for art in _ARTICLES:
        if t.startswith(art):
            t = t[len(art):]
            break
    return t


def screening_year(s: Screening) -> int | None:
    if s.year:
        return s.year
    m = _YEAR_SUFFIX.search(s.title)
    return int(m.group(1)) if m else None


@dataclass(frozen=True)
class Match:
    film: Film
    screening: Screening
    year_confirmed: bool


def find_matches(films: list[Film], screenings: list[Screening]) -> list[Match]:
    by_title: dict[str, list[Film]] = {}
    for f in films:
        by_title.setdefault(normalize(f.title), []).append(f)

    matches = []
    for s in screenings:
        candidates = by_title.get(normalize(s.title), [])
        if not candidates:
            continue
        year = screening_year(s)
        if year is not None:
            # Venues are sometimes a year off from Letterboxd (festival vs release year).
            hits = [f for f in candidates if f.year is None or abs(f.year - year) <= 1]
            matches += [Match(f, s, year_confirmed=f.year is not None) for f in hits]
        else:
            # No year to check: only alert when the title is unambiguous on the watchlist.
            if len(candidates) == 1:
                matches.append(Match(candidates[0], s, year_confirmed=False))
    return matches
