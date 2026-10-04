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


def test_create_debt_accepts_canonical_payload(client, auth_headers):
    response = client.post("/api/finance/debts", headers=auth_headers, json={
        "creditor": "测试对象", "type": "borrow", "amount": 100, "remaining": 100,
    })
    assert response.status_code == 200
    assert response.json()["creditor"] == "测试对象"


def test_debt_response_contains_ordered_payments_and_zero_remaining(
    client, auth_headers, debt,
):
    payment_responses = [
        client.post(
            f"/api/finance/debts/{debt.id}/payments",
            headers=auth_headers,
            json={"amount": 20, "date": "2026-08-05", "description": "较晚"},
        ),
        client.post(
            f"/api/finance/debts/{debt.id}/payments",
            headers=auth_headers,
            json={"amount": 30, "date": "2026-08-04", "description": "较早"},
        ),
        client.post(
            f"/api/finance/debts/{debt.id}/payments",
            headers=auth_headers,
            json={"amount": 10, "date": "2026-08-05", "description": "同日一"},
        ),
        client.post(
            f"/api/finance/debts/{debt.id}/payments",
            headers=auth_headers,
            json={"amount": 40, "date": "2026-08-05", "description": "同日二"},
        ),
    ]
    assert all(response.status_code == 200 for response in payment_responses)
    payments = [response.json() for response in payment_responses]

    response = client.get("/api/finance/debts", headers=auth_headers)
    row = response.json()[0]
    assert "payments" in row
    assert row["remaining"] == 0
    assert row["status"] == "settled"
    assert [payment["id"] for payment in row["payments"]] == [
        payment["id"] for payment in sorted(payments, key=lambda item: (item["date"], item["id"]))
    ]
    assert [payment["description"] for payment in row["payments"]] == [
        payment["description"] for payment in sorted(payments, key=lambda item: (item["date"], item["id"]))
    ]


def test_debt_type_filter_and_recurring_update_are_scoped_and_canonical(
    client, auth_headers, db_session, user,
):
    borrowed = client.post(
        "/api/finance/debts",
        headers=auth_headers,
        json={"creditor": "借入方", "type": "borrow", "amount": 100, "remaining": 100},
    ).json()
    lent = client.post(
        "/api/finance/debts",
        headers=auth_headers,
        json={"creditor": "借出方", "type": "lend", "amount": 100, "remaining": 100},
    ).json()
    from app.models.debt import Debt, DebtStatus, DebtType
    from app.models.user import User

    settled = client.post(
        "/api/finance/debts",
        headers=auth_headers,
        json={"creditor": "已结清", "type": "borrow", "amount": 100, "remaining": 100},
    ).json()
    settled_payment = client.post(
        f"/api/finance/debts/{settled['id']}/payments",
        headers=auth_headers,
        json={"amount": 100, "date": "2026-08-04"},
    )
    assert settled_payment.status_code == 200
    foreign_user = User(
        username="foreign-debt-filter",
        email="foreign-debt-filter@example.com",
        password_hash="not-used",
    )
    foreign_debt = Debt(
        user=foreign_user,
        creditor="他人借入",
        type=DebtType.BORROW,
        amount=100,
        remaining=100,
        status=DebtStatus.ACTIVE,
    )
    db_session.add(foreign_debt)
    db_session.commit()

    filtered = client.get(
        "/api/finance/debts", headers=auth_headers, params={"status": "active", "type": "borrow"},
    )
    assert filtered.status_code == 200
    active_borrow_rows = filtered.json()
    assert [row["id"] for row in active_borrow_rows] == [borrowed["id"]]
    assert [row["user_id"] for row in active_borrow_rows] == [str(user.id)]
    settled_filtered = client.get(
        "/api/finance/debts", headers=auth_headers, params={"status": "settled", "type": "borrow"},
    )
    assert settled_filtered.status_code == 200
    settled_rows = settled_filtered.json()
    assert [row["id"] for row in settled_rows] == [settled["id"]]
    assert [row["user_id"] for row in settled_rows] == [str(user.id)]
    lend_filtered = client.get(
        "/api/finance/debts", headers=auth_headers, params={"type": "lend"},
    )
    assert lend_filtered.status_code == 200
    lend_rows = lend_filtered.json()
    assert [row["id"] for row in lend_rows] == [lent["id"]]
    assert [row["user_id"] for row in lend_rows] == [str(user.id)]
    assert str(foreign_debt.id) not in {row["id"] for row in active_borrow_rows}

    account = client.post(
        "/api/finance/accounts", headers=auth_headers, json={"name": "Recurring", "balance": 100},
    ).json()
    recurring = client.post(
        "/api/finance/recurring",
        headers=auth_headers,
        json={
            "account_id": account["id"], "type": "expense", "amount": 10,
            "frequency": "monthly", "next_date": "2026-08-04",
        },
    ).json()
    updated = client.put(
        f"/api/finance/recurring/{recurring['id']}",
        headers=auth_headers,
        json={"description": None, "category_id": None, "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] is None
    assert updated.json()["category_id"] is None
    assert updated.json()["is_active"] is False


def test_legacy_debt_fields_are_accepted_without_conflicting_canonical_values(
    client, auth_headers,
):
    legacy = client.post(
        "/api/finance/debts",
        headers=auth_headers,
        json={"creditor_name": "旧字段", "type": "borrowed", "amount": 100, "remaining": 100},
    )
    assert legacy.status_code == 200
    assert legacy.json()["creditor"] == "旧字段"
    assert legacy.json()["type"] == "borrow"

    conflict = client.post(
        "/api/finance/debts",
        headers=auth_headers,
        json={
            "creditor": "规范字段", "creditor_name": "冲突字段",
            "type": "borrow", "amount": 100, "remaining": 100,
        },
    )
    assert conflict.status_code == 422


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
