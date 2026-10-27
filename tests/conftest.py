import base64

import pytest


@pytest.fixture(autouse=True)
def test_vault_key(monkeypatch):
    # Public fixture key, for disposable tests only. Never a deployment key.
    monkeypatch.setenv("VERITAS_VAULT_KEY", base64.b64encode(bytes(range(32))).decode())
