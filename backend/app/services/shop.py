from typing import List
import logging
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.models.shop import ShopItem, ExchangeHistory, ExchangeStatus
from app.models.coin_transaction import CoinSource, CoinType
from app.repositories.shop import ShopItemRepository, ExchangeHistoryRepository
from app.repositories.coin_transaction import CoinTransactionRepository
from app.repositories.user import UserRepository
from app.schemas.shop import ShopItemCreate, ShopItemUpdate, ExchangeHistoryCreate
from app.services.achievement import AchievementService
from app.services.backpack import BackpackService
from app.models.backpack import BackpackItem, ItemStatus, UsageAction
from app.services.transaction import rollback_on_error


class ShopService:
    logger = logging.getLogger(__name__)

    SYSTEM_ITEMS = {
        "tribulation-pill": {
            "name": "渡劫丹",
            "description": "渡劫时稳定心神、提升成功概率的消耗品。",
            "icon": None,
            "category": "consumable",
            "coin_price": 100,
            "stock": -1,
            "is_active": True,
        },
    }

    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ShopItemRepository(db)
        self.exchange_repo = ExchangeHistoryRepository(db)
        self.coin_repo = CoinTransactionRepository(db)
        self.user_repo = UserRepository(db)
        self.achievement_service = AchievementService(db)

    @classmethod
    def seed_system_items(cls, db: Session) -> List[ShopItem]:
        """Create or restore authoritative system products idempotently."""
        seeded = []
        for item_key, values in cls.SYSTEM_ITEMS.items():
            item = db.query(ShopItem).filter(ShopItem.item_key == item_key).one_or_none()
            if item is None:
                # Pre-key installations stored system rows without item_key.
                item = db.query(ShopItem).filter(
                    ShopItem.item_key.is_(None),
                    ShopItem.created_by.is_(None),
                    ShopItem.name == values["name"],
                ).order_by(ShopItem.created_at, ShopItem.id).first()
            if item is None:
                item = ShopItem(item_key=item_key, created_by=None, **values)
                db.add(item)
            else:
                item.item_key = item_key
                item.created_by = None
                for field, value in values.items():
                    setattr(item, field, value)
            seeded.append(item)
        db.commit()
        return seeded

    # --- Ownership checks ---
    def get_item_for_user(self, item_id: UUID, user_id: UUID) -> ShopItem:
        item = self.item_repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        if item.created_by is not None and item.created_by != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return item

    @classmethod
    def _is_system_item(cls, item: ShopItem) -> bool:
        return item.item_key in cls.SYSTEM_ITEMS

    def get_mutable_item_for_user(self, item_id: UUID, user_id: UUID) -> ShopItem:
        item = self.get_item_for_user(item_id, user_id)
        if self._is_system_item(item):
            raise HTTPException(status_code=403, detail="System shop items are immutable")
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
        if self._is_system_item(item):
            raise HTTPException(status_code=403, detail="System shop items are immutable")
        update_data = item_in.model_dump(exclude_unset=True)
        return self.item_repo.update(item, update_data)

    def delete_item(self, item_id: UUID, user_id: UUID) -> bool:
        """Delete a shop item, verifying ownership first."""
        self.get_mutable_item_for_user(item_id, user_id)
        return self.item_repo.delete(item_id)

    # --- Exchange (purchase) operations ---
    @staticmethod
    def _coin_source_id(exchange_id: UUID, action: str) -> str:
        if action == "purchase":
            return str(exchange_id)
        return str(uuid5(NAMESPACE_URL, f"lifequest:shop:{action}:{exchange_id}"))

    @rollback_on_error
    def purchase_item(self, user_id: UUID, exchange_in: ExchangeHistoryCreate) -> ExchangeHistory:
        self.user_repo.lock(user_id)
        # The price, active flag, and stock decision must come from the same
        # locked row used for this purchase.
        item = self.item_repo.get_for_update(exchange_in.item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        self.db.refresh(item)
        if not item.is_active:
            raise HTTPException(status_code=400, detail="Item is not available")

        # Only decrement stock for finite-stock items (stock >= 0)
        if item.stock >= 0:
            if not self.item_repo.decrement_stock_atomic(exchange_in.item_id, exchange_in.quantity):
                raise HTTPException(status_code=400, detail="Item is out of stock")
        total_cost = item.coin_price * exchange_in.quantity

        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        self.user_repo.debit_coins(user_id, total_cost)
        self.db.refresh(user)

        # Create exchange record (no commit -- we commit everything at once below)
        exchange_data = {
            "user_id": user_id,
            "item_id": item.id,
            "quantity": exchange_in.quantity,
            "total_cost": total_cost,
            "status": ExchangeStatus.COMPLETED,
        }
        exchange = self.exchange_repo._create_no_commit(exchange_data)
        self.coin_repo._create_no_commit({
            "user_id": user_id,
            "amount": total_cost,
            "type": CoinType.SPEND,
            "source": CoinSource.SHOP.value,
            "source_id": self._coin_source_id(exchange.id, "purchase"),
            "description": f"商城购买：{item.name}",
        })

        # Add purchased items to user's backpack (defer commit)
        backpack_service = BackpackService(self.db)
        backpack_service._add_item_no_commit(user_id, item.id, quantity=exchange_in.quantity)

        # Flush and refresh before commit so an exceptional refresh is still
        # covered by the all-or-nothing transaction.
        self.db.flush()
        self.db.refresh(exchange)
        self.db.commit()

        # Check coins_spent and transaction_count achievements
        try:
            self.achievement_service.check_coins_spent(user_id)
            self.achievement_service.check_transactions(user_id)
        except Exception:
            self.logger.exception("Shop achievement processing failed for user %s", user_id)

        return exchange

    def get_user_exchanges(self, user_id: UUID) -> List[ExchangeHistory]:
        return self.exchange_repo.get_by_user(user_id)

    @rollback_on_error
    def refund_exchange(self, exchange: ExchangeHistory) -> ExchangeHistory:
        self.user_repo.lock(exchange.user_id)
        self.db.refresh(exchange)
        changed = self.db.execute(update(ExchangeHistory).where(
            ExchangeHistory.id == exchange.id,
            ExchangeHistory.status == ExchangeStatus.COMPLETED.value,
        ).values(status=ExchangeStatus.REFUNDED.value)).rowcount
        if not changed:
            raise HTTPException(status_code=400, detail="Can only refund completed exchanges")

        backpack_service = BackpackService(self.db)
        rows = self.db.query(BackpackItem).filter(
            BackpackItem.user_id == exchange.user_id,
            BackpackItem.shop_item_id == exchange.item_id,
            BackpackItem.status == ItemStatus.ACTIVE,
        ).order_by(BackpackItem.id).populate_existing().all()
        remaining = exchange.quantity
        for item in rows:
            quantity = min(item.quantity, remaining)
            if quantity <= 0:
                continue
            changed = self.db.execute(update(BackpackItem).where(
                BackpackItem.id == item.id,
                BackpackItem.status == ItemStatus.ACTIVE,
                BackpackItem.quantity >= quantity,
            ).values(quantity=BackpackItem.quantity - quantity)).rowcount
            if not changed:
                raise HTTPException(status_code=400, detail="Insufficient refundable items")
            backpack_service._log_history_no_commit(
                exchange.user_id, item.id, item.shop_item_id, UsageAction.REFUND, quantity
            )
            self.db.refresh(item)
            if item.quantity == 0:
                self.db.delete(item)
            remaining -= quantity
            if remaining == 0:
                break
        if remaining:
            raise HTTPException(status_code=400, detail="Insufficient refundable items; unequip or return unused items first")

        user = self.user_repo.get_by_id(exchange.user_id)

        # Refund coins (do not count as earned)
        if user:
            self.user_repo._refund_coins_no_commit(user, exchange.total_cost)

        # Atomically restore stock
        self.item_repo.restore_stock_atomic(exchange.item_id, exchange.quantity)

        self.coin_repo._create_no_commit({
            "user_id": exchange.user_id,
            "amount": exchange.total_cost,
            "type": CoinType.EARN,
            "source": CoinSource.SHOP.value,
            "source_id": self._coin_source_id(exchange.id, "refund"),
            "description": "商城退款",
        })

        exchange.status = ExchangeStatus.REFUNDED
        self.db.flush()
        self.exchange_repo.db.refresh(exchange)
        self.exchange_repo.db.commit()
        return exchange
