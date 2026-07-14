import pytest


@pytest.fixture()
def category_id(client, auth_headers):
    headers = auth_headers()
    resp = client.post("/categories", headers=headers, json={"name": "Subscriptions"})
    return resp.get_json()["id"]


def _create_rule(client, headers, category_id, **overrides):
    payload = {
        "category_id": category_id,
        "amount": "9.99",
        "frequency": "monthly",
        "start_date": "2026-01-01",
    }
    payload.update(overrides)
    return client.post("/recurring-rules", headers=headers, json=payload)


def test_create_recurring_rule_requires_auth(client, category_id):
    resp = _create_rule(client, {}, category_id)
    assert resp.status_code == 401


def test_create_recurring_rule(client, auth_headers, category_id):
    headers = auth_headers()
    resp = _create_rule(client, headers, category_id)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["amount"] == "9.99"
    assert body["category_id"] == category_id
    assert body["frequency"] == "monthly"
    assert body["start_date"] == "2026-01-01"
    assert body["end_date"] is None


def test_create_recurring_rule_with_end_date(client, auth_headers, category_id):
    headers = auth_headers()
    resp = _create_rule(client, headers, category_id, end_date="2026-12-31")
    assert resp.status_code == 201
    assert resp.get_json()["end_date"] == "2026-12-31"


def test_create_recurring_rule_missing_fields_returns_400(client, auth_headers):
    headers = auth_headers()
    resp = client.post(
        "/recurring-rules", headers=headers, json={"amount": "9.99"}
    )
    assert resp.status_code == 400
    body = resp.get_json()["error"]
    assert "category_id" in body
    assert "frequency" in body
    assert "start_date" in body


def test_create_recurring_rule_with_other_users_category_returns_400(
    client, auth_headers
):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_id = client.post(
        "/categories", headers=headers_b, json={"name": "Rent"}
    ).get_json()["id"]

    resp = _create_rule(client, headers_a, cat_id)
    assert resp.status_code == 400


def test_create_recurring_rule_with_nonexistent_category_returns_400(
    client, auth_headers
):
    headers = auth_headers()
    resp = _create_rule(client, headers, 999999)
    assert resp.status_code == 400


def test_list_recurring_rules_requires_auth(client):
    resp = client.get("/recurring-rules")
    assert resp.status_code == 401


def test_list_recurring_rules_only_returns_own(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_a = client.post(
        "/categories", headers=headers_a, json={"name": "Subs"}
    ).get_json()["id"]
    cat_b = client.post(
        "/categories", headers=headers_b, json={"name": "Subs"}
    ).get_json()["id"]
    _create_rule(client, headers_a, cat_a)
    _create_rule(client, headers_b, cat_b)

    resp = client.get("/recurring-rules", headers=headers_a)
    assert len(resp.get_json()) == 1


def test_get_recurring_rule(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_rule(client, headers, category_id).get_json()
    resp = client.get(f"/recurring-rules/{created['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()["id"] == created["id"]


def test_get_recurring_rule_not_found(client, auth_headers):
    headers = auth_headers()
    resp = client.get("/recurring-rules/999999", headers=headers)
    assert resp.status_code == 404


def test_get_other_users_recurring_rule_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_id = client.post(
        "/categories", headers=headers_a, json={"name": "Subs"}
    ).get_json()["id"]
    created = _create_rule(client, headers_a, cat_id).get_json()

    resp = client.get(f"/recurring-rules/{created['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_update_recurring_rule(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_rule(client, headers, category_id).get_json()

    resp = client.patch(
        f"/recurring-rules/{created['id']}",
        headers=headers,
        json={"amount": "15.00", "frequency": "weekly"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["amount"] == "15.00"
    assert body["frequency"] == "weekly"


def test_update_recurring_rule_end_date_can_be_cleared(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_rule(
        client, headers, category_id, end_date="2026-12-31"
    ).get_json()

    resp = client.patch(
        f"/recurring-rules/{created['id']}",
        headers=headers,
        json={"end_date": None},
    )
    assert resp.status_code == 200
    assert resp.get_json()["end_date"] is None


def test_update_recurring_rule_with_invalid_category_returns_400(
    client, auth_headers, category_id
):
    headers = auth_headers()
    created = _create_rule(client, headers, category_id).get_json()

    resp = client.patch(
        f"/recurring-rules/{created['id']}",
        headers=headers,
        json={"category_id": 999999},
    )
    assert resp.status_code == 400


def test_update_other_users_recurring_rule_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_id = client.post(
        "/categories", headers=headers_a, json={"name": "Subs"}
    ).get_json()["id"]
    created = _create_rule(client, headers_a, cat_id).get_json()

    resp = client.patch(
        f"/recurring-rules/{created['id']}",
        headers=headers_b,
        json={"amount": "1.00"},
    )
    assert resp.status_code == 404


def test_delete_recurring_rule(client, auth_headers, category_id):
    headers = auth_headers()
    created = _create_rule(client, headers, category_id).get_json()

    resp = client.delete(f"/recurring-rules/{created['id']}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/recurring-rules/{created['id']}", headers=headers)
    assert resp.status_code == 404


def test_delete_other_users_recurring_rule_returns_404(client, auth_headers):
    headers_a = auth_headers(email="a@example.com")
    headers_b = auth_headers(email="b@example.com")
    cat_id = client.post(
        "/categories", headers=headers_a, json={"name": "Subs"}
    ).get_json()["id"]
    created = _create_rule(client, headers_a, cat_id).get_json()

    resp = client.delete(f"/recurring-rules/{created['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_delete_category_with_recurring_rule_is_restricted(client, auth_headers):
    # RecurringRule.category_id uses ondelete="RESTRICT" — no DELETE route
    # exists for categories, but this documents that a rule keeps its
    # category alive at the DB level if that ever changes.
    headers = auth_headers()
    cat_id = client.post(
        "/categories", headers=headers, json={"name": "Subs"}
    ).get_json()["id"]
    _create_rule(client, headers, cat_id)

    from app.db import SessionLocal
    from app.models import Category
    from sqlalchemy.exc import IntegrityError

    with SessionLocal() as session:
        category = session.get(Category, cat_id)
        session.delete(category)
        with pytest.raises(IntegrityError):
            session.commit()
