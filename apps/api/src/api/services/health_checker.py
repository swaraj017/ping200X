
import time
from urllib.parse import urljoin

import httpx

from api.services.secure_transport import SecureAsyncHTTPTransport
from api.services.url_security import UnsafeURLError, validate_url


MAX_REDIRECTS = 5
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


async def check_url(url: str):
    timeout = httpx.Timeout(10.0)
    start_time = time.perf_counter()
    current_url = url
    redirects_followed = 0

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=SecureAsyncHTTPTransport(
                trust_env=False,
            ),
        ) as client:
            while True:
                # Validate every destination, including redirects.
                validate_url(current_url)

                response = await client.get(current_url)

                if response.status_code not in REDIRECT_STATUSES:
                    return {
                        "status": "UP",
                        "status_code": response.status_code,
                        "response_time_ms": round(
                            (time.perf_counter() - start_time) * 1000
                        ),
                        "error": None,
                    }

                location = response.headers.get("location")

                # A redirect without a Location header is just
                # the HTTP response we received.
                if not location:
                    return {
                        "status": "UP",
                        "status_code": response.status_code,
                        "response_time_ms": round(
                            (time.perf_counter() - start_time) * 1000
                        ),
                        "error": None,
                    }

                if redirects_followed >= MAX_REDIRECTS:
                    raise UnsafeURLError("Too many redirects")

                current_url = urljoin(current_url, location)
                redirects_followed += 1

    except httpx.TimeoutException:
        error = "Request timed out"
    except UnsafeURLError as exc:
        error = str(exc)
    except httpx.RequestError as exc:
        error = str(exc)

    return {
        "status": "DOWN",
        "status_code": None,
        "response_time_ms": round(
            (time.perf_counter() - start_time) * 1000
        ),
        "error": error,
    }
