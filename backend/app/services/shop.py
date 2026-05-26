from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.shop import ShopItem, ExchangeHistory, ExchangeStatus
from app.repositories.shop import ShopItemRepository, ExchangeHistoryRepository
from app.repositories.user import UserRepository
from app.schemas.shop import ShopItemCreate, ShopItemUpdate, ExchangeHistoryCreate
from app.services.backpack import BackpackService


class ShopService:
    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ShopItemRepository(db)
        self.exchange_repo = ExchangeHistoryRepository(db)
        self.user_repo = UserRepository(db)

    # --- Ownership checks ---
    def get_item_for_user(self, item_id: UUID, user_id: UUID) -> ShopItem:
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        if item.created_by is not None and item.created_by != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return item

    def get_exchange_for_user(self, exchange_id: UUID, user_id: UUID) -> ExchangeHistory:
        exchange = self.exchange_repo.get_by_id(exchange_id)
        if exchange is None:
            raise HTTPException(status_code=404, detail="Exchange not found")
        if exchange.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return exchange

    # --- Shop item CRUD ---
    def create_item(self, item_in: ShopItemCreate, creator_id: UUID) -> ShopItem:
        data = item_in.model_dump()
        data["created_by"] = creator_id
        return self.item_repo.create(data)

    def get_items(self, skip: int = 0, limit: int = 100) -> List[ShopItem]:
        return self.item_repo.get_active_items(skip=skip, limit=limit)

    def get_item(self, item_id: UUID) -> ShopItem:
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        return item

    def update_item(self, item: ShopItem, item_in: ShopItemUpdate) -> ShopItem:
        update_data = item_in.model_dump(exclude_unset=True)
        return self.item_repo.update(item, update_data)

    def delete_item(self, item_id: UUID, user_id: UUID) -> bool:
        """Delete a shop item, verifying ownership first."""
        self.get_item_for_user(item_id, user_id)
        return self.item_repo.delete(item_id)

    # --- Exchange (purchase) operations ---
    def purchase_item(self, user_id: UUID, exchange_in: ExchangeHistoryCreate) -> ExchangeHistory:
        # Atomic stock decrement: only succeeds if stock >= quantity
        if not self.item_repo.decrement_stock_atomic(exchange_in.item_id, exchange_in.quantity):
            # Check whether item exists / is active or simply out of stock
            item = self.item_repo.get_by_id(exchange_in.item_id)
            if item is None:
                raise HTTPException(status_code=404, detail="Shop item not found")
            if not item.is_active:
                raise HTTPException(status_code=400, detail="Item is not available")
            raise HTTPException(status_code=400, detail="Item is out of stock")

        # Item exists and is active; fetch for cost calculation
        item = self.item_repo.get_by_id(exchange_in.item_id)
        total_cost = item.coin_price * exchange_in.quantity

        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        if user.coins < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient coins")

        # Deduct coins (no commit)
        self.user_repo._update_coins_no_commit(user, -total_cost)

        # Create exchange record (single commit for everything)
        exchange_data = {
            "user_id": user_id,
            "item_id": item.id,
            "quantity": exchange_in.quantity,
            "total_cost": total_cost,
            "status": ExchangeStatus.COMPLETED,
        }
        exchange = self.exchange_repo.create(exchange_data)

        # Add purchased items to user's backpack
        backpack_service = BackpackService(self.db)
        backpack_service.add_item(user_id, item.id, quantity=exchange_in.quantity)

        return exchange

    def get_user_exchanges(self, user_id: UUID) -> List[ExchangeHistory]:
        return self.exchange_repo.get_by_user(user_id)

    def refund_exchange(self, exchange: ExchangeHistory) -> ExchangeHistory:
        if exchange.status != ExchangeStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="Can only refund completed exchanges")

        user = self.user_repo.get_by_id(exchange.user_id)

        # Refund coins
        if user:
            self.user_repo._update_coins_no_commit(user, exchange.total_cost)

        # Atomically restore stock
        self.item_repo.restore_stock_atomic(exchange.item_id, exchange.quantity)

        exchange.status = ExchangeStatus.REFUNDED
        self.exchange_repo.db.commit()
        self.exchange_repo.db.refresh(exchange)
        return exchange
