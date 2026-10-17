
import asyncio
import ipaddress
import socket

import httpcore
from httpcore._backends.auto import AutoBackend


class UnsafeAddressError(httpcore.ConnectError):
    """Raised when a connection targets a prohibited IP address."""


class PublicOnlyNetworkBackend:
    """Resolve, validate, and connect directly to public IP addresses."""

    def __init__(self):
        self._backend = AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options=None,
    ):
        try:
            loop = asyncio.get_running_loop()
            records = await asyncio.wait_for(
                loop.getaddrinfo(
                    host,
                    port,
                    type=socket.SOCK_STREAM,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            raise httpcore.ConnectTimeout(
                "DNS resolution timed out"
            ) from exc
        except OSError as exc:
            raise httpcore.ConnectError(
                "Hostname could not be resolved"
            ) from exc

        addresses = {
            ipaddress.ip_address(record[4][0].split("%", 1)[0])
            for record in records
        }

        if not addresses:
            raise httpcore.ConnectError(
                "Hostname has no resolved IP addresses"
            )

        # Reject mixed public/private DNS responses too.
        if any(not address.is_global for address in addresses):
            raise UnsafeAddressError(
                "Connection to non-public IP addresses is prohibited"
            )

        last_error = None

        # Connect directly to a validated IP address.
        for address in sorted(
            addresses,
            key=lambda item: (item.version, int(item)),
        ):
            try:
                return await self._backend.connect_tcp(
                    host=str(address),
                    port=port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        raise httpcore.ConnectError(
            "No usable public IP address found"
        )

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options=None,
    ):
        """Reject Unix-domain socket connections."""
        raise UnsafeAddressError(
            "Unix-domain socket connections are prohibited"
        )

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)
