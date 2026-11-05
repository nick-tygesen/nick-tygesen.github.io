# NYC watchlist alerts

Once a day, a GitHub Action reads the public Letterboxd watchlist for
[nicktygesen](https://letterboxd.com/nicktygesen/watchlist/) and checks it against
NYC theater schedules. It sends one email listing any new screenings of watchlist films.

## How it works

| Step | Code |
| --- | --- |
| Read every watchlist page (title, year, Letterboxd link) | `watchlist_alerts/letterboxd.py` |
| Pull the next 14 days of screenings from each theater | `watchlist_alerts/venues/` |
| Match by normalized title, checked against the year when the theater lists it | `watchlist_alerts/matching.py` |
| Email new matches only | `watchlist_alerts/notify.py`, `state/seen.json` |

Matching rules:

- Titles are normalized: case, accents, "The/A/An", "&" and tags like "(35mm)" or "(4K Restoration)" are ignored.
- A year difference of ±1 is allowed.
- If the theater gives no year, the alert says "year not confirmed". If two watchlist films share that title, no alert is sent.

## Theaters

| Theater | Source | Year check | Look-ahead |
| --- | --- | --- | --- |
| Film Forum | `/now_playing` tabs + film page | yes | 7 days |
| Metrograph | `/nyc/` calendar | yes | ~3 weeks |
| IFC Center | homepage schedule + film page | yes | 7 days |
| BAM | `/film` list + film page + BAM's performances JSON | yes | 14 days |
| Quad Cinema | homepage day grids + film page | yes | 7 days |
| Nitehawk (Williamsburg, Prospect Park) | schema.org data on homepage, coming-soon and film pages | yes | 14 days |
| Paris Theater | film records embedded in the homepage | yes | run dates only, no showtimes |

Detail pages are only fetched for films whose title might be on the watchlist.
Requests are spaced 0.75s apart per site and identify themselves with a descriptive User-Agent.

Not included, because they block automated requests or redirect off the allowed list:
Film at Lincoln Center, MoMA, Museum of the Moving Image (Cloudflare bot checks), Screen Slate (same),
Anthology Film Archives and Roxy Cinema (not yet tried at their new domains).

To add a theater, write a module in `watchlist_alerts/venues/` with `NAME` and
`fetch(days, want)`, then add it to `_load()` in `venues/__init__.py`.

## Setup (one time)

1. Create a Gmail **app password**: Google Account → Security → 2-Step Verification → App passwords.
2. In this repo, go to **Settings → Secrets and variables → Actions** and add:
   - `SMTP_USER`: your Gmail address
   - `SMTP_PASSWORD`: the app password
   - `EMAIL_TO`: where alerts should go
3. Keep the Letterboxd watchlist public.
4. Test it: **Actions → NYC watchlist alerts → Run workflow**, with "dry run" ticked.

## Run locally

```sh
cd watchlist-alerts
pip install -r requirements.txt
python -m watchlist_alerts --dry-run          # print matches, don't email
python -m pytest -q                           # tests
```
