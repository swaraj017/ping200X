
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    """Raised when a URL targets a prohibited destination."""


def validate_url(url: str) -> str:
    """Validate URL syntax and reject non-public IP destinations."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            raise UnsafeURLError("Only HTTP and HTTPS URLs are allowed")

        if not parsed.hostname:
            raise UnsafeURLError("URL must contain a hostname")

        if parsed.username is not None or parsed.password is not None:
            raise UnsafeURLError("URLs containing credentials are not allowed")

        hostname = parsed.hostname.rstrip(".")
        if hostname.lower() == "localhost" or hostname.lower().endswith(".localhost"):
            raise UnsafeURLError("Localhost URLs are not allowed")

        try:
            addresses = [ipaddress.ip_address(hostname)]
        except ValueError:
            try:
                records = socket.getaddrinfo(
                    hostname,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            except socket.gaierror as exc:
                raise UnsafeURLError("Hostname could not be resolved") from exc

            addresses = [
                ipaddress.ip_address(record[4][0])
                for record in records
            ]

        if not addresses:
            raise UnsafeURLError("Hostname has no resolved IP addresses")

        if any(not address.is_global for address in addresses):
            raise UnsafeURLError(
                "URLs resolving to non-public IP addresses are not allowed"
            )

        return url
    except UnsafeURLError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise UnsafeURLError("Invalid URL") from exc
