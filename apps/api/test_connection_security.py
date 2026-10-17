
import asyncio
import socket
from unittest.mock import AsyncMock, patch

import httpcore
import pytest

from api.services.connection_security import (
    PublicOnlyNetworkBackend,
    UnsafeAddressError,
)


def dns_record(ip: str):
    return (
        socket.AF_INET6 if ":" in ip else socket.AF_INET,
        socket.SOCK_STREAM,
        socket.IPPROTO_TCP,
        "",
        (ip, 443, 0, 0) if ":" in ip else (ip, 443),
    )


@pytest.mark.asyncio
async def test_private_dns_address_is_rejected():
    backend = PublicOnlyNetworkBackend()

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        return_value=[dns_record("192.168.1.10")],
    ):
        with pytest.raises(UnsafeAddressError):
            await backend.connect_tcp("example.com", 443)


@pytest.mark.asyncio
async def test_mixed_public_and_private_dns_is_rejected():
    backend = PublicOnlyNetworkBackend()

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        return_value=[
            dns_record("8.8.8.8"),
            dns_record("192.168.1.10"),
        ],
    ):
        with pytest.raises(UnsafeAddressError):
            await backend.connect_tcp("example.com", 443)


@pytest.mark.asyncio
async def test_public_dns_connects_to_validated_ip():
    backend = PublicOnlyNetworkBackend()
    stream = object()

    with (
        patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            return_value=[dns_record("8.8.8.8")],
        ),
        patch.object(
            backend._backend,
            "connect_tcp",
            new_callable=AsyncMock,
            return_value=stream,
        ) as connect,
    ):
        result = await backend.connect_tcp("example.com", 443)

    assert result is stream
    assert connect.await_args.kwargs["host"] == "8.8.8.8"


@pytest.mark.asyncio
async def test_loopback_dns_address_is_rejected():
    backend = PublicOnlyNetworkBackend()

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        return_value=[dns_record("127.0.0.1")],
    ):
        with pytest.raises(UnsafeAddressError):
            await backend.connect_tcp("example.com", 443)


@pytest.mark.asyncio
async def test_dns_resolution_timeout():
    backend = PublicOnlyNetworkBackend()

    async def slow_dns(*args, **kwargs):
        await asyncio.sleep(0.1)
        return [dns_record("8.8.8.8")]

    with patch(
        "asyncio.BaseEventLoop.getaddrinfo",
        side_effect=slow_dns,
    ):
        with pytest.raises(httpcore.ConnectTimeout):
            await backend.connect_tcp(
                "example.com",
                443,
                timeout=0.01,
            )
