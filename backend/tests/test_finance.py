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


def test_account_update_rejects_explicit_null_type_and_balance(client):
    headers = _register_and_login(client)
    account = _create_account(client, headers, "不可置空账户", 100)

    null_type = client.put(
        f"/api/finance/accounts/{account['id']}",
        json={"type": None},
        headers=headers,
    )
    null_balance = client.put(
        f"/api/finance/accounts/{account['id']}",
        json={"balance": None},
        headers=headers,
    )

    assert null_type.status_code == 422
    assert null_balance.status_code == 422
    current = client.get("/api/finance/accounts", headers=headers).json()
    stored = next(item for item in current if item["id"] == account["id"])
    assert stored["type"] == "cash"
    assert stored["balance"] == 100


def test_transfer_update_can_replace_target_credit_with_income_after_target_spending(client):
    headers = _register_and_login(client)
    source = _create_account(client, headers, "转出账户", 100)
    target = _create_account(client, headers, "转入账户", 0)
    transfer = client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": source["id"],
            "to_account_id": target["id"],
            "amount": 50,
            "date": "2026-09-15",
        },
        headers=headers,
    ).json()["transaction"]
    expense = client.post(
        "/api/finance/transactions",
        json={
            "account_id": target["id"],
            "type": "expense",
            "amount": 50,
            "date": "2026-09-15",
        },
        headers=headers,
    )
    assert expense.status_code == 200

    updated = client.put(
        f"/api/finance/transactions/{transfer['id']}",
        json={
            "account_id": target["id"],
            "type": "income",
            "amount": 50,
            "to_account_id": None,
        },
        headers=headers,
    )

    assert updated.status_code == 200
    assert updated.json()["type"] == "income"
    assert updated.json()["to_account_id"] is None
    current = {item["id"]: item for item in client.get("/api/finance/accounts", headers=headers).json()}
    assert current[source["id"]]["balance"] == 100
    assert current[target["id"]]["balance"] == 0


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


def test_credit_account_can_spend_down_to_its_credit_limit(client):
    headers = _register_and_login(client)
    response = client.post(
        "/api/finance/accounts",
        json={"name": "花呗", "type": "credit", "balance": 0, "credit_limit": 1000},
        headers=headers,
    )
    assert response.status_code == 200
    account = response.json()

    first_expense = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 750,
            "date": "2026-06-09",
        },
        headers=headers,
    )
    second_expense = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 250,
            "date": "2026-06-09",
        },
        headers=headers,
    )
    over_limit = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 0.01,
            "date": "2026-06-09",
        },
        headers=headers,
    )

    assert first_expense.status_code == 200
    assert second_expense.status_code == 200
    assert over_limit.status_code == 400
    current = client.get("/api/finance/accounts", headers=headers).json()
    assert next(item["balance"] for item in current if item["id"] == account["id"]) == -1000


def test_credit_account_rejects_balance_below_limit_and_credit_limit_reduction(client):
    headers = _register_and_login(client)
    response = client.post(
        "/api/finance/accounts",
        json={"name": "超额花呗", "type": "credit", "balance": -1001, "credit_limit": 1000},
        headers=headers,
    )
    assert response.status_code == 422

    response = client.post(
        "/api/finance/accounts",
        json={"name": "信用卡", "type": "credit", "balance": -500, "credit_limit": 1000},
        headers=headers,
    )
    assert response.status_code == 200
    account = response.json()

    balance_update = client.put(
        f"/api/finance/accounts/{account['id']}",
        json={"type": "credit", "balance": -600},
        headers=headers,
    )
    reduced = client.put(
        f"/api/finance/accounts/{account['id']}",
        json={"credit_limit": 400},
        headers=headers,
    )
    assert balance_update.status_code == 200
    assert reduced.status_code == 422


def test_regular_accounts_reject_negative_balances_and_income_deletion_that_would_overdraw(client):
    headers = _register_and_login(client)
    negative_create = client.post(
        "/api/finance/accounts",
        json={"name": "现金", "type": "cash", "balance": -1},
        headers=headers,
    )
    assert negative_create.status_code == 422

    account = _create_account(client, headers, "正常账户", 0)
    income = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "income",
            "amount": 100,
            "date": "2026-06-09",
        },
        headers=headers,
    ).json()
    expense_response = client.post(
        "/api/finance/transactions",
        json={
            "account_id": account["id"],
            "type": "expense",
            "amount": 100,
            "date": "2026-06-09",
        },
        headers=headers,
    )
    delete_income = client.delete(
        f"/api/finance/transactions/{income['id']}",
        headers=headers,
    )

    assert expense_response.status_code == 200
    assert delete_income.status_code == 400
    current = client.get("/api/finance/accounts", headers=headers).json()
    assert next(item["balance"] for item in current if item["id"] == account["id"]) == 0


def test_credit_repayment_transfer_restores_credit_balance(client):
    headers = _register_and_login(client)
    cash = _create_account(client, headers, "银行卡", 1000)
    credit = client.post(
        "/api/finance/accounts",
        json={"name": "信用卡", "type": "credit", "balance": 0, "credit_limit": 1000},
        headers=headers,
    ).json()
    expense_response = client.post(
        "/api/finance/transactions",
        json={
            "account_id": credit["id"],
            "type": "expense",
            "amount": 400,
            "date": "2026-06-09",
        },
        headers=headers,
    )
    repayment = client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": cash["id"],
            "to_account_id": credit["id"],
            "amount": 400,
            "date": "2026-06-09",
        },
        headers=headers,
    )

    assert expense_response.status_code == 200
    assert repayment.status_code == 200
    current = {item["id"]: item for item in client.get("/api/finance/accounts", headers=headers).json()}
    assert current[credit["id"]]["balance"] == 0
    assert current[cash["id"]]["balance"] == 600


def test_credit_transaction_update_and_delete_preserve_credit_floor(client):
    headers = _register_and_login(client)
    credit = client.post(
        "/api/finance/accounts",
        json={"name": "额度账户", "type": "credit", "balance": 0, "credit_limit": 100},
        headers=headers,
    ).json()
    transaction = client.post(
        "/api/finance/transactions",
        json={
            "account_id": credit["id"],
            "type": "expense",
            "amount": 60,
            "date": "2026-06-09",
        },
        headers=headers,
    ).json()

    over_limit_update = client.put(
        f"/api/finance/transactions/{transaction['id']}",
        json={"amount": 101},
        headers=headers,
    )
    valid_update = client.put(
        f"/api/finance/transactions/{transaction['id']}",
        json={"amount": 100},
        headers=headers,
    )
    delete_transaction = client.delete(
        f"/api/finance/transactions/{transaction['id']}",
        headers=headers,
    )

    assert over_limit_update.status_code == 400
    assert valid_update.status_code == 200
    assert delete_transaction.status_code == 200
    current = client.get("/api/finance/accounts", headers=headers).json()
    assert next(item["balance"] for item in current if item["id"] == credit["id"]) == 0


def test_recurring_credit_expense_obeys_credit_limit(client):
    headers = _register_and_login(client)
    credit = client.post(
        "/api/finance/accounts",
        json={"name": "周期信用卡", "type": "credit", "balance": 0, "credit_limit": 100},
        headers=headers,
    ).json()
    recurring = client.post(
        "/api/finance/recurring",
        json={
            "account_id": credit["id"],
            "type": "expense",
            "amount": 75,
            "frequency": "monthly",
            "next_date": "2026-06-09",
        },
        headers=headers,
    ).json()
    triggered = client.post(
        f"/api/finance/recurring/{recurring['id']}/trigger",
        headers=headers,
    )

    assert triggered.status_code == 200
    current = client.get("/api/finance/accounts", headers=headers).json()
    assert next(item["balance"] for item in current if item["id"] == credit["id"]) == -75


def test_deleting_transfer_cannot_overdraw_regular_target(client):
    headers = _register_and_login(client)
    source = _create_account(client, headers, "转出账户", 100)
    target = _create_account(client, headers, "转入账户", 0)
    transfer = client.post(
        "/api/finance/accounts/transfer",
        json={
            "from_account_id": source["id"],
            "to_account_id": target["id"],
            "amount": 50,
            "date": "2026-06-09",
        },
        headers=headers,
    ).json()["transaction"]
    client.post(
        "/api/finance/transactions",
        json={
            "account_id": target["id"],
            "type": "expense",
            "amount": 50,
            "date": "2026-06-09",
        },
        headers=headers,
    )

    deleted = client.delete(
        f"/api/finance/transactions/{transfer['id']}",
        headers=headers,
    )

    assert deleted.status_code == 400
    current = {item["id"]: item for item in client.get("/api/finance/accounts", headers=headers).json()}
    assert current[source["id"]]["balance"] == 50
    assert current[target["id"]]["balance"] == 0


def test_finance_transactions_support_page_pagination_and_legacy_skip(client):
    headers = _register_and_login(client)
    account = _create_account(client, headers, "Pagination account", 1000)

    for index in range(5):
        response = client.post(
            "/api/finance/transactions",
            json={
                "account_id": account["id"],
                "type": "expense",
                "amount": index + 1,
                "description": f"Pagination transaction {index}",
                "date": "2026-06-09",
            },
            headers=headers,
        )
        assert response.status_code == 200

    page_one = client.get(
        "/api/finance/transactions?page=1&page_size=2",
        headers=headers,
    )
    page_two = client.get(
        "/api/finance/transactions?page=2&page_size=2",
        headers=headers,
    )
    legacy_page_two = client.get(
        "/api/finance/transactions?skip=2&page_size=2",
        headers=headers,
    )

    assert page_one.status_code == 200
    assert page_two.status_code == 200
    assert legacy_page_two.status_code == 200
    assert set(page_one.json()) == {"items", "total", "page", "page_size", "has_more"}
    assert page_one.json()["page"] == 1
    assert page_two.json()["page"] == 2
    assert page_one.json()["page_size"] == 2
    assert page_one.json()["total"] == 5
    assert page_one.json()["has_more"] is True
    assert {item["id"] for item in page_one.json()["items"]}.isdisjoint(
        {item["id"] for item in page_two.json()["items"]}
    )
    assert [item["id"] for item in page_two.json()["items"]] == [
        item["id"] for item in legacy_page_two.json()["items"]
    ]


def test_finance_filtered_pagination_metadata_matches_filtered_rows(client):
    headers = _register_and_login(client)
    account = _create_account(client, headers, "Filtered pagination account", 1000)

    for transaction_type, amount, transaction_date in [
        ("expense", 10, "2026-06-07"),
        ("income", 20, "2026-06-08"),
        ("expense", 30, "2026-06-09"),
    ]:
        response = client.post(
            "/api/finance/transactions",
            json={
                "account_id": account["id"],
                "type": transaction_type,
                "amount": amount,
                "description": "Filtered pagination transaction",
                "date": transaction_date,
            },
            headers=headers,
        )
        assert response.status_code == 200

    response = client.get(
        "/api/finance/transactions?type=expense&page=2&page_size=1",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert len(payload["items"]) == 1
    assert payload["has_more"] is False
