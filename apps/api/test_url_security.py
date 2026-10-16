
import pytest

from api.services.url_security import (
    UnsafeURLError,
    validate_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254",
        "file:///etc/passwd",
        "http://user:password@example.com",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_rejects_invalid_scheme():
    with pytest.raises(UnsafeURLError):
        validate_url("ftp://example.com")
