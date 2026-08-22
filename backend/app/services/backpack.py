from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.backpack import BackpackItem, ItemType, ItemStatus, UsageAction, UsageHistory
from app.models.shop import ShopItem
from app.repositories.backpack import BackpackItemRepository, UsageHistoryRepository
from app.repositories.shop import ShopItemRepository


class BackpackService:
    def __init__(self, db: Session):
        self.db = db
        self.backpack_repo = BackpackItemRepository(db)
        self.history_repo = UsageHistoryRepository(db)
        self.shop_item_repo = ShopItemRepository(db)

    # --- Ownership check ---
    def get_item_for_user(self, item_id: UUID, user_id: UUID) -> BackpackItem:
        item = self.backpack_repo.get_by_id(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Backpack item not found")
        if item.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")
        return item

    # --- Core operations ---
    def add_item(
        self,
        user_id: UUID,
        shop_item_id: UUID,
        quantity: int = 1,
        item_type: ItemType = ItemType.CONSUMABLE,
        commit: bool = True,
    ) -> BackpackItem:
        """Add an item to the user's backpack. Increments quantity if already present.

        Args:
            commit: If True (default), commits the transaction immediately.
                    Pass False to defer the commit to the caller.
        """
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        shop_item = self.shop_item_repo.get_by_id(shop_item_id)
        if shop_item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")

        existing = self.backpack_repo.get_by_user_and_shop_item(user_id, shop_item_id)
        if existing:
            existing.quantity += quantity
            self._log_history_no_commit(user_id, existing.id, shop_item_id, UsageAction.ADD, quantity)
            if commit:
                self.db.commit()
                self.db.refresh(existing)
            return existing

        item_data = {
            "user_id": user_id,
            "shop_item_id": shop_item_id,
            "item_type": item_type,
            "status": ItemStatus.ACTIVE,
            "quantity": quantity,
        }
        item = self.backpack_repo._create_no_commit(item_data)
        self._log_history_no_commit(user_id, item.id, shop_item_id, UsageAction.ADD, quantity)
        if commit:
            self.db.commit()
            self.db.refresh(item)
        return item

    def use_item(self, item: BackpackItem, quantity: int = 1) -> BackpackItem:
        """Use a consumable item. Decrements quantity; deletes entry when quantity reaches 0."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if item.item_type != ItemType.CONSUMABLE:
            raise HTTPException(status_code=400, detail="Only consumable items can be used")

        if item.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity")

        item.quantity -= quantity
        self._log_history_no_commit(item.user_id, item.id, item.shop_item_id, UsageAction.USE, quantity)

        if item.quantity <= 0:
            self.db.delete(item)
            self.db.commit()
            return item

        self.db.commit()
        self.db.refresh(item)
        return item

    def equip_item(self, item: BackpackItem) -> BackpackItem:
        """Equip an item. Unequips other items of the same item_type."""
        if item.status == ItemStatus.EQUIPPED:
            raise HTTPException(status_code=400, detail="Item is already equipped")

        # Unequip other items of the same type
        equipped_items = self.backpack_repo.get_equipped_by_type(item.user_id, item.item_type)
        for equipped in equipped_items:
            equipped.status = ItemStatus.ACTIVE
            self._log_history_no_commit(
                item.user_id, equipped.id, equipped.shop_item_id, UsageAction.UNEQUIP
            )

        item.status = ItemStatus.EQUIPPED
        self._log_history_no_commit(item.user_id, item.id, item.shop_item_id, UsageAction.EQUIP)
        self.db.commit()
        self.db.refresh(item)
        return item

    def discard_item(self, item: BackpackItem, quantity: int = 1) -> BackpackItem:
        """Discard items. Deletes entry when quantity reaches 0.
        If the item is equipped, unequips it first."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if item.status == ItemStatus.EQUIPPED:
            item.status = ItemStatus.ACTIVE
            self._log_history_no_commit(
                item.user_id, item.id, item.shop_item_id, UsageAction.UNEQUIP
            )

        if item.quantity < quantity:
            raise HTTPException(status_code=400, detail="Insufficient quantity")

        item.quantity -= quantity
        self._log_history_no_commit(item.user_id, item.id, item.shop_item_id, UsageAction.DISCARD, quantity)

        if item.quantity <= 0:
            self.db.delete(item)
            self.db.commit()
            return item

        self.db.commit()
        self.db.refresh(item)
        return item

    # --- Queries ---
    def get_user_items(
        self, user_id: UUID, status: Optional[ItemStatus] = None
    ) -> List[BackpackItem]:
        return self.backpack_repo.get_by_user(user_id, status=status)

    def get_usage_history(self, user_id: UUID) -> List[UsageHistory]:
        return self.history_repo.get_by_user(user_id)

    def get_items_by_key(self, user_id: UUID, item_key: str, lock: bool = False) -> List[BackpackItem]:
        query = self.db.query(BackpackItem).join(
            ShopItem, ShopItem.id == BackpackItem.shop_item_id
        ).filter(
            BackpackItem.user_id == user_id,
            ShopItem.item_key == item_key,
            BackpackItem.status.in_((ItemStatus.ACTIVE, ItemStatus.EQUIPPED)),
            BackpackItem.quantity > 0,
        ).order_by(BackpackItem.id)
        if lock:
            query = query.with_for_update()
        return query.all()

    def consume_by_key(self, user_id: UUID, item_key: str, quantity: int) -> int:
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        if quantity == 0:
            return 0

        rows = self.get_items_by_key(user_id, item_key, lock=True)
        owned = sum(row.quantity for row in rows)
        if owned < quantity:
            raise PermissionError(
                f"TRIBULATION_PILL_INSUFFICIENT:{quantity}:{owned}"
            )

        remaining = quantity
        for row in rows:
            consumed = min(row.quantity, remaining)
            row.quantity -= consumed
            self._log_history_no_commit(
                user_id, row.id, row.shop_item_id, UsageAction.USE, consumed
            )
            remaining -= consumed
            if row.quantity <= 0:
                self.db.delete(row)
            if remaining == 0:
                break
        self.db.flush()
        return quantity

    def get_usage_history_with_names(
        self, user_id: UUID
    ) -> List[Tuple[UsageHistory, Optional[str]]]:
        """Return usage history enriched with shop item names via batch query."""
        history = self.history_repo.get_by_user(user_id)
        if not history:
            return []

        shop_item_ids = list({entry.shop_item_id for entry in history})
        shop_items = self.shop_item_repo.get_by_ids(shop_item_ids)
        name_map = {item.id: item.name for item in shop_items}

        return [(entry, name_map.get(entry.shop_item_id)) for entry in history]

    # --- Internal helpers ---
    def _resolve_item_type(self, category: Optional[str]) -> ItemType:
        """Map a shop item category to the backpack ItemType."""
        mapping = {
            "consumable": ItemType.CONSUMABLE,
            "gear": ItemType.GEAR,
            "weapon": ItemType.GEAR,
            "armor": ItemType.GEAR,
            "collectible": ItemType.COLLECTIBLE,
            "quest": ItemType.QUEST,
        }
        if category:
            return mapping.get(category.lower(), ItemType.CONSUMABLE)
        return ItemType.CONSUMABLE

    def _add_item_no_commit(
        self,
        user_id: UUID,
        shop_item_id: UUID,
        quantity: int = 1,
    ) -> BackpackItem:
        """Add an item to the backpack without committing. For use within
        multi-step operations managed by the caller. Resolves item type
        from the shop item's category."""
        shop_item = self.shop_item_repo.get_by_id(shop_item_id)
        if shop_item is None:
            raise HTTPException(status_code=404, detail="Shop item not found")
        item_type = self._resolve_item_type(shop_item.category)
        return self.add_item(user_id, shop_item_id, quantity, item_type, commit=False)

    def _log_history_no_commit(
        self,
        user_id: UUID,
        item_id: UUID,
        shop_item_id: UUID,
        action: UsageAction,
        quantity: int = 1,
    ) -> UsageHistory:
        history_data = {
            "user_id": user_id,
            "item_id": item_id,
            "shop_item_id": shop_item_id,
            "action": action,
            "quantity": quantity,
        }
        return self.history_repo._create_no_commit(history_data)
