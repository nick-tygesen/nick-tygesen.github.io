"""Email alerts over SMTP (works with a Gmail app password)."""

from __future__ import annotations

import html
import os
import smtplib
from collections import defaultdict
from email.message import EmailMessage
from itertools import groupby

from .matching import Match


def _time(m: Match) -> str:
    return m.screening.start.strftime("%-I:%M %p").replace(":00 ", " ")


def _venue_lines(ms: list[Match]) -> list[tuple[str, str, str]]:
    """Group one film's matches by venue -> [(venue, plain text, html)]."""
    out = []
    by_venue: dict[str, list[Match]] = defaultdict(list)
    for m in ms:
        by_venue[m.screening.venue].append(m)
    for venue, vms in sorted(by_venue.items(), key=lambda kv: min(_sort_key(m) for m in kv[1])):
        vms.sort(key=_sort_key)
        flag = "" if all(m.year_confirmed for m in vms) else " [year not confirmed]"
        timed = [m for m in vms if m.screening.start]
        text_days, html_days = [], []
        for day, group in groupby(timed, key=lambda m: m.screening.start.date()):
            group = list(group)
            label = group[0].screening.start.strftime("%a %b %-d")
            text_days.append(f"{label} " + ", ".join(_time(m) for m in group))
            html_days.append(f"{label} " + ", ".join(
                f'<a href="{html.escape(m.screening.url)}">{_time(m)}</a>' for m in group))
        for m in vms:
            if not m.screening.start:
                text_days.append(m.screening.note or "See venue for times")
                html_days.append(f'<a href="{html.escape(m.screening.url)}">'
                                 f'{html.escape(m.screening.note or "See venue for times")}</a>')
        out.append((
            venue,
            f"  {venue}{flag}: " + "; ".join(text_days) + f"\n    tickets: {vms[0].screening.url}",
            f"<li><b>{html.escape(venue)}</b>{html.escape(flag)}: " + " · ".join(html_days) + "</li>",
        ))
    return out


def _sort_key(m: Match):
    s = m.screening
    return (s.start is None, s.start.timestamp() if s.start else 0, s.venue)


def build_email(matches: list[Match]) -> tuple[str, str, str]:
    by_film: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        by_film[m.film.slug].append(m)
    films = sorted(by_film.values(), key=lambda ms: min(_sort_key(m) for m in ms))

    names = [ms[0].film.title for ms in films]
    subject = "Watchlist in NYC: " + ", ".join(names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")

    text, body = [], []
    for ms in films:
        f = ms[0].film
        label = f"{f.title} ({f.year})" if f.year else f.title
        lines = _venue_lines(ms)
        text += [label] + [t for _, t, _ in lines] + [""]
        body.append(f'<h3><a href="{html.escape(f.url)}">{html.escape(label)}</a></h3>'
                    f'<ul>{"".join(h for _, _, h in lines)}</ul>')
    return subject, "\n".join(text), "".join(body)


def send_email(matches: list[Match]) -> None:
    subject, text, body_html = build_email(matches)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.environ.get("EMAIL_FROM") or os.environ["SMTP_USER"]
    msg["To"] = os.environ["EMAIL_TO"]
    msg.set_content(text)
    msg.add_alternative(f"<html><body>{body_html}</body></html>", subtype="html")

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
