def test_login_is_rate_limited_after_five_attempts(client):
    # The limiter runs suite-wide and reset_rate_limiter (conftest) clears its
    # counters before each test, so these five are the only login attempts
    # this IP has made this minute.
    credentials = {"email": "nobody@example.com", "password": "wrong"}

    for _ in range(5):
        assert client.post("/auth/login", json=credentials).status_code == 401

    # Sixth attempt in the same minute is the one that should be refused —
    # 429, not another 401, so brute-forcing stops being free.
    assert client.post("/auth/login", json=credentials).status_code == 429


def test_register_is_rate_limited_after_three_accounts(client):
    # Distinct emails so the first three are genuine 201s, not 409 duplicates:
    # the cap is on how many accounts one IP can create, not on repeats.
    for i in range(3):
        resp = client.post(
            "/auth/register", json={"email": f"user{i}@example.com", "password": "hunter2"}
        )
        assert resp.status_code == 201

    resp = client.post(
        "/auth/register", json={"email": "user4@example.com", "password": "hunter2"}
    )
    assert resp.status_code == 429


def test_rate_limit_keys_on_forwarded_client_ip(client):
    # Behind a proxy the socket IP is the proxy's, identical for everyone, so
    # the limiter must key on X-Forwarded-For instead. Exhaust one client's
    # login budget, then a different forwarded IP must still have its own.
    creds = {"email": "nobody@example.com", "password": "wrong"}
    client_a = {"X-Forwarded-For": "203.0.113.10"}
    client_b = {"X-Forwarded-For": "203.0.113.20"}

    for _ in range(5):
        assert client.post("/auth/login", json=creds, headers=client_a).status_code == 401
    assert client.post("/auth/login", json=creds, headers=client_a).status_code == 429

    # Different client, untouched budget — a shared proxy must not make one
    # user's attempts count against another's.
    assert client.post("/auth/login", json=creds, headers=client_b).status_code == 401
