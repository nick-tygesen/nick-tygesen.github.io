"""Shared HTTP session: descriptive User-Agent, retries, and a per-host delay."""

from __future__ import annotations

import time
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "nyc-watchlist-alerts/0.1 (personal daily check; "
    "+https://github.com/nick-tygesen/nick-tygesen.github.io)"
)
MIN_INTERVAL = 0.75  # seconds between requests to the same host

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
_session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])),
)
_last_hit: dict[str, float] = {}


def _fetch(url: str, **kwargs) -> requests.Response:
    host = urlsplit(url).netloc
    wait = _last_hit.get(host, 0) + MIN_INTERVAL - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    try:
        resp = _session.get(url, timeout=30, **kwargs)
    finally:
        _last_hit[host] = time.monotonic()
    resp.raise_for_status()
    return resp


def get(url: str, **kwargs) -> str:
    return _fetch(url, **kwargs).text


def get_json(url: str, **kwargs):
    return _fetch(url, **kwargs).json()
