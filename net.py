"""
HTTP - one place that knows how to fetch a URL.

WHY THIS EXISTS
    macOS Python does not read the system keychain, so HTTPS requests fail with
    CERTIFICATE_VERIFY_FAILED even though curl works fine. The fix is to point
    Python at certifi's CA bundle.

    The wrong fix is ssl._create_unverified_context(), which silently turns off
    certificate checking. That would make every request vulnerable to
    interception - unacceptable in an app that will later carry a session
    cookie and portfolio data.

    Putting it here means every request in the project gets the same correct
    settings: verified TLS, a real User-Agent, and a timeout.
"""
from __future__ import annotations

import ssl
import urllib.request

import certifi

from config import HTTP_TIMEOUT_SECONDS, USER_AGENT

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def fetch(url: str, timeout: int | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(
        request, timeout=timeout or HTTP_TIMEOUT_SECONDS, context=_SSL_CONTEXT
    ) as response:
        return response.read()


def fetch_text(url: str, timeout: int | None = None) -> str:
    return fetch(url, timeout).decode("utf-8", errors="replace")
