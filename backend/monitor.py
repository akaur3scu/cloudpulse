from datetime import datetime, timezone
from time import perf_counter

import requests


def check_endpoint(url: str) -> dict:
    """Check an HTTP endpoint and return its status and response time."""

    start_time = perf_counter()

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "CloudPulse/1.0"},
        )

        response_time_ms = round(
            (perf_counter() - start_time) * 1000,
            2,
        )

        return {
            "url": url,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "online" if response.ok else "error",
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
        }

    except requests.RequestException as error:
        return {
            "url": url,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "status": "offline",
            "status_code": None,
            "response_time_ms": None,
            "error": str(error),
        }


if __name__ == "__main__":
    result = check_endpoint("https://www.scu.edu")
    print(result)

print(check_endpoint("https://github.com"))
#print(check_endpoint("https://httpstat.us/503"))