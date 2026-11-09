from fastapi.testclient import TestClient

HEALTH_URL = "/api/v1/health"
FRONTEND_ORIGIN = "http://localhost:5173"


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get(HEALTH_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["uptime_seconds"] >= 0


def test_security_headers_present(client: TestClient) -> None:
    response = client.get(HEALTH_URL)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_cors_allows_frontend_origin(client: TestClient) -> None:
    response = client.options(
        HEALTH_URL,
        headers={"Origin": FRONTEND_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get(HEALTH_URL, headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
