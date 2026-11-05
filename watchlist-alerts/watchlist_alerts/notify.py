"""Email alerts over SMTP (works with a Gmail app password)."""

from __future__ import annotations

import html
import os
import smtplib
from collections import defaultdict
from email.message import EmailMessage

from .matching import Match


def _when(m: Match) -> str:
    s = m.screening
    if s.start:
        return s.start.strftime("%a %b %-d, %-I:%M %p")
    return s.note or "See venue for times"


def build_email(matches: list[Match]) -> tuple[str, str, str]:
    by_film: dict[str, list[Match]] = defaultdict(list)
    for m in matches:
        by_film[m.film.slug].append(m)

    names = sorted({f"{ms[0].film.title}" for ms in by_film.values()})
    subject = "Watchlist in NYC: " + ", ".join(names[:3]) + (f" +{len(names) - 3} more" if len(names) > 3 else "")

    text_lines, html_parts = [], []
    for ms in sorted(by_film.values(), key=lambda ms: ms[0].film.title):
        f = ms[0].film
        label = f"{f.title} ({f.year})" if f.year else f.title
        text_lines.append(label)
        rows = []
        for m in sorted(ms, key=lambda m: (m.screening.start is None, m.screening.start or 0, m.screening.venue)):
            flag = "" if m.year_confirmed else " [year not confirmed]"
            text_lines.append(f"  - {m.screening.venue}: {_when(m)}{flag}  {m.screening.url}")
            rows.append(
                f'<li><b>{html.escape(m.screening.venue)}</b> — {html.escape(_when(m))}'
                f'{html.escape(flag)} · <a href="{html.escape(m.screening.url)}">tickets / info</a></li>'
            )
        text_lines.append("")
        html_parts.append(
            f'<h3><a href="{html.escape(f.url)}">{html.escape(label)}</a></h3><ul>{"".join(rows)}</ul>'
        )
    return subject, "\n".join(text_lines), "".join(html_parts)


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
