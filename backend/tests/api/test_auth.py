def test_login_success(client, test_admin):
    login_data = {
        "username": "test@admin.com",
        "password": "testpassword",
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    assert r.status_code == 200
    assert "access_token" in r.json()

def test_login_invalid_password(client, test_admin):
    login_data = {
        "username": "test@admin.com",
        "password": "wrongpassword",
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    assert r.status_code == 401
    assert r.json()["detail"] == "Incorrect email or password"

def test_login_unknown_admin(client):
    login_data = {
        "username": "nobody@admin.com",
        "password": "password",
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    assert r.status_code == 401

def test_read_me_success(client, admin_token_headers, test_admin):
    r = client.get("/api/v1/auth/me", headers=admin_token_headers)
    assert r.status_code == 200
    assert r.json()["success"] == True
    assert r.json()["data"]["email"] == test_admin.email

def test_read_me_unauthorized(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
