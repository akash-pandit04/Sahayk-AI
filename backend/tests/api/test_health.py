def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "API is operational"}}

def test_db_health_check(client):
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "Database is connected and operational"}}
