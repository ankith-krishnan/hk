import pytest
from pydantic import ValidationError

from app.config import Settings, is_loopback_url


def test_offline_mode_accepts_only_loopback_vlm_urls():
    assert is_loopback_url("http://127.0.0.1:8000/v1")
    assert is_loopback_url("http://localhost:8000/v1")
    assert is_loopback_url("http://[::1]:8000/v1")
    assert not is_loopback_url("https://api.example.com/v1")
    assert not is_loopback_url("http://user:password@127.0.0.1:8000/v1")
    assert not is_loopback_url("http://127.0.0.1:8000/v1?token=secret")
    assert not is_loopback_url("http://localhost.example.com/v1")
    with pytest.raises(ValidationError):
        Settings(vlm_base_url="https://api.example.com/v1", offline_mode=True)

