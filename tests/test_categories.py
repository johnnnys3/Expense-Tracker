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


def test_rename_category_requires_auth(client):
    resp = client.patch("/categories/1", json={"name": "New"})
    assert resp.status_code == 401


def test_rename_category(client, auth_headers):
    headers = auth_headers()
    created = client.post("/categories", headers=headers, json={"name": "Groceries"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers, json={"name": "Food"})
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Food"


def test_rename_category_not_owned_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    created = client.post("/categories", headers=headers_a, json={"name": "Rent"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers_b, json={"name": "X"})
    assert resp.status_code == 404


def test_rename_category_to_duplicate_name_returns_409(client, auth_headers):
    headers = auth_headers()
    client.post("/categories", headers=headers, json={"name": "Rent"})
    created = client.post("/categories", headers=headers, json={"name": "Utilities"})
    cat_id = created.get_json()["id"]

    resp = client.patch(f"/categories/{cat_id}", headers=headers, json={"name": "Rent"})
    assert resp.status_code == 409
