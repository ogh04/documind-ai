def test_health_check_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "documind-ai-backend"


def test_database_health_check_returns_ok(client):
    response = client.get("/db-health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["service"] == "postgresql"