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
    t = re.sub(r"['’`]", "", t)  # "Stoker's" -> "stokers", matching URL slugs
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for art in _ARTICLES:
        if t.startswith(art):
            t = t[len(art):]
            break
    return t


def title_parts(s: Screening) -> list[tuple[str, int | None]]:
    """Each film in a listing, with its year. Double bills ("A + B (2014)") are split;
    a year in parentheses beats the venue's year field, which belongs to the whole bill."""
    parts = re.split(r"\s+\+\s+", s.title)
    out = []
    for p in parts:
        m = _YEAR_SUFFIX.search(p)
        out.append((p, int(m.group(1)) if m else (s.year if len(parts) == 1 else None)))
    return out


def make_prefilter(films: list[Film]):
    """Loose title/slug test venues use to decide which detail pages to fetch.
    Also accepts "<Director>'s <Title>" style names."""
    titles = {normalize(f.title) for f in films}

    def want(text: str) -> bool:
        t = normalize(re.sub(r"[-_]+", " ", text))
        t = re.sub(r" (19|20)\d\d$", "", t)
        return t in titles or any(t.endswith(" " + x) for x in titles if len(x) > 3)

    return want


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
        for title, year in title_parts(s):
            candidates = by_title.get(normalize(title), [])
            if year is not None:
                # Venues are sometimes a year off from Letterboxd (festival vs release year).
                hits = [f for f in candidates if f.year is None or abs(f.year - year) <= 1]
                matches += [Match(f, s, year_confirmed=f.year is not None) for f in hits]
            elif len(candidates) == 1:
                # No year to check: only alert when the title is unambiguous on the watchlist.
                matches.append(Match(candidates[0], s, year_confirmed=False))
    return matches
