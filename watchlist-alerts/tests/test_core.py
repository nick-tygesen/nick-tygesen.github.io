from datetime import datetime

from watchlist_alerts.letterboxd import Film, parse_watchlist_page
from watchlist_alerts.matching import find_matches, normalize
from watchlist_alerts.notify import build_email
from watchlist_alerts.venues import Screening

PAGE = """
<ul>
<li><div class="react-component" data-item-name="Paris, Texas (1984)" data-item-slug="paris-texas"
     data-item-full-display-name="Paris, Texas (1984)" data-target-link="/film/paris-texas/"></div></li>
<li><div class="react-component" data-item-name="Ikiru (1952)" data-item-slug="ikiru"
     data-item-full-display-name="Ikiru (1952)"></div></li>
<li><div class="react-component" data-item-name="Untitled Thing" data-item-slug="untitled-thing"></div></li>
</ul>
<div class="paginate-nextprev"><a class="next" href="/x/watchlist/page/2/">Older</a></div>
"""


def test_parse_watchlist_page():
    films, has_next = parse_watchlist_page(PAGE)
    assert has_next
    assert films == [
        Film("Paris, Texas", 1984, "paris-texas"),
        Film("Ikiru", 1952, "ikiru"),
        Film("Untitled Thing", None, "untitled-thing"),
    ]


def test_normalize():
    assert normalize("The Devils") == normalize("Devils")
    assert normalize("PARIS, TEXAS (35mm)") == "paris texas"
    assert normalize("Ikiru (New 4K Restoration)") == "ikiru"
    assert normalize("Ikiru (1952)") == "ikiru"
    assert normalize("Amélie") == "amelie"
    assert normalize("Pat & Mike") == "pat and mike"


def s(title, year=None, venue="Film Forum"):
    return Screening(venue=venue, title=title, start=datetime(2026, 11, 7, 19, 30), url="https://x/", year=year)


def test_matching_uses_year_when_available():
    films = [Film("Suspiria", 1977, "suspiria"), Film("Ikiru", 1952, "ikiru")]
    got = find_matches(films, [s("Suspiria", 2018), s("Suspiria", 1977), s("IKIRU")])
    assert [(m.film.slug, m.screening.year, m.year_confirmed) for m in got] == [
        ("suspiria", 1977, True),
        ("ikiru", None, False),
    ]


def test_ambiguous_title_without_year_is_skipped():
    films = [Film("Solaris", 1972, "solaris"), Film("Solaris", 2002, "solaris-2002")]
    assert find_matches(films, [s("Solaris")]) == []
    assert [m.film.slug for m in find_matches(films, [s("Solaris", 2002)])] == ["solaris-2002"]


def test_email_lists_each_film_once():
    films = [Film("Ikiru", 1952, "ikiru")]
    matches = find_matches(films, [s("Ikiru", 1952), s("Ikiru", 1952, venue="Metrograph")])
    subject, text, html = build_email(matches)
    assert subject == "Watchlist in NYC: Ikiru"
    assert text.count("Ikiru (1952)") == 1 and "Metrograph" in text and "Film Forum" in text
    assert "letterboxd.com/film/ikiru/" in html
