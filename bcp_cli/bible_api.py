from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .errors import usage_error

API_ROOT = "https://bible-api.com"


def passage_url(ref: str) -> str:
    encoded = urllib.parse.quote(ref)
    query = urllib.parse.urlencode(
        {
            "translation": "kjv",
            "single_chapter_book_matching": "indifferent",
        }
    )
    return f"{API_ROOT}/{encoded}?{query}"


def fetch_passage(ref: str) -> dict:
    request = urllib.request.Request(
        passage_url(ref),
        headers={"User-Agent": "bcp-cli-prototype/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        usage_error(f"Could not fetch KJV text for {ref!r}: {exc}")

