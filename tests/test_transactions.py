import pytest


@pytest.fixture()
def category_id(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/categories", headers=headers, json={"name": "Groceries"})
    return resp.get_json()["id"]


def _create_txn(client, headers, category_id, **overrides):
    payload = {
        "category_id": category_id,
        "amount": "12.50",
        "occurred_at": "2026-01-15",
        "description": "Weekly shop",
    }
    payload.update(overrides)
    return client.post("/transactions", headers=headers, json=payload)


def test_create_transaction_requires_auth(client, category_id):
    resp = _create_txn(client, {}, category_id)
    assert resp.status_code == 401


def test_create_transaction(client, auth_headers, category_id):
    headers = auth_headers()
    resp = _create_txn(client, headers, category_id)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["amount"] == "12.50"
    assert body["category_id"] == category_id
    assert body["occurred_at"] == "2026-01-15"
    assert body["description"] == "Weekly shop"


def test_create_transaction_with_other_users_category_returns_400(
    client, auth_headers
):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_resp = client.post("/categories", headers=headers_b, json={"name": "Rent"})
    other_category_id = cat_resp.get_json()["id"]

    resp = _create_txn(client, headers_a, other_category_id)
    assert resp.status_code == 400


def test_create_transaction_with_nonexistent_category_returns_400(
    client, auth_headers
):
    headers = auth_headers()
    resp = _create_txn(client, headers, 999999)
    assert resp.status_code == 400


def test_get_transaction(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_txn(client, headers, category_id).get_json()
    resp = client.get(f"/transactions/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["id"] == created["id"]


def test_get_transaction_not_found(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/transactions/999999", headers=headers)
    assert resp.status_code == 404


def test_get_other_users_transaction_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_resp = client.post("/categories", headers=headers_a, json={"name": "Food"})
    cat_id = cat_resp.get_json()["id"]
    created = _create_txn(client, headers_a, cat_id).get_json()

    resp = client.get(f"/transactions/{created['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_update_transaction(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_txn(client, headers, category_id).get_json()

    resp = client.patch(
        f"/transactions/{created['id']}",
        headers=headers,
        json={"amount": "20.00", "description": "Updated"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["amount"] == "20.00"
    assert body["description"] == "Updated"


def test_update_transaction_with_invalid_category_returns_400(
    client, auth_headers, category_id
):
    headers = auth_headers()
    created = _create_txn(client, headers, category_id).get_json()

    resp = client.patch(
        f"/transactions/{created['id']}",
        headers=headers,
        json={"category_id": 999999},
    )
    assert resp.status_code == 400


def test_update_other_users_transaction_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_resp = client.post("/categories", headers=headers_a, json={"name": "Food"})
    cat_id = cat_resp.get_json()["id"]
    created = _create_txn(client, headers_a, cat_id).get_json()

    resp = client.patch(
        f"/transactions/{created['id']}", headers=headers_b, json={"amount": "1.00"}
    )
    assert resp.status_code == 404


def test_delete_transaction(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_txn(client, headers, category_id).get_json()

    resp = client.delete(f"/transactions/{created['id']}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/transactions/{created['id']}", headers=headers)
    assert resp.status_code == 404


def test_delete_other_users_transaction_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_resp = client.post("/categories", headers=headers_a, json={"name": "Food"})
    cat_id = cat_resp.get_json()["id"]
    created = _create_txn(client, headers_a, cat_id).get_json()

    resp = client.delete(f"/transactions/{created['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_list_transactions_only_returns_own(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_a = client.post("/categories", headers=headers_a, json={"name": "Food"}).get_json()["id"]
    cat_b = client.post("/categories", headers=headers_b, json={"name": "Food"}).get_json()["id"]
    _create_txn(client, headers_a, cat_a)
    _create_txn(client, headers_b, cat_b)

    resp = client.get("/transactions", headers=headers_a)
    body = resp.get_json()
    assert len(body) == 1


def test_list_transactions_filters_by_category(client, auth_headers):
    headers = auth_headers()
    cat1 = client.post("/categories", headers=headers, json={"name": "Food"}).get_json()["id"]
    cat2 = client.post("/categories", headers=headers, json={"name": "Fun"}).get_json()["id"]
    _create_txn(client, headers, cat1)
    _create_txn(client, headers, cat2)

    resp = client.get(f"/transactions?category_id={cat1}", headers=headers)
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["category_id"] == cat1


def test_list_transactions_filters_by_month(client, auth_headers, category_id):
    headers = auth_headers()
    _create_txn(client, headers, category_id, occurred_at="2026-01-15")
    _create_txn(client, headers, category_id, occurred_at="2026-02-10")

    resp = client.get("/transactions?month=2026-01", headers=headers)
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["occurred_at"] == "2026-01-15"


def test_list_transactions_month_filter_handles_december(client, auth_headers, category_id):
    headers = auth_headers()
    _create_txn(client, headers, category_id, occurred_at="2026-12-25")
    _create_txn(client, headers, category_id, occurred_at="2027-01-02")

    resp = client.get("/transactions?month=2026-12", headers=headers)
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["occurred_at"] == "2026-12-25"


def test_list_transactions_pagination(client, auth_headers, category_id):
    headers = auth_headers()
    for day in range(1, 6):
        _create_txn(client, headers, category_id, occurred_at=f"2026-01-0{day}")

    resp = client.get("/transactions?limit=2&page=1", headers=headers)
    assert len(resp.get_json()) == 2

    resp = client.get("/transactions?limit=2&page=3", headers=headers)
    assert len(resp.get_json()) == 1


def test_list_transactions_limit_capped_at_100(client, auth_headers, category_id):
    headers = auth_headers()
    _create_txn(client, headers, category_id)

    resp = client.get("/transactions?limit=1000", headers=headers)
    assert resp.status_code == 200


def test_list_transactions_ordered_by_occurred_at_desc(client, auth_headers, category_id):
    headers = auth_headers()
    _create_txn(client, headers, category_id, occurred_at="2026-01-01")
    _create_txn(client, headers, category_id, occurred_at="2026-01-20")
    _create_txn(client, headers, category_id, occurred_at="2026-01-10")

    resp = client.get("/transactions", headers=headers)
    dates = [t["occurred_at"] for t in resp.get_json()]
    assert dates == ["2026-01-20", "2026-01-10", "2026-01-01"]


def test_summary_requires_auth(client):
    resp = client.get("/transactions/summary")
    assert resp.status_code == 401


def test_summary_groups_by_category(client, auth_headers):
    headers = auth_headers()
    groceries = client.post(
        "/categories", headers=headers, json={"name": "Groceries"}
    ).get_json()["id"]
    fun = client.post("/categories", headers=headers, json={"name": "Fun"}).get_json()[
        "id"
    ]
    _create_txn(client, headers, groceries, amount="10.00")
    _create_txn(client, headers, groceries, amount="5.50")
    _create_txn(client, headers, fun, amount="20.00")

    resp = client.get("/transactions/summary", headers=headers)
    assert resp.status_code == 200
    body = {row["category_name"]: row["total"] for row in resp.get_json()}
    assert body == {"Groceries": "15.50", "Fun": "20.00"}


def test_summary_omits_categories_with_no_transactions(client, auth_headers, category_id):
    headers = auth_headers()
    empty_category = client.post(
        "/categories", headers=headers, json={"name": "Unused"}
    ).get_json()["id"]
    _create_txn(client, headers, category_id, amount="1.00")

    resp = client.get("/transactions/summary", headers=headers)
    category_ids = [row["category_id"] for row in resp.get_json()]
    assert empty_category not in category_ids


def test_summary_only_includes_own_transactions(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_a = client.post("/categories", headers=headers_a, json={"name": "Food"}).get_json()["id"]
    cat_b = client.post("/categories", headers=headers_b, json={"name": "Food"}).get_json()["id"]
    _create_txn(client, headers_a, cat_a, amount="10.00")
    _create_txn(client, headers_b, cat_b, amount="99.00")

    resp = client.get("/transactions/summary", headers=headers_a)
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["total"] == "10.00"


def test_summary_filters_by_month(client, auth_headers, category_id):
    headers = auth_headers()
    _create_txn(client, headers, category_id, amount="10.00", occurred_at="2026-01-15")
    _create_txn(client, headers, category_id, amount="99.00", occurred_at="2026-02-15")

    resp = client.get("/transactions/summary?month=2026-01", headers=headers)
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["total"] == "10.00"
