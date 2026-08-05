def _register_and_login(client, username, email):
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "testpassword123",
        },
    )
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": "testpassword123"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_finance_resources_cannot_cross_user_boundaries(client):
    headers_a = _register_and_login(client, "finance-a", "finance-a@example.com")
    headers_b = _register_and_login(client, "finance-b", "finance-b@example.com")

    account_a = client.post(
        "/api/finance/accounts",
        json={"name": "A account", "balance": 1000},
        headers=headers_a,
    ).json()
    account_b = client.post(
        "/api/finance/accounts",
        json={"name": "B account", "balance": 500},
        headers=headers_b,
    ).json()
    category_a = client.post(
        "/api/finance/categories",
        json={"name": "A category", "type": "expense"},
        headers=headers_a,
    ).json()
    transaction_a = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account_a["id"],
            "category_id": category_a["id"],
            "type": "expense",
            "amount": 100,
            "date": "2026-08-04",
        },
        headers=headers_a,
    ).json()
    budget_a = client.post(
        "/api/finance/budgets",
        json={"category_id": category_a["id"], "amount": 300, "period": "monthly"},
        headers=headers_a,
    ).json()
    debt_a = client.post(
        "/api/finance/debts",
        json={
            "creditor": "A creditor",
            "type": "borrow",
            "amount": 300,
            "remaining": 300,
        },
        headers=headers_a,
    ).json()
    recurring_a = client.post(
        "/api/finance/recurring",
        json={
            "account_id": account_a["id"],
            "type": "expense",
            "amount": 20,
            "frequency": "monthly",
            "next_date": "2026-09-01",
        },
        headers=headers_a,
    ).json()

    assert client.put(
        f"/api/finance/transactions/{transaction_a['id']}",
        json={"account_id": account_b["id"]},
        headers=headers_b,
    ).status_code == 404
    assert client.put(
        f"/api/finance/transactions/{transaction_a['id']}",
        json={"account_id": account_b["id"]},
        headers=headers_a,
    ).status_code == 404
    assert client.delete(
        f"/api/finance/categories/{category_a['id']}", headers=headers_b
    ).status_code == 403
    assert client.put(
        f"/api/finance/budgets/{budget_a['id']}",
        json={"amount": 1},
        headers=headers_b,
    ).status_code == 404
    assert client.put(
        f"/api/finance/debts/{debt_a['id']}",
        json={"remaining": 1},
        headers=headers_b,
    ).status_code == 404
    assert client.delete(
        f"/api/finance/recurring/{recurring_a['id']}", headers=headers_b
    ).status_code == 404
    assert client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": account_a["id"],
            "to_account_id": account_b["id"],
            "amount": 50,
        },
        headers=headers_a,
    ).status_code == 404

    accounts_a = client.get("/api/finance/accounts", headers=headers_a).json()
    accounts_b = client.get("/api/finance/accounts", headers=headers_b).json()
    assert accounts_a[0]["balance"] == 900
    assert accounts_b[0]["balance"] == 500
