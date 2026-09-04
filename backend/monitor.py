"""HTTP endpoint validation and monitoring utilities."""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime, timezone
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_url(url: str, *, resolve_dns: bool = True) -> str:
    """Return a normalized public HTTP(S) URL or raise ValueError."""
    candidate = url.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a complete HTTP or HTTPS URL.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not supported.")

    if resolve_dns:
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(parsed.hostname, parsed.port)
            }
        except socket.gaierror as error:
            raise ValueError("The hostname could not be resolved.") from error
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("Only public internet endpoints can be monitored.")
    return parsed.geturl()


def check_endpoint(url: str, timeout: float = 10) -> dict:
    """Check an HTTP endpoint and return a JSON-serializable result."""
    checked_at = utc_now()
    try:
        normalized_url = validate_url(url)
    except ValueError as error:
        return {
            "url": url,
            "checked_at": checked_at,
            "status": "offline",
            "status_code": None,
            "response_time_ms": None,
            "error": str(error),
        }

    start_time = perf_counter()
    request = Request(
        normalized_url,
        headers={"User-Agent": "CloudPulse/1.0"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = response.status
        response_time_ms = round((perf_counter() - start_time) * 1000, 2)
        return {
            "url": normalized_url,
            "checked_at": checked_at,
            "status": "online" if status_code < 400 else "offline",
            "status_code": status_code,
            "response_time_ms": response_time_ms,
        }
    except HTTPError as error:
        response_time_ms = round((perf_counter() - start_time) * 1000, 2)
        return {
            "url": normalized_url,
            "checked_at": checked_at,
            "status": "offline",
            "status_code": error.code,
            "response_time_ms": response_time_ms,
            "error": f"HTTP {error.code}",
        }
    except (URLError, TimeoutError, OSError) as error:
        return {
            "url": normalized_url,
            "checked_at": checked_at,
            "status": "offline",
            "status_code": None,
            "response_time_ms": None,
            "error": str(error),
        }


if __name__ == "__main__":
    print(check_endpoint("https://example.com"))
