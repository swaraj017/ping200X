import socket
from unittest.mock import patch

import httpx
import pytest

from api.services.connection_security import UnsafeAddressError
from api.services.secure_transport import SecureAsyncHTTPTransport


def dns_record(ip: str):
    return (
        socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (ip, 80),
    )


@pytest.mark.asyncio
async def test_secure_transport_rejects_hostname_resolving_to_private_ip():
    transport = SecureAsyncHTTPTransport(trust_env=False)

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        return_value=[dns_record("127.0.0.1")],
    ):
        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            timeout=2.0,
        ) as client:
            with pytest.raises(httpx.RequestError) as exc_info:
                await client.get("http://example.test")

    error = exc_info.value
    assert isinstance(error.__cause__, UnsafeAddressError) or isinstance(
        error.__context__, UnsafeAddressError
    )

@pytest.mark.asyncio
async def test_secure_transport_rejects_private_dns_for_https():
    transport = SecureAsyncHTTPTransport(trust_env=False)

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        return_value=[dns_record("127.0.0.1")],
    ):
        async with httpx.AsyncClient(
            transport=transport,
            trust_env=False,
            timeout=2.0,
        ) as client:
            with pytest.raises(httpx.RequestError) as exc_info:
                await client.get("https://example.test")

    error = exc_info.value
    assert isinstance(error.__cause__, UnsafeAddressError) or isinstance(
        error.__context__, UnsafeAddressError
    )