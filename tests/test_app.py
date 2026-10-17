from datetime import date

from fastapi.testclient import TestClient

from benchmark import app as app_module
from tests.test_pipeline import make_bundle


def client_with_bundle(tmp_path, monkeypatch):
    bundle, _ = make_bundle(tmp_path)
    monkeypatch.setattr(app_module, "RUNS_DIR", tmp_path / "runs")
    return TestClient(app_module.app, base_url="http://127.0.0.1"), bundle


def test_page_and_bundle_served(tmp_path, monkeypatch):
    client, bundle = client_with_bundle(tmp_path, monkeypatch)
    assert "Peer benchmark" in client.get("/").text
    data = client.get("/api/bundle").json()
    assert data["as_of"] == "2025-12-31"
    assert data["table"]["nav_per_share"]["TAKIX"]["value"] == "8.32"


def test_export_returns_xlsx(tmp_path, monkeypatch):
    client, _ = client_with_bundle(tmp_path, monkeypatch)
    resp = client.get("/api/export.xlsx")
    assert resp.status_code == 200 and resp.content[:2] == b"PK"


def test_run_starts_in_background_and_reports_status(tmp_path, monkeypatch):
    client, _ = client_with_bundle(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(app_module.pipeline, "run", lambda as_of, progress, **kw: calls.append(as_of) or progress("Done."))
    assert client.post("/api/run", json={"as_of": "2025-09-30"}).status_code == 202
    app_module.RUNNER.thread.join(timeout=5)
    assert calls == [date(2025, 9, 30)]
    assert client.get("/api/status").json()["running"] is False


def test_run_rejects_a_date_that_is_not_a_quarter_end(tmp_path, monkeypatch):
    client, _ = client_with_bundle(tmp_path, monkeypatch)
    assert client.post("/api/run", json={"as_of": "2025-11-15"}).status_code == 400


def test_requests_with_a_foreign_host_header_are_refused(tmp_path, monkeypatch):
    # DNS rebinding: a web page that resolves its own domain to 127.0.0.1 must not reach the API.
    client, _ = client_with_bundle(tmp_path, monkeypatch)
    assert client.get("/api/bundle", headers={"host": "evil.example"}).status_code == 400
