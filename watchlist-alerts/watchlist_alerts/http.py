"""Shared HTTP session with a descriptive User-Agent and retries."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "nyc-watchlist-alerts/0.1 (personal daily check; "
    "+https://github.com/nick-tygesen/nick-tygesen.github.io)"
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
_session.mount(
    "https://",
    HTTPAdapter(max_retries=Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])),
)


def get(url: str, **kwargs) -> str:
    resp = _session.get(url, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.text


def get_json(url: str, **kwargs):
    resp = _session.get(url, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp.json()
