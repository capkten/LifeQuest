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


def _create_shop_item(client, headers, coin_price=10, stock=10, category="consumable"):
    """Helper: create a shop item and return its id."""
    response = client.post(
        "/api/shop/items",
        json={
            "name": "Health Potion",
            "description": "Restores 50 HP",
            "category": category,
            "coin_price": coin_price,
            "stock": stock,
        },
        headers=headers,
    )
    return response.json()["id"]


def _earn_coins(client, headers, amount=100):
    """Helper: earn coins by completing a task."""
    task_response = client.post(
        "/api/todos/tasks",
        json={"title": "Earn coins", "coins_reward": amount, "exp_reward": 0},
        headers=headers,
    )
    task_id = task_response.json()["id"]
    client.post(f"/api/todos/tasks/{task_id}/complete", headers=headers)


def _purchase_item(client, headers, item_id, quantity=1):
    """Helper: purchase a shop item."""
    return client.post(
        "/api/shop/exchange",
        json={"item_id": item_id, "quantity": quantity},
        headers=headers,
    )


def test_get_backpack_items_empty(client):
    """New user should have an empty backpack."""
    headers = _register_and_login(client)

    response = client.get("/api/backpack/items", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_use_item(client):
    """Using a consumable item should decrement quantity and log usage history."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    # Purchase item (auto-adds to backpack)
    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    purchase_resp = _purchase_item(client, headers, item_id, quantity=2)
    assert purchase_resp.status_code == 200

    # Get backpack items
    items = client.get("/api/backpack/items", headers=headers).json()
    assert len(items) == 1
    backpack_item_id = items[0]["id"]
    assert items[0]["quantity"] == 2

    # Use 1 item
    use_response = client.post(
        f"/api/backpack/items/{backpack_item_id}/use?quantity=1",
        headers=headers,
    )
    assert use_response.status_code == 200
    data = use_response.json()
    assert data["quantity"] == 1
    assert data["status"] == "active"

    # Verify usage history was created
    history = client.get("/api/backpack/history", headers=headers).json()
    assert len(history) >= 1
    use_records = [h for h in history if h["action"] == "use"]
    assert len(use_records) == 1
    assert use_records[0]["quantity"] == 1
    assert use_records[0]["item_name"] == "Health Potion"


def test_use_item_removes_when_quantity_zero(client):
    """Using the last item should remove it from the backpack."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    _purchase_item(client, headers, item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]

    # Use the only item
    use_response = client.post(
        f"/api/backpack/items/{backpack_item_id}/use",
        headers=headers,
    )
    assert use_response.status_code == 200
    assert use_response.json()["quantity"] == 0

    # Backpack should be empty
    items_after = client.get("/api/backpack/items", headers=headers).json()
    assert len(items_after) == 0


def test_use_item_insufficient_quantity(client):
    """Cannot use more items than owned."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    _purchase_item(client, headers, item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]

    response = client.post(
        f"/api/backpack/items/{backpack_item_id}/use?quantity=5",
        headers=headers,
    )
    assert response.status_code == 400


def test_equip_item(client):
    """Equipping a gear item should set is_equipped=True."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    # Create and purchase a gear item
    gear_response = client.post(
        "/api/shop/items",
        json={
            "name": "Iron Sword",
            "description": "A sturdy sword",
            "category": "weapon",
            "coin_price": 10,
            "stock": 5,
        },
        headers=headers,
    )
    gear_shop_item_id = gear_response.json()["id"]
    _purchase_item(client, headers, gear_shop_item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers).json()
    assert len(items) == 1
    backpack_item_id = items[0]["id"]
    assert items[0]["is_equipped"] is False

    # Equip the item
    equip_response = client.post(
        f"/api/backpack/items/{backpack_item_id}/equip",
        headers=headers,
    )
    assert equip_response.status_code == 200
    data = equip_response.json()
    assert data["is_equipped"] is True
    assert data["status"] == "equipped"


def test_equip_item_already_equipped(client):
    """Cannot equip an already-equipped item."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    gear_response = client.post(
        "/api/shop/items",
        json={
            "name": "Iron Sword",
            "description": "A sturdy sword",
            "category": "weapon",
            "coin_price": 10,
            "stock": 5,
        },
        headers=headers,
    )
    gear_shop_item_id = gear_response.json()["id"]
    _purchase_item(client, headers, gear_shop_item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]

    # Equip once
    client.post(f"/api/backpack/items/{backpack_item_id}/equip", headers=headers)

    # Try to equip again
    response = client.post(
        f"/api/backpack/items/{backpack_item_id}/equip",
        headers=headers,
    )
    assert response.status_code == 400


def test_discard_item(client):
    """Discarding an item should decrement its quantity."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    _purchase_item(client, headers, item_id, quantity=3)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]
    assert items[0]["quantity"] == 3

    # Discard 1
    discard_response = client.post(
        f"/api/backpack/items/{backpack_item_id}/discard?quantity=1",
        headers=headers,
    )
    assert discard_response.status_code == 200
    assert discard_response.json()["quantity"] == 2

    # Discard remaining 2
    discard_response2 = client.post(
        f"/api/backpack/items/{backpack_item_id}/discard?quantity=2",
        headers=headers,
    )
    assert discard_response2.status_code == 200
    assert discard_response2.json()["quantity"] == 0

    # Should be removed from backpack
    items_after = client.get("/api/backpack/items", headers=headers).json()
    assert len(items_after) == 0


def test_discard_item_insufficient_quantity(client):
    """Cannot discard more items than owned."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    _purchase_item(client, headers, item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]

    response = client.post(
        f"/api/backpack/items/{backpack_item_id}/discard?quantity=5",
        headers=headers,
    )
    assert response.status_code == 400


def test_backpack_ownership_check(client):
    """Users cannot access another user's backpack items."""
    headers_owner = _register_and_login(client, "owner", "owner@example.com")
    headers_other = _register_and_login(client, "other", "other@example.com")

    _earn_coins(client, headers_owner, amount=100)
    item_id = _create_shop_item(client, headers_owner, coin_price=10, stock=5)
    _purchase_item(client, headers_owner, item_id, quantity=1)

    items = client.get("/api/backpack/items", headers=headers_owner).json()
    backpack_item_id = items[0]["id"]

    # Other user should not be able to use the item
    use_response = client.post(
        f"/api/backpack/items/{backpack_item_id}/use",
        headers=headers_other,
    )
    assert use_response.status_code == 403


def test_backpack_item_not_found(client):
    """Requesting a non-existent backpack item should return 404."""
    headers = _register_and_login(client)

    import uuid
    fake_id = str(uuid.uuid4())
    response = client.post(
        f"/api/backpack/items/{fake_id}/use",
        headers=headers,
    )
    assert response.status_code == 404


def test_usage_history_with_item_name(client):
    """Usage history responses should include item_name from the shop item."""
    headers = _register_and_login(client)
    _earn_coins(client, headers, amount=100)

    item_id = _create_shop_item(client, headers, coin_price=10, stock=5)
    _purchase_item(client, headers, item_id, quantity=2)

    items = client.get("/api/backpack/items", headers=headers).json()
    backpack_item_id = items[0]["id"]

    # Use an item to generate history
    client.post(f"/api/backpack/items/{backpack_item_id}/use?quantity=1", headers=headers)

    history = client.get("/api/backpack/history", headers=headers).json()
    assert len(history) >= 2  # add + use

    for entry in history:
        assert "item_name" in entry
        assert entry["item_name"] == "Health Potion"
