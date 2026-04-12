from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    """Smoke test for CI and local checks.

    TODO: Add API contract assertions for response envelope and schema details.
    """

    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "ok"
