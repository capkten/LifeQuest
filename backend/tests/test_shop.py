def _register_and_login(client, username="testuser", email="test@example.com", password="testpassword123"):
    """Helper: register a user and return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    login_response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_item(client, headers, coin_price=50, stock=10):
    """Helper: create a shop item and return the response data."""
    response = client.post(
        "/api/shop/items",
        json={
            "name": "Health Potion",
            "description": "Restores 50 HP",
            "category": "consumable",
            "coin_price": coin_price,
            "stock": stock,
        },
        headers=headers,
    )
    return response


def test_create_shop_item(client):
    headers = _register_and_login(client)

    response = _create_item(client, headers)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Health Potion"
    assert data["description"] == "Restores 50 HP"
    assert data["category"] == "consumable"
    assert data["coin_price"] == 50
    assert data["stock"] == 10
    assert data["is_active"] is True
    assert data["id"] is not None

    # Verify item is in the list
    list_response = client.get("/api/shop/items", headers=headers)
    assert list_response.status_code == 200
    items = list_response.json()
    assert len(items) == 1
    assert items[0]["id"] == data["id"]


def test_purchase_insufficient_coins(client):
    headers = _register_and_login(client)

    # Create item with a high price
    item_response = _create_item(client, headers, coin_price=1000, stock=10)
    item_id = item_response.json()["id"]

    # Attempt purchase - user has 0 coins
    purchase_response = client.post(
        "/api/shop/exchange",
        json={
            "item_id": item_id,
            "quantity": 1,
        },
        headers=headers,
    )
    assert purchase_response.status_code == 400
    assert "Insufficient coins" in purchase_response.json()["detail"]

    # Verify no exchange was created
    history_response = client.get("/api/shop/exchange/history", headers=headers)
    assert history_response.status_code == 200
    assert len(history_response.json()) == 0


def test_purchase_success(client):
    headers = _register_and_login(client)

    # Create item with low price
    item_response = _create_item(client, headers, coin_price=10, stock=5)
    item_id = item_response.json()["id"]

    # Give user coins via completing a task (use todo system)
    task_response = client.post(
        "/api/todos/tasks",
        json={
            "title": "Earn coins",
            "coins_reward": 100,
            "exp_reward": 0,
        },
        headers=headers,
    )
    task_id = task_response.json()["id"]
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)

    # Purchase the item
    purchase_response = client.post(
        "/api/shop/exchange",
        json={
            "item_id": item_id,
            "quantity": 2,
        },
        headers=headers,
    )
    assert purchase_response.status_code == 200
    exchange = purchase_response.json()
    assert exchange["total_cost"] == 20
    assert exchange["quantity"] == 2
    assert exchange["status"] == "completed"

    # Verify user coins were deducted
    user = client.get("/api/users/me", headers=headers).json()
    assert user["coins"] == 80  # 100 earned - 20 spent

    # Verify stock was decremented
    item_detail = client.get(f"/api/shop/items/{item_id}", headers=headers).json()
    assert item_detail["stock"] == 3  # 5 - 2


def test_update_item_authorization(client):
    """Only the creator can update a shop item."""
    headers_creator = _register_and_login(client, "creator", "creator@example.com")
    headers_other = _register_and_login(client, "other", "other@example.com")

    item_response = _create_item(client, headers_creator)
    item_id = item_response.json()["id"]

    # Creator can update
    update_response = client.put(
        f"/api/shop/items/{item_id}",
        json={"name": "Updated Potion"},
        headers=headers_creator,
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Potion"

    # Other user cannot update
    other_update_response = client.put(
        f"/api/shop/items/{item_id}",
        json={"name": "Hacked Name"},
        headers=headers_other,
    )
    assert other_update_response.status_code == 403


def test_refund_exchange(client):
    headers = _register_and_login(client)

    # Create item and give user coins
    item_response = _create_item(client, headers, coin_price=10, stock=5)
    item_id = item_response.json()["id"]

    task_response = client.post(
        "/api/todos/tasks",
        json={"title": "Earn coins", "coins_reward": 100, "exp_reward": 0},
        headers=headers,
    )
    task_id = task_response.json()["id"]
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)

    # Purchase
    purchase_response = client.post(
        "/api/shop/exchange",
        json={"item_id": item_id, "quantity": 1},
        headers=headers,
    )
    exchange_id = purchase_response.json()["id"]

    # Verify coins deducted
    user_before_refund = client.get("/api/users/me", headers=headers).json()
    assert user_before_refund["coins"] == 90  # 100 - 10

    # Refund
    refund_response = client.post(
        f"/api/shop/exchange/{exchange_id}/refund",
        headers=headers,
    )
    assert refund_response.status_code == 200
    assert refund_response.json()["status"] == "refunded"

    # Verify coins restored
    user_after_refund = client.get("/api/users/me", headers=headers).json()
    assert user_after_refund["coins"] == 100
