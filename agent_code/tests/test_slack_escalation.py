from __future__ import annotations

import json
from pathlib import Path


class FakeGitHubResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_slack_event_blueprint_is_registered_on_active_app(client, monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)

    response = client.post("/slack/events", json={"type": "event_callback"})

    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "warning": "slack not configured"}


def test_employees_endpoint_returns_github_contributors(client, app_module, monkeypatch, tmp_path):
    counts_path = tmp_path / "assigned_issues.json"
    counts_path.write_text(json.dumps({"alice": 2}), encoding="utf-8")
    monkeypatch.setattr(app_module, "ASSIGNMENTS_FILE", counts_path)
    monkeypatch.setenv("GITHUB_REPO", "example/profitpilot")

    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeGitHubResponse(
            200,
            [
                {"login": "alice", "avatar_url": "https://example.test/alice.png"},
                {"login": "bob", "avatar_url": ""},
            ],
        )

    monkeypatch.setattr(app_module.requests, "get", fake_get)

    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    assert response.get_json() == {
        "employees": [
            {
                "login": "alice",
                "avatar_url": "https://example.test/alice.png",
                "assigned_issues": 2,
            },
            {"login": "bob", "avatar_url": "", "assigned_issues": 0},
        ],
        "source": "github",
    }
    assert captured["url"] == "https://api.github.com/repos/example/profitpilot/contributors"
    assert captured["timeout"] == 20


def test_employees_endpoint_falls_back_when_github_is_unavailable(client, app_module, monkeypatch, tmp_path):
    counts_path = tmp_path / "assigned_issues.json"
    counts_path.write_text(json.dumps({"engineer_b": 3}), encoding="utf-8")
    monkeypatch.setattr(app_module, "ASSIGNMENTS_FILE", counts_path)
    monkeypatch.setenv("ESCALATION_FALLBACK_EMPLOYEES", "engineer_a,engineer_b")

    def fake_get(*args, **kwargs):
        raise app_module.requests.Timeout("github timeout")

    monkeypatch.setattr(app_module.requests, "get", fake_get)

    response = client.get("/api/v1/employees")

    assert response.status_code == 200
    assert response.get_json() == {
        "employees": [
            {"login": "engineer_a", "avatar_url": "", "assigned_issues": 0},
            {"login": "engineer_b", "avatar_url": "", "assigned_issues": 3},
        ],
        "source": "fallback",
    }


def test_escalate_requires_query_or_summary(client):
    response = client.post("/api/v1/escalate", json={})

    assert response.status_code == 400
    assert response.get_json() == {"error": "Either query or summary is required"}


def test_escalate_returns_service_error_when_slack_is_not_configured(client, app_module, monkeypatch):
    class FakeDelivery:
        client = None
        demo_channel_id = ""

        def configured(self):
            return False

    monkeypatch.setattr(app_module, "_load_slack_delivery", lambda: FakeDelivery())

    response = client.post(
        "/api/v1/escalate",
        json={"query": "Need a human review", "summary": "The answer was incomplete."},
    )

    assert response.status_code == 503
    assert response.get_json() == {"error": "Slack is not configured. Set SLACK_BOT_TOKEN first."}


def test_escalate_posts_to_slack_and_tracks_selected_assignee(client, app_module, monkeypatch, tmp_path):
    counts_path = tmp_path / "assigned_issues.json"
    counts_path.write_text(json.dumps({"alice": 1}), encoding="utf-8")
    monkeypatch.setattr(app_module, "ASSIGNMENTS_FILE", Path(counts_path))

    class FakeSlackClient:
        def __init__(self):
            self.messages = []

        def chat_postMessage(self, **kwargs):
            self.messages.append(kwargs)
            return {"ok": True}

    fake_client = FakeSlackClient()

    class FakeDelivery:
        client = fake_client
        demo_channel_id = "C123"

        def configured(self):
            return True

    monkeypatch.setattr(app_module, "_load_slack_delivery", lambda: FakeDelivery())

    response = client.post(
        "/api/v1/escalate",
        json={
            "query": "Why did revenue drop?",
            "summary": "The assistant found a steep revenue decline.",
            "assignee_name": "alice",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "assignee": "alice", "auto_assigned": False}
    assert json.loads(counts_path.read_text(encoding="utf-8")) == {"alice": 2}
    assert fake_client.messages[0]["channel"] == "C123"
    assert fake_client.messages[0]["text"] == "Web Chatbot Escalation"
    assert "Why did revenue drop?" in fake_client.messages[0]["blocks"][1]["text"]["text"]
