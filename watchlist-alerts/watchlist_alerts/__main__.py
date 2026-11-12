"""Daily run: watchlist x NYC theater schedules -> email new matches.

Usage: python -m watchlist_alerts [--user NAME] [--days N] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from . import letterboxd
from .matching import find_matches, make_prefilter
from .notify import build_email, send_email
from .venues import NYC, VENUES

STATE = Path(__file__).resolve().parent.parent / "state" / "seen.json"


def load_seen() -> dict[str, str]:
    try:
        return json.loads(STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_seen(seen: dict[str, str]) -> None:
    # Forget entries older than 60 days so the file stays small.
    cutoff = (date.today() - timedelta(days=60)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(dict(sorted(seen.items())), indent=1) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="nicktygesen")
    ap.add_argument("--days", type=int, default=14, help="how far ahead to look")
    ap.add_argument("--dry-run", action="store_true", help="print instead of emailing; don't update state")
    args = ap.parse_args()

    missing = [k for k in ("SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO") if not os.environ.get(k)]
    if missing and not args.dry_run:
        print(f"::error::Missing email settings: {', '.join(missing)}. Add them as repository secrets "
              "(Settings -> Secrets and variables -> Actions); see watchlist-alerts/README.md.", file=sys.stderr)
        return 1

    films = letterboxd.fetch_watchlist(args.user)
    print(f"Watchlist: {len(films)} films")
    if not films:
        print("Watchlist came back empty (private account or page change?)", file=sys.stderr)
        return 1

    want = make_prefilter(films)
    screenings, failures = [], []
    for venue in VENUES:
        try:
            got = venue.fetch(args.days, want)
            print(f"{venue.NAME}: {len(got)} screenings")
            screenings += got
        except Exception as e:  # one broken site shouldn't stop the others
            failures.append(venue.NAME)
            print(f"{venue.NAME}: FAILED ({e!r})", file=sys.stderr)

    now = datetime.now(NYC)
    screenings = [s for s in screenings if s.start is None or s.start > now]
    seen = load_seen()
    new = [m for m in find_matches(films, screenings) if m.screening.key not in seen]
    print(f"New matches: {len(new)}")

    if new:
        if args.dry_run:
            print("\n".join(build_email(new)[:2]))
        else:
            send_email(new)
            today = date.today().isoformat()
            for m in new:
                seen[m.screening.key] = today
    if not args.dry_run:
        save_seen(seen)

    # Fail the run (so GitHub emails you) only if every venue broke.
    return 1 if VENUES and len(failures) == len(VENUES) else 0


if __name__ == "__main__":
    sys.exit(main())
