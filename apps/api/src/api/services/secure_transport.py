import httpcore
import httpx

from api.services.connection_security import PublicOnlyNetworkBackend


class SecureAsyncHTTPTransport(httpx.AsyncHTTPTransport):
    """HTTPX transport that validates DNS addresses before connecting."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        pool = self._pool

        if not isinstance(pool, httpcore.AsyncConnectionPool):
            raise ValueError("Secure transport does not support proxies")

        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=pool._ssl_context,
            max_connections=pool._max_connections,
            max_keepalive_connections=pool._max_keepalive_connections,
            keepalive_expiry=pool._keepalive_expiry,
            http1=pool._http1,
            http2=pool._http2,
            retries=pool._retries,
            local_address=pool._local_address,
            socket_options=pool._socket_options,
            network_backend=PublicOnlyNetworkBackend(),
        )