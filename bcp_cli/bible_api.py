from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

from .errors import runtime_error

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
        headers={"User-Agent": "daily-bcp/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        reason = exc.reason
        message = f"Could not fetch KJV text for {ref!r}: {exc}"
        if isinstance(reason, ssl.SSLCertVerificationError):
            message += (
                "\n\nHTTPS certificate verification failed. On macOS with Python from "
                "python.org, run the matching `Install Certificates.command` from "
                "`/Applications/Python 3.x/`, then reinstall or retry daily-bcp."
            )
        runtime_error(message)
    except Exception as exc:
        runtime_error(f"Could not fetch KJV text for {ref!r}: {exc}")
