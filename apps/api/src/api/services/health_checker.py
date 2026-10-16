
import time

import httpx


async def check_url(url: str):
    timeout = httpx.Timeout(10.0)

    # Start measuring before sending the request.
    start_time = time.perf_counter()

    async with httpx.AsyncClient(
        timeout=timeout,follow_redirects=True,) as client:
        try:
            response = await client.get(url)

            # Calculate elapsed time in milliseconds.
            response_time_ms = round(
                (time.perf_counter() - start_time) * 1000
            )

            return {
                "status": "UP",
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
                "error": None,
            }

        except httpx.TimeoutException:
            response_time_ms = round(
                (time.perf_counter() - start_time) * 1000
            )

            return {
                "status": "DOWN",
                "status_code": None,
                "response_time_ms": response_time_ms,
                "error": "Request timed out",
            }

        except httpx.RequestError as error:
            response_time_ms = round(
                (time.perf_counter() - start_time) * 1000
            )

            return {
                "status": "DOWN",
                "status_code": None,
                "response_time_ms": response_time_ms,
                "error": str(error),
            }