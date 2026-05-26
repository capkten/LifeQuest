from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.backpack import BackpackItem, ItemStatus, UsageHistory, UsageAction
from app.repositories.base import BaseRepository


class BackpackItemRepository(BaseRepository[BackpackItem]):
    def __init__(self, db: Session):
        super().__init__(BackpackItem, db)

    def get_by_user(self, user_id: UUID, status: Optional[ItemStatus] = None) -> List[BackpackItem]:
        query = self.db.query(BackpackItem).filter(BackpackItem.user_id == user_id)
        if status is not None:
            query = query.filter(BackpackItem.status == status)
        return query.all()

    def get_by_user_and_shop_item(self, user_id: UUID, shop_item_id: UUID) -> Optional[BackpackItem]:
        return (
            self.db.query(BackpackItem)
            .filter(
                BackpackItem.user_id == user_id,
                BackpackItem.shop_item_id == shop_item_id,
            )
            .first()
        )

    def get_equipped_by_type(self, user_id: UUID, item_type: str) -> List[BackpackItem]:
        return (
            self.db.query(BackpackItem)
            .filter(
                BackpackItem.user_id == user_id,
                BackpackItem.item_type == item_type,
                BackpackItem.is_equipped == True,  # noqa: E712
            )
            .all()
        )

    def _create_no_commit(self, obj_in: dict) -> BackpackItem:
        db_obj = BackpackItem(**obj_in)
        self.db.add(db_obj)
        self.db.flush()
        return db_obj


class UsageHistoryRepository(BaseRepository[UsageHistory]):
    def __init__(self, db: Session):
        super().__init__(UsageHistory, db)

    def get_by_user(self, user_id: UUID) -> List[UsageHistory]:
        return (
            self.db.query(UsageHistory)
            .filter(UsageHistory.user_id == user_id)
            .all()
        )

    def get_by_item(self, item_id: UUID) -> List[UsageHistory]:
        return (
            self.db.query(UsageHistory)
            .filter(UsageHistory.item_id == item_id)
            .all()
        )

    def get_by_action(self, user_id: UUID, action: UsageAction) -> List[UsageHistory]:
        return (
            self.db.query(UsageHistory)
            .filter(
                UsageHistory.user_id == user_id,
                UsageHistory.action == action,
            )
            .all()
        )

    def _create_no_commit(self, obj_in: dict) -> UsageHistory:
        db_obj = UsageHistory(**obj_in)
        self.db.add(db_obj)
        self.db.flush()
        return db_obj
