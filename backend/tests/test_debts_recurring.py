def _login(client):
    client.post(
        "/api/auth/register",
        json={"username": "finance-cycle", "email": "finance-cycle@example.com", "password": "testpassword123"},
    )
    token = client.post(
        "/api/auth/login",
        data={"username": "finance-cycle", "password": "testpassword123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_debt_payment_cannot_exceed_remaining_and_recurring_advances(client):
    headers = _login(client)
    debt = client.post(
        "/api/finance/debts",
        json={"creditor": "银行", "type": "borrow", "amount": 100, "remaining": 100},
        headers=headers,
    ).json()
    payment = client.post(
        f"/api/finance/debts/{debt['id']}/payments",
        json={"amount": 101, "date": "2026-08-04"},
        headers=headers,
    )
    assert payment.status_code == 400

    account = client.post(
        "/api/finance/accounts", json={"name": "Cycle", "balance": 100}, headers=headers
    ).json()
    recurring = client.post(
        "/api/finance/recurring",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 10,
            "frequency": "monthly",
            "next_date": "2026-08-04",
        },
        headers=headers,
    ).json()
    triggered = client.post(
        f"/api/finance/recurring/{recurring['id']}/trigger", headers=headers
    )
    assert triggered.status_code == 200
    updated = client.get("/api/finance/recurring", headers=headers).json()[0]
    assert updated["next_date"] == "2026-09-04"
