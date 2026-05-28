from __future__ import annotations


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_root_endpoint_returns_service_metadata(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json()["service"] == "ProfitPilot Backend"


def test_metrics_endpoint_exposes_prometheus_text(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.mimetype.startswith("text/plain")
    assert b"python_info" in response.data
