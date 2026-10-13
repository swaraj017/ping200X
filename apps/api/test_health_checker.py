
import httpx
import pytest
import respx

from api.services.health_checker import check_url


@pytest.mark.asyncio
@respx.mock
async def test_successful_check():
    respx.get("https://example.com").mock(
        return_value=httpx.Response(200)
    )

    result = await check_url("https://example.com")

    assert result["status"] == "UP"
    assert result["status_code"] == 200
    assert result["response_time_ms"] >= 0
    assert result["error"] is None


@pytest.mark.asyncio
@respx.mock

@pytest.mark.asyncio
@respx.mock
async def test_redirect_is_followed():
    calls = 0

    def redirect_callback(request):
        nonlocal calls
        calls += 1

        if calls == 1:
            return httpx.Response(
                301,
                headers={"Location": "https://example.com/final"},
                request=request,
            )

        return httpx.Response(200, request=request)

    respx.get("https://example.com/").mock(
        side_effect=redirect_callback
    )
    respx.get("https://example.com/final").mock(
        side_effect=redirect_callback
    )

    result = await check_url("https://example.com/")

    assert result["status"] == "UP"
    assert result["status_code"] == 200
@pytest.mark.asyncio
@respx.mock
async def test_connection_failure():
    respx.get("https://example.com").mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

    result = await check_url("https://example.com")

    assert result["status"] == "DOWN"
    assert result["status_code"] is None
    assert result["response_time_ms"] >= 0
    assert result["error"] is not None