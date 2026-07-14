def test_register_creates_user_and_returns_token(client):
    resp = client.post(
        "/auth/register", json={"email": "a@example.com", "password": "pw123"}
    )
    assert resp.status_code == 201
    assert "access_token" in resp.get_json()


def test_register_duplicate_email_returns_409(client, register_user):
    register_user(email="dupe@example.com")
    resp = register_user(email="dupe@example.com")
    assert resp.status_code == 409


def test_login_with_correct_credentials_returns_token(client, register_user):
    register_user(email="b@example.com", password="pw123")
    resp = client.post(
        "/auth/login", json={"email": "b@example.com", "password": "pw123"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_with_wrong_password_returns_401(client, register_user):
    register_user(email="c@example.com", password="pw123")
    resp = client.post(
        "/auth/login", json={"email": "c@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_with_unknown_email_returns_401(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "pw123"}
    )
    assert resp.status_code == 401


def test_me_requires_auth(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, auth_headers):
    headers = auth_headers(email="d@example.com")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "d@example.com"


def test_soft_delete_me_requires_auth(client):
    resp = client.delete("/auth/me")
    assert resp.status_code == 401


def test_soft_delete_me_returns_204(client, auth_headers):
    headers = auth_headers(email="e@example.com")
    resp = client.delete("/auth/me", headers=headers)
    assert resp.status_code == 204


def test_login_after_soft_delete_returns_401(client, auth_headers):
    headers = auth_headers(email="f@example.com", password="pw123")
    client.delete("/auth/me", headers=headers)

    resp = client.post(
        "/auth/login", json={"email": "f@example.com", "password": "pw123"}
    )
    assert resp.status_code == 401


def test_soft_deleted_users_existing_token_still_works_for_me(client, auth_headers):
    # ponytail note in auth.py: no blocklist, so a token issued before the
    # delete stays valid until it naturally expires.
    headers = auth_headers(email="g@example.com")
    client.delete("/auth/me", headers=headers)

    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
