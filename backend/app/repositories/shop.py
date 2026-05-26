from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.shop import ShopItem, ExchangeHistory, ExchangeStatus
from app.repositories.base import BaseRepository


class ShopItemRepository(BaseRepository[ShopItem]):
    def __init__(self, db: Session):
        super().__init__(ShopItem, db)

    def get_active_items(self, skip: int = 0, limit: int = 100) -> List[ShopItem]:
        return (
            self.db.query(ShopItem)
            .filter(ShopItem.is_active == 1)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(self, category: str) -> List[ShopItem]:
        return (
            self.db.query(ShopItem)
            .filter(ShopItem.category == category, ShopItem.is_active == 1)
            .all()
        )

    def get_by_creator(self, creator_id: UUID) -> List[ShopItem]:
        return (
            self.db.query(ShopItem)
            .filter(ShopItem.created_by == creator_id)
            .all()
        )


class ExchangeHistoryRepository(BaseRepository[ExchangeHistory]):
    def __init__(self, db: Session):
        super().__init__(ExchangeHistory, db)

    def get_by_user(self, user_id: UUID) -> List[ExchangeHistory]:
        return (
            self.db.query(ExchangeHistory)
            .filter(ExchangeHistory.user_id == user_id)
            .all()
        )

    def get_by_status(self, user_id: UUID, status: ExchangeStatus) -> List[ExchangeHistory]:
        return (
            self.db.query(ExchangeHistory)
            .filter(
                ExchangeHistory.user_id == user_id,
                ExchangeHistory.status == status.value,
            )
            .all()
        )
