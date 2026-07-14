def test_create_category_requires_auth(client):
    resp = client.post("/categories", json={"name": "Groceries"})
    assert resp.status_code == 401


def test_create_category(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/categories", headers=headers, json={"name": "Groceries"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Groceries"
    assert "id" in body


def test_create_duplicate_category_for_same_user_returns_409(client, auth_headers):
    headers = auth_headers()
    client.post("/categories", headers=headers, json={"name": "Groceries"})
    resp = client.post("/categories", headers=headers, json={"name": "Groceries"})
    assert resp.status_code == 409


def test_same_category_name_allowed_for_different_users(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    resp_a = client.post("/categories", headers=headers_a, json={"name": "Rent"})
    resp_b = client.post("/categories", headers=headers_b, json={"name": "Rent"})
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201


def test_list_categories_requires_auth(client):
    resp = client.get("/categories")
    assert resp.status_code == 401


def test_list_categories_only_returns_own(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    client.post("/categories", headers=headers_a, json={"name": "Rent"})
    client.post("/categories", headers=headers_b, json={"name": "Utilities"})

    resp = client.get("/categories", headers=headers_a)
    names = [c["name"] for c in resp.get_json()]
    assert names == ["Rent"]
