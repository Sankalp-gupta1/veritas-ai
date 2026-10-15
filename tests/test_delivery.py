"""Deployment-shell freshness must not depend on a previous build's timestamps."""

from importlib import import_module

from fastapi.testclient import TestClient


def test_shell_reloads_current_assets_even_with_conditional_headers(tmp_path, monkeypatch):
    main = import_module("app.main")
    monkeypatch.setattr(main, "frontend", tmp_path)
    index = tmp_path / "index.html"
    index.write_text('<html><script src="/assets/old.js"></script></html>')
    client = TestClient(main.app)
    before = client.get("/")
    assert before.status_code == 200
    index.write_text('<html><script src="/assets/new.js"></script></html>')
    for path in ("/", "/index.html"):
        after = client.get(
            path,
            headers={
                "If-None-Match": before.headers["etag"],
                "If-Modified-Since": before.headers["last-modified"],
            },
        )
        assert after.status_code == 200
        assert "/assets/new.js" in after.text
        assert "no-store" in after.headers["cache-control"]
