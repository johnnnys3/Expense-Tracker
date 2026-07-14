def test_register_missing_fields_returns_400(client):
    resp = client.post("/auth/register", json={"email": "a@example.com"})
    assert resp.status_code == 400
    assert "password" in resp.get_json()["error"]


def test_register_no_body_returns_400(client):
    resp = client.post("/auth/register", content_type="application/json", data="")
    assert resp.status_code == 400


def test_login_missing_fields_returns_400(client):
    resp = client.post("/auth/login", json={"email": "a@example.com"})
    assert resp.status_code == 400


def test_create_category_missing_name_returns_400(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/categories", headers=headers, json={})
    assert resp.status_code == 400


def test_create_transaction_missing_fields_returns_400(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/transactions", headers=headers, json={"amount": "5.00"})
    assert resp.status_code == 400
    assert "category_id" in resp.get_json()["error"]
    assert "occurred_at" in resp.get_json()["error"]
