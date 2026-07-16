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


def test_register_malformed_email_returns_400(client):
    resp = client.post("/auth/register", json={"email": "not-an-email", "password": "hunter2"})
    assert resp.status_code == 400
    assert "email" in resp.get_json()["error"]


def _category(client, headers, name="food"):
    return client.post("/categories", headers=headers, json={"name": name}).get_json()["id"]


def test_create_transaction_non_numeric_amount_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "abc", "occurred_at": "2026-01-01"},
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def test_create_transaction_negative_amount_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "-5.00", "occurred_at": "2026-01-01"},
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def test_create_transaction_amount_over_column_max_returns_400(client, auth_headers):
    # Numeric(10,2) overflows above 99999999.99: Postgres raises (500 in
    # production) while SQLite silently stores it. Rejecting in app code is
    # what makes this test mean the same thing on both.
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "100000000.00", "occurred_at": "2026-01-01"},
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def test_create_transaction_nan_amount_returns_400(client, auth_headers):
    # Decimal("NaN") is a successful parse, so it slips past the try/except
    # and then makes every subsequent comparison raise.
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "NaN", "occurred_at": "2026-01-01"},
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def test_create_transaction_malformed_occurred_at_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "5.00", "occurred_at": "not-a-date"},
    )
    assert resp.status_code == 400
    assert "occurred_at" in resp.get_json()["error"]


def test_list_transactions_malformed_month_returns_400(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/transactions?month=foo", headers=headers)
    assert resp.status_code == 400
    assert "month" in resp.get_json()["error"]


def test_list_transactions_month_thirteen_returns_400(client, auth_headers):
    # Parses as ints but isn't a real month — date(2026, 13, 1) raises.
    headers = auth_headers()
    resp = client.get("/transactions?month=2026-13", headers=headers)
    assert resp.status_code == 400
    assert "month" in resp.get_json()["error"]


def test_summary_malformed_month_returns_400(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/transactions/summary?month=foo", headers=headers)
    assert resp.status_code == 400
    assert "month" in resp.get_json()["error"]


def _transaction(client, headers, category_id):
    resp = client.post(
        "/transactions",
        headers=headers,
        json={"category_id": category_id, "amount": "5.00", "occurred_at": "2026-01-01"},
    )
    return resp.get_json()["id"]


def test_patch_transaction_malformed_occurred_at_returns_400(client, auth_headers):
    headers = auth_headers()
    transaction_id = _transaction(client, headers, _category(client, headers))
    resp = client.patch(
        f"/transactions/{transaction_id}", headers=headers, json={"occurred_at": "not-a-date"}
    )
    assert resp.status_code == 400
    assert "occurred_at" in resp.get_json()["error"]


def test_patch_transaction_negative_amount_returns_400(client, auth_headers):
    headers = auth_headers()
    transaction_id = _transaction(client, headers, _category(client, headers))
    resp = client.patch(
        f"/transactions/{transaction_id}", headers=headers, json={"amount": "-1.00"}
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def _rule_payload(category_id, **overrides):
    payload = {
        "category_id": category_id,
        "amount": "10.00",
        "frequency": "monthly",
        "start_date": "2026-01-01",
    }
    payload.update(overrides)
    return payload


def test_create_rule_malformed_start_date_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/recurring-rules", headers=headers, json=_rule_payload(category_id, start_date="nope")
    )
    assert resp.status_code == 400
    assert "start_date" in resp.get_json()["error"]


def test_create_rule_malformed_end_date_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/recurring-rules", headers=headers, json=_rule_payload(category_id, end_date="nope")
    )
    assert resp.status_code == 400
    assert "end_date" in resp.get_json()["error"]


def test_create_rule_non_numeric_amount_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    resp = client.post(
        "/recurring-rules", headers=headers, json=_rule_payload(category_id, amount="abc")
    )
    assert resp.status_code == 400
    assert "amount" in resp.get_json()["error"]


def test_patch_rule_malformed_start_date_returns_400(client, auth_headers):
    headers = auth_headers()
    category_id = _category(client, headers)
    rule_id = client.post(
        "/recurring-rules", headers=headers, json=_rule_payload(category_id)
    ).get_json()["id"]
    resp = client.patch(
        f"/recurring-rules/{rule_id}", headers=headers, json={"start_date": "nope"}
    )
    assert resp.status_code == 400
    assert "start_date" in resp.get_json()["error"]
