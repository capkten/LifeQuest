def _register_and_login(client):
    client.post(
        "/api/auth/register",
        json={
            "username": "financeuser",
            "email": "finance@example.com",
            "password": "testpassword123",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": "financeuser", "password": "testpassword123"},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_account(client, headers, name, balance):
    response = client.post(
        "/api/finance/accounts",
        json={
            "name": name,
            "balance": balance,
            "type": "cash",
        },
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_transfer_accepts_account_field_names_and_preserves_date(client):
    headers = _register_and_login(client)
    from_account = _create_account(client, headers, "银行卡A", 1000)
    to_account = _create_account(client, headers, "零钱包B", 100)

    response = client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": from_account["id"],
            "to_account_id": to_account["id"],
            "amount": 260,
            "description": "房租转账",
            "date": "2026-06-09",
        },
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["from_balance"] == 740
    assert payload["to_balance"] == 360
    assert payload["transaction"]["type"] == "transfer"
    assert payload["transaction"]["date"] == "2026-06-09"

    accounts_response = client.get("/api/finance/accounts", headers=headers)
    assert accounts_response.status_code == 200
    accounts = accounts_response.json()
    balances = {acc["id"]: acc["balance"] for acc in accounts}
    assert balances[from_account["id"]] == 740
    assert balances[to_account["id"]] == 360


def test_update_transaction_accepts_date(client):
    headers = _register_and_login(client)
    account = _create_account(client, headers, "记账账户", 1000)

    create_response = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 120,
            "description": "旧日期流水",
            "date": "2026-06-08",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    transaction_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/finance/transactions/{transaction_id}",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 120,
            "description": "改日期流水",
            "date": "2026-06-09",
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["date"] == "2026-06-09"


def test_update_transfer_transaction_updates_balances(client):
    headers = _register_and_login(client)
    from_account = _create_account(client, headers, "转出账户", 1000)
    to_account = _create_account(client, headers, "转入账户", 100)

    create_response = client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": from_account["id"],
            "to_account_id": to_account["id"],
            "amount": 260,
            "description": "第一次转账",
            "date": "2026-06-08",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    transaction_id = create_response.json()["transaction"]["id"]

    update_response = client.put(
        f"/api/finance/transactions/{transaction_id}",
        json={
            "account_id": from_account["id"],
            "to_account_id": to_account["id"],
            "type": "transfer",
            "amount": 100,
            "description": "修改后的转账",
            "date": "2026-06-09",
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["amount"] == 100
    assert payload["date"] == "2026-06-09"

    accounts_response = client.get("/api/finance/accounts", headers=headers)
    accounts = accounts_response.json()
    balances = {acc["id"]: acc["balance"] for acc in accounts}
    assert balances[from_account["id"]] == 900
    assert balances[to_account["id"]] == 200


def test_finance_rejects_non_positive_amounts_and_invalid_debt_remaining(client):
    headers = _register_and_login(client)
    account = _create_account(client, headers, "校验账户", 1000)

    transaction = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 0,
            "date": "2026-06-09",
        },
        headers=headers,
    )
    assert transaction.status_code == 422

    budget = client.post(
        "/api/finance/budgets",
        json={"amount": 0, "period": "monthly"},
        headers=headers,
    )
    assert budget.status_code == 422

    debt = client.post(
        "/api/finance/debts",
        json={
            "creditor": "银行",
            "type": "loan",
            "amount": 100,
            "remaining": 101,
        },
        headers=headers,
    )
    assert debt.status_code == 422
